"""Tes modul kedaluwarsa (PRD 8.8).

Zona dan OCR sama-sama diganti tiruan, jadi tes lulus tanpa bobot apa pun.
Bobot zona memang belum ada: jalur cadangan FR-12 juga diuji di sini.
"""
import copy
import types
from datetime import date

import numpy as np
import pytest

from sayit.config import load_config
from sayit.response import templates as T
from sayit.vision import expiry as E
from sayit.vision.document import TextBox

HARI_INI = date(2026, 9, 18)


@pytest.fixture
def cfg():
    c = copy.deepcopy(load_config())
    # bobot zona sengaja diarahkan ke berkas yang pasti tidak ada, agar tes tidak
    # berubah perilakunya saat nanti models/best_zone.pt benar-benar dibuat
    c["vision"]["expiry"]["zone_weights"] = "models/zona_yang_tidak_ada.pt"
    return c


def kotak_teks(teks, y=100, tinggi=20):
    """Satu kotak OCR per baris, seperti keluaran EasyOCR."""
    return [TextBox(baris, 0.9, (50, y + i * 30, 400, y + i * 30 + tinggi))
            for i, baris in enumerate(teks.splitlines()) if baris.strip()]


class OcrPalsu:
    """Menggantikan DocumentReader. Tiap panggilan mengambil jawaban berikutnya."""

    def __init__(self, *jawaban):
        self.jawaban = list(jawaban) or [""]
        self.panggilan = []

    def ocr_boxes(self, image):
        self.panggilan.append(image.shape)
        teks = self.jawaban[min(len(self.panggilan) - 1, len(self.jawaban) - 1)]
        return kotak_teks(teks), 0.01


def hasil_yolo(kotak, skor):
    boxes = types.SimpleNamespace(
        xyxy=np.array(kotak, dtype=np.float32).reshape(-1, 4),
        conf=np.array(skor, dtype=np.float32),
    )
    return [types.SimpleNamespace(boxes=boxes)]


def pabrik_zona(kotak=(), skor=()):
    class ModelPalsu:
        def __init__(self, path):
            self.path = path
            self.panggilan = []

        def __call__(self, image, **kwargs):
            self.panggilan.append({"shape": image.shape, **kwargs})
            return hasil_yolo(kotak, skor)

    def buat(path):
        buat.model = ModelPalsu(path)
        return buat.model
    return buat


def pembaca(cfg, ocr, kotak=(), skor=()):
    zona = pabrik_zona(kotak, skor) if kotak else None
    return E.ExpiryReader(cfg, ocr=ocr, zone_factory=zona)


FOTO = np.zeros((600, 800, 3), np.uint8)


# --------------------------------------------------------------------------- crop

def test_crop_memakai_margin_sepuluh_persen():
    img = np.zeros((600, 800, 3), np.uint8)
    crop = E.crop_with_margin(img, (100.0, 200.0, 300.0, 250.0), 0.10)
    # lebar 200 -> margin 20 tiap sisi; tinggi 50 -> margin 5 tiap sisi
    assert crop.shape[:2] == (50 + 10, 200 + 40)


def test_crop_tidak_keluar_dari_gambar():
    img = np.zeros((100, 100, 3), np.uint8)
    crop = E.crop_with_margin(img, (0.0, 0.0, 100.0, 100.0), 0.5)
    assert crop.shape[:2] == (100, 100)


def test_crop_margin_nol():
    img = np.zeros((600, 800, 3), np.uint8)
    assert E.crop_with_margin(img, (10.0, 20.0, 110.0, 70.0), 0.0).shape[:2] == (50, 100)


def test_kotak_di_luar_gambar_ditolak():
    img = np.zeros((100, 100, 3), np.uint8)
    with pytest.raises(ValueError, match="di luar gambar"):
        E.crop_with_margin(img, (200.0, 200.0, 300.0, 300.0), 0.1)


# --------------------------------------------------------------------------- zona

def test_ekstraksi_zona():
    zona = E.extract_zones(hasil_yolo([[10, 20, 110, 70], [200, 30, 300, 80]], [0.9, 0.5]))
    assert [z.score for z in zona] == [pytest.approx(0.9), pytest.approx(0.5)]
    assert zona[0].box == (10.0, 20.0, 110.0, 70.0)


