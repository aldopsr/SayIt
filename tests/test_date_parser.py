"""Tes parser tanggal kedaluwarsa (PRD 8.8.1).

PRD mewajibkan unit test untuk setiap format yang didukung. Tidak butuh data,
model, atau internet.
"""
import copy
from datetime import date

import pytest

from sayit.config import load_config
from sayit.response import templates as T
from sayit.vision import date_parser as D

HARI_INI = date(2026, 9, 18)          # tanggal acuan tetap, agar tes tidak berubah seiring waktu


@pytest.fixture
def cfg():
    return copy.deepcopy(load_config())


def urai(teks, cfg, today=HARI_INI):
    return D.parse_expiry(teks, today, cfg)


# --------------------------------------------------------------------------- setiap format PRD

@pytest.mark.parametrize("teks, harapan", [
    ("03/12/2026", date(2026, 12, 3)),          # DD/MM/YYYY
    ("03-12-26", date(2026, 12, 3)),            # DD-MM-YY
    ("03.12.2026", date(2026, 12, 3)),          # DD.MM.YYYY
    ("2026.12.03", date(2026, 12, 3)),          # YYYY.MM.DD
    ("3/12/2026", date(2026, 12, 3)),           # hari satu digit
    ("31-12-2026", date(2026, 12, 31)),
])
def test_format_hari_bulan_tahun(teks, harapan, cfg):
    hasil = urai(teks, cfg)
    assert hasil.value == harapan
    assert hasil.month_only is False


@pytest.mark.parametrize("teks, harapan", [
    ("12/2027", date(2027, 12, 31)),            # MM/YY(YY) -> akhir bulan
    ("12/27", date(2027, 12, 31)),
    ("12 2027", date(2027, 12, 31)),            # MM YYYY
    ("02/2028", date(2028, 2, 29)),             # akhir Februari tahun kabisat
    ("02/2027", date(2027, 2, 28)),
])
def test_format_bulan_tahun_tanpa_hari(teks, harapan, cfg):
    hasil = urai(teks, cfg)
    assert hasil.value == harapan
    assert hasil.month_only is True


@pytest.mark.parametrize("teks, harapan", [
    ("03 DES 2026", date(2026, 12, 3)),         # DD MMM YYYY, singkatan Indonesia
    ("03 DEC 2026", date(2026, 12, 3)),         # singkatan Inggris
    ("3 DESEMBER 2026", date(2026, 12, 3)),     # nama panjang
    ("3 DECEMBER 2026", date(2026, 12, 3)),
    ("15 AGU 2027", date(2027, 8, 15)),
    ("15 AUG 2027", date(2027, 8, 15)),
    ("01 MEI 2027", date(2027, 5, 1)),
    ("01 MAY 2027", date(2027, 5, 1)),
    ("20 OKT 2027", date(2027, 10, 20)),
    ("20 OCT 2027", date(2027, 10, 20)),
    ("05-JAN-2027", date(2027, 1, 5)),          # dengan pemisah
])
def test_format_dengan_nama_bulan(teks, harapan, cfg):
    assert urai(teks, cfg).value == harapan


@pytest.mark.parametrize("teks, harapan", [
    ("DES 2026", date(2026, 12, 31)),
    ("SEP 2027", date(2027, 9, 30)),
    ("MEI 2028", date(2028, 5, 31)),
    ("JANUARI 2027", date(2027, 1, 31)),
])
def test_nama_bulan_tanpa_hari(teks, harapan, cfg):
    hasil = urai(teks, cfg)
    assert hasil.value == harapan
    assert hasil.month_only is True


def test_seluruh_nama_bulan_dikenali(cfg):
    """Dua belas bulan, versi Indonesia dan Inggris, semuanya harus terbaca."""
    for nomor, nama_nama in D.MONTH_NAMES.items():
        for nama in nama_nama:
            hasil = urai(f"15 {nama} 2027", cfg)
            assert hasil.value == date(2027, nomor, 15), f"{nama} gagal"


# --------------------------------------------------------------------------- koreksi karakter OCR

