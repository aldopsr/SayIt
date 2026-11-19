"""Tes quality gate dengan gambar sintetis (tidak butuh foto asli)."""
import copy

import cv2
import numpy as np
import pytest

from sayit.config import load_config
from sayit.response import templates as T
from sayit.vision import quality_gate as qg


@pytest.fixture
def cfg():
    # salinan dalam, agar tes yang mengubah toggle tidak bocor ke tes lain
    return copy.deepcopy(load_config())


def papan_catur(h=800, w=800, block=8, lo=60, hi=200):
    """Pola bergantian: banyak tepi tajam, mean di tengah, tidak ada piksel jenuh."""
    yy, xx = np.indices((h, w))
    return np.where(((yy // block) + (xx // block)) % 2 == 0, lo, hi).astype(np.uint8)


@pytest.fixture
def tajam():
    return papan_catur()


# --------------------------------------------------------------------------- kasus dasar

def test_foto_tajam_lolos(tajam, cfg):
    laporan = qg.check_quality(tajam, cfg)
    assert laporan.ok
    assert laporan.issues == []
    assert laporan.main_issue is None


def test_foto_buram_ditolak(tajam, cfg):
    buram = cv2.GaussianBlur(tajam, (31, 31), 10)
    laporan = qg.check_quality(buram, cfg)
    assert not laporan.ok
    assert laporan.kinds == ["buram"]
    assert laporan.metrics["blur_variance"] < cfg["vision"]["quality_gate"]["blur"]["min_variance"]


def test_foto_gelap_ditolak_dan_disebut_gelap_bukan_buram(cfg):
    gelap = np.full((800, 800), 30, np.uint8)
    laporan = qg.check_quality(gelap, cfg)
    assert not laporan.ok
    # frame gelap rata juga rendah variance-nya, tetapi saran yang berguna adalah "gelap"
    assert "buram" in laporan.kinds
    assert laporan.main_issue.kind == "gelap"


def test_foto_terlalu_terang_ditolak(cfg):
    terang = np.full((800, 800), 252, np.uint8)      # betul-betul terbakar cahaya
    laporan = qg.check_quality(terang, cfg)
    assert not laporan.ok
    assert laporan.main_issue.kind == "terang"


def kertas_putih(latar=240):
    """Halaman dokumen: sebagian besar kertas putih, tulisan hitam tipis."""
    img = np.full((1000, 700), latar, np.uint8)
    for y in range(80, 900, 45):
        img[y:y + 14, 70:630] = 25
    return img


@pytest.mark.parametrize("latar", [225, 230, 235, 240])
def test_foto_dokumen_kertas_putih_tidak_ditolak(latar, cfg):
    """Regresi: ambang PRD 220 menolak halaman putih yang sah.

    Pada latar 230-240 tidak ada satu pun piksel jenuh dan tulisannya tajam,
    tetapi rata-rata intensitasnya memang tinggi karena kertasnya putih.
    Penjaga silau yang sebenarnya adalah proporsi piksel jenuh, bukan rata-rata.
    """
    laporan = qg.check_quality(kertas_putih(latar), cfg)
    assert laporan.metrics["saturated_ratio"] == 0.0
    assert laporan.ok, f"latar {latar} ditolak: {laporan.kinds}"


def test_kertas_putih_yang_terbakar_cahaya_tetap_ditolak(cfg):
    """Batasnya tetap ada: halaman yang benar-benar silau harus tertangkap."""
    laporan = qg.check_quality(kertas_putih(255), cfg)
    assert not laporan.ok
    assert laporan.main_issue.kind == "terang"
    assert laporan.metrics["saturated_ratio"] > 0.25


def test_silau_lokal_ditolak_walau_mean_wajar(tajam, cfg):
    """Setengah frame jenuh karena pantulan: mean masih di bawah ambang, tetap ditolak."""
    silau = tajam.copy()
    silau[:, :400] = 255
    laporan = qg.check_quality(silau, cfg)
    assert laporan.metrics["mean"] < cfg["vision"]["quality_gate"]["bright"]["min_mean"]
    assert laporan.metrics["saturated_ratio"] == pytest.approx(0.5)
    assert laporan.main_issue.kind == "terang"


def test_resolusi_kecil_ditolak(tajam, cfg):
    kecil = cv2.resize(tajam, (320, 240), interpolation=cv2.INTER_AREA)
    laporan = qg.check_quality(kecil, cfg)
    assert not laporan.ok
    assert laporan.main_issue.kind == "kecil"
    assert laporan.metrics["short_side"] == 240


def test_tepat_di_ambang_resolusi_masih_lolos(tajam, cfg):
    batas = cfg["vision"]["quality_gate"]["resolution"]["min_short_side"]
    pas = cv2.resize(tajam, (batas + 100, batas), interpolation=cv2.INTER_AREA)
    assert qg.check_quality(pas, cfg).ok


# --------------------------------------------------------------------------- normalisasi skala

def test_ambang_blur_tidak_bergantung_resolusi(tajam):
    """Inti keputusan: foto sama pada dua resolusi harus menghasilkan nilai blur yang sebanding.
    Tanpa normalisasi, variance mentahnya berbeda beberapa kali lipat."""
    besar = cv2.resize(tajam, (2400, 2400), interpolation=cv2.INTER_AREA)
    mentah_kecil = cv2.Laplacian(tajam, cv2.CV_64F).var()
    mentah_besar = cv2.Laplacian(besar, cv2.CV_64F).var()
    assert mentah_kecil > 3 * mentah_besar          # bukti masalahnya nyata

    norm_kecil = qg.blur_variance(tajam, 720)
    norm_besar = qg.blur_variance(besar, 720)
    assert norm_besar == pytest.approx(norm_kecil, rel=0.05)


def test_resize_hanya_memperkecil(tajam):
    assert qg.resize_short_side(tajam, 720).shape[0] == 720
    assert qg.resize_short_side(tajam, 2000).shape == tajam.shape      # tidak diperbesar
    assert qg.resize_short_side(tajam, 0).shape == tajam.shape         # normalisasi dimatikan


# --------------------------------------------------------------------------- toggle untuk uji ablasi

def test_pemeriksaan_blur_bisa_dimatikan(tajam, cfg):
    buram = cv2.GaussianBlur(tajam, (31, 31), 10)
    assert not qg.check_quality(buram, cfg).ok
    cfg["vision"]["quality_gate"]["blur"]["enabled"] = False
    laporan = qg.check_quality(buram, cfg)
    assert laporan.ok
    # metrik tetap dihitung meski pemeriksaannya mati, supaya bisa dicatat saat ablasi
    assert laporan.metrics["blur_variance"] < cfg["vision"]["quality_gate"]["blur"]["min_variance"]


def test_seluruh_gate_bisa_dimatikan(cfg):
    gelap = np.full((100, 100), 5, np.uint8)
    cfg["vision"]["quality_gate"]["enabled"] = False
    laporan = qg.check_quality(gelap, cfg)
    assert laporan.ok and laporan.issues == []
    assert laporan.metrics["short_side"] == 100          # metrik tetap tersedia


def test_ambang_diambil_dari_config_bukan_angka_ajaib(tajam, cfg):
    cfg["vision"]["quality_gate"]["blur"]["min_variance"] = 1_000_000.0
    laporan = qg.check_quality(tajam, cfg)
    assert laporan.main_issue.kind == "buram"
    assert laporan.main_issue.threshold == 1_000_000.0


# --------------------------------------------------------------------------- bentuk masukan

def test_menerima_bgr_dan_bgra(tajam, cfg):
    bgr = cv2.cvtColor(tajam, cv2.COLOR_GRAY2BGR)
    bgra = cv2.cvtColor(tajam, cv2.COLOR_GRAY2BGRA)
    assert qg.check_quality(bgr, cfg).ok
    assert qg.check_quality(bgra, cfg).ok
    assert qg.to_gray(bgr).ndim == 2


def test_citra_kosong_ditolak_tegas(cfg):
    with pytest.raises(ValueError):
        qg.check_quality(np.zeros((0, 0), np.uint8), cfg)
    with pytest.raises(ValueError):
        qg.to_gray(None)


# --------------------------------------------------------------------------- jembatan ke suara

def test_setiap_masalah_punya_klip_suara():
    for kind in qg.ISSUE_ORDER:
        assert qg.CLIP_KEYS[kind] in T.FIXED_PHRASES


def test_respons_suara_untuk_foto_gelap(cfg):
    gelap = np.full((800, 800), 30, np.uint8)
    utt = qg.quality_response(qg.check_quality(gelap, cfg))
    assert utt == [T.Clip("foto_gelap")]
    assert "terlalu gelap" in T.to_plain_text(utt)


def test_respons_suara_menolak_foto_yang_lolos(tajam, cfg):
    with pytest.raises(ValueError):
        qg.quality_response(qg.check_quality(tajam, cfg))


# ------------------------------------------------- penanda objek terpotong tepi bingkai

BINGKAI = (600, 800, 3)         # tinggi 600, lebar 800 -> margin 2% = 16 x 12 px


def test_kotak_di_tengah_tidak_terpotong():
    assert qg.terpotong_tepi([(100, 100, 700, 500)], BINGKAI, 0.02) is False


def test_kotak_menempel_tepi_kanan_terpotong():
    assert qg.terpotong_tepi([(100, 100, 790, 500)], BINGKAI, 0.02) is True


def test_kotak_menempel_tepi_atas_terpotong():
    assert qg.terpotong_tepi([(100, 5, 700, 500)], BINGKAI, 0.02) is True


def test_kotak_seluruh_bingkai_terpotong():
    """Kasus uji lapangan 12-11: dua lembar jadi kotak seukuran bingkai."""
    assert qg.terpotong_tepi([(0, 0, 800, 600)], BINGKAI, 0.02) is True


def test_satu_kotak_terpotong_sudah_cukup():
    assert qg.terpotong_tepi([(100, 100, 700, 500), (0, 100, 300, 500)], BINGKAI, 0.02) is True


def test_tanpa_kotak_tidak_menuduh_terpotong():
    assert qg.terpotong_tepi([], BINGKAI, 0.02) is False


def test_citra_tanpa_ukuran_tidak_meledak():
    assert qg.terpotong_tepi([(0, 0, 1, 1)], (0, 0, 3), 0.02) is False
