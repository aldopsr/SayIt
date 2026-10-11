"""Tes perangkaian seluruh modul (PRD 7).

Semua komponen berat diganti tiruan, jadi tes lulus tanpa mikrofon, tanpa bobot
model, dan tanpa internet.
"""
import copy
from datetime import date

import cv2
import numpy as np
import pytest

from sayit.config import load_config
from sayit.intent import keywords as K
from sayit.pipeline import Pipeline, Turn
from sayit.response import templates as T
from sayit.vision.document import TextBox, build_result
from sayit.vision.money import Detection, MoneyResult

HARI_INI = date(2026, 9, 18)


@pytest.fixture
def cfg():
    c = copy.deepcopy(load_config())
    c["vision"]["expiry"]["zone_weights"] = "models/zona_yang_tidak_ada.pt"
    return c


# --------------------------------------------------------------------------- tiruan

def foto_layak():
    """Papan catur: tajam, terang sedang, resolusi cukup - lolos quality gate."""
    yy, xx = np.indices((800, 800))
    abu = np.where(((yy // 8) + (xx // 8)) % 2 == 0, 60, 200).astype(np.uint8)
    return cv2.cvtColor(abu, cv2.COLOR_GRAY2BGR)


def foto_buram():
    return cv2.GaussianBlur(foto_layak(), (31, 31), 10)


class MoneyPalsu:
    def __init__(self, hasil=None, error=None):
        self.hasil = hasil or MoneyResult(counts={50000: 1}, total=50000,
                                          detections=[Detection(50000, 0.9, (0, 0, 10, 10))],
                                          notes={"raw": 1})
        self.error = error
        self.panggilan = 0

    def load(self, *a, **k):
        if self.error:
            raise self.error
        return self

    def detect(self, image, preprocess=True):
        self.panggilan += 1
        if self.error:
            raise self.error
        return self.hasil


class OcrPalsu:
    def __init__(self, cfg, teks="", error=None):
        self.cfg = cfg
        self.teks = teks
        self.error = error
        self.panggilan = 0

    def load(self, *a, **k):
        if self.error:
            raise self.error
        return self

    def _kotak(self, teks):
        return [TextBox(b, 0.9, (50, 100 + i * 30, 400, 120 + i * 30))
                for i, b in enumerate(teks.splitlines()) if b.strip()]

    def ocr_boxes(self, image):
        self.panggilan += 1
        if self.error:
            raise self.error
        return self._kotak(self.teks), 0.01

    def read(self, image, preprocess=True):
        self.panggilan += 1
        if self.error:
            raise self.error
        return build_result(self._kotak(self.teks), self.cfg)


class SttPalsu:
    def __init__(self, teks="", empty=False, reason=""):
        self.teks, self.empty, self.reason = teks, empty, reason
        self.panggilan = 0

    def load(self, *a, **k):
        return self

    def transcribe(self, audio, sr=16000):
        self.panggilan += 1
        from sayit.audio.stt import Transcript
        return Transcript(self.teks, self.empty, 1.2, 5.0, self.reason)


def buat(cfg, teks_ocr="", money=None, stt=None):
    ocr = OcrPalsu(cfg, teks_ocr)
    p = Pipeline(cfg, transcriber=stt, money=money or MoneyPalsu(), ocr=ocr,
                 today=lambda: HARI_INI)
    p.ocr = ocr
    p.expiry.ocr = ocr
    return p


# --------------------------------------------------------------------------- foto dan quality gate

def test_foto_layak_diterima(cfg):
    p = buat(cfg)
    giliran = p.set_photo(foto_layak())
    assert p.has_photo
    assert giliran.utterance == [T.Clip("foto_diambil")]
    assert giliran.diterima
    assert "quality" in giliran.notes


def test_foto_buram_ditolak_dan_tidak_disimpan(cfg):
    p = buat(cfg)
    giliran = p.set_photo(foto_buram())
    assert not p.has_photo
    assert giliran.utterance == [T.Clip("foto_buram")]
    assert giliran.notes["issues"] == ["buram"]
    # Intent-nya tetap "FOTO" walau ditolak, jadi penerimaan HARUS dibaca dari
    # `diterima`. Klien web dulu menyimpulkannya dari intent dan akibatnya
    # meminta pengguna bertanya tentang foto yang tidak pernah tersimpan.
    assert giliran.intent == "FOTO"
    assert not giliran.diterima


def test_quality_gate_bisa_dimatikan(cfg):
    cfg["pipeline"]["quality_gate_on_photo"] = False
    p = buat(cfg)
    p.set_photo(foto_buram())
    assert p.has_photo


def test_citra_kosong_ditolak(cfg):
    with pytest.raises(ValueError):
        buat(cfg).set_photo(np.zeros((0, 0, 3), np.uint8))


# --------------------------------------------------------------------------- intent tugas butuh foto

@pytest.mark.parametrize("kalimat", ["ini uang berapa", "tolong bacakan tulisannya",
                                     "kapan kedaluwarsanya"])
def test_tugas_tanpa_foto_diminta_memotret(cfg, kalimat):
    giliran = buat(cfg).ask(kalimat)
    assert giliran.utterance == [T.Clip("belum_ada_foto")]
    assert giliran.reason == "intent tugas tanpa foto"


def test_uang_setelah_ada_foto(cfg):
    p = buat(cfg)
    p.set_photo(foto_layak())
    giliran = p.ask("ini uang berapa")
    assert giliran.intent == K.UANG
    assert giliran.text == "Uang lima puluh ribu rupiah."


def test_baca_setelah_ada_foto(cfg):
    p = buat(cfg, teks_ocr="Surat Keterangan Domisili")
    p.set_photo(foto_layak())
    giliran = p.ask("tolong bacakan tulisannya")
    assert giliran.intent == K.BACA
    assert "Surat Keterangan Domisili" in giliran.text


def test_kedaluwarsa_setelah_ada_foto(cfg):
    p = buat(cfg, teks_ocr="KOPI BUBUK\nEXP 03/12/2026")
    p.set_photo(foto_layak())
    giliran = p.ask("kapan kedaluwarsanya")
    assert giliran.intent == K.KEDALUWARSA
    # tanpa bobot zona, jalur cadangan dipakai dan hasilnya kurang yakin
    assert giliran.text.startswith("Saya kurang yakin")
    assert giliran.notes["source"] == "seluruh gambar"


def test_tanggal_dibandingkan_dengan_hari_ini_yang_disuntikkan(cfg):
    """`today` bisa dioper agar tes tidak berubah seiring waktu."""
    p = buat(cfg, teks_ocr="EXP 03/12/2026")
    p.set_photo(foto_layak())
    assert "sisa tujuh puluh enam hari" in p.ask("kapan kedaluwarsanya").text


# --------------------------------------------------------------------------- intent kendali

def test_bantuan_tidak_butuh_foto(cfg):
    assert buat(cfg).ask("kamu bisa apa").utterance == [T.Clip("menu_bantuan")]


def test_tidak_mengerti(cfg):
    giliran = buat(cfg).ask("halo apa kabar")
    assert giliran.intent == K.TIDAK_DIKENALI
    assert giliran.utterance == [T.Clip("tidak_mengerti")]


def test_ulangi_sebelum_ada_jawaban(cfg):
    assert buat(cfg).ask("ulangi").utterance == [T.Clip("tidak_ada_ulangan")]


def test_ulangi_mengembalikan_jawaban_terakhir(cfg):
    p = buat(cfg)
    p.set_photo(foto_layak())
    pertama = p.ask("ini uang berapa")
    ulang = p.ask("ulangi")
    assert ulang.intent == K.ULANGI
    assert ulang.utterance == pertama.utterance


def test_ulangi_tidak_menimpa_jawaban_terakhir(cfg):
    """Mengulang dua kali harus tetap mengembalikan jawaban tugas, bukan dirinya sendiri."""
    p = buat(cfg)
    p.set_photo(foto_layak())
    jawaban = p.ask("ini uang berapa").utterance
    p.ask("ulangi")
    assert p.ask("ulangi").utterance == jawaban


def test_foto_baru_membuang_foto(cfg):
    p = buat(cfg)
    p.set_photo(foto_layak())
    giliran = p.ask("foto ulang")
    assert giliran.utterance == [T.Clip("silakan_foto")]
    assert not p.has_photo
    assert p.ask("ini uang berapa").utterance == [T.Clip("belum_ada_foto")]


# --------------------------------------------------------------------------- lanjut

@pytest.fixture
def teks_panjang():
    """Tiap baris sengaja berbeda isinya, agar potongan yang berbeda benar-benar terbukti berbeda."""
    return "\n".join(f"baris ke {i} berisi satu dua tiga empat lima enam tujuh delapan."
                     for i in range(12))


def test_lanjut_sebelum_ada_bacaan(cfg):
    p = buat(cfg)
    p.set_photo(foto_layak())
    assert p.ask("lanjut").utterance == [T.Clip("tidak_ada_lanjutan")]


def test_lanjut_membacakan_potongan_berikutnya(cfg, teks_panjang):
    p = buat(cfg, teks_ocr=teks_panjang)
    p.set_photo(foto_layak())
    pertama = p.ask("bacakan tulisannya")
    assert p.document.total_chunks > 1
    kedua = p.ask("lanjut")
    assert kedua.intent == K.LANJUT
    assert kedua.text != pertama.text
    assert p.chunk_index == 1


def test_potongan_terakhir_lalu_lanjut_lagi(cfg, teks_panjang):
    p = buat(cfg, teks_ocr=teks_panjang)
    p.set_photo(foto_layak())
    p.ask("bacakan tulisannya")
    for _ in range(p.document.total_chunks - 1):
        p.ask("lanjut")
    habis = p.ask("lanjut")
    assert habis.utterance == [T.Clip("tidak_ada_lanjutan")]
    assert p.ask("lanjut").utterance == [T.Clip("tidak_ada_lanjutan")]   # tidak melewati ujung


def test_membaca_ulang_mengembalikan_posisi_ke_awal(cfg, teks_panjang):
    p = buat(cfg, teks_ocr=teks_panjang)
    p.set_photo(foto_layak())
    pertama = p.ask("bacakan tulisannya")
    p.ask("lanjut")
    assert p.ask("bacakan tulisannya").text == pertama.text
    assert p.chunk_index == 0


def test_foto_baru_membatalkan_bacaan_lama(cfg, teks_panjang):
    p = buat(cfg, teks_ocr=teks_panjang)
    p.set_photo(foto_layak())
    p.ask("bacakan tulisannya")
    p.set_photo(foto_layak())
    assert p.document is None
    assert p.ask("lanjut").utterance == [T.Clip("tidak_ada_lanjutan")]


# --------------------------------------------------------------------------- suara masuk

def test_dari_rekaman_ke_jawaban(cfg):
    p = buat(cfg, stt=SttPalsu("ini uang berapa"))
    p.set_photo(foto_layak())
    giliran = p.listen(np.zeros(16000, np.float32))
    assert giliran.intent == K.UANG
    assert giliran.notes["transcript"] == "ini uang berapa"
    assert giliran.notes["stt_s"] == pytest.approx(1.2)


def test_transkrip_kosong_diminta_ulang(cfg):
    p = buat(cfg, stt=SttPalsu("", empty=True, reason="tidak ada ucapan"))
    giliran = p.listen(np.zeros(16000, np.float32))
    assert giliran.utterance == [T.Clip("suara_tidak_jelas")]
    assert giliran.reason == "tidak ada ucapan"


def test_tanpa_stt_terpasang(cfg):
    giliran = buat(cfg).listen(np.zeros(16000, np.float32))
    assert giliran.utterance == [T.Clip("modul_belum_siap")]


# --------------------------------------------------------------------------- penanda sedang diproses

def test_intent_lambat_memicu_penanda(cfg):
    p = buat(cfg, teks_ocr="Surat")
    p.set_photo(foto_layak())
    diputar = []
    p.ask("bacakan tulisannya", on_progress=diputar.append)
    assert diputar == [[T.Clip("sedang_memproses")]]


def test_intent_cepat_tidak_memicu_penanda(cfg):
    p = buat(cfg)
    p.set_photo(foto_layak())
    diputar = []
    p.ask("ini uang berapa", on_progress=diputar.append)
    assert diputar == []


def test_daftar_intent_lambat_diambil_dari_config(cfg):
    cfg["pipeline"]["slow_intents"] = ["UANG"]
    p = buat(cfg)
    p.set_photo(foto_layak())
    diputar = []
    p.ask("ini uang berapa", on_progress=diputar.append)
    assert diputar == [[T.Clip("sedang_memproses")]]


def test_penanda_tidak_diputar_bila_foto_belum_ada(cfg):
    diputar = []
    buat(cfg).ask("bacakan tulisannya", on_progress=diputar.append)
    assert diputar == []


# --------------------------------------------------------------------------- pemuatan model

def test_status_pemuatan_dilaporkan(cfg):
    p = buat(cfg, stt=SttPalsu("x"))
    status = p.load()
    assert status["stt"].startswith("siap")
    assert status["money"].startswith("siap")
    assert status["ocr"].startswith("siap")
    assert status["zone"].startswith("bobot belum ada")


def test_satu_modul_gagal_tidak_mematikan_yang_lain(cfg):
    """Anggota tim tanpa best_money.pt harus tetap bisa mendemokan modul dokumen."""
    p = buat(cfg, teks_ocr="Surat Keterangan",
             money=MoneyPalsu(error=FileNotFoundError("models/best_money.pt tidak ada")))
    status = p.load()
    assert status["money"].startswith("gagal")
    assert status["ocr"].startswith("siap")

    p.set_photo(foto_layak())
    assert p.ask("ini uang berapa").utterance == [T.Clip("modul_belum_siap")]
    assert "Surat Keterangan" in p.ask("bacakan tulisannya").text


def test_strict_meneruskan_kesalahan(cfg):
    p = buat(cfg, money=MoneyPalsu(error=FileNotFoundError("bobot hilang")))
    with pytest.raises(FileNotFoundError):
        p.load(strict=True)


def test_bobot_hilang_tanpa_load_tetap_dijawab_bukan_mati(cfg):
    """Demo tidak boleh mati hanya karena load() lupa dipanggil."""
    p = buat(cfg, money=MoneyPalsu(error=FileNotFoundError("bobot hilang")))
    p.set_photo(foto_layak())
    giliran = p.ask("ini uang berapa")
    assert giliran.utterance == [T.Clip("modul_belum_siap")]
    assert p.status["money"].startswith("gagal")


def test_stt_tidak_dipasang_terlihat_di_status(cfg):
    assert buat(cfg).load()["stt"] == "tidak dipasang"


# --------------------------------------------------------------------------- catatan dan ujaran

def test_giliran_menyimpan_skor_router(cfg):
    giliran = buat(cfg).ask("ini uang berapa")
    assert giliran.notes["scores"][K.UANG] >= 2
    assert "uang" in giliran.notes["matched"][K.UANG]


def test_teks_giliran_bisa_ditampilkan(cfg):
    giliran = buat(cfg).ask("kamu bisa apa")
    assert isinstance(giliran.text, str) and giliran.text


def test_semua_klip_yang_mungkin_keluar_sudah_terdaftar(cfg):
    """Klip yang belum ada di CLIP_TEXTS tidak akan punya file suara saat demo."""
    p = buat(cfg, teks_ocr="KOPI BUBUK\nEXP 03/12/2026", stt=SttPalsu("ini uang berapa"))
    giliran_giliran = [p.set_photo(foto_buram()), p.set_photo(foto_layak())]
    for kalimat in ["ini uang berapa", "bacakan tulisannya", "kapan kedaluwarsanya",
                    "ulangi", "lanjut", "kamu bisa apa", "halo apa kabar", "foto ulang",
                    "ini uang berapa"]:
        giliran_giliran.append(p.ask(kalimat))
    giliran_giliran.append(p.listen(np.zeros(16000, np.float32)))
    for g in giliran_giliran:
        for kunci in T.clip_keys(g.utterance):
            assert kunci in T.CLIP_TEXTS, f"klip {kunci!r} belum terdaftar"


def test_seluruh_alur_satu_sesi(cfg, teks_panjang):
    """Skenario demo: foto buram, foto ulang, tanya uang, baca, lanjut, ulangi."""
    p = buat(cfg, teks_ocr=teks_panjang)
    assert p.set_photo(foto_buram()).utterance == [T.Clip("foto_buram")]
    assert p.ask("ini uang berapa").utterance == [T.Clip("belum_ada_foto")]

    p.set_photo(foto_layak())
    assert p.ask("ini uang berapa").text == "Uang lima puluh ribu rupiah."

    baca = p.ask("bacakan tulisannya")
    assert p.document.total_chunks > 1
    assert "Katakan lanjut" in baca.text

    lanjut = p.ask("lanjut")
    assert lanjut.text != baca.text
    assert p.ask("ulangi").utterance == lanjut.utterance


# --------------------------------------------------------------------------- mesin per modul

def test_mesin_kedaluwarsa_terpisah_bila_config_berbeda(cfg):
    """`vision.expiry.engine` boleh berbeda dari `vision.document.engine`.

    Dipilih 02-10: PaddleOCR menaikkan akurasi kedaluwarsa 44% -> 81%, tetapi
    membuat pembacaan dokumen 42 detik per halaman - di atas PRD NFR-01.
    """
    cfg["vision"]["document"]["engine"] = "easyocr"
    cfg["vision"]["expiry"]["engine"] = "paddleocr"
    dok = object()
    p = Pipeline(cfg, ocr=dok, ocr_expiry=object())
    assert p.ocr is dok
    assert p.ocr_expiry is not dok


def test_mesin_sama_memakai_satu_pembaca(cfg):
    """Memuat dua kali memakan 4 detik dan memori dua kali lipat."""
    cfg["vision"]["document"]["engine"] = "easyocr"
    cfg["vision"]["expiry"]["engine"] = "easyocr"
    dok = object()
    p = Pipeline(cfg, ocr=dok)
    assert p.ocr_expiry is dok


def test_engine_kedaluwarsa_kosong_memakai_mesin_dokumen(cfg):
    cfg["vision"]["expiry"]["engine"] = None
    dok = object()
    p = Pipeline(cfg, ocr=dok)
    assert p.ocr_expiry is dok