@pytest.mark.parametrize("teks, harapan", [
    ("O3/12/2026", date(2026, 12, 3)),          # O -> 0
    ("03/I2/2026", date(2026, 12, 3)),          # I -> 1
    ("03/12/2O26", date(2026, 12, 3)),
    ("3l/12/2026", date(2026, 12, 31)),         # l -> 1
    ("0S/12/2026", date(2026, 12, 5)),          # S -> 5
    ("0B/12/2026", date(2026, 12, 8)),          # B -> 8
    ("O3/I2/2O26", date(2026, 12, 3)),          # beberapa sekaligus
])
def test_koreksi_karakter_ocr(teks, harapan, cfg):
    hasil = urai(teks, cfg)
    assert hasil.value == harapan
    assert hasil.candidates[0].corrected is True


def test_koreksi_tidak_merusak_nama_bulan(cfg):
    """SEP, OKT, DES, FEB berisi huruf yang bisa tertukar; nama bulan tidak boleh ikut dikoreksi."""
    for nama, nomor in (("SEP", 9), ("OKT", 10), ("DES", 12), ("FEB", 2)):
        hasil = urai(f"10 {nama} 2027", cfg)
        assert hasil.value == date(2027, nomor, 10), f"{nama} rusak"
        assert hasil.candidates[0].corrected is False


def test_kata_tanpa_angka_tidak_dibaca_sebagai_tanggal(cfg):
    """Tanpa penjaga ini, 'SI' menjadi 51 dan 'BOLA' menjadi 8014."""
    assert D.fix_ocr_digits("SI") == "51"        # koreksinya sendiri memang begitu
    assert urai("SI/BO/LOSI", cfg).value is None
    assert urai("BOLA BOLA", cfg).value is None


def test_fungsi_koreksi_terpisah_bisa_diuji():
    assert D.fix_ocr_digits("2O26") == "2026"
    assert D.fix_ocr_digits("3l") == "31"
    assert D.fix_ocr_digits("12") == "12"


# --------------------------------------------------------------------------- validasi

@pytest.mark.parametrize("teks", [
    "32/12/2026",       # hari tidak ada di kalender
    "31/02/2027",       # Februari tidak punya tanggal 31
    "29/02/2027",       # 2027 bukan tahun kabisat
    "00/12/2026",
])
def test_tanggal_tidak_sah_ditolak(teks, cfg):
    assert urai(teks, cfg).value is None


def test_tanggal_kabisat_yang_sah_diterima(cfg):
    assert urai("29/02/2028", cfg).value == date(2028, 2, 29)


@pytest.mark.parametrize("teks", [
    "01/01/2010",       # lebih dari 5 tahun ke belakang
    "01/01/2050",       # lebih dari 10 tahun ke depan
])
def test_di_luar_rentang_wajar_ditolak(teks, cfg):
    assert urai(teks, cfg).value is None


def test_batas_rentang_diambil_dari_config(cfg):
    assert urai("01/01/2040", cfg).value is None
    cfg["vision"]["date_parser"]["years_forward"] = 20
    assert urai("01/01/2040", cfg).value == date(2040, 1, 1)


def test_tahun_dua_digit_memakai_basis_dari_config(cfg):
    assert urai("03-12-27", cfg).value == date(2027, 12, 3)
    assert D.expand_year(27, cfg) == 2027
    assert D.expand_year(2027, cfg) == 2027


def test_akhir_bulan_dihitung_benar():
    assert D.end_of_month(2027, 2) == date(2027, 2, 28)
    assert D.end_of_month(2028, 2) == date(2028, 2, 29)
    assert D.end_of_month(2027, 4) == date(2027, 4, 30)
    assert D.end_of_month(2027, 12) == date(2027, 12, 31)


def test_rentang_aman_saat_hari_ini_29_februari(cfg):
    """today.replace(year=...) meledak pada 29 Februari bila tidak dijaga."""
    kabisat = date(2028, 2, 29)
    assert D.in_range(date(2030, 1, 1), kabisat, cfg) is True
    assert D.in_range(date(2020, 1, 1), kabisat, cfg) is False


# --------------------------------------------------------------------------- urutan hari dan bulan

def test_asumsi_hari_sebelum_bulan(cfg):
    """05/06/2027 diartikan 5 Juni, bukan 6 Mei (asumsi format Indonesia)."""
    assert urai("05/06/2027", cfg).value == date(2027, 6, 5)


