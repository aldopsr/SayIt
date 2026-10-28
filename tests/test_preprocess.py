"""Tes pra-pemrosesan PRD 8.3 dengan gambar sintetis (tidak butuh foto asli)."""
import copy

import cv2
import numpy as np
import pytest

from sayit.config import load_config
from sayit.vision import preprocess as P


@pytest.fixture
def cfg():
    return copy.deepcopy(load_config())


@pytest.fixture
def steps(cfg):
    return cfg["vision"]["preprocess"]["steps"]


def kertas_bertulisan(h=400, w=600):
    """Kertas putih dengan baris-baris 'tulisan' hitam."""
    img = np.full((h, w, 3), 245, np.uint8)
    for y in range(40, h - 60, 40):
        cv2.rectangle(img, (60, y), (w - 60, y + 12), (20, 20, 20), -1)
    return img


def foto_kertas_miring():
    """Kertas difoto dari sudut: trapesium di atas meja gelap. Sudut asli diketahui.

    Kertasnya sengaja memenuhi ~70% bidang. Foto dokumen sungguhan memang begitu,
    dan `perspective.min_area_ratio` justru mengandalkan sifat itu untuk membedakan
    halaman dari benda kecil yang kebetulan berbentuk segi empat.
    """
    latar = np.full((700, 900, 3), 40, np.uint8)
    kertas = kertas_bertulisan()
    sumber = np.float32([[0, 0], [599, 0], [599, 399], [0, 399]])
    tujuan = np.float32([[120, 70], [840, 40], [870, 660], [80, 620]])
    M = cv2.getPerspectiveTransform(sumber, tujuan)
    foto = cv2.warpPerspective(kertas, M, (900, 700), dst=latar.copy(),
                               borderMode=cv2.BORDER_TRANSPARENT)
    return foto, tujuan


def foto_uang():
    """Foto seukuran kamera HP: cukup besar agar langkah resize benar-benar bekerja."""
    foto = np.zeros((1800, 2400, 3), np.uint8)
    cv2.rectangle(foto, (600, 600), (1800, 1200), (120, 140, 160), -1)
    return foto


def rentang(a):
    return int(a.max()) - int(a.min())


# --------------------------------------------------------------------------- resize

def test_resize_hanya_memperkecil_dan_menjaga_rasio(steps):
    besar = np.zeros((1200, 2400, 3), np.uint8)
    hasil = P.resize(besar, steps["resize"])
    assert max(hasil.shape[:2]) == steps["resize"]["max_side"]
    assert hasil.shape[1] / hasil.shape[0] == pytest.approx(2.0, rel=0.01)

    kecil = np.zeros((300, 400, 3), np.uint8)
    assert P.resize(kecil, steps["resize"]) is kecil          # tidak diperbesar


# --------------------------------------------------------------------------- CLAHE

def test_clahe_menaikkan_kontras_citra_redup(steps):
    rng = np.random.default_rng(1)
    t = cv2.GaussianBlur(rng.normal(0, 1, (300, 300)), (0, 0), 3)
    t = (t - t.min()) / (t.max() - t.min())
    redup = (90 + t * 40).astype(np.uint8)                    # hanya memakai 90..130
    hasil = P.clahe(cv2.cvtColor(redup, cv2.COLOR_GRAY2BGR), steps["clahe"])
    assert hasil.std() > 2 * redup.std()
    assert rentang(hasil) > 2 * rentang(redup)


def test_clahe_bekerja_pada_citra_abu_abu(steps):
    abu = np.full((200, 200), 120, np.uint8)
    abu[50:150, 50:150] = 135
    hasil = P.clahe(abu, steps["clahe"])
    assert hasil.ndim == 2 and hasil.dtype == np.uint8


def test_clahe_menjaga_jumlah_kanal(steps):
    bgr = kertas_bertulisan()
    bgra = cv2.cvtColor(bgr, cv2.COLOR_BGR2BGRA)
    assert P.clahe(bgr, steps["clahe"]).shape[2] == 3
    hasil = P.clahe(bgra, steps["clahe"])
    assert hasil.shape[2] == 4
    assert np.array_equal(hasil[:, :, 3], bgra[:, :, 3])      # alpha tidak ikut diproses