def test_ekstraksi_zona_kosong():
    assert E.extract_zones(hasil_yolo([], [])) == []
    assert E.extract_zones([]) == []


def test_zona_terbaik_dipilih():
    zona = [E.Zone(0.5, (0, 0, 10, 10)), E.Zone(0.8, (20, 20, 30, 30))]
    assert E.pick_zone(zona, 0.4).score == pytest.approx(0.8)


def test_zona_di_bawah_ambang_diabaikan():
    zona = [E.Zone(0.3, (0, 0, 10, 10))]
    assert E.pick_zone(zona, 0.4) is None
    assert E.pick_zone([], 0.4) is None


def test_detektor_tahu_bobotnya_belum_ada(cfg):
    d = E.ZoneDetector(cfg)
    assert d.available is False
    with pytest.raises(FileNotFoundError, match="jalur cadangan"):
        d.load()


def test_detektor_siap_bila_diberi_pabrik(cfg):
    d = E.ZoneDetector(cfg, model_factory=pabrik_zona([[10, 20, 110, 70]], [0.9]))
    assert d.available is True
    assert len(d.detect(FOTO)) == 1


# --------------------------------------------------------------------------- jalur cadangan (keadaan sekarang)

def test_tanpa_bobot_zona_memakai_jalur_cadangan(cfg):
    ocr = OcrPalsu("KOPI BUBUK\nEXP 03/12/2026")
    hasil = pembaca(cfg, ocr).read(FOTO, today=HARI_INI)
    assert hasil.source == E.SOURCE_FULL
    assert hasil.zone is None
    assert hasil.date.value == date(2026, 12, 3)
    assert hasil.notes["zone_model"].startswith("bobot belum ada")


def test_jalur_cadangan_tidak_pernah_dinyatakan_yakin(cfg):
    """PRD 8.8 langkah 6: hasil dari OCR seluruh gambar harus disebut kurang pasti,
    walau parsernya sendiri yakin karena ada penanda EXP."""
    ocr = OcrPalsu("EXP 03/12/2026")
    hasil = pembaca(cfg, ocr).read(FOTO, today=HARI_INI)
    assert hasil.date.confident is True          # parser yakin
    assert hasil.confident is False              # tetapi modul tidak
    teks = T.to_plain_text(E.expiry_utterance(hasil, HARI_INI))
    assert teks.startswith("Saya kurang yakin")


def test_jalur_cadangan_memakai_rangkaian_dokumen(cfg):
    ocr = OcrPalsu("EXP 03/12/2026")
    hasil = pembaca(cfg, ocr).read(FOTO, today=HARI_INI)
    assert "threshold" not in hasil.notes["fallback"]["steps"]     # rangkaian dokumen, bukan kedaluwarsa
    assert ocr.panggilan[0][:2] == (600, 800)                      # gambar utuh, bukan crop


# --------------------------------------------------------------------------- jalur zona

def test_zona_terdeteksi_memakai_crop(cfg):
    ocr = OcrPalsu("EXP 03/12/2026")
    r = pembaca(cfg, ocr, kotak=[[100, 200, 300, 250]], skor=[0.9])
    hasil = r.read(FOTO, today=HARI_INI)
    assert hasil.source == E.SOURCE_ZONE
    assert hasil.zone.score == pytest.approx(0.9)
    assert hasil.notes["crop_shape"] == (60, 240)                  # crop + margin 10%
    assert ocr.panggilan[0][:2] != (600, 800)                      # bukan gambar utuh


def biner(cfg):
    """Pasang rangkaian zona yang memuat binarisasi, untuk menguji mekanisme ulangan.

    Rangkaian bawaan tidak lagi memakai threshold sejak 30-09 (terbukti merusak
    cetakan dot-matrix pada 9 potongan zona sungguhan), tetapi mekanisme
    "ulangi tanpa binarisasi" tetap ada dan tetap harus bekerja bila dipasang.
    """
    cfg["vision"]["preprocess"]["chains"]["kedaluwarsa"] = [
        "upscale", "clahe", "denoise", "threshold", "morphology"]
    # rangkaian bawaannya null sejak 02-10, jadi harus ditunjuk ulang di sini
    cfg["vision"]["expiry"]["preprocess_chain"] = "kedaluwarsa"
    return cfg


