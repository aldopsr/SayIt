"""Baca berkas yang diunggah pengguna: gambar, PDF, atau DOCX.

PDF dan DOCX yang sudah punya lapisan teks TIDAK dilewatkan OCR sama sekali.
Teksnya sudah ada dan akurat; meng-OCR hasil render justru lebih lambat dan
lebih banyak salah baca. OCR hanya dipakai untuk PDF hasil pindai, yang memang
tidak punya teks.

Tidak ada dependensi baru: `pypdfium2` sudah ikut terpasang bersama paddlex,
dan DOCX hanya zip berisi XML sehingga cukup ditangani pustaka standar.
"""
from __future__ import annotations

import io
import re
import zipfile

import numpy as np

GAMBAR = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".heic", ".heif"}
PDF = {".pdf"}
DOCX = {".docx"}
DIDUKUNG = GAMBAR | PDF | DOCX

# Satu halaman sudah cukup: modul dokumen membacakan per potongan 40 kata, dan
# membaca seluruh PDF sekaligus membuat pengguna menunggu tanpa guna.
HALAMAN_PERTAMA = 0
SKALA_RENDER = 2.0          # ~144 dpi, cukup untuk OCR tanpa membengkakkan latensi


def jenis(nama: str) -> str:
    """'gambar' | 'pdf' | 'docx' | '' untuk yang tidak didukung."""
    ekst = ("." + nama.rsplit(".", 1)[-1]).lower() if "." in nama else ""
    if ekst in GAMBAR:
        return "gambar"
    if ekst in PDF:
        return "pdf"
    if ekst in DOCX:
        return "docx"
    return ""


def teks_dari_docx(data: bytes) -> str:
    """Teks dari DOCX. Hanya zip berisi XML, jadi pustaka standar cukup."""
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            xml = z.read("word/document.xml").decode("utf-8", "replace")
    except (zipfile.BadZipFile, KeyError) as e:
        # .doc lama dan berkas rusak sama-sama mendarat di sini
        raise ValueError("Berkas DOCX tidak bisa dibaca atau rusak.") from e
    # tiap <w:p> satu paragraf; <w:br> dan <w:tab> jadi pemisah agar tidak menempel
    xml = re.sub(r"<w:(?:br|tab)\b[^>]*/?>", " ", xml)
    xml = re.sub(r"</w:p>", "\n", xml)
    teks = re.sub(r"<[^>]+>", "", xml)
    return _rapikan(teks)


def _buka_pdf(data: bytes):
    """Buka PDF, atau lempar ValueError berpesan jelas.

    pypdfium2 melempar PdfiumError untuk berkas rusak maupun PDF tanpa halaman -
    keduanya sampai ke sini sebagai berkas yang diunggah pengguna, jadi pesannya
    harus bisa dibacakan, bukan jejak tumpukan.
    """
    import pypdfium2 as pdfium

    try:
        doc = pdfium.PdfDocument(data)
    except Exception as e:                       # PdfiumError dan turunannya
        raise ValueError("Berkas PDF tidak bisa dibaca atau rusak.") from e
    if len(doc) == 0:
        doc.close()
        raise ValueError("Berkas PDF tidak punya halaman.")
    return doc


def teks_dari_pdf(data: bytes) -> str:
    """Lapisan teks halaman pertama. Kosong berarti PDF hasil pindai."""
    doc = _buka_pdf(data)
    try:
        return _rapikan(doc[HALAMAN_PERTAMA].get_textpage().get_text_range())
    finally:
        doc.close()


def gambar_dari_pdf(data: bytes) -> np.ndarray:
    """Render halaman pertama menjadi citra BGR, untuk PDF hasil pindai."""
    doc = _buka_pdf(data)
    try:
        pil = doc[HALAMAN_PERTAMA].render(scale=SKALA_RENDER).to_pil().convert("RGB")
        return np.asarray(pil)[:, :, ::-1].copy()      # RGB -> BGR seperti sayit.gambar
    finally:
        doc.close()


def _rapikan(teks: str) -> str:
    """Rapatkan spasi dan baris kosong beruntun; entitas XML dasar dikembalikan."""
    for dari, jadi in (("&amp;", "&"), ("&lt;", "<"), ("&gt;", ">"), ("&quot;", '"'), ("&apos;", "'")):
        teks = teks.replace(dari, jadi)
    teks = re.sub(r"[ \t ]+", " ", teks)
    teks = re.sub(r"\n{3,}", "\n\n", teks)
    return "\n".join(b.strip() for b in teks.splitlines()).strip()