def test_urutan_dibalik_bila_hari_dulu_tidak_masuk_akal(cfg):
    """25 tidak mungkin nomor bulan, jadi 05/25/2027 dibaca sebagai bulan-hari."""
    hasil = urai("05/25/2027", cfg)
    assert hasil.value == date(2027, 5, 25)
    assert hasil.candidates[0].swapped is True


def test_tidak_dibalik_bila_hari_dulu_sudah_masuk_akal(cfg):
    hasil = urai("03/12/2026", cfg)
    assert hasil.candidates[0].swapped is False


# --------------------------------------------------------------------------- penanda

@pytest.mark.parametrize("penanda", [
    "EXP", "EXPIRED", "ED", "BB", "BEST BEFORE", "USE BY",
    "KEDALUWARSA", "KADALUWARSA", "BAIK DIGUNAKAN SEBELUM",
])
def test_penanda_dikenali(penanda, cfg):
    hasil = urai(f"{penanda} 03/12/2026", cfg)
    assert hasil.value == date(2026, 12, 3)
    assert hasil.confident is True
    assert hasil.candidates[0].marker


def test_penanda_menang_atas_tanggal_produksi(cfg):
    """Kasus khas kemasan: tanggal produksi lebih dulu, kedaluwarsa bertanda EXP."""
    hasil = urai("MFG 01/01/2026 EXP 01/06/2027", cfg)
    assert hasil.value == date(2027, 6, 1)
    assert hasil.confident is True
    assert "penanda" in hasil.reason


def test_penanda_memilih_tanggal_lebih_awal_bila_memang_itu_yang_bertanda(cfg):
    """Penanda mengalahkan urutan kronologis, bukan sekadar memilih yang terjauh."""
    hasil = urai("EXP 01/06/2027 PROD 01/07/2027", cfg)
    assert hasil.value == date(2027, 6, 1)
    assert hasil.confident is True


def test_penanda_terlalu_jauh_tidak_dihitung(cfg):
    jauh = "EXP" + " " * 40 + "03/12/2026"
    assert urai(jauh, cfg).candidates[0].marker == ""


def test_jendela_penanda_diambil_dari_config(cfg):
    teks = "EXP" + " " * 30 + "03/12/2026"
    assert urai(teks, cfg).candidates[0].marker == ""
    cfg["vision"]["date_parser"]["marker_window"] = 40
    assert urai(teks, cfg).candidates[0].marker == "exp"


def test_penanda_tidak_tercomot_dari_tengah_kata(cfg):
    """'ED' tidak boleh terbaca dari kata 'EXPIRED' atau 'NETTO'."""
    hasil = urai("TERBUAT DARI BAHAN TERPILIH 03/12/2026", cfg)
    assert hasil.candidates[0].marker == ""


# --------------------------------------------------------------------------- beberapa tanggal

def test_dua_tanggal_tanpa_penanda_pilih_yang_terjauh(cfg):
    hasil = urai("01/01/2026 12/12/2027", cfg)
    assert hasil.value == date(2027, 12, 12)
    assert hasil.confident is False
    assert len(hasil.candidates) == 2
    assert "tanpa penanda" in hasil.reason


def test_dua_tanggal_berpenanda_dibacakan_keduanya(cfg):
    hasil = urai("EXP 01/06/2027 BB 01/07/2027", cfg)
    assert hasil.ambiguous is not None
    assert hasil.confident is False
    a, b = hasil.ambiguous
    assert (a.value, b.value) == (date(2027, 6, 1), date(2027, 7, 1))


def test_dua_penanda_pada_tanggal_yang_sama_tidak_dianggap_ambigu(cfg):
    hasil = urai("EXP 01/06/2027 BB 01/06/2027", cfg)
    assert hasil.ambiguous is None
    assert hasil.confident is True


def test_satu_tanggal_tanpa_penanda_tetap_dianggap_yakin(cfg):
    hasil = urai("03/12/2026", cfg)
    assert hasil.confident is True
    assert hasil.reason == "hanya satu tanggal ditemukan"


def test_kandidat_terurut_sesuai_posisi_di_teks(cfg):
    hasil = urai("12/12/2027 lalu 01/01/2026", cfg)
    assert [k.value for k in hasil.candidates] == [date(2027, 12, 12), date(2026, 1, 1)]