# --------------------------------------------------------------------------- denoise

@pytest.fixture
def pasangan_derau():
    """(citra bersih, citra berderau) dengan derau Gaussian sigma 25."""
    rng = np.random.default_rng(0)
    bersih = np.full((300, 300, 3), 150, np.uint8)
    cv2.rectangle(bersih, (60, 60), (240, 240), (40, 40, 40), -1)
    berderau = np.clip(bersih.astype(np.int16) + rng.normal(0, 25, bersih.shape),
                       0, 255).astype(np.uint8)
    return bersih, berderau


def galat(a, b):
    return float(np.abs(a.astype(np.int16) - b.astype(np.int16)).mean())


def test_bilateral_mengurangi_derau(steps, pasangan_derau):
    bersih, berderau = pasangan_derau
    hasil = P.denoise(berderau, steps["denoise"])
    assert galat(hasil, bersih) < galat(berderau, bersih) / 2


def test_nlm_mengurangi_derau(steps, pasangan_derau):
    bersih, berderau = pasangan_derau
    params = copy.deepcopy(steps["denoise"])
    params["method"] = "nlm"
    hasil = P.denoise(berderau, params)
    assert galat(hasil, bersih) < galat(berderau, bersih) / 2


def test_kedua_metode_bisa_dipilih_dari_config(steps, pasangan_derau):
    """Bukti bahwa saklar method benar-benar mengganti algoritma, bukan sekadar nama."""
    _, berderau = pasangan_derau
    bil = copy.deepcopy(steps["denoise"]); bil["method"] = "bilateral"
    nlm = copy.deepcopy(steps["denoise"]); nlm["method"] = "nlm"
    assert not np.array_equal(P.denoise(berderau, bil), P.denoise(berderau, nlm))


def test_metode_denoise_tidak_dikenal_ditolak(steps, pasangan_derau):
    _, berderau = pasangan_derau
    params = copy.deepcopy(steps["denoise"])
    params["method"] = "gaussian"
    with pytest.raises(ValueError, match="tidak dikenal"):
        P.denoise(berderau, params)


def test_denoise_abu_abu_untuk_kedua_metode(steps):
    rng = np.random.default_rng(3)
    abu = np.clip(rng.normal(150, 20, (120, 120)), 0, 255).astype(np.uint8)
    for metode in ("bilateral", "nlm"):
        params = copy.deepcopy(steps["denoise"])
        params["method"] = metode
        hasil = P.denoise(abu, params)
        assert hasil.shape == abu.shape and hasil.ndim == 2


# --------------------------------------------------------------------------- perspektif

def test_kertas_tiruan_memenuhi_ambang_config(steps):
    """Jaga agar fixture dan ambang config tidak melenceng diam-diam.

    Saat `min_area_ratio` dinaikkan 0,25 -> 0,50, tiga tes gagal sekaligus dengan
    pesan yang tidak menyebut sebabnya sama sekali. Tes ini gagal lebih dulu dan
    langsung menunjuk penyebabnya.
    """
    foto, sudut_asli = foto_kertas_miring()
    luas = cv2.contourArea(P.order_corners(sudut_asli))
    rasio = luas / (foto.shape[0] * foto.shape[1])
    assert rasio > steps["perspective"]["min_area_ratio"], (
        f"kertas tiruan hanya {rasio:.1%} bidang, sedangkan ambangnya "
        f"{steps['perspective']['min_area_ratio']:.0%}: perbesar quad di foto_kertas_miring()")
    assert rasio < steps["perspective"]["max_area_ratio"]


def test_sudut_kertas_ditemukan(steps):
    foto, sudut_asli = foto_kertas_miring()
    quad = P.find_document_quad(foto, steps["perspective"])
    assert quad is not None
    assert np.abs(quad - P.order_corners(sudut_asli)).max() < 5      # toleransi 5 piksel


