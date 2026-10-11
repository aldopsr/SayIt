"""Perangkaian seluruh modul SayIt (PRD 7): foto, pertanyaan suara, jawaban suara.

`Pipeline` menyimpan keadaan satu sesi: foto terakhir yang lolos quality gate,
jawaban terakhir (untuk ULANGI), dan posisi bacaan dokumen (untuk LANJUT).
Seluruh komponen berat bisa dioper dari luar, sehingga pipeline bisa diuji
tanpa mikrofon, tanpa model, dan tanpa internet.

Urutan pada `ask()`:
1. Router menentukan intent dari transkrip.
2. Intent kendali (ULANGI, LANJUT, FOTO_BARU, BANTUAN) dijawab langsung.
3. Intent tugas butuh foto. Tanpa foto, pengguna diminta memotret lebih dulu.
4. Modul yang sesuai dijalankan, jawabannya disimpan untuk ULANGI.

Quality gate dijalankan saat foto masuk, bukan saat pertanyaan datang, supaya
pengguna tunanetra langsung tahu fotonya buram dan bisa mengulang saat itu juga.
"""
from __future__ import annotations

import copy
import time
from dataclasses import dataclass, field
from datetime import date
from typing import Any, Callable

import numpy as np

from sayit.intent import keywords as K
from sayit.intent.router import IntentRouter
from sayit.response.templates import Utterance, fixed, to_plain_text
from sayit.vision import quality_gate as qg
from sayit.vision.document import DocumentReader, chunk_utterance
from sayit.vision.expiry import ExpiryReader, expiry_utterance
from sayit.vision.money import MoneyDetector, money_utterance


@dataclass
class Turn:
    """Satu giliran percakapan: apa yang diucapkan balik, dan mengapa."""
    utterance: Utterance
    intent: str = ""
    reason: str = ""                                    # penjelasan untuk layar dan log
    notes: dict[str, Any] = field(default_factory=dict)

    @property
    def text(self) -> str:
        return to_plain_text(self.utterance)