def test_pola_paling_lengkap_menang(cfg):
    """03/12/2026 tidak boleh ikut terbaca sebagai pasangan bulan-tahun 03/12."""
    hasil = urai("03/12/2026", cfg)
    assert len(hasil.candidates) == 1
    assert hasil.candidates[0].pattern == "dmy"
    assert hasil.month_only is False


def test_tanggal_serba_angka_tidak_dipisah_spasi(cfg):
    """Bila spasi diizinkan sebagai pemisah, '2026 12/12' terbaca sebagai satu tanggal
    yang melintasi dua tanggal berbeda, dan tanggal kedua hilang."""
    hasil = urai("01/01/2026 12/12/2027", cfg)
    assert len(hasil.candidates) == 2


# --------------------------------------------------------------------------- tidak ketemu

@pytest.mark.parametrize("teks", [
    "",
    "   ",
    "tidak ada tanggal di sini",
    "HARGA 12500 NETTO 250 G",
    "ISI 12 500",
])
def test_teks_tanpa_tanggal(teks, cfg):
    hasil = urai(teks, cfg)
    assert hasil.found is False
    assert hasil.candidates == []


# --------------------------------------------------------------------------- ujaran

def test_ujaran_tanggal_yakin(cfg):
    teks = T.to_plain_text(D.expiry_utterance(urai("EXP 03/12/2026", cfg), HARI_INI))
    assert teks == ("Tanggal kedaluwarsa tiga Desember dua ribu dua puluh enam. "
                    "Produk masih berlaku, sisa tujuh puluh enam hari.")


def test_ujaran_tanpa_hari_menyebut_berlaku_sampai(cfg):
    teks = T.to_plain_text(D.expiry_utterance(urai("12/2027", cfg), HARI_INI))
    assert teks.startswith("Berlaku sampai Desember dua ribu dua puluh tujuh.")


def test_ujaran_kurang_yakin(cfg):
    teks = T.to_plain_text(D.expiry_utterance(urai("01/01/2027 01/06/2027", cfg), HARI_INI))
    assert teks.startswith("Saya kurang yakin, tetapi tanggal yang terbaca adalah")


def test_ujaran_dua_tanggal_menyebut_keduanya(cfg):
    teks = T.to_plain_text(D.expiry_utterance(urai("EXP 01/06/2027 BB 01/07/2027", cfg), HARI_INI))
    assert "Saya menemukan dua tanggal." in teks
    assert "satu Juni dua ribu dua puluh tujuh" in teks
    assert "satu Juli dua ribu dua puluh tujuh" in teks


def test_ujaran_produk_sudah_lewat(cfg):
    teks = T.to_plain_text(D.expiry_utterance(urai("01/01/2026", cfg), HARI_INI))
    assert teks.endswith("Produk sudah melewati tanggal kedaluwarsa sejak dua ratus enam puluh hari lalu.")


def test_ujaran_hari_terakhir(cfg):
    teks = T.to_plain_text(D.expiry_utterance(urai("18/09/2026", cfg), HARI_INI))
    assert "hari terakhir" in teks


def test_ujaran_saat_tidak_ada_tulisan(cfg):
    assert D.expiry_utterance(urai("", cfg), HARI_INI) == [T.Clip("tidak_ada_tanggal")]


def test_ujaran_saat_ada_tulisan_tetapi_bukan_tanggal(cfg):
    """PRD 8.9: tulisannya tetap dibacakan, supaya pengguna bisa menilai sendiri."""
    utt = D.expiry_utterance(urai("NETTO 250 G", cfg), HARI_INI)
    assert T.Clip("tulisan_bukan_tanggal") in utt
    assert T.Text("NETTO 250 G") in utt


def test_semua_klip_ujaran_terdaftar(cfg):
    """Klip yang belum terdaftar di CLIP_TEXTS tidak akan ada file suaranya."""
    contoh = ["EXP 03/12/2026", "12/2027", "01/01/2026 01/06/2027",
              "EXP 01/06/2027 BB 01/07/2027", "01/01/2026", "18/09/2026", ""]
    for teks in contoh:
        utt = D.expiry_utterance(urai(teks, cfg), HARI_INI)
        for kunci in T.clip_keys(utt):
            assert kunci in T.CLIP_TEXTS, f"klip {kunci!r} belum terdaftar"


# --------------------------------------------------------------------------- penanda menempel tanggal

