"""Modul kedaluwarsa (PRD 8.8): dari foto kemasan menjadi tanggal yang dibacakan.

Alur PRD 8.8:
1. YOLOv8 mendeteksi zona `expired_date_zone`.
2. Crop dengan margin 10%.
3. Pra-pemrosesan crop (rangkaian `kedaluwarsa`: upscale, CLAHE, binarisasi, morfologi).
4. OCR pada crop. Bila gagal, ulangi tanpa binarisasi.
5. Parser tanggal (`sayit/vision/date_parser.py`).
6. Bila zona tidak terdeteksi: OCR seluruh gambar lalu parser tanggal (FR-12),
   dan hasilnya dinyatakan kurang pasti.
7. Di luar PRD: bila seluruh alur di atas tidak menemukan tanggal, alur itu
   diulang pada foto yang diputar (`expiry.rotate_retry`). Penambahan ini
   berasal dari temuan uji: foto kemasan sering terpotret terbalik atau miring
   90 derajat, dan pengguna tunanetra tidak punya cara memeriksanya sendiri.

KEADAAN SEKARANG: bobot deteksi zona belum ada karena datasetnya belum dibuat.
Selama `models/best_zone.pt` tidak ditemukan, langkah 1-3 dilewati dan modul
langsung memakai jalur cadangan langkah 6. Itu bukan kegagalan, melainkan mode
kerja yang disengaja, dan selalu tercatat di `ExpiryResult.source`.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field, replace
from datetime import date
from typing import Any, Callable, Sequence

import cv2
import numpy as np

from sayit.config import project_path
from sayit.response.templates import Utterance
from sayit.vision import preprocess as pre
from sayit.vision.date_parser import DateParseResult, expiry_utterance as _date_utterance, parse_expiry
from sayit.vision.document import (DocumentReader, TextBox, compose_text,
                                   filter_by_score, rotate_image)
from sayit.vision.money import as_float_array

Box = tuple[float, float, float, float]

SOURCE_ZONE = "zona"
SOURCE_FULL = "seluruh gambar"


@dataclass(frozen=True)
class Zone:
    score: float
    box: Box
    # Kosong berarti modelnya tidak memberi nama kelas yang bisa dipakai - itu
    # keadaan model 1 kelas yang terpasang sekarang (`expired_date_zone`), dan
    # seluruh perilaku lama bergantung pada kolom ini boleh kosong.
    cls: str = ""


@dataclass
class ExpiryResult:
    date: DateParseResult = field(default_factory=DateParseResult)
    zone: Zone | None = None
    source: str = SOURCE_FULL
    notes: dict[str, Any] = field(default_factory=dict)

    @property
    def found(self) -> bool:
        return self.date.found

    @property
    def confident(self) -> bool:
        """Jalur cadangan tidak pernah dinyatakan yakin (PRD 8.8 langkah 6)."""
        return self.date.confident and self.source == SOURCE_ZONE


# --------------------------------------------------------------------------- rotasi

# `rotate_image` pindah ke `vision/document.py` (31-10) karena modul dokumen juga
# memutar seluruh gambar. Namanya tetap diekspor dari sini supaya pemanggil lama
# dan tesnya tidak perlu berubah.


# --------------------------------------------------------------------------- crop

def crop_with_margin(image: np.ndarray, box: Box, margin_ratio: float) -> np.ndarray:
    """Potong kotak dengan margin, dipotong lagi agar tidak keluar dari gambar.

    Margin dihitung dari sisi kotak, bukan dari gambar, supaya zona kecil tetap
    mendapat ruang napas yang sebanding.
    """
    h, w = image.shape[:2]
    x1, y1, x2, y2 = box
    mx = (x2 - x1) * margin_ratio
    my = (y2 - y1) * margin_ratio
    kx1 = max(0, int(round(x1 - mx)))
    ky1 = max(0, int(round(y1 - my)))
    kx2 = min(w, int(round(x2 + mx)))
    ky2 = min(h, int(round(y2 + my)))
    if kx2 <= kx1 or ky2 <= ky1:
        raise ValueError(f"Kotak zona di luar gambar: {box}")
    return image[ky1:ky2, kx1:kx2]


# --------------------------------------------------------------------------- deteksi zona

def extract_zones(results) -> list[Zone]:
    """Ubah hasil ultralytics menjadi daftar Zone, beserta NAMA KELASNYA bila ada.

    Model yang terpasang sekarang hanya punya satu kelas (`expired_date_zone`),
    jadi namanya tidak membedakan apa pun dan `Zone.cls` boleh kosong. Nama kelas
    mulai berguna pada model 4 kelas (`date` / `code` / `due` / `prod`) yang
    memungkinkan wilayah KODE PRODUKSI ditolak sebelum OCR - akar jawaban salah
    `chees`, yang tidak bisa diperbaiki dari sisi parser karena OCR tidak pernah
    membaca labelnya (diukur 20-11).

    Dibuat tahan model lama: bila `names` tidak ada atau indeksnya tidak dikenal,
    `cls` kosong dan `pick_zone` kembali ke perilaku "ambil skor tertinggi".
    """
    if not results:
        return []
    boxes = getattr(results[0], "boxes", None)
    if boxes is None:
        return []
    xyxy = as_float_array(boxes.xyxy).reshape(-1, 4)
    conf = as_float_array(boxes.conf).ravel()
    if xyxy.shape[0] == 0:
        return []
    nama = getattr(results[0], "names", None) or {}
    idx = as_float_array(getattr(boxes, "cls", [])).ravel() if hasattr(boxes, "cls") else []
    kelas = [str(nama.get(int(i), "")).strip().lower() for i in idx] if len(idx) else []
    return [Zone(score=float(s), box=(float(k[0]), float(k[1]), float(k[2]), float(k[3])),
                 cls=kelas[i] if i < len(kelas) else "")
            for i, (k, s) in enumerate(zip(xyxy, conf))]


def pick_zone(zones: Sequence[Zone], score_min: float,
              kelas_tanggal: Sequence[str] = (), kelas_ditolak: Sequence[str] = ()) -> Zone | None:
    """Zona berskor tertinggi yang lolos ambang. None berarti jalur cadangan.

    Dengan model 4 kelas, wilayah yang jelas-jelas BUKAN tanggal (kode produksi,
    tanggal produksi) dibuang lebih dulu, lalu kelas `date` diutamakan. Itu
    menolak kode produksi SEBELUM OCR - jauh lebih kuat daripada menebaknya dari
    teks hasil OCR, yang pada `chees` terbukti tidak memuat labelnya sama sekali.

    Mundur aman dengan sengaja: zona tanpa nama kelas (model 1 kelas yang
    terpasang sekarang) tidak pernah dibuang, dan bila tidak ada satu pun zona
    berkelas `date` maka pilihannya kembali ke "skor tertinggi yang tersisa".
    Jadi memasang daftar kelas di config TIDAK mengubah apa pun sampai bobot
    4 kelas benar-benar dipakai.
    """
    tolak = {k.strip().lower() for k in kelas_ditolak}
    tanggal = {k.strip().lower() for k in kelas_tanggal}
    lolos = [z for z in zones if z.score >= score_min and (not z.cls or z.cls not in tolak)]
    if not lolos:
        return None
    bertanggal = [z for z in lolos if z.cls and z.cls in tanggal]
    return max(bertanggal or lolos, key=lambda z: z.score)


class ZoneDetector:
    """Membungkus YOLO zona kedaluwarsa. Tahu diri bila bobotnya belum ada."""

    def __init__(self, cfg: dict, model_factory: Callable | None = None):
        self.cfg = cfg
        self.e = cfg["vision"]["expiry"]
        self._factory = model_factory
        self._model = None

    @property
    def weights_path(self):
        return project_path(self.e["zone_weights"])

    @property
    def available(self) -> bool:
        """False bila bobot belum ada. Pemanggil memakai jalur cadangan, bukan gagal."""
        return self._factory is not None or self.weights_path.exists()

    def load(self):
        if self._model is not None:
            return self._model
        if not self.available:
            raise FileNotFoundError(
                f"Bobot zona kedaluwarsa belum ada: {self.weights_path}. "
                "Datasetnya belum dibuat; sementara ini jalur cadangan FR-12 yang dipakai.")
        if self._factory is None:
            from ultralytics import YOLO
            self._factory = YOLO
        self._model = self._factory(str(self.weights_path))
        return self._model

    def detect(self, image: np.ndarray) -> list[Zone]:
        self.load()
        hasil = self._model(image, device=self.e["device"], imgsz=int(self.e["imgsz"]),
                            max_det=int(self.e["max_det"]), verbose=False)
        return extract_zones(hasil)


# --------------------------------------------------------------------------- pembacaan

def text_from_boxes(boxes: Sequence[TextBox], cfg: dict) -> str:
    """Susun teks OCR dengan ambang skor milik modul kedaluwarsa."""
    e = cfg["vision"]["expiry"]
    return compose_text(filter_by_score(boxes, float(e["text_score_min"])), cfg)


class ExpiryReader:
    """Rangkai deteksi zona, OCR, dan parser tanggal menjadi satu jawaban.

    `ocr` sebaiknya berupa `DocumentReader` yang sudah dimuat, agar mesin OCR
    dipakai bersama modul dokumen dan tidak dimuat dua kali.
    """

    def __init__(self, cfg: dict, ocr: DocumentReader | None = None,
                 zone_factory: Callable | None = None):
        self.cfg = cfg
        self.e = cfg["vision"]["expiry"]
        self.ocr = ocr or DocumentReader(cfg)
        self.zones = ZoneDetector(cfg, model_factory=zone_factory)

    def _langkah(self, nama_kunci: str) -> list[str]:
        """Langkah pra-pemrosesan untuk sebuah kunci config; kosong bila dimatikan.

        Dikosongkan (null) pada 02-10 setelah ablasi: dengan PaddleOCR, pra-pemrosesan
        MERUGIKAN modul kedaluwarsa (69% lawan 81% pada 16 kemasan), kebalikan dari
        EasyOCR yang justru dibantu (+6%). PaddleOCR punya normalisasi internalnya
        sendiri, sehingga upscale dan CLAHE kami menambah kerusakan.
        """
        nama = self.e.get(nama_kunci)
        return pre.chain_steps(self.cfg, nama) if nama else []

    def _ocr_text(self, image: np.ndarray, steps: list[str]) -> tuple[str, dict]:
        hasil_pra = pre.run_steps(image, self.cfg, steps)
        kotak, detik = self.ocr.ocr_boxes(hasil_pra.image)
        return text_from_boxes(kotak, self.cfg), {"steps": hasil_pra.steps,
                                                  "boxes": len(kotak), "ocr_s": detik}

    def read(self, image: np.ndarray, today: date | None = None) -> ExpiryResult:
        """Baca tanggal kedaluwarsa, dan bila gagal, coba lagi dengan foto diputar.

        Pengguna tunanetra tidak bisa memastikan kemasan terpegang tegak, jadi
        rotasi ditangani sistem. Sengaja sebagai PERCOBAAN ULANG, bukan selalu
        dijalankan: foto yang sudah tegak menjawab pada percobaan pertama dan
        tidak membayar apa pun, sementara foto terbalik membayar waktu tambahan
        hanya ketika memang perlu.
        """
        if image is None or image.size == 0:
            raise ValueError("Citra kosong.")
        today = today or date.today()
        t_mulai = time.perf_counter()

        hasil = self._read_once(image, today)
        if not hasil.found and hasil.notes.get("crop_rotations_tried"):
            # Zona SUDAH ketemu dan potongannya sudah dicoba di seluruh sudut.
            # Memutar gambar penuh di sini hanya mengulang deteksi zona yang tadi
            # berhasil, pada gambar 3000x4000, tiga kali lagi. Uji lapangan 12-11
            # (Indomie, 44,9 detik): zona ketemu skor 0,755 di lintasan pertama,
            # lalu OCR membaca sampah di keempat rotasi - yang gagal PENGENALAN
            # CETAKAN, dan rotasi gambar penuh tidak menyentuh itu sama sekali.
            hasil.notes["rotate_full_dilewati"] = "potongan sudah dicoba di semua sudut"
        elif not hasil.found:
            dicoba: list[int] = []
            for derajat in self.e.get("rotate_retry") or []:
                ulang = self._read_once(rotate_image(image, derajat), today)
                if ulang.found:
                    ulang.notes["rotated_deg"] = int(derajat)
                    hasil = ulang
                    break
                dicoba.append(int(derajat))
            # jejaknya menempel pada hasil yang dikembalikan, termasuk saat salah
            # satu rotasi berhasil: yang ingin diketahui justru sudut mana saja
            # yang sudah dilewati sebelum jawabannya ketemu
            if dicoba:
                hasil.notes["rotations_tried"] = dicoba

        hasil.notes["total_s"] = time.perf_counter() - t_mulai
        return hasil

    def _read_once(self, image: np.ndarray, today: date) -> ExpiryResult:
        """Satu kali lewat alur PRD 8.8, tanpa percobaan rotasi."""
        catatan: dict[str, Any] = {}

        zona = None
        if self.zones.available:
            semua = self.zones.detect(image)
            catatan["zones_found"] = len(semua)
            zona = pick_zone(semua, float(self.e["zone_score_min"]),
                             kelas_tanggal=self.e.get("zone_classes_date") or (),
                             kelas_ditolak=self.e.get("zone_classes_reject") or ())
            if zona is None:
                catatan["zone_reason"] = "tidak ada zona yang lolos ambang skor"
        else:
            catatan["zone_model"] = "bobot belum ada, jalur cadangan dipakai"

        if zona is None:
            return self._read_full(image, today, catatan)

        # Eskalasi bertingkat, URUTANNYA yang menentukan biaya. Diukur 16-11:
        # memindahkan rotasi potongan ke DEPAN jalur ini melambatkan median
        # 6,54 -> 9,33 detik tanpa menambah satu jawaban benar pun, karena
        # langkah yang murah dan sering berhasil justru yang ditunda. Jadi:
        #   1. potongan zona tegak   - paling murah, paling sering benar
        #   2. OCR seluruh gambar    - murah, dan terbukti menyelamatkan (ajinomoto)
        #   3. rotasi POTONGAN       - paling mahal, paling jarang menolong
        # Gambar PENUH yang diputar tidak ada di daftar ini: itu ditangani
        # `read()`, dan hanya dipakai bila zona tidak ketemu sama sekali.
        hasil = self._read_zone(image, zona, today, catatan)
        if hasil.found:
            return hasil

        # Zona adalah PETUNJUK letak, bukan komitmen. Terbukti 30-09: ajinomoto
        # terdeteksi zonanya dengan skor 0,76, gagal dibaca lewat potongan, padahal
        # OCR seluruh gambar membaca `110426` dengan benar. Sebelum ini sistem
        # terkunci di jalur zona dan membuang jawaban yang sudah ada di tangan.
        penuh = None
        if self.e.get("full_image_fallback", True):
            catatan["zone_gagal"] = "potongan zona tidak menghasilkan tanggal, mundur ke seluruh gambar"
            penuh = self._read_full(image, today, dict(catatan))
            if penuh.found:
                return penuh

        if self.e.get("rotate_crop", False):
            diputar = self._putar_potongan(image, zona, today, catatan)
            if diputar.found:
                return diputar
            hasil = diputar         # jejak rotasinya ikut, termasuk saat gagal

        return penuh if (penuh is not None and penuh.found) else hasil

    def _urai_crop(self, crop, langkah: list[str], today: date,
                   catatan: dict, imbuhan: str = "") -> DateParseResult:
        """OCR satu potongan lalu urai tanggalnya, termasuk ulangan tanpa binarisasi."""
        teks, jejak = self._ocr_text(crop, langkah)
        catatan["pass1" + imbuhan] = jejak
        terurai = parse_expiry(teks, today, self.cfg)
        if terurai.found:
            return terurai

        # PRD 8.8 langkah 4: binarisasi bisa menghapus cetakan tipis.
        buang = set(self.e.get("retry_without_steps") or [])
        langkah2 = [s for s in langkah if s not in buang]
        if langkah2 == langkah:
            return terurai
        teks2, jejak2 = self._ocr_text(crop, langkah2)
        catatan["pass2" + imbuhan] = jejak2
        terurai2 = parse_expiry(teks2, today, self.cfg)
        if terurai2.found or not terurai.text.strip():
            return terurai2         # tulisan apa pun lebih berguna daripada kosong
        return terurai

    def _read_zone(self, image, zona: Zone, today: date, catatan: dict) -> ExpiryResult:
        """Potongan zona TEGAK saja. Rotasinya ditangani `_putar_potongan`, lebih belakang."""
        crop = crop_with_margin(image, zona.box, float(self.e["crop_margin_ratio"]))
        catatan["crop_shape"] = tuple(crop.shape[:2])
        terurai = self._urai_crop(crop, self._langkah("preprocess_chain"), today, catatan)
        return ExpiryResult(date=terurai, zone=zona, source=SOURCE_ZONE, notes=catatan)

    def _putar_potongan(self, image, zona: Zone, today: date, catatan: dict) -> ExpiryResult:
        """Langkah eskalasi TERAKHIR: putar potongannya, bukan gambar penuhnya.

        Memutar potongan lawan memutar gambar penuh adalah soal apa yang dibayar
        ulang. Satu lintasan gambar penuh berarti deteksi zona YOLO pada gambar
        3000x4000 lagi, lalu potong lagi, lalu OCR lagi; memutar potongan hanya
        membayar OCR potongan yang kecil. Zona yang sudah ketemu tidak akan hilang
        karena gambarnya diputar, jadi mendeteksinya ulang tidak membeli apa pun.

        Ditempatkan SESUDAH OCR seluruh gambar, bukan sebelumnya. Urutan terbalik
        sudah diukur 16-11 dan merugikan: median 6,54 -> 9,33 detik, akurasi identik
        per berkas, melambat di 13 dari 16 kemasan - karena langkah yang murah dan
        sering berhasil justru ditunda di belakang tiga rotasi yang jarang menolong.
        """
        crop = crop_with_margin(image, zona.box, float(self.e["crop_margin_ratio"]))
        langkah = self._langkah("preprocess_chain")
        terakhir, dicoba = None, []
        for derajat in self.e.get("rotate_retry") or []:
            ulang = self._urai_crop(rotate_image(crop, int(derajat)), langkah, today,
                                    catatan, f"_putar{int(derajat)}")
            if ulang.found:
                catatan["crop_rotated_deg"] = int(derajat)
                catatan["crop_rotations_tried"] = list(dicoba)
                return ExpiryResult(date=ulang, zone=zona, source=SOURCE_ZONE, notes=catatan)
            dicoba.append(int(derajat))
            if terakhir is None or not terakhir.text.strip():
                terakhir = ulang    # tulisan apa pun lebih berguna daripada kosong
        catatan["crop_rotations_tried"] = dicoba
        return ExpiryResult(date=terakhir or DateParseResult(), zone=zona,
                            source=SOURCE_ZONE, notes=catatan)

    def _read_full(self, image, today: date, catatan: dict) -> ExpiryResult:
        langkah = self._langkah("fallback_preprocess_chain")
        teks, jejak = self._ocr_text(image, langkah)
        catatan["fallback"] = jejak
        terurai = parse_expiry(teks, today, self.cfg)
        return ExpiryResult(date=terurai, zone=None, source=SOURCE_FULL, notes=catatan)


# --------------------------------------------------------------------------- ujaran

def expiry_utterance(hasil: ExpiryResult, today: date) -> Utterance:
    """Ujaran untuk pengguna. Jalur cadangan selalu dibacakan sebagai kurang yakin."""
    terurai = hasil.date if hasil.confident else replace(hasil.date, confident=False)
    return _date_utterance(terurai, today)