class Pipeline:
    def __init__(self, cfg: dict, transcriber=None, money: MoneyDetector | None = None,
                 ocr: DocumentReader | None = None, expiry: ExpiryReader | None = None,
                 ocr_expiry: DocumentReader | None = None,
                 router: IntentRouter | None = None, today: Callable[[], date] = date.today):
        self.cfg = cfg
        self.p = cfg.get("pipeline", {})
        self.router = router or IntentRouter.from_config(cfg)
        self.transcriber = transcriber
        self.money = money or MoneyDetector(cfg)
        self.ocr = ocr or DocumentReader(cfg)
        # Modul kedaluwarsa boleh memakai mesin OCR yang BERBEDA dari modul dokumen
        # (`vision.expiry.engine`). Dipilih 02-10 setelah ablasi: PaddleOCR menaikkan
        # akurasi kedaluwarsa 44% -> 81%, tetapi membuat pembacaan dokumen menjadi
        # 42 detik per halaman - jauh di atas NFR-01. Jadi dokumen tetap EasyOCR.
        # Bila mesinnya sama, satu pembaca dipakai bersama: memuat dua kali memakan
        # 4 detik dan memori dua kali lipat.
        self.ocr_expiry = ocr_expiry or self._ocr_untuk_kedaluwarsa()
        self.expiry = expiry or ExpiryReader(cfg, ocr=self.ocr_expiry)
        self._today = today

        self.photo: np.ndarray | None = None
        self.last_utterance: Utterance | None = None
        self.document = None                            # DocumentResult terakhir
        self.chunk_index = 0
        self.status: dict[str, str] = {}                # hasil load() per modul

    def _ocr_untuk_kedaluwarsa(self) -> DocumentReader:
        """Pembaca OCR untuk modul kedaluwarsa, mesinnya bisa berbeda dari dokumen.

        Tes yang ingin menghindari pemuatan mesin kedua cukup mengoper `ocr_expiry=`
        atau `expiry=`; keduanya mendahului pembuatan otomatis di sini.
        """
        mesin = self.cfg["vision"]["expiry"].get("engine")
        if not mesin or mesin == self.cfg["vision"]["document"].get("engine", "easyocr"):
            return self.ocr
        cfg_exp = copy.deepcopy(self.cfg)
        cfg_exp["vision"]["document"]["engine"] = mesin
        return DocumentReader(cfg_exp)

    # ------------------------------------------------------------------ pemuatan

    def load(self, strict: bool = False) -> dict[str, str]:
        """Muat semua model sekali di awal. Kegagalan satu modul tidak mematikan yang lain.

        Anggota tim yang belum menyalin `models/best_money.pt` tetap bisa
        mendemokan modul dokumen. Status tiap modul dikembalikan apa adanya.
        """
        bagian = [("stt", self.transcriber.load if self.transcriber else None),
                  ("money", self.money.load),
                  ("ocr", self.ocr.load)]
        if self.ocr_expiry is not self.ocr:
            bagian.append(("ocr_kedaluwarsa", self.ocr_expiry.load))
        for nama, muat in bagian:
            if muat is None:
                self.status[nama] = "tidak dipasang"
                continue
            t = time.perf_counter()
            try:
                muat()
                self.status[nama] = f"siap ({time.perf_counter() - t:.1f} s)"
            except Exception as e:                      # noqa: BLE001 - status dilaporkan, bukan ditelan
                self.status[nama] = f"gagal: {e}"
                if strict:
                    raise
        # zona kedaluwarsa memang boleh belum ada; itu bukan kegagalan
        self.status["zone"] = "siap" if self.expiry.zones.available else "bobot belum ada, jalur cadangan"
        return self.status

    def _ready(self, nama: str) -> bool:
        return self.status.get(nama, "siap").startswith("siap")

    # ------------------------------------------------------------------ foto

    def set_photo(self, image: np.ndarray) -> Turn:
        """Terima foto baru. Foto yang tidak layak tidak disimpan."""
        if image is None or image.size == 0:
            raise ValueError("Citra kosong.")
        if not self.p.get("quality_gate_on_photo", True):
            self.photo = image
            return self._jawab(fixed("foto_diambil"), "FOTO", "quality gate dimatikan")

        laporan = qg.check_quality(image, self.cfg)
        if not laporan.ok:
            masalah = laporan.main_issue
            return self._jawab(qg.quality_response(laporan), "FOTO",
                               f"foto ditolak: {masalah.kind}",
                               {"quality": laporan.metrics, "issues": laporan.kinds})

        self.photo = image
        self.document = None                            # foto baru membatalkan bacaan lama
        self.chunk_index = 0
        return self._jawab(fixed("foto_diambil"), "FOTO", "foto layak",
                           {"quality": laporan.metrics})

    @property
    def has_photo(self) -> bool:
        return self.photo is not None

    # ------------------------------------------------------------------ pertanyaan

    def listen(self, audio: np.ndarray, sr: int | None = None,
               on_progress: Callable[[Utterance], None] | None = None) -> Turn:
        """Dari rekaman suara ke jawaban. Transkrip kosong dijawab minta ulang."""
        if self.transcriber is None:
            return self._jawab(fixed("modul_belum_siap"), K.TIDAK_DIKENALI, "STT tidak tersedia")
        sr = sr or self.cfg["audio"]["sample_rate"]
        hasil = self.transcriber.transcribe(audio, sr=sr)
        if hasil.empty:
            return self._jawab(fixed("suara_tidak_jelas"), K.TIDAK_DIKENALI,
                               hasil.reason or "transkrip kosong", {"stt_s": hasil.elapsed_s})
        giliran = self.ask(hasil.text, on_progress=on_progress)
        giliran.notes["transcript"] = hasil.text
        giliran.notes["stt_s"] = hasil.elapsed_s
        return giliran

    def ask(self, text: str, on_progress: Callable[[Utterance], None] | None = None) -> Turn:
        """Dari transkrip ke jawaban."""
        rute = self.router.route(text)
        intent = rute.intent
        catatan = {"scores": rute.scores, "matched": rute.matched}

        if intent == K.TIDAK_DIKENALI:
            return self._jawab(fixed("tidak_mengerti"), intent, "tidak ada intent yang cukup kuat", catatan)
        if intent == K.BANTUAN:
            return self._jawab(fixed("menu_bantuan"), intent, "menu bantuan", catatan)
        if intent == K.ULANGI:
            return self._ulangi(catatan)
        if intent == K.FOTO_BARU:
            self.photo = None
            self.document = None
            self.chunk_index = 0
            return self._jawab(fixed("silakan_foto"), intent, "foto dibuang atas permintaan", catatan)
        if intent == K.KELUAR:
            # Web tidak bisa menutup tabnya sendiri; klien yang mengembalikan
            # tampilan ke layar sambutan setelah mendengar ini.
            self.photo = None
            self.document = None
            self.chunk_index = 0
            return self._jawab(fixed("sampai_jumpa"), intent, "pengguna mengakhiri", catatan)
        if intent == K.LANJUT:
            return self._lanjut(catatan)

        if not self.has_photo:
            return self._jawab(fixed("belum_ada_foto"), intent, "intent tugas tanpa foto", catatan)

        if on_progress is not None and intent in (self.p.get("slow_intents") or []):
            on_progress(fixed("sedang_memproses"))

        if intent == K.UANG:
            return self._uang(catatan)
        if intent == K.BACA:
            return self._baca(catatan)
        if intent == K.KEDALUWARSA:
            return self._kedaluwarsa(catatan)
        raise ValueError(f"Intent tidak tertangani: {intent!r}")   # pengaman bila keywords bertambah

    # ------------------------------------------------------------------ intent kendali

    def _ulangi(self, catatan: dict) -> Turn:
        if self.last_utterance is None:
            return self._jawab(fixed("tidak_ada_ulangan"), K.ULANGI, "belum ada jawaban", catatan)
        # sengaja tidak disimpan ulang: mengulang tidak mengubah "jawaban terakhir"
        return Turn(self.last_utterance, K.ULANGI, "mengulang jawaban terakhir", catatan)

    def _lanjut(self, catatan: dict) -> Turn:
        if self.document is None:
            return self._jawab(fixed("tidak_ada_lanjutan"), K.LANJUT, "belum ada bacaan", catatan)
        self.chunk_index += 1
        catatan["chunk"] = self.chunk_index
        catatan["total_chunks"] = self.document.total_chunks
        if self.chunk_index >= self.document.total_chunks:
            self.chunk_index = self.document.total_chunks      # jangan melewati ujung
            return self._jawab(fixed("tidak_ada_lanjutan"), K.LANJUT, "bacaan sudah habis", catatan)
        return self._jawab(chunk_utterance(self.document, self.chunk_index), K.LANJUT,
                           f"potongan {self.chunk_index + 1} dari {self.document.total_chunks}", catatan)

    # ------------------------------------------------------------------ intent tugas

    def _gagal_modul(self, nama: str, e: Exception, intent: str, catatan: dict) -> Turn:
        """Bobot yang hilang dijawab dengan pesan, bukan dengan aplikasi yang mati saat demo."""
        self.status[nama] = f"gagal: {e}"
        return self._jawab(fixed("modul_belum_siap"), intent, str(e), catatan)

    def _uang(self, catatan: dict) -> Turn:
        if not self._ready("money"):
            return self._jawab(fixed("modul_belum_siap"), K.UANG, self.status.get("money", ""), catatan)
        try:
            hasil = self.money.detect(self.photo)
        except FileNotFoundError as e:
            return self._gagal_modul("money", e, K.UANG, catatan)
        catatan.update(hasil.notes)
        alasan = hasil.reason or f"{hasil.sheets} lembar, total {hasil.total}"
        return self._jawab(money_utterance(hasil), K.UANG, alasan, catatan)

    def _baca(self, catatan: dict) -> Turn:
        if not self._ready("ocr"):
            return self._jawab(fixed("modul_belum_siap"), K.BACA, self.status.get("ocr", ""), catatan)
        try:
            self.document = self.ocr.read(self.photo)
        except FileNotFoundError as e:
            return self._gagal_modul("ocr", e, K.BACA, catatan)
        self.chunk_index = 0
        catatan.update(self.document.notes)
        alasan = (f"{self.document.total_chunks} potongan" if self.document.found
                  else "tidak ada tulisan terbaca")
        return self._jawab(chunk_utterance(self.document, 0), K.BACA, alasan, catatan)

    def _kedaluwarsa(self, catatan: dict) -> Turn:
        if not self._ready("ocr"):
            return self._jawab(fixed("modul_belum_siap"), K.KEDALUWARSA, self.status.get("ocr", ""), catatan)
        hari_ini = self._today()
        try:
            hasil = self.expiry.read(self.photo, today=hari_ini)
        except FileNotFoundError as e:
            return self._gagal_modul("ocr", e, K.KEDALUWARSA, catatan)
        catatan.update(hasil.notes)
        catatan["source"] = hasil.source
        alasan = f"{hasil.source}: {hasil.date.reason}"
        return self._jawab(expiry_utterance(hasil, hari_ini), K.KEDALUWARSA, alasan, catatan)

    # ------------------------------------------------------------------ utilitas

    def _jawab(self, utt: Utterance, intent: str, reason: str = "", catatan: dict | None = None) -> Turn:
        self.last_utterance = utt
        return Turn(utt, intent, reason, catatan or {})