def test_warp_meluruskan_kertas(steps):
    foto, _ = foto_kertas_miring()
    hasil = P.perspective(foto, steps["perspective"])
    assert hasil.shape[:2] != foto.shape[:2]
    # latar meja yang gelap sudah terbuang, tinggal kertas terang
    assert hasil.mean() > foto.mean() + 40
    # baris tulisan kembali mendatar
    assert abs(P.skew_angle(hasil, steps["deskew"])) < 1.5


def test_tanpa_kertas_citra_dikembalikan_apa_adanya(steps):
    rng = np.random.default_rng(4)
    acak = rng.integers(0, 255, (300, 300, 3), dtype=np.uint8)
    assert P.find_document_quad(acak, steps["perspective"]) is None
    assert P.perspective(acak, steps["perspective"]) is acak


def test_urutan_sudut(steps):
    acak = np.array([[300, 200], [10, 10], [300, 10], [10, 200]], np.float32)
    ka, kn, kb, kib = P.order_corners(acak)
    assert tuple(ka) == (10, 10) and tuple(kn) == (300, 10)
    assert tuple(kb) == (300, 200) and tuple(kib) == (10, 200)


# --------------------------------------------------------------------------- kemiringan

@pytest.mark.parametrize("derajat", [-12, -7, -3, 3, 7, 12])
def test_deskew_meluruskan_dokumen(steps, derajat):
    miring = P.rotate(kertas_bertulisan(), derajat)
    assert P.skew_angle(miring, steps["deskew"]) == pytest.approx(-derajat, abs=1.0)
    lurus = P.deskew(miring, steps["deskew"])
    assert abs(P.skew_angle(lurus, steps["deskew"])) < 1.0


def test_sudut_ekstrem_dianggap_salah_ukur(steps):
    """Di atas max_angle_deg, rotasi dibatalkan: minAreaRect mudah tertipu latar ramai."""
    miring = P.rotate(kertas_bertulisan(), 35)
    assert P.skew_angle(miring, steps["deskew"]) == 0.0
    assert P.deskew(miring, steps["deskew"]) is miring


def test_sudut_sangat_kecil_tidak_diputar(steps):
    lurus = kertas_bertulisan()
    assert P.deskew(lurus, steps["deskew"]) is lurus      # hemat blur interpolasi


def test_citra_polos_tidak_membuat_deskew_gagal(steps):
    polos = np.zeros((100, 100), np.uint8)
    assert P.skew_angle(polos, steps["deskew"]) == 0.0


# --------------------------------------------------------------------------- upscale

def test_upscale_dua_kali(steps):
    crop = np.full((30, 90, 3), 200, np.uint8)
    hasil = P.upscale(crop, steps["upscale"])
    assert hasil.shape[:2] == (60, 180)


def test_faktor_satu_tidak_mengubah_apa_pun(steps):
    crop = np.full((30, 90, 3), 200, np.uint8)
    params = copy.deepcopy(steps["upscale"]); params["factor"] = 1.0
    assert P.upscale(crop, params) is crop


# --------------------------------------------------------------------------- binarisasi

def test_threshold_menghasilkan_citra_biner(steps):
    kertas = kertas_bertulisan()
    hasil = P.threshold(kertas, steps["threshold"])
    assert hasil.ndim == 2
    assert set(np.unique(hasil).tolist()) <= {0, 255}


def test_threshold_adaptif_tahan_gradien_cahaya(steps):
    """Keunggulan adaptive atas threshold global: sisi gelap dan terang sama-sama terbaca."""
    kertas = cv2.cvtColor(kertas_bertulisan(), cv2.COLOR_BGR2GRAY)
    gradien = np.linspace(-70, 70, kertas.shape[1], dtype=np.float32)
    tidak_rata = np.clip(kertas + gradien[None, :], 0, 255).astype(np.uint8)
    biner = P.threshold(tidak_rata, steps["threshold"])
    kiri = (biner[:, :100] == 0).sum()
    kanan = (biner[:, -100:] == 0).sum()
    assert kiri > 0 and kanan > 0                      # tulisan terbaca di kedua sisi


