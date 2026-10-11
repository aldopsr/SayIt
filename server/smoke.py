"""Uji asap API mengikuti alur aplikasi: foto dulu, pertanyaan kemudian.

Dipisah dari pytest karena memuat model sungguhan (2,5 GB, ~10 detik).

    python server\\smoke.py
"""
import base64
import io
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import soundfile as sf
from fastapi.testclient import TestClient

from server.app import app

FOTO = Path("data/uji_sendiri/100000_dipegang_01.JPG")


def durasi(b64):
    audio, sr = sf.read(io.BytesIO(base64.b64decode(b64)))
    return len(audio) / sr


with TestClient(app) as c:
    assert c.get("/sehat").json()["status"], "modul tidak ada yang siap"

    # langkah 3-5: foto diterima, lalu pengguna diminta bertanya
    r = c.post("/foto", files={"foto": (FOTO.name, FOTO.read_bytes(), "image/jpeg")})
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["diterima"] is True, j
    assert durasi(j["audio"]) > 1.0
    print(f"OK  /foto  diterima, audio {durasi(j['audio']):.1f}s -> {j['teks']}")

    # langkah 6-8: pertanyaan dijawab, dan tawaran langkah berikutnya ikut disuarakan
    r = c.post("/tanya", data={"teks": "berapa nilai uang ini"})
    j = r.json()
    assert j["intent"] == "UANG", j
    assert "seratus ribu" in j["teks"].lower(), j["teks"]
    print(f"OK  /tanya audio {durasi(j['audio']):.1f}s -> {j['teks']}")

    # langkah 9-12: ketiga jawaban tindak lanjut dikenali router
    for teks, harap in (("ulangi", "ULANGI"), ("foto lagi", "FOTO_BARU"), ("keluar", "KELUAR")):
        got = c.post("/tanya", data={"teks": teks}).json()["intent"]
        assert got == harap, f"{teks!r} -> {got}, harusnya {harap}"
        print(f"OK  tindak lanjut {teks!r} -> {got}")

    # klip statis dipakai klien untuk sambutan dan penanda proses
    for nama in ("sambutan", "sedang_memproses"):
        assert c.get(f"/klip/{nama}.mp3").status_code == 200, nama
    print("OK  klip sambutan dan sedang_memproses tersedia")

    # ---------------------------------------------------------------- unggah berkas
    # gambar: jalur sama dengan kamera
    r = c.post("/berkas", files={"berkas": (FOTO.name, FOTO.read_bytes(), "image/jpeg")})
    j = r.json()
    assert j["diterima"] and j["intent"] == "FOTO", j
    print(f"OK  /berkas gambar -> {j['teks']}")

    # DOCX: dibaca tanpa OCR sama sekali
    import zipfile
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("word/document.xml",
                   '<?xml version="1.0"?><w:document '
                   'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
                   "<w:body><w:p><w:r><w:t>Surat keterangan domisili.</w:t></w:r></w:p>"
                   "</w:body></w:document>")
    j = c.post("/berkas", files={"berkas": ("surat.docx", buf.getvalue(), "application/octet-stream")}).json()
    assert j["intent"] == "BACA" and "domisili" in j["teks"].lower(), j
    print(f"OK  /berkas docx -> {j['teks'][:60]}")

    # Jenis tak didukung dan berkas rusak: pesan, bukan 500 - DAN pesannya
    # harus ikut berbunyi, karena pengguna tunanetra tidak melihat layar.
    for nama, isi, cari in (("lagu.mp3", b"x", "tidak didukung"),
                            ("rusak.pdf", b"bukan pdf", "rusak"),
                            ("rusak.docx", b"bukan zip", "rusak")):
        j = c.post("/berkas", files={"berkas": (nama, isi, "application/octet-stream")}).json()
        assert cari in j.get("error", ""), j
        assert durasi(j["audio"]) > 1.0, f"{nama}: galat tanpa audio"
        # tiap peringatan wajib menyebut jalan keluarnya
        assert any(k in j["error"].lower() for k in ("pilih", "coba")), j["error"]
    print("OK  /berkas menolak dengan pesan yang berbunyi dan menyebut jalan keluar")

    # Berkas sah tetapi mutunya ditolak quality gate: klipnya menyuruh "foto ulang",
    # jadi jalan keluar yang cocok untuk pengunggah harus disambung - dan `diterima`
    # harus False supaya klien tidak memindahkan pengguna ke tahap bertanya.
    kecil = Path("web/public/logo.png")
    j = c.post("/berkas", files={"berkas": (kecil.name, kecil.read_bytes(), "image/png")}).json()
    assert j["diterima"] is False, j
    assert "memilih berkas lain" in j["teks"], j["teks"]
    print(f"OK  /berkas mutu ditolak -> {j['teks']}")