@pytest.mark.parametrize("teks, harapan", [
    ("BB 12/2027", date(2027, 12, 31)),          # B ada di tabel koreksi OCR
    ("BBE 12/2027", date(2027, 12, 31)),
    ("EXP 12/2027", date(2027, 12, 31)),
    ("ED 12/2027", date(2027, 12, 31)),
    ("BEST BEFORE 12/2027", date(2027, 12, 31)),
    ("BB 03/12/2026", date(2026, 12, 3)),
    ("SEBAIKNYA DIGUNAKAN SEBELUM 12/2027", date(2027, 12, 31)),
])
def test_penanda_tidak_menelan_tanggalnya(teks, harapan, cfg):
    """Regresi: huruf penanda yang ada di tabel koreksi OCR (O, I, L, S, B) pernah
    ikut tercocok sebagai angka, lalu menggeser pemindaian melewati tanggalnya."""
    hasil = urai(teks, cfg)
    assert hasil.value == harapan, f"{teks!r} gagal terbaca"


def test_kandidat_gagal_tidak_menggeser_pemindaian(cfg):
    """Teks sampah di depan tanggal tidak boleh membuat tanggalnya hilang."""
    assert urai("SBO 12/2027", cfg).value == date(2027, 12, 31)
    assert urai("ISI BERSIH 250 G BB 12/2027", cfg).value == date(2027, 12, 31)


# --------------------------------------------------------------------------- tanggal rapat tanpa pemisah

@pytest.mark.parametrize("teks, harapan", [
    ("EXP 210829", date(2029, 8, 21)),          # DDMMYY, bentuk paling lazim di kemasan
    ("EXP 010129", date(2029, 1, 1)),           # angka nol di depan tidak boleh hilang
    ("BB 21082029", date(2029, 8, 21)),         # DDMMYYYY
    ("BB 20290821", date(2029, 8, 21)),         # YYYYMMDD
    ("EXP 8 210829 ~ 04:12", date(2029, 8, 21)),   # apa adanya dari OCR kemasan tisu
])
def test_tanggal_rapat_dibaca(teks, harapan, cfg):
    assert urai(teks, cfg).value == harapan


@pytest.mark.parametrize("teks", [
    "210829",                        # tanpa penanda sama sekali
    "NO BETS 210829 ISI 250 G",      # nomor bets, penanda kedaluwarsa tidak ada
    "KODE 20290821",
])
def test_tanggal_rapat_tanpa_penanda_ditolak(teks, cfg):
    """Enam angka berurutan juga bisa nomor bets, kode produksi, atau barcode.

    Tanpa syarat penanda, sistem akan mengarang tanggal kedaluwarsa dari kode
    apa pun yang kebetulan berupa angka. Syaratnya dinyalakan eksplisit di sini:
    sejak 30-09 nilai bawaannya di config justru dimatikan, karena pada 21 foto
    sungguhan pelonggaran itu menambah 5 jawaban benar tanpa menambah satu pun
    jawaban salah. Tes ini menjaga aturannya tetap bekerja saat dinyalakan, dan
    mendokumentasikan apa yang kita tukar saat mematikannya.
    """
    cfg["vision"]["date_parser"]["require_marker_for_compact"] = True
    assert urai(teks, cfg).value is None


def test_tanggal_rapat_tidak_sah_ditolak(cfg):
    """Tidak sah pada kedua urutan, jadi tidak ada yang bisa diselamatkan."""
    assert urai("EXP 999999", cfg).value is None        # bulan 99 pada kedua urutan
    assert urai("EXP 003200", cfg).value is None        # bulan 32 pada kedua urutan


def test_urutan_kedua_dipakai_bila_yang_pertama_tidak_sah(cfg):
    """320829: 32 tidak mungkin hari, jadi dibaca terbalik sebagai YYMMDD.

    Keterbatasan yang disadari: kemasan yang memakai urutan tidak lazim bisa
    terbaca sebagai tanggal lain yang kebetulan sah. Penjaga utamanya adalah
    syarat penanda dan rentang tahun yang wajar.
    """
    assert urai("EXP 320829", cfg).value == date(2032, 8, 29)


def test_pemisah_tetap_menang_atas_pola_rapat(cfg):
    """21/08/29 harus dibaca pola bertanda pemisah, bukan dipecah jadi pola rapat."""
    hasil = urai("EXP 21/08/29", cfg)
    assert hasil.value == date(2029, 8, 21)
    assert hasil.candidates[0].pattern == "dmy"