def test_block_size_harus_ganjil_dan_cukup_besar(steps):
    kertas = kertas_bertulisan()
    for nilai, pesan in ((30, "ganjil"), (1, "minimal 3")):
        params = copy.deepcopy(steps["threshold"]); params["block_size"] = nilai
        with pytest.raises(ValueError, match=pesan):
            P.threshold(kertas, params)


# --------------------------------------------------------------------------- morfologi

@pytest.fixture
def teks_dot_matrix():
    """Tiga baris cetakan titik-titik, seperti kode kedaluwarsa pada kemasan."""
    img = np.full((120, 400), 255, np.uint8)
    for x in range(40, 360, 7):
        for y in (40, 60, 80):
            cv2.circle(img, (x, y), 2, 0, -1)
    return img


def jumlah_komponen(biner):
    return cv2.connectedComponentsWithStats(cv2.bitwise_not(biner), 8)[0] - 1


def test_closing_menyambung_titik_cetakan(steps, teks_dot_matrix):
    biner = P.threshold(teks_dot_matrix, steps["threshold"])
    sebelum = jumlah_komponen(biner)
    sesudah = jumlah_komponen(P.morphology(biner, steps["morphology"]))
    assert sebelum > 100          # masih terpisah menjadi ratusan titik
    assert sesudah <= 5           # menyambung menjadi baris-baris


def test_dilate_menebalkan_tinta(steps, teks_dot_matrix):
    biner = P.threshold(teks_dot_matrix, steps["threshold"])
    params = copy.deepcopy(steps["morphology"]); params["op"] = "dilate"
    hasil = P.morphology(biner, params)
    assert (hasil == 0).sum() > (biner == 0).sum()      # piksel tinta bertambah


def test_operasi_morfologi_tidak_dikenal_ditolak(steps, teks_dot_matrix):
    params = copy.deepcopy(steps["morphology"]); params["op"] = "erode"
    with pytest.raises(ValueError, match="tidak dikenal"):
        P.morphology(teks_dot_matrix, params)


# --------------------------------------------------------------------------- perangkai dan ablasi

def test_rangkaian_bawaan_lengkap(cfg):
    """Setiap nama di chains harus benar-benar ada sebagai langkah."""
    pre = cfg["vision"]["preprocess"]
    for nama_rantai, langkah in pre["chains"].items():
        assert langkah, f"rangkaian {nama_rantai} kosong"
        for l in langkah:
            assert l in P.STEPS, f"{nama_rantai}: langkah {l!r} tidak ada di STEPS"
            assert l in pre["steps"], f"{nama_rantai}: langkah {l!r} tidak ada di config"


def test_rangkaian_uang_berjalan(cfg):
    hasil = P.run_chain(foto_uang(), cfg, "uang")
    # CLAHE sengaja TIDAK ada di sini sejak 28-10: model dilatih pada gambar asli,
    # jadi menerapkannya saat inferensi membuat distribusi pakai != distribusi latih.
    # Lihat docs/keputusan-teknis.md. Jangan tambahkan kembali tanpa mengukur ulang.
    assert hasil.steps == ["resize"]
    assert hasil.notes["chain"] == "uang"
    assert max(hasil.image.shape[:2]) == cfg["vision"]["preprocess"]["steps"]["resize"]["max_side"]


def test_rangkaian_dokumen_mencatat_bukti(cfg):
    foto, _ = foto_kertas_miring()
    hasil = P.run_chain(foto, cfg, "dokumen")
    assert hasil.notes["document_found"] is True
    assert "skew_angle" in hasil.notes
    assert "perspective" in hasil.steps