def test_zona_memakai_rangkaian_dari_config(cfg):
    cfg = biner(cfg)
    ocr = OcrPalsu("EXP 03/12/2026")
    r = pembaca(cfg, ocr, kotak=[[100, 200, 300, 250]], skor=[0.9])
    hasil = r.read(FOTO, today=HARI_INI)
    assert hasil.notes["pass1"]["steps"] == cfg["vision"]["preprocess"]["chains"]["kedaluwarsa"]


def test_rangkaian_kedaluwarsa_wajib_memuat_resize(cfg):
    """`resize` adalah PENGENDALI LATENSI, bukan sekadar perbaikan citra.

    Pada 02-10 rangkaian ini sempat dikosongkan sepenuhnya demi akurasi (CLAHE dan
    upscale merugikan PaddleOCR). Akibatnya foto 3024x4032 utuh masuk ke OCR dan
    latensinya mencapai 116 detik, sedangkan PRD NFR-01 membatasi 8 detik.
    Tes ini membuat pengosongan serupa gagal keras.
    """
    for kunci in ("preprocess_chain", "fallback_preprocess_chain"):
        nama = cfg["vision"]["expiry"][kunci]
        assert nama, f"{kunci} kosong: foto resolusi penuh akan masuk ke OCR"
        assert "resize" in cfg["vision"]["preprocess"]["chains"][nama], kunci


def test_rangkaian_kedaluwarsa_tidak_memperbaiki_citra(cfg):
    """Keputusan akurasi 02-10: CLAHE dan upscale merugikan modul ini pada PaddleOCR
    (69% lawan 81% pada 16 kemasan), kebalikan dari EasyOCR yang dibantu +6%."""
    rantai = cfg["vision"]["preprocess"]["chains"][cfg["vision"]["expiry"]["preprocess_chain"]]
    assert rantai == ["resize"]


def test_rangkaian_kosong_tetap_ditangani(cfg):
    """Bila seseorang mengosongkannya, kodenya tidak boleh meledak - hanya melewati."""
    cfg["vision"]["expiry"]["preprocess_chain"] = None
    ocr = OcrPalsu("EXP 03/12/2026")
    r = pembaca(cfg, ocr, kotak=[[100, 200, 300, 250]], skor=[0.9])
    hasil = r.read(FOTO, today=HARI_INI)
    assert hasil.notes["pass1"]["steps"] == []


def test_rangkaian_zona_bawaan_tidak_membinarisasi(cfg):
    """Keputusan 30-09, dikunci di tes supaya tidak kembali diam-diam."""
    rantai = cfg["vision"]["preprocess"]["chains"]["kedaluwarsa"]
    assert "threshold" not in rantai and "morphology" not in rantai
    assert "upscale" in rantai and "clahe" in rantai


def test_jalur_zona_boleh_yakin(cfg):
    ocr = OcrPalsu("EXP 03/12/2026")
    r = pembaca(cfg, ocr, kotak=[[100, 200, 300, 250]], skor=[0.9])
    hasil = r.read(FOTO, today=HARI_INI)
    assert hasil.confident is True
    teks = T.to_plain_text(E.expiry_utterance(hasil, HARI_INI))
    assert teks.startswith("Tanggal kedaluwarsa tiga Desember")


def test_zona_berskor_rendah_jatuh_ke_jalur_cadangan(cfg):
    ocr = OcrPalsu("EXP 03/12/2026")
    r = pembaca(cfg, ocr, kotak=[[100, 200, 300, 250]], skor=[0.2])
    hasil = r.read(FOTO, today=HARI_INI)
    assert hasil.source == E.SOURCE_FULL
    assert hasil.notes["zones_found"] == 1
    assert "ambang skor" in hasil.notes["zone_reason"]


