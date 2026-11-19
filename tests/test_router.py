import csv
from pathlib import Path

import pytest

from sayit.intent import keywords as K
from sayit.intent.router import IntentRouter

ROUTER = IntentRouter()
DATA = Path(__file__).parent / "data" / "fase0_transkrip_small.csv"

REFERENSI = [
    ("berapa nominal uang ini", K.UANG),
    ("tolong hitung uang kembalian saya", K.UANG),
    ("ini uang berapa rupiah", K.UANG),
    ("tolong bacakan tulisan di kertas ini", K.BACA),
    ("apa isi surat ini", K.BACA),
    ("baca dokumennya", K.BACA),
    ("kapan tanggal kedaluwarsanya", K.KEDALUWARSA),
    ("produk ini sudah expired belum", K.KEDALUWARSA),
    ("susu ini masih bisa diminum sampai kapan", K.KEDALUWARSA),
    ("tolong baca tanggal kedaluwarsa di kemasan ini", K.KEDALUWARSA),
    ("ulangi", K.ULANGI),
    ("lanjut", K.LANJUT),
    ("foto lagi", K.FOTO_BARU),
    ("kamu bisa bantu apa saja", K.BANTUAN),
    ("ini benda apa", K.TIDAK_DIKENALI),
]

# Kalimat baru yang ditulis SETELAH aturan disusun dari data Fase 0.
# Putaran pertama: 24 dari 27 lolos. Tiga yang gagal ("tertulis", "masih layak", "basi")
# lalu dinaikkan menjadi kata kunci kuat, sehingga ketiganya tidak lagi termasuk data "belum terlihat".
KALIMAT_BARU = [
    ("ini duit berapa", K.UANG),
    ("uang saya ada berapa lembar", K.UANG),
    ("pecahan berapa ini", K.UANG),
    ("totalnya berapa rupiah", K.UANG),
    ("coba cek nominalnya", K.UANG),
    ("tolong bacain isi kertas ini", K.BACA),
    ("apa yang tertulis di sini", K.BACA),
    ("bisa bacakan suratnya", K.BACA),
    ("isi dokumen ini apa", K.BACA),
    ("tolong baca tulisannya", K.BACA),
    ("roti ini kadaluarsa kapan", K.KEDALUWARSA),
    ("obat ini masih layak nggak", K.KEDALUWARSA),
    ("kapan expirednya", K.KEDALUWARSA),
    ("sampai kapan boleh dimakan", K.KEDALUWARSA),
    ("sudah basi belum ya", K.KEDALUWARSA),
    ("tolong baca tanggal expired di kotak ini", K.KEDALUWARSA),
    ("sekali lagi", K.ULANGI),
    ("tadi apa ulangi dong", K.ULANGI),
    ("lanjutkan", K.LANJUT),
    ("bagian berikutnya", K.LANJUT),
    ("aku mau foto ulang", K.FOTO_BARU),
    ("ambil foto lagi", K.FOTO_BARU),
    ("bantuan", K.BANTUAN),
    ("cara pakai aplikasi ini gimana", K.BANTUAN),
    ("warna baju ini apa", K.TIDAK_DIKENALI),
    ("halo", K.TIDAK_DIKENALI),
    ("", K.TIDAK_DIKENALI),
]

# Kasus yang dulu gagal di simulasi awal: kata pendek yang mirip
KASUS_MIRIP = [
    ("berapa nominal uang ini", K.UANG),      # "uang" tidak boleh cocok dengan "ulang"
    ("ini uang berapa rupiah", K.UANG),
    ("foto lagi", K.FOTO_BARU),               # "lagi" tidak boleh memicu ULANGI
    ("baca dokumennya", K.BACA),              # akhiran -nya
    ("kapan tanggal kedaluwarsanya", K.KEDALUWARSA),
    ("susu ini masih bisa di minum sampai kapan", K.KEDALUWARSA),   # kata terpisah
]