def test_rangkaian_kedaluwarsa_membesarkan_tanpa_membinarisasi(cfg, teks_dot_matrix):
    """Sejak 30-09 rangkaian zona tidak lagi membinarisasi.

    Pada 9 potongan zona dari foto kemasan sungguhan, binarisasi memberi 0 jawaban
    benar dan hampir selalu menghasilkan teks kosong; `upscale+clahe` memberi 2.
    Threshold menghapus cetakan dot-matrix alih-alih menyambungnya.
    """
    hasil = P.run_chain(teks_dot_matrix, cfg, "kedaluwarsa")
    assert hasil.image.shape[0] == teks_dot_matrix.shape[0] * 2      # sudah di-upscale
    assert "threshold" not in hasil.steps and "morphology" not in hasil.steps
    assert len(np.unique(hasil.image)) > 2                           # masih bergradasi


def test_binarisasi_tetap_bekerja_bila_dipasang(cfg, teks_dot_matrix):
    """Langkahnya tidak dihapus, hanya dikeluarkan dari rangkaian bawaan."""
    cfg["vision"]["preprocess"]["chains"]["kedaluwarsa"] = [
        "upscale", "clahe", "denoise", "threshold", "morphology"]
    hasil = P.run_chain(teks_dot_matrix, cfg, "kedaluwarsa")
    assert set(np.unique(hasil.image).tolist()) <= {0, 255}
    assert "threshold" in hasil.steps and "morphology" in hasil.steps


def test_langkah_bisa_dimatikan_satu_per_satu(cfg):
    """Basis uji ablasi per langkah: saklar `enabled` tiap langkah harus benar-benar
    memotong langkah itu dan mencatatnya di `skipped`.

    Dulu diuji lewat `clahe` pada rangkaian `uang`; sejak CLAHE dibuang dari rangkaian
    itu (28-10) pengujiannya pindah ke `clahe` pada rangkaian `dokumen`, yang masih
    memakainya. Yang dijaga adalah MEKANISMENYA, bukan rangkaian tertentu.
    """
    cfg["vision"]["preprocess"]["steps"]["clahe"]["enabled"] = False
    foto, _ = foto_kertas_miring()
    hasil = P.run_chain(foto, cfg, "dokumen")
    assert "clahe" not in hasil.steps
    assert "clahe" in hasil.skipped
    # saklarnya selektif: langkah lain tetap berjalan. (Tidak menyebut langkah
    # tertentu karena `skipped` juga memuat langkah yang kebetulan tidak perlu
    # bekerja pada foto uji ini - `resize` pada gambar yang sudah kecil, misalnya.)
    assert hasil.steps, "mematikan clahe ikut mematikan langkah lain"


def test_seluruh_pra_pemrosesan_bisa_dimatikan(cfg):
    """Basis uji ablasi: citra harus lewat tanpa tersentuh sama sekali."""
    foto, _ = foto_kertas_miring()
    cfg["vision"]["preprocess"]["enabled"] = False
    hasil = P.run_chain(foto, cfg, "dokumen")
    assert hasil.image is foto
    assert hasil.steps == []
    assert hasil.skipped == P.chain_steps(cfg, "dokumen")


def test_urutan_langkah_bisa_diganti_untuk_percobaan(cfg, teks_dot_matrix):
    hasil = P.run_steps(teks_dot_matrix, cfg, ["threshold", "morphology"])
    assert hasil.steps == ["threshold", "morphology"]


def test_nama_yang_salah_ditolak_tegas(cfg, teks_dot_matrix):
    with pytest.raises(KeyError):
        P.run_chain(teks_dot_matrix, cfg, "belanja")
    with pytest.raises(KeyError):
        P.run_steps(teks_dot_matrix, cfg, ["sharpen"])


def test_citra_kosong_ditolak(cfg):
    with pytest.raises(ValueError):
        P.run_chain(np.zeros((0, 0), np.uint8), cfg, "uang")


def test_langkah_aktif_yang_tidak_mengubah_apa_pun_dicatat_sebagai_skipped(cfg):
    """Foto yang sudah kecil tidak perlu di-resize; laporan harus jujur soal itu."""
    kecil = np.zeros((300, 400, 3), np.uint8)
    cv2.rectangle(kecil, (100, 100), (300, 200), (120, 140, 160), -1)
    hasil = P.run_chain(kecil, cfg, "uang")
    assert "resize" in hasil.skipped
    assert "resize" not in hasil.steps
