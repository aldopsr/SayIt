"""Tes modul uang (PRD 8.6).

Semua tes memakai model tiruan, jadi lulus di laptop yang belum punya
`models/best_money.pt`. Tes yang butuh bobot asli ditandai skip otomatis.
"""
import copy
import types

import numpy as np
import pytest

from sayit.config import load_config, project_path
from sayit.response import templates as T
from sayit.vision import money as M


@pytest.fixture
def cfg():
    return copy.deepcopy(load_config())


def det(nominal, score, box):
    return M.Detection(nominal=nominal, score=score, box=box)


# kotak acuan: satu lembar uang di kiri, satu di kanan, tidak bersinggungan
KIRI = (0.0, 0.0, 100.0, 50.0)
KANAN = (200.0, 0.0, 300.0, 50.0)


# --------------------------------------------------------------------------- geometri

def test_luas_dan_irisan():
    assert M.area(KIRI) == 5000
    assert M.area((10, 10, 10, 20)) == 0                 # kotak pipih tidak punya luas
    assert M.intersection_area(KIRI, KANAN) == 0
    assert M.intersection_area(KIRI, (50, 0, 150, 50)) == 2500


def test_iou():
    assert M.iou(KIRI, KIRI) == pytest.approx(1.0)
    assert M.iou(KIRI, KANAN) == 0.0
    assert M.iou(KIRI, (50, 0, 150, 50)) == pytest.approx(2500 / 7500)


def test_rasio_bersarang():
    dalam = (10, 10, 40, 40)
    assert M.contained_ratio(dalam, KIRI) == pytest.approx(1.0)
    assert M.contained_ratio(KIRI, dalam) == pytest.approx(900 / 5000)
    assert M.contained_ratio((0, 0, 0, 0), KIRI) == 0.0   # kotak kosong tidak meledak


# --------------------------------------------------------------------------- ambang skor

def ambang(cfg) -> float:
    """Skor minimum dari config. Tes mengikuti nilainya, bukan angka mati, supaya
    kalibrasi ambang tidak membuat tes palsu gagal atau palsu lulus."""
    return float(cfg["vision"]["money"]["score_min"])


def test_deteksi_lemah_dibuang(cfg):
    lemah = ambang(cfg) - 0.1
    dets = [det(50000, 0.9, KIRI), det(10000, lemah, KANAN)]
    hasil = M.postprocess(dets, cfg)
    assert hasil.counts == {50000: 1}
    assert hasil.notes["raw"] == 2 and hasil.notes["after_score"] == 1


def test_tepat_di_ambang_diterima(cfg):
    """Perbandingannya >=, jadi skor yang persis sama dengan ambang harus lolos."""
    hasil = M.postprocess([det(20000, ambang(cfg), KIRI)], cfg)
    assert hasil.counts == {20000: 1}


def test_semua_deteksi_lemah_berarti_tidak_yakin(cfg):
    """Beda dengan 'tidak ada uang': ada sesuatu yang terlihat, hanya tidak meyakinkan."""
    tertinggi = ambang(cfg) - 0.05
    hasil = M.postprocess([det(50000, tertinggi, KIRI), det(50000, tertinggi / 2, KANAN)], cfg)
    assert not hasil.confident
    assert hasil.counts == {}
    assert "ambang skor" in hasil.reason
    assert hasil.notes["best_score"] == pytest.approx(tertinggi)
    assert M.money_utterance(hasil) == [T.Clip("tidak_yakin_uang")]


def test_tanpa_deteksi_sama_sekali_berarti_tidak_ada_uang(cfg):
    hasil = M.postprocess([], cfg)
    assert hasil.confident and hasil.counts == {}
    assert M.money_utterance(hasil) == [T.Clip("tidak_ada_uang")]


# --------------------------------------------------------------------------- kotak bersarang

def test_kotak_bersarang_sekelas_dibuang(cfg):
    """Potret dan angka nominal kerap dianotasi sebagai kotak terpisah di dalam lembar."""
    lembar = det(100000, 0.9, (0, 0, 200, 100))
    potret = det(100000, 0.8, (20, 20, 80, 80))          # 100% di dalam lembar
    hasil = M.postprocess([lembar, potret], cfg)
    assert hasil.counts == {100000: 1}
    assert hasil.detections == [lembar]                  # lembar utuh yang dipertahankan
    assert hasil.notes["after_nested"] == 1


def test_lembar_utuh_dipertahankan_walau_skornya_lebih_rendah(cfg):
    lembar = det(50000, 0.6, (0, 0, 200, 100))
    potret = det(50000, 0.95, (20, 20, 80, 80))
    hasil = M.postprocess([lembar, potret], cfg)
    assert hasil.detections == [lembar]