def test_zona_terbaik_yang_dipakai_bila_ada_beberapa(cfg):
    ocr = OcrPalsu("EXP 03/12/2026")
    r = pembaca(cfg, ocr, kotak=[[0, 0, 50, 50], [100, 200, 300, 250]], skor=[0.5, 0.95])
    hasil = r.read(FOTO, today=HARI_INI)
    assert hasil.zone.box == (100.0, 200.0, 300.0, 250.0)


# --------------------------------------------------------------------------- ulangi tanpa binarisasi

def test_gagal_lalu_berhasil_tanpa_binarisasi(cfg):
    """PRD 8.8 langkah 4. Binarisasi bisa menghapus cetakan tipis; percobaan kedua
    memakai rangkaian yang sama tanpa threshold dan morfologi."""
    ocr = OcrPalsu("IIII", "EXP 03/12/2026")
    r = pembaca(biner(cfg), ocr, kotak=[[100, 200, 300, 250]], skor=[0.9])
    hasil = r.read(FOTO, today=HARI_INI)
    assert hasil.date.value == date(2026, 12, 3)
    assert "pass2" in hasil.notes
    langkah2 = hasil.notes["pass2"]["steps"]
    assert "threshold" not in langkah2 and "morphology" not in langkah2
    assert "upscale" in langkah2 and "clahe" in langkah2


def test_percobaan_kedua_tidak_dijalankan_bila_yang_pertama_berhasil(cfg):
    ocr = OcrPalsu("EXP 03/12/2026", "01/01/2030")
    r = pembaca(cfg, ocr, kotak=[[100, 200, 300, 250]], skor=[0.9])
    hasil = r.read(FOTO, today=HARI_INI)
    assert "pass2" not in hasil.notes
    assert len(ocr.panggilan) == 1


def test_dua_duanya_gagal_tetap_mengembalikan_hasil(cfg):
    ocr = OcrPalsu("NETTO 250 G", "NETTO 250 G")
    r = pembaca(biner(cfg), ocr, kotak=[[100, 200, 300, 250]], skor=[0.9])
    hasil = r.read(FOTO, today=HARI_INI)
    assert hasil.found is False
    assert "pass2" in hasil.notes
    utt = E.expiry_utterance(hasil, HARI_INI)
    assert T.Clip("tulisan_bukan_tanggal") in utt


def test_langkah_yang_dibuang_diambil_dari_config(cfg):
    cfg = biner(cfg)
    cfg["vision"]["expiry"]["retry_without_steps"] = ["morphology"]
    ocr = OcrPalsu("IIII", "EXP 03/12/2026")
    r = pembaca(cfg, ocr, kotak=[[100, 200, 300, 250]], skor=[0.9])
    hasil = r.read(FOTO, today=HARI_INI)
    assert "threshold" in hasil.notes["pass2"]["steps"]
    assert "morphology" not in hasil.notes["pass2"]["steps"]


# --------------------------------------------------------------------------- tidak ketemu

def test_tanpa_tulisan_sama_sekali(cfg):
    hasil = pembaca(cfg, OcrPalsu("")).read(FOTO, today=HARI_INI)
    assert hasil.found is False
    assert E.expiry_utterance(hasil, HARI_INI) == [T.Clip("tidak_ada_tanggal")]


def test_ada_tulisan_tetapi_bukan_tanggal(cfg):
    hasil = pembaca(cfg, OcrPalsu("KOPI BUBUK NETTO 250 G")).read(FOTO, today=HARI_INI)
    assert hasil.found is False
    utt = E.expiry_utterance(hasil, HARI_INI)
    assert T.Clip("tulisan_bukan_tanggal") in utt


def test_citra_kosong_ditolak(cfg):
    with pytest.raises(ValueError):
        pembaca(cfg, OcrPalsu("")).read(np.zeros((0, 0, 3), np.uint8))


# --------------------------------------------------------------------------- catatan untuk laporan

def test_waktu_dan_jejak_tercatat(cfg):
    ocr = OcrPalsu("EXP 03/12/2026")
    hasil = pembaca(cfg, ocr).read(FOTO, today=HARI_INI)
    assert hasil.notes["total_s"] >= 0
    assert hasil.notes["fallback"]["boxes"] == 1
    assert hasil.notes["fallback"]["ocr_s"] >= 0


