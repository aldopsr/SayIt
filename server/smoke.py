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
