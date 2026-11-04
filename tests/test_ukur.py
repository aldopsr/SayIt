"""Tes bagian murni dari kedua skrip pengukuran.

Skrip pengukuran tidak menghasilkan kode yang dipakai pengguna, tetapi
angkanya masuk laporan. Kekeliruan di sini membuat sistem yang benar terlihat
gagal, dan itu justru kesalahan yang paling mahal: pernah terjadi 11 dari 13
dokumen terlewat diam-diam hanya karena beda satu spasi pada nama berkas.

Yang diuji hanya fungsi tanpa perangkat: pencocokan nama, pembersihan teks,
jarak edit, dan pembacaan tanggal dari nama berkas. OCR tidak disentuh.
"""
from datetime import date

import pytest

from scripts.ukur_dokumen import buang_markup, cer, jarak_edit, normalkan, pasangan
from scripts.ukur_kedaluwarsa import harapan_dari_nama


# --------------------------------------------------------------------------- pasangan berkas

@pytest.fixture
def folder(tmp_path):
    def buat(*nama):
        for n in nama:
            (tmp_path / n).write_bytes(b"x")
        return tmp_path
    return buat


def test_pasangan_nama_persis(folder):
    f = folder("surat.jpg", "surat.txt")
    assert [(g.name, a.name) for g, a in pasangan(f)] == [("surat.jpg", "surat.txt")]


def test_pasangan_menerima_md(folder):
    f = folder("surat.jpg", "surat.md")
    assert [a.name for _, a in pasangan(f)] == ["surat.md"]


def test_pasangan_tahan_beda_spasi(folder):
    """Windows menamai salinan `r (1).JPG`, acuan biasanya diketik `r(1).txt`."""
    f = folder("r (1).JPG", "r(1).txt")
    assert [(g.name, a.name) for g, a in pasangan(f)] == [("r (1).JPG", "r(1).txt")]


def test_pasangan_tahan_beda_huruf_besar(folder):
    f = folder("Surat.JPG", "surat.txt")
    assert len(pasangan(f)) == 1


def test_foto_tanpa_acuan_dilewati(folder):
    f = folder("ada.jpg", "ada.txt", "sendirian.jpg")
    assert [g.name for g, _ in pasangan(f)] == ["ada.jpg"]


def test_acuan_tanpa_foto_tidak_bikin_kacau(folder):
    f = folder("hanya_teks.txt")
    assert pasangan(f) == []


# --------------------------------------------------------------------------- normalisasi teks

def test_markup_markdown_dibuang():
    assert buang_markup("# Judul") == "Judul"
    assert buang_markup("**tebal**") == "tebal"
    assert buang_markup("`kode`") == "kode"
    assert buang_markup("[SayIt](http://contoh.id)") == "SayIt"


def test_penanda_daftar_tidak_dibuang():
    """Penanda daftar biasanya memang tercetak, jadi OCR wajar membacanya."""
    assert "-" in buang_markup("- butir pertama")
    assert "1." in buang_markup("1. butir pertama")


def test_normalkan_tidak_menghukum_hal_yang_tak_terlihat():
    """Huruf besar, jenis kutip, dan jumlah spasi tidak mengubah rupa foto."""
    assert normalkan("Kata   Pengantar") == normalkan("kata pengantar")
    assert normalkan("“tes”") == normalkan('"tes"')
    assert normalkan("a – b") == normalkan("a - b")


# --------------------------------------------------------------------------- CER

def test_jarak_edit_dasar():
    assert jarak_edit("", "") == 0
    assert jarak_edit("", "abc") == 3
    assert jarak_edit("abc", "abc") == 0
    assert jarak_edit("kesimpulan", "kesmpuln") == 2      # dua huruf hilang


def test_cer_sempurna_nol():
    assert cer("Kata Pengantar", "kata pengantar") == 0.0


def test_cer_menghitung_proporsi():
    assert cer("abcd", "abcx") == pytest.approx(0.25)


def test_cer_acuan_kosong_tidak_membagi_nol():
    assert cer("", "apa pun") == 0.0


def test_cer_boleh_melebihi_satu():
    """OCR yang mengarang lebih panjang daripada acuannya tetap harus terukur."""
    assert cer("ab", "abcdefghij") > 1.0