# Prioritas saat skor seri / campuran (PRD 8.5)
KASUS_CAMPURAN = [
    ("tolong baca tanggal kedaluwarsa", K.KEDALUWARSA),
    ("berapa uang yang tertulis di surat ini", K.BACA),   # konteks surat lebih kuat daripada kata "uang"
    ("surat ini tanggal berapa", K.BACA),
    ("ulangi nominal uangnya", K.UANG),                   # kata tugas mengalahkan perintah kendali
]


@pytest.mark.parametrize("text, intent", REFERENSI)
def test_kalimat_referensi(text, intent):
    assert ROUTER.route(text).intent == intent


@pytest.mark.parametrize("text, intent", KALIMAT_BARU)
def test_kalimat_baru(text, intent):
    assert ROUTER.route(text).intent == intent


@pytest.mark.parametrize("text, intent", KASUS_MIRIP + KASUS_CAMPURAN)
def test_kasus_khusus(text, intent):
    assert ROUTER.route(text).intent == intent


def _fase0_rows():
    with open(DATA, encoding="utf-8") as f:
        return [(r["transkrip"], r["intent"]) for r in csv.DictReader(f)]


@pytest.mark.parametrize("text, intent", _fase0_rows())
def test_transkrip_asli_fase0(text, intent):
    """Transkrip faster-whisper small + prompt dari rekaman Fase 0."""
    assert ROUTER.route(text).intent == intent


def test_hasil_berisi_skor_dan_kata_cocok():
    res = ROUTER.route("Berapa NOMINAL uang ini?")
    assert res.text == "berapa nominal uang ini"
    assert res.scores[K.UANG] == 5
    assert set(res.matched[K.UANG]) == {"uang", "nominal", "berapa"}


@pytest.mark.parametrize("teks", ["keluar", "selesai", "tutup aplikasinya", "berhenti", "sudah cukup"])
def test_intent_keluar(teks):
    assert ROUTER.route(teks).intent == K.KELUAR


def test_keluar_tidak_menelan_kalimat_lain():
    """`sudah` sendirian terlalu lazim, jadi hanya `sudah cukup` yang dihitung."""
    r = ROUTER
    assert r.route("uang ini sudah berapa").intent != K.KELUAR


# --------------------------------------------------------------------------- kendali tombol

@pytest.mark.parametrize("teks", [
    "putar kamera", "ganti kamera", "balik kamera", "tukar kamera",
    "tolong putar kameranya", "pakai kamera belakang", "ganti ke kamera depan",
])
def test_putar_kamera_dikenali(teks):
    assert ROUTER.route(teks).intent == K.PUTAR_KAMERA


@pytest.mark.parametrize("teks", [
    "pilih berkas", "pilih file", "buka galeri", "ambil dari galeri",
    "unggah foto", "upload gambar",
])
def test_pilih_berkas_dikenali(teks):
    assert ROUTER.route(teks).intent == K.PILIH_BERKAS


def test_putar_tanpa_kamera_bukan_kendali_kamera():
    """`putar` sendirian terlalu umum; harus berpasangan dengan `kamera`."""
    assert ROUTER.route("putar lagunya").intent != K.PUTAR_KAMERA
    assert ROUTER.route("putar balik").intent != K.PUTAR_KAMERA


def test_kendali_kamera_tidak_menelan_pertanyaan_uang():
    """Kalimat tugas yang kebetulan menyebut kamera tetap harus jadi intent tugas."""
    assert ROUTER.route("ini uang berapa").intent == K.UANG
    assert ROUTER.route("bacakan tulisan di kertas ini").intent == K.BACA


def test_apa_itu_sayit_membuka_bantuan():
    """Pintu bantuan yang diumumkan sambutan. Ejaan nama aplikasi dari STT beragam."""
    for teks in ["apa itu sayit", "apa itu say it", "apa itu sai it",
                 "apa itu aplikasi ini", "saya belum paham"]:
        assert ROUTER.route(teks).intent == K.BANTUAN, teks