def test_kotak_bersarang_beda_kelas_tidak_dibuang_oleh_aturan_ini(cfg):
    """Kotak bersarang beda kelas justru pertanda bermasalah, ditangani aturan konflik."""
    besar = det(100000, 0.9, (0, 0, 200, 100))
    kecil = det(1000, 0.9, (20, 20, 80, 80))
    sisa = M.drop_nested([besar, kecil], cfg["vision"]["money"]["nested_area_ratio"])
    assert len(sisa) == 2


def test_tumpang_tindih_sedikit_tidak_dianggap_bersarang(cfg):
    """Dua lembar bersebelahan yang ujungnya bersentuhan harus tetap terhitung dua."""
    a = det(20000, 0.9, (0, 0, 100, 50))
    b = det(20000, 0.9, (80, 0, 180, 50))                # hanya 20% luasnya beririsan
    hasil = M.postprocess([a, b], cfg)
    assert hasil.counts == {20000: 2}


def test_ambang_bersarang_diambil_dari_config(cfg):
    """Menguji `nested_area_ratio` SENDIRI, jadi penggabungan IoU dimatikan dulu.

    Kedua kotak ini ber-IoU 0,333, sehingga `same_class_iou` bawaan juga akan
    menggabungkannya - dan tes ini tidak akan lagi menguji apa yang dinamainya.
    """
    cfg["vision"]["money"]["same_class_iou"] = 0.0
    a = det(5000, 0.9, (0, 0, 100, 50))
    b = det(5000, 0.9, (50, 0, 150, 50))                 # 50% luas b di dalam a
    assert M.postprocess([a, b], cfg).counts == {5000: 2}
    cfg["vision"]["money"]["nested_area_ratio"] = 0.4
    assert M.postprocess([a, b], cfg).counts == {5000: 1}


# ------------------------------------------------------------------ penggabungan sekelas

def test_kotak_sekelas_bertindihan_digabung(cfg):
    """Mekanismenya bekerja bila DINYALAKAN; bawaannya mati (lihat config).

    Dibuat 06-10 untuk menangkap kotak ganda atas lembar yang sama, lalu terbukti
    tidak menyentuh kasus nyata: salah hitung yang ada berasal dari deteksi di
    wilayah foto berbeda (IoU 0,198), bukan kotak ganda. Tetap diuji supaya kalau
    nanti dinyalakan, perilakunya sudah terkunci.
    """
    cfg["vision"]["money"]["same_class_iou"] = 0.30
    # bertindihan 43% (IoU) tetapi TIDAK bersarang (0,60 < 0,85), jadi hanya
    # penggabungan IoU yang bisa menangkapnya
    a = det(100000, 0.70, (0, 0, 100, 100))
    b = det(100000, 0.66, (40, 0, 140, 100))
    assert M.contained_ratio(b.box, a.box) < 0.85
    assert M.postprocess([a, b], cfg).counts == {100000: 1}


def test_skor_tertinggi_yang_dipertahankan_saat_digabung(cfg):
    cfg["vision"]["money"]["same_class_iou"] = 0.30
    a = det(100000, 0.55, (0, 0, 100, 100))
    b = det(100000, 0.90, (40, 0, 140, 100))
    hasil = M.postprocess([a, b], cfg)
    assert hasil.counts == {100000: 1}
    assert hasil.detections[0].score == pytest.approx(0.90)


def test_lembar_terpisah_tidak_digabung(cfg):
    """Dua lembar yang tidak bersinggungan harus tetap dihitung dua."""
    a = det(50000, 0.9, (0, 0, 100, 100))
    b = det(50000, 0.9, (300, 0, 400, 100))
    assert M.postprocess([a, b], cfg).counts == {50000: 2}


def test_penggabungan_mati_secara_bawaan(cfg):
    """Nilai bawaannya 0 karena sapuan 06-10 menunjukkan nol efek pada 35 foto,
    sedangkan risikonya pada foto banyak lembar belum bisa diuji."""
    assert cfg["vision"]["money"]["same_class_iou"] == 0.0
    a = det(100000, 0.70, (0, 0, 100, 100))
    b = det(100000, 0.66, (40, 0, 140, 100))
    assert M.postprocess([a, b], cfg).counts == {100000: 2}


def test_ambang_penggabungan_diambil_dari_config(cfg):
    a = det(5000, 0.9, (0, 0, 100, 50))
    b = det(5000, 0.8, (50, 0, 150, 50))                 # IoU 0,333
    cfg["vision"]["money"]["same_class_iou"] = 0.5
    assert M.postprocess([a, b], cfg).counts == {5000: 2}
    cfg["vision"]["money"]["same_class_iou"] = 0.3
    assert M.postprocess([a, b], cfg).counts == {5000: 1}


