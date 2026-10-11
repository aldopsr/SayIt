"""Tes pembacaan berkas unggahan: gambar, PDF, DOCX.

PDF dan DOCX dibuat di dalam tes, jadi tidak butuh berkas contoh di repo.
"""
import io
import zipfile

import pytest

from sayit import berkas as bk
from sayit.config import load_config
from sayit.vision.document import result_dari_teks


@pytest.fixture
def cfg():
    import copy
    return copy.deepcopy(load_config())


def docx_palsu(paragraf):
    """DOCX minimal: zip berisi word/document.xml. Cukup untuk menguji pembacanya."""
    isi = "".join(f"<w:p><w:r><w:t>{p}</w:t></w:r></w:p>" for p in paragraf)
    xml = ('<?xml version="1.0"?><w:document '
           'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
           f"<w:body>{isi}</w:body></w:document>")
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("word/document.xml", xml)
    return buf.getvalue()


# --------------------------------------------------------------------------- jenis

@pytest.mark.parametrize("nama,harap", [
    ("surat.jpg", "gambar"), ("foto.HEIC", "gambar"), ("scan.PNG", "gambar"),
    ("laporan.pdf", "pdf"), ("tugas.DOCX", "docx"),
    ("catatan.txt", ""), ("lagu.mp3", ""), ("tanpaekstensi", ""),
])
def test_jenis_dikenali_dari_nama(nama, harap):
    assert bk.jenis(nama) == harap


# --------------------------------------------------------------------------- DOCX

def test_docx_dibaca_per_paragraf():
    data = docx_palsu(["Baris pertama.", "Baris kedua."])
    assert bk.teks_dari_docx(data) == "Baris pertama.\nBaris kedua."


def test_docx_entitas_xml_dikembalikan():
    assert bk.teks_dari_docx(docx_palsu(["Ani &amp; Budi &lt;tim&gt;"])) == "Ani & Budi <tim>"


def test_docx_tag_dalam_teks_tidak_ikut():
    """Teks terbagi beberapa <w:r> saat ada format tebal; harus menyatu."""
    xml = ('<?xml version="1.0"?><w:document '
           'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
           "<w:body><w:p><w:r><w:t>Nomor </w:t></w:r>"
           "<w:r><w:rPr><w:b/></w:rPr><w:t>123</w:t></w:r></w:p></w:body></w:document>")
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("word/document.xml", xml)
    assert bk.teks_dari_docx(buf.getvalue()) == "Nomor 123"


# --------------------------------------------------------------------------- PDF

def test_pdf_rusak_memberi_pesan_yang_bisa_dibacakan():
    """Kegagalan paling nyata di produksi: pengguna mengunggah berkas rusak."""
    with pytest.raises(ValueError, match="tidak bisa dibaca atau rusak"):
        bk.teks_dari_pdf(b"ini jelas bukan pdf")
    with pytest.raises(ValueError, match="tidak bisa dibaca atau rusak"):
        bk.gambar_dari_pdf(b"ini jelas bukan pdf")


def test_docx_rusak_memberi_pesan_yang_bisa_dibacakan():
    with pytest.raises(ValueError, match="tidak bisa dibaca atau rusak"):
        bk.teks_dari_docx(b"bukan zip")
    # zip yang sah tetapi bukan DOCX
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("lain.txt", "halo")
    with pytest.raises(ValueError, match="tidak bisa dibaca atau rusak"):
        bk.teks_dari_docx(buf.getvalue())


def test_pdf_dirender_menjadi_citra_bgr():
    import pypdfium2 as pdfium
    doc = pdfium.PdfDocument.new()
    doc.new_page(300, 200)
    buf = io.BytesIO()
    doc.save(buf)
    img = bk.gambar_dari_pdf(buf.getvalue())
    assert img.ndim == 3 and img.shape[2] == 3
    # dirender pada SKALA_RENDER, jadi lebih besar daripada ukuran titik PDF
    assert img.shape[1] > 300


# --------------------------------------------------------------------------- jalur teks -> potongan

def test_teks_panjang_dipotong_seperti_jalur_ocr(cfg):
    maks = cfg["vision"]["document"]["max_words_per_chunk"]
    hasil = result_dari_teks(" ".join(["kata"] * (maks * 3)), cfg, "DOCX")
    assert hasil.found and hasil.total_chunks == 3
    assert hasil.notes["sumber"] == "DOCX"


def test_teks_kosong_dianggap_tidak_ada_tulisan(cfg):
    for kosong in ("", "   \n\n  "):
        hasil = result_dari_teks(kosong, cfg)
        assert not hasil.found and hasil.total_chunks == 0