# --------------------------------------------------------------------------- saklar penanda

def test_syarat_penanda_menolak_kode_bets(cfg):
    """Perilaku saat syarat penanda dinyalakan, apa pun nilai bawaannya di config."""
    cfg["vision"]["date_parser"]["require_marker_for_compact"] = True
    assert urai("NO BETS 210829 ISI 250 G", cfg).value is None


def test_pelonggaran_menerima_tanggal_rapat_tanpa_penanda(cfg):
    """Bukti dari foto sungguhan: `110426` pada kemasan ajinomoto terbaca OCR
    dengan benar lalu dibuang karena tidak ada kata penanda di dekatnya."""
    cfg["vision"]["date_parser"]["require_marker_for_compact"] = False
    assert urai("110426 110425", cfg).value == date(2026, 4, 11)


def test_pelonggaran_juga_menerima_yang_seharusnya_ditolak(cfg):
    """Harga dari pelonggaran itu, ditulis eksplisit supaya tidak terlupakan."""
    cfg["vision"]["date_parser"]["require_marker_for_compact"] = False
    assert urai("NO BETS 210829 ISI 250 G", cfg).value is not None


def test_pelonggaran_tidak_mengubah_tanggal_yang_berpemisah(cfg):
    """Saklar ini hanya menyentuh pola rapat, bukan seluruh parser."""
    for wajib in (True, False):
        cfg["vision"]["date_parser"]["require_marker_for_compact"] = wajib
        assert urai("EXP 03/12/2026", cfg).value == date(2026, 12, 3)
        assert urai("12/2027", cfg).value == date(2027, 12, 31)   # bulan-saja -> akhir bulan


def test_penanda_tetap_dihormati_saat_dilonggarkan(cfg):
    cfg["vision"]["date_parser"]["require_marker_for_compact"] = False
    assert urai("EXP 210829", cfg).value == date(2029, 8, 21)


# --------------------------------------------------------------------------- pemisah spasi

def test_tanggal_berpemisah_spasi_dengan_penanda(cfg):
    """Bukti dari foto sungguhan: PaddleOCR membaca `20261008` sebagai 'EXP :08 10 26'."""
    assert urai("EXP 06 03 2029", cfg).value == date(2029, 3, 6)
    assert urai("Baik digunakan sebelum : EXP :08 10 26 UDUS.", cfg).value == date(2026, 10, 8)


def test_spasi_tanpa_penanda_ditolak_secara_bawaan(cfg):
    assert cfg["vision"]["date_parser"]["require_marker_for_spaced"] is True
    assert urai("06 03 2029", cfg).value is None
    assert urai("NETTO 250 300 2029 G", cfg).value is None


def test_spasi_tanpa_penanda_diterima_bila_dilonggarkan(cfg):
    cfg["vision"]["date_parser"]["require_marker_for_spaced"] = False
    assert urai("06 03 2029", cfg).value == date(2029, 3, 6)


def test_dua_tanggal_berdampingan_tetap_terpisah(cfg):
    """REGRESI. Inilah sebabnya spasi tidak boleh masuk ke `SEP`.

    Dulu dengan spasi sebagai pemisah biasa, '01/01/2026 12/12/2027' terbaca
    sebagai SATU tanggal yang melintasi keduanya, dan tanggal kedua hilang.
    Pola `dmy_spasi` aman karena mewajibkan ketiga kelompok angka ada.
    """
    for wajib in (True, False):
        cfg["vision"]["date_parser"]["require_marker_for_spaced"] = wajib
        kandidat = D.find_candidates("01/01/2026 12/12/2027", HARI_INI, cfg)
        assert [k.text for k in kandidat] == ["01/01/2026", "12/12/2027"]


def test_spasi_tidak_melompati_baris(cfg):
    """Pemisahnya maksimum dua spasi dan bukan baris baru, agar kecocokan tidak
    menyatukan angka dari dua baris OCR yang tidak berhubungan."""
    cfg["vision"]["date_parser"]["require_marker_for_spaced"] = False
    assert urai("EXP 06\n03\n2029", cfg).value is None
    assert urai("EXP 06    03    2029", cfg).value is None       # empat spasi