def test_semua_klip_ujaran_terdaftar(cfg):
    for teks in ("EXP 03/12/2026", "12/2027", "NETTO 250 G", "",
                 "EXP 01/06/2027 BB 01/07/2027"):
        hasil = pembaca(cfg, OcrPalsu(teks)).read(FOTO, today=HARI_INI)
        for kunci in T.clip_keys(E.expiry_utterance(hasil, HARI_INI)):
            assert kunci in T.CLIP_TEXTS, f"klip {kunci!r} belum terdaftar"


# --------------------------------------------------------------------------- rotasi

def test_rotasi_nol_mengembalikan_citra_yang_sama():
    assert E.rotate_image(FOTO, 0) is FOTO
    assert E.rotate_image(FOTO, 360) is FOTO


def test_rotasi_menukar_sisi():
    assert E.rotate_image(FOTO, 90).shape[:2] == (800, 600)
    assert E.rotate_image(FOTO, 270).shape[:2] == (800, 600)
    assert E.rotate_image(FOTO, 180).shape[:2] == (600, 800)


def test_rotasi_membalik_isi():
    """180 derajat dua kali harus kembali persis ke citra semula."""
    asli = np.arange(2 * 3 * 3, dtype=np.uint8).reshape(2, 3, 3)
    assert np.array_equal(E.rotate_image(E.rotate_image(asli, 180), 180), asli)
    assert np.array_equal(E.rotate_image(E.rotate_image(asli, 90), 270), asli)


def test_rotasi_selain_kelipatan_sembilan_puluh_ditolak():
    with pytest.raises(ValueError, match="kelipatan 90"):
        E.rotate_image(FOTO, 45)


def test_foto_tegak_tidak_membayar_rotasi(cfg):
    """Tanggal ketemu pada percobaan pertama, jadi tidak ada OCR tambahan."""
    ocr = OcrPalsu("EXP 03/12/2026")
    hasil = pembaca(cfg, ocr).read(FOTO, today=HARI_INI)
    assert len(ocr.panggilan) == 1
    assert "rotated_deg" not in hasil.notes
    assert "rotations_tried" not in hasil.notes


def test_foto_terbalik_diputar_otomatis(cfg):
    """Percobaan pertama gagal, percobaan pada 180 derajat berhasil."""
    ocr = OcrPalsu("NETTO 250 G", "EXP 03/12/2026")
    hasil = pembaca(cfg, ocr).read(FOTO, today=HARI_INI)
    assert hasil.date.value == date(2026, 12, 3)
    assert hasil.notes["rotated_deg"] == 180
    assert len(ocr.panggilan) == 2


def test_rotasi_berhenti_pada_yang_pertama_berhasil(cfg):
    """90 baru dicoba setelah 180 gagal, dan 270 tidak pernah dicoba."""
    ocr = OcrPalsu("NETTO", "NETTO", "EXP 03/12/2026")
    hasil = pembaca(cfg, ocr).read(FOTO, today=HARI_INI)
    assert hasil.notes["rotated_deg"] == 90
    assert hasil.notes["rotations_tried"] == [180]
    assert len(ocr.panggilan) == 3


def test_semua_rotasi_gagal_tetap_menjawab(cfg):
    ocr = OcrPalsu("NETTO 250 G")
    hasil = pembaca(cfg, ocr).read(FOTO, today=HARI_INI)
    assert hasil.found is False
    assert hasil.notes["rotations_tried"] == [180, 90, 270]
    assert len(ocr.panggilan) == 4
    utt = E.expiry_utterance(hasil, HARI_INI)
    assert T.Clip("tulisan_bukan_tanggal") in utt


def test_rotasi_bisa_dimatikan_lewat_config(cfg):
    cfg["vision"]["expiry"]["rotate_retry"] = []
    ocr = OcrPalsu("NETTO 250 G")
    hasil = pembaca(cfg, ocr).read(FOTO, today=HARI_INI)
    assert len(ocr.panggilan) == 1
    assert "rotations_tried" not in hasil.notes