def test_dua_kotak_identik_dihitung_satu(cfg):
    a = det(10000, 0.9, KIRI)
    b = det(10000, 0.7, KIRI)
    assert M.postprocess([a, b], cfg).counts == {10000: 1}


# --------------------------------------------------------------------------- konflik antar-kelas

def test_dua_kelas_bertindihan_menjadi_tidak_yakin(cfg):
    """Satu lembar tidak mungkin punya dua nominal sekaligus."""
    a = det(50000, 0.9, (0, 0, 100, 50))
    b = det(100000, 0.8, (5, 0, 105, 50))                # IoU tinggi, kelas berbeda
    hasil = M.postprocess([a, b], cfg)
    assert not hasil.confident
    assert "50000/100000" in hasil.reason
    assert hasil.counts == {}
    assert M.money_utterance(hasil) == [T.Clip("tidak_yakin_uang")]


def test_kelas_berbeda_yang_terpisah_aman(cfg):
    hasil = M.postprocess([det(50000, 0.9, KIRI), det(10000, 0.9, KANAN)], cfg)
    assert hasil.confident
    assert hasil.counts == {50000: 1, 10000: 1}


def test_ambang_konflik_diambil_dari_config(cfg):
    a = det(1000, 0.9, (0, 0, 100, 50))
    b = det(2000, 0.9, (60, 0, 160, 50))                 # IoU sekitar 0,25
    assert M.postprocess([a, b], cfg).confident
    cfg["vision"]["money"]["conflict_iou"] = 0.2
    assert not M.postprocess([a, b], cfg).confident


# --------------------------------------------------------------------------- perhitungan dan ujaran

def test_hitung_dan_total_beberapa_lembar(cfg):
    dets = [det(50000, 0.9, (0, 0, 100, 50)),
            det(50000, 0.9, (200, 0, 300, 50)),
            det(10000, 0.9, (400, 0, 500, 50))]
    hasil = M.postprocess(dets, cfg)
    assert hasil.counts == {50000: 2, 10000: 1}
    assert hasil.total == 110000
    assert hasil.sheets == 3


def test_urutan_hitungan_dari_nominal_terbesar(cfg):
    dets = [det(1000, 0.9, (0, 0, 50, 25)),
            det(100000, 0.9, (200, 0, 300, 50)),
            det(20000, 0.9, (400, 0, 500, 50))]
    assert list(M.postprocess(dets, cfg).counts) == [100000, 20000, 1000]


def test_ujaran_menyebut_total(cfg):
    dets = [det(50000, 0.9, (0, 0, 100, 50)),
            det(50000, 0.9, (200, 0, 300, 50)),
            det(10000, 0.9, (400, 0, 500, 50))]
    teks = T.to_plain_text(M.money_utterance(M.postprocess(dets, cfg)))
    assert teks == ("Terdeteksi tiga lembar, dua lembar lima puluh ribu rupiah, "
                    "dan satu lembar sepuluh ribu rupiah. Totalnya seratus sepuluh ribu rupiah.")


def test_ujaran_satu_lembar(cfg):
    hasil = M.postprocess([det(20000, 0.9, KIRI)], cfg)
    assert T.to_plain_text(M.money_utterance(hasil)) == "Uang dua puluh ribu rupiah."


# --------------------------------------------------------------------------- nama kelas model

def test_nama_kelas_diubah_menjadi_nominal():
    assert M.parse_nominal("50000") == 50000
    assert M.parse_nominal(" 1000 ") == 1000


def test_nama_kelas_aneh_ditolak():
    with pytest.raises(ValueError, match="bukan nominal"):
        M.parse_nominal("lima puluh ribu")
    with pytest.raises(ValueError, match="di luar 7 kelas"):
        M.parse_nominal("75000")


# --------------------------------------------------------------------------- model tiruan

NAMES = {0: "1000", 1: "2000", 2: "5000", 3: "10000", 4: "20000", 5: "50000", 6: "100000"}


def hasil_palsu(kotak, skor, kelas):
    """Tiruan objek Results ultralytics: yang dipakai hanya .boxes dan .names."""
    boxes = types.SimpleNamespace(
        xyxy=np.array(kotak, dtype=np.float32).reshape(-1, 4),
        conf=np.array(skor, dtype=np.float32),
        cls=np.array(kelas, dtype=np.float32),
    )
    return [types.SimpleNamespace(boxes=boxes, names=NAMES)]