# --------------------------------------------------------------------------- tanggal dari nama

def test_tanggal_lengkap_dari_nama(tmp_path):
    n, hanya_bulan = harapan_dari_nama(tmp_path / "20261203_kopi.jpg")
    assert (n, hanya_bulan) == (date(2026, 12, 3), False)


def test_bulan_saja_ditandai(tmp_path):
    n, hanya_bulan = harapan_dari_nama(tmp_path / "202612_susu.jpg")
    assert (n, hanya_bulan) == (date(2026, 12, 1), True)


def test_kemasan_tanpa_tanggal(tmp_path):
    assert harapan_dari_nama(tmp_path / "tidakada_permen.jpg") == ("kosong", False)
    assert harapan_dari_nama(tmp_path / "tanpatanggal_permen.jpg") == ("kosong", False)


def test_nama_tanpa_awalan_tanggal_dilewati(tmp_path):
    assert harapan_dari_nama(tmp_path / "kopi_bubuk.jpg")[0] is None


def test_awalan_tujuh_digit_ditolak(tmp_path):
    """`2026411` ambigu di permukaan dan pernah membuat 9 kemasan terlewat.

    Ditolak dengan sengaja: acuan pengukuran harus tegas, jadi nama berkasnya
    yang dibetulkan menjadi `20260411`, bukan skripnya yang menebak.
    """
    assert harapan_dari_nama(tmp_path / "2026411_ajinomoto.jpg")[0] is None


# --------------------------------------------------------------------------- ekspor notebook

class TestEksporNotebook:
    """Penjaga `scripts/ekspor_notebook.py`.

    Notebook adalah satu-satunya tempat logika k-fold penghasil angka 90,1%,
    dan `.ipynb` tidak terbaca AST mana pun - bukan oleh graphify, bukan oleh
    linter, bukan oleh `grep -n`. Ekspor inilah yang membuatnya terlihat, jadi
    kegagalannya harus keras, bukan diam-diam.
    """

    def test_baris_ajaib_dikomentari(self):
        from scripts.ekspor_notebook import baris_aman
        assert baris_aman("!pip install ultralytics").startswith("# [ajaib ipython]")
        assert baris_aman("    %cd /content").startswith("# [ajaib ipython]")
        # baris biasa tidak disentuh, termasuk yang memuat ! atau % di tengah
        assert baris_aman("x = a % b") == "x = a % b"
        assert baris_aman("assert x != y") == "assert x != y"

    def test_notebook_buatan_menghasilkan_python_sah(self, tmp_path):
        import ast
        import json
        from scripts.ekspor_notebook import ekspor_satu

        nb = tmp_path / "uji.ipynb"
        nb.write_text(json.dumps({"cells": [
            {"cell_type": "markdown", "source": ["# judul, harus dilewati\n"]},
            {"cell_type": "code", "source": ["!pip install x\n", "def f():\n", "    return 1\n"]},
            {"cell_type": "code", "source": ["   \n"]},           # kosong, dilewati
            {"cell_type": "code", "source": ["KONSTAN = 2\n"]},
        ]}), encoding="utf-8")

        teks, n_sel, n_ajaib = ekspor_satu(nb)
        assert (n_sel, n_ajaib) == (2, 1)
        ast.parse(teks)                                  # inilah penjaga yang sesungguhnya
        nama = {n.name for n in ast.walk(ast.parse(teks)) if isinstance(n, ast.FunctionDef)}
        assert nama == {"f"}
        assert "judul, harus dilewati" not in teks

    def test_seluruh_notebook_asli_terekspor_dan_sah(self):
        """Uji pada notebook SUNGGUHAN, bukan hanya yang dibuat-buat."""
        import ast
        from scripts.ekspor_notebook import SUMBER, ekspor_satu

        asli = sorted(SUMBER.glob("*.ipynb"))
        assert asli, "tidak ada notebook; apakah foldernya dipindah?"
        for nb in asli:
            teks, n_sel, _ = ekspor_satu(nb)
            assert n_sel > 0, f"{nb.name} tidak menghasilkan satu sel kode pun"
            ast.parse(teks, filename=nb.name)