def test_rotasi_juga_berlaku_pada_jalur_zona(cfg):
    """Zona terdeteksi tetapi tanggalnya tidak terbaca; rotasi tetap dicoba."""
    ocr = OcrPalsu("NETTO", "NETTO", "EXP 03/12/2026")
    r = pembaca(cfg, ocr, kotak=[[100, 200, 300, 250]], skor=[0.9])
    hasil = r.read(FOTO, today=HARI_INI)
    assert hasil.date.value == date(2026, 12, 3)
    assert hasil.source == E.SOURCE_ZONE
    assert hasil.notes["rotated_deg"] == 180


def test_waktu_total_mencakup_rotasi(cfg):
    ocr = OcrPalsu("NETTO 250 G")
    hasil = pembaca(cfg, ocr).read(FOTO, today=HARI_INI)
    assert hasil.notes["total_s"] > 0


# --------------------------------------------------------------------------- zona mundur ke seluruh gambar

def test_zona_gagal_mundur_ke_seluruh_gambar(cfg):
    """Zona adalah petunjuk letak, bukan komitmen.

    Bukti dari foto sungguhan (30-09): ajinomoto terdeteksi zonanya dengan skor
    0,76 tetapi potongannya tidak terbaca, padahal OCR seluruh gambar membaca
    `110426` dengan benar. Sebelum ini sistem terkunci di jalur zona.
    """
    ocr = OcrPalsu("NETTO 250 G", "EXP 03/12/2026")
    r = pembaca(cfg, ocr, kotak=[[100, 200, 300, 250]], skor=[0.9])
    hasil = r.read(FOTO, today=HARI_INI)
    assert hasil.date.value == date(2026, 12, 3)
    assert hasil.source == E.SOURCE_FULL
    assert "zone_gagal" in hasil.notes


def test_zona_berhasil_tidak_mundur(cfg):
    ocr = OcrPalsu("EXP 03/12/2026", "01/01/2030")
    r = pembaca(cfg, ocr, kotak=[[100, 200, 300, 250]], skor=[0.9])
    hasil = r.read(FOTO, today=HARI_INI)
    assert hasil.source == E.SOURCE_ZONE
    assert "zone_gagal" not in hasil.notes
    assert len(ocr.panggilan) == 1


def test_mundur_juga_gagal_hasil_zona_yang_dikembalikan(cfg):
    """Bila keduanya gagal, jawaban yang dikembalikan tetap dari jalur zona.

    Jalur zona lebih spesifik, jadi teksnya lebih berguna untuk didiagnosis
    daripada teks seluruh kemasan yang penuh komposisi dan klaim gizi.
    """
    ocr = OcrPalsu("NETTO 250 G")
    r = pembaca(cfg, ocr, kotak=[[100, 200, 300, 250]], skor=[0.9])
    hasil = r.read(FOTO, today=HARI_INI)
    assert hasil.found is False
    assert hasil.source == E.SOURCE_ZONE
    assert "zone_gagal" in hasil.notes


def test_mundur_bisa_dimatikan_lewat_config(cfg):
    cfg["vision"]["expiry"]["full_image_fallback"] = False
    cfg["vision"]["expiry"]["rotate_retry"] = []      # isolasi: rotasi juga bisa menyelamatkan
    ocr = OcrPalsu("NETTO 250 G", "EXP 03/12/2026")
    r = pembaca(cfg, ocr, kotak=[[100, 200, 300, 250]], skor=[0.9])
    hasil = r.read(FOTO, today=HARI_INI)
    assert hasil.found is False
    assert "zone_gagal" not in hasil.notes


def test_mundur_tidak_pernah_dinyatakan_yakin(cfg):
    """Jawaban dari seluruh gambar tetap dibacakan kurang yakin (PRD 8.8 langkah 6)."""
    ocr = OcrPalsu("NETTO 250 G", "EXP 03/12/2026")
    r = pembaca(cfg, ocr, kotak=[[100, 200, 300, 250]], skor=[0.9])
    hasil = r.read(FOTO, today=HARI_INI)
    assert hasil.confident is False