class ModelPalsu:
    """Mengganti YOLO. Mencatat argumen panggilan agar bisa diperiksa."""

    def __init__(self, path, kotak=(), skor=(), kelas=()):
        self.path = path
        self.names = NAMES
        self.panggilan = []
        self._jawaban = (list(kotak), list(skor), list(kelas))

    def __call__(self, image, **kwargs):
        self.panggilan.append({"shape": image.shape, **kwargs})
        return hasil_palsu(*self._jawaban)


def pabrik(**jawaban):
    def buat(path):
        buat.model = ModelPalsu(path, **jawaban)
        return buat.model
    return buat


def test_ekstraksi_dari_hasil_ultralytics():
    hasil = hasil_palsu([[0, 0, 100, 50], [200, 0, 300, 50]], [0.9, 0.8], [5, 3])
    dets = M.extract_detections(hasil, NAMES)
    assert [d.nominal for d in dets] == [50000, 10000]
    assert dets[0].score == pytest.approx(0.9)
    assert dets[0].box == (0.0, 0.0, 100.0, 50.0)


def test_ekstraksi_dari_hasil_kosong():
    assert M.extract_detections(hasil_palsu([], [], []), NAMES) == []
    assert M.extract_detections([], NAMES) == []


def test_detector_memakai_parameter_dari_config(cfg):
    f = pabrik(kotak=[[0, 0, 100, 50]], skor=[0.9], kelas=[5])
    d = M.MoneyDetector(cfg, model_factory=f)
    hasil = d.detect(np.zeros((600, 800, 3), np.uint8))
    assert hasil.counts == {50000: 1}
    panggilan = f.model.panggilan[-1]
    assert panggilan["device"] == cfg["vision"]["money"]["device"]
    assert panggilan["imgsz"] == cfg["vision"]["money"]["imgsz"]
    assert panggilan["max_det"] == cfg["vision"]["money"]["max_det"]


def test_detector_memanaskan_model_sekali(cfg):
    f = pabrik(kotak=[], skor=[], kelas=[])
    d = M.MoneyDetector(cfg, model_factory=f)
    d.load()
    assert len(f.model.panggilan) == 1                    # pemanasan
    d.load()
    assert len(f.model.panggilan) == 1                    # tidak dimuat ulang
    assert d.load_s is not None


def test_detector_menjalankan_pra_pemrosesan(cfg):
    f = pabrik(kotak=[], skor=[], kelas=[])
    d = M.MoneyDetector(cfg, model_factory=f)
    hasil = d.detect(np.zeros((1800, 2400, 3), np.uint8))
    assert hasil.notes["preprocess_steps"] == ["resize", "clahe"]
    # foto 2400 piksel sudah diperkecil sebelum sampai ke model
    assert f.model.panggilan[-1]["shape"][1] == cfg["vision"]["preprocess"]["steps"]["resize"]["max_side"]


def test_pra_pemrosesan_bisa_dilewati_untuk_ablasi(cfg):
    f = pabrik(kotak=[], skor=[], kelas=[])
    d = M.MoneyDetector(cfg, model_factory=f)
    d.detect(np.zeros((1800, 2400, 3), np.uint8), preprocess=False)
    assert f.model.panggilan[-1]["shape"] == (1800, 2400, 3)


def test_detector_mencatat_waktu_inferensi(cfg):
    f = pabrik(kotak=[[0, 0, 100, 50]], skor=[0.9], kelas=[5])
    d = M.MoneyDetector(cfg, model_factory=f)
    hasil = d.detect(np.zeros((600, 800, 3), np.uint8))
    assert hasil.notes["inference_s"] >= 0


def test_citra_kosong_ditolak(cfg):
    d = M.MoneyDetector(cfg, model_factory=pabrik())
    with pytest.raises(ValueError):
        d.detect(np.zeros((0, 0, 3), np.uint8))


def test_bobot_hilang_memberi_pesan_yang_jelas(cfg):
    cfg["vision"]["money"]["weights"] = "models/tidak_ada.pt"
    d = M.MoneyDetector(cfg)
    with pytest.raises(FileNotFoundError, match="models/README.md"):
        d.load()


# --------------------------------------------------------------------------- model asli (dilewati bila bobot tidak ada)

@pytest.mark.skipif(not project_path("models/best_money.pt").exists(),
                    reason="models/best_money.pt tidak ada di laptop ini")
def test_kelas_model_asli_sesuai_kesepakatan(cfg):
    """Menjaga agar bobot yang disalin anggota tim benar-benar model 7 kelas v2.1."""
    d = M.MoneyDetector(cfg)
    model = d.load(warmup=False)
    assert sorted(M.parse_nominal(n) for n in model.names.values()) == sorted(T.VALID_NOMINALS)