def test_spasi_tidak_mengganggu_pemisah_lain(cfg):
    for teks in ("EXP 06/03/2029", "EXP 06.03.2029", "EXP 06-03-2029"):
        assert urai(teks, cfg).value == date(2029, 3, 6), teks


def test_spasi_memilih_urutan_hari_bulan(cfg):
    """Kebiasaan Indonesia: hari lebih dulu. 25 tidak mungkin bulan, jadi dibalik."""
    assert urai("EXP 25 05 2027", cfg).value == date(2027, 5, 25)
    assert urai("EXP 05 25 2027", cfg).value == date(2027, 5, 25)


def test_spasi_tanggal_tak_sah_ditolak(cfg):
    assert urai("EXP 32 13 2029", cfg).value is None


def test_spasi_menolak_hari_satu_digit(cfg):
    """Bacaan OCR yang terpotong tidak boleh menjadi tanggal.

    ovaltine terbaca `EXP : 2 09 27` padahal harinya 27; dengan hari satu digit
    diizinkan, sistem menjawab 2027-09-02. Tanggal cetak pada kemasan praktis
    selalu berangka nol di depan, jadi dua digit adalah syarat yang murah.
    """
    assert urai("EXP : 2 09 27 15820.", cfg).value is None
    # pola spasi tidak boleh ikut mencocokkan angka satu digit
    pola = [k.pattern for k in D.find_candidates("EXP 6 3 2029", HARI_INI, cfg)]
    assert "dmy_spasi" not in pola


def test_spasi_tetap_menerima_dua_digit(cfg):
    assert urai("EXP 08 10 26", cfg).value == date(2026, 10, 8)
    assert urai("EXP 06 03 2029", cfg).value == date(2029, 3, 6)


# --------------------------------------------------------------------------- klaim rentang

@pytest.mark.parametrize("teks", [
    "NETTO 12 29 2028 G",      # "12 29" sah sebagai Des 2029, padahal ini bukan tanggal
    "LOT 11 27 2028 XY",       # "11 27" sah sebagai Nov 2027
])
def test_rentang_mencurigakan_menekan_tafsiran_yang_lebih_lemah(teks, cfg):
    """Kandidat berpenjaga mengklaim rentangnya walau nanti dibuang. DISENGAJA.

    Pada 02-10 perilaku ini sempat dianggap bug dan "diperbaiki" dengan melepas
    rentangnya bila penandanya tidak ada. Hasilnya dua jawaban SALAH baru, karena
    pola bulan-tahun lalu menafsirkan dua angka pertama sebagai bulan dan tahun.
    Tes ini membuat percobaan serupa gagal keras.
    """
    assert urai(teks, cfg).value is None


def test_penjaga_tidak_menekan_tanggal_yang_berpenanda(cfg):
    """Penekanan itu hanya berlaku saat penjaganya memang membuang kandidatnya."""
    assert urai("EXP 12 29 2028", cfg).value == date(2028, 12, 29)


# --------------------------------------------------------------------------- bulan-tahun berspasi

def test_bulan_tahun_berspasi_wajib_tahun_empat_digit(cfg):
    """Pembedanya diambil dari PRD 8.8.1 sendiri.

    PRD mendaftarkan `MM/YY` (pemisah tercetak, tahun dua digit) dan `MM YYYY`
    (spasi, tahun empat digit). Spasi dengan tahun dua digit tidak pernah diminta,
    dan itulah yang dulu membuat `'LOT 12 34 2028'` dijawab Desember 2034.
    """
    assert urai("12 2027", cfg).value == date(2027, 12, 31)      # PRD: MM YYYY
    assert urai("12/27", cfg).value == date(2027, 12, 31)        # PRD: MM/YY
    assert urai("LOT 12 34 2028", cfg).value is None            # spasi + tahun 2 digit


def test_bulan_tahun_berspasi_tidak_butuh_penanda(cfg):
    """Mewajibkan penanda di sini akan melanggar kewajiban format PRD `MM YYYY`."""
    for wajib in (True, False):
        cfg["vision"]["date_parser"]["require_marker_for_spaced"] = wajib
        assert urai("12 2027", cfg).value == date(2027, 12, 31)


def test_pola_my_spasi_terdaftar_dan_terpakai(cfg):
    pola = [k.pattern for k in D.find_candidates("12 2027", HARI_INI, cfg)]
    assert pola == ["my_spasi"]