def test_sambutan_pendek_tetap_menyebut_pintu_bantuannya():
    """Sambutan sengaja dipendekkan; satu-satunya jalan ke daftar perintah adalah
    kalimat yang ia sebutkan sendiri. Kalau keduanya menyimpang, fitur bantuannya
    hilang tanpa ada yang sadar."""
    from sayit.response.templates import CLIP_TEXTS
    sambutan = CLIP_TEXTS["sambutan"].lower()
    assert "apa itu sayit" in sambutan
    assert ROUTER.route("apa itu sayit").intent == K.BANTUAN


# --------------------------------------------------------------------------- bantuan longgar

@pytest.mark.parametrize("teks", [
    # ejaan nama aplikasi yang keluar dari STT - "sayit" tidak ada di kamus Whisper
    "apa itu sayit", "apa itu sait", "apa itu sayid", "apa itu cyit", "apa itu sae it",
    # susunan kalimat lain yang sama maksudnya
    "sayit itu apa", "apa sih sayit itu", "ini aplikasi apa", "aplikasi ini buat apa",
    "ada fitur apa saja", "siapa kamu", "saya belum paham",
])
def test_bantuan_toleran_terhadap_variasi_ucapan(teks):
    """Diukur 22-10: 10 dari 15 ucapan wajar gagal karena BANTUAN dicocokkan persis.

    Melonggarkannya aman - salah memicu BANTUAN hanya membacakan satu kalimat,
    tidak seperti KELUAR yang menutup aplikasi.
    """
    assert ROUTER.route(teks).intent == K.BANTUAN


def test_prompt_stt_memuat_kata_yang_disuruh_diucapkan_aplikasi():
    """Kata yang tidak ada di initial_prompt jauh lebih sering salah ditranskrip.

    Sambutan menyuruh pengguna mengucapkan "apa itu SayIt", jadi "sayit" wajib
    ada di prompt - kalau tidak, pintu masuk pengguna baru dibiarkan rapuh.
    """
    from sayit.config import load_config
    prompt = load_config()["stt"]["initial_prompt"].lower()
    for kata in ["sayit", "bantuan", "keluar", "putar kamera", "pilih berkas"]:
        assert kata in prompt, f"{kata!r} tidak ada di initial_prompt"


# --------------------------------------------------------------- perintah suara senter

@pytest.mark.parametrize("ucapan", [
    "nyalakan senter", "hidupkan senter", "senter nyala", "senter on", "nyalakan lampu",
    "hidupkan lampu", "nyalakan flash", "nyalakan blitz", "nyalakan lampu kamera",
    "kasih cahaya", "senter", "flash", "blitz", "tolong nyalakan senternya",
])
def test_senter_nyala(ucapan):
    assert ROUTER.route(ucapan).intent == K.SENTER_NYALA


@pytest.mark.parametrize("ucapan", [
    "matikan senter", "senter mati", "senter off", "matikan lampu", "matikan flash",
    "matikan blitz", "matikan lampu kamera", "senternya matikan", "senternya mati",
    "sudah terang", "tolong matikan senternya",
])
def test_senter_mati(ucapan):
    assert ROUTER.route(ucapan).intent == K.SENTER_MATI


def test_matikan_senter_tidak_boleh_terbaca_nyalakan():
    """Regresi: "matikan senter" memuat kata kunci "senter" milik SENTER_NYALA.

    Pada bobot sama skornya SERI dan pemenangnya ditentukan urutan daftar, dan
    sebelum diperbaiki yang menang SENTER_NYALA - yaitu menyalakan senter ketika
    pengguna minta dimatikan. Pengguna tunanetra tidak bisa melihat keadaannya,
    jadi kesalahan itu tidak akan pernah ia sadari. Dijaga dua lapis: bobot 3
    pada frasa "matikan", dan SENTER_MATI diletakkan sebelum SENTER_NYALA.
    """
    for ucapan in ("matikan senter", "senternya matikan", "matikan lampu kamera"):
        assert ROUTER.route(ucapan).intent == K.SENTER_MATI, ucapan


def test_senter_tidak_menelan_intent_tugas():
    assert ROUTER.route("uang ini berapa").intent == K.UANG
    assert ROUTER.route("bacakan tulisannya").intent == K.BACA
    assert ROUTER.route("kapan kedaluwarsanya").intent == K.KEDALUWARSA
