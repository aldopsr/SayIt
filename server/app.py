"""API web SayIt: membungkus Pipeline yang sudah ada.

Satu endpoint, satu Pipeline. Klien mengirim foto + pertanyaan (suara atau teks),
server menjawab dengan teks DAN audio dalam satu respons, supaya pengguna tunanetra
tidak menunggu dua perjalanan jaringan.

Jalankan lokal:  uvicorn server.app:app --reload
"""
from __future__ import annotations

import base64
import io
import threading

import numpy as np
import soundfile as sf
from fastapi import FastAPI, File, Form, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from sayit.appkit import foto_dari_berkas, suara_dari_berkas
from sayit.audio.stt import Transcriber
from sayit.audio.tts import SpeechRenderer
from sayit.config import load_config, project_path
from sayit.pipeline import Pipeline
from sayit.response.templates import fixed

cfg = load_config()
pipeline = Pipeline(cfg, transcriber=Transcriber(cfg))
penyuara = SpeechRenderer(cfg)
status: dict[str, str] = {}

# ponytail: satu Pipeline dipakai bersama, dikunci supaya tidak saling menimpa.
# Modelnya 2,5 GB dan butuh 10 detik dimuat, jadi satu instans per pengguna mustahil.
# Konsekuensinya permintaan diantre, bukan diparalelkan. Kalau nanti perlu paralel:
# pisahkan model (dibagi) dari state percakapan (per sesi).
kunci = threading.Lock()

app = FastAPI(title="SayIt")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# Klip tetap disajikan apa adanya supaya klien bisa memutar "sedang saya proses"
# sendiri saat menunggu, tanpa perjalanan jaringan tambahan.
app.mount("/klip", StaticFiles(directory=str(project_path(cfg["tts"]["cache_dir"]))), name="klip")


@app.on_event("startup")
def muat():
    status.update(pipeline.load())


def _wav_b64(audio: np.ndarray, sr: int) -> str:
    buf = io.BytesIO()
    sf.write(buf, audio, sr, format="WAV")
    return base64.b64encode(buf.getvalue()).decode()


class _Berkas:
    """soundfile dan cv2 di appkit hanya butuh .getvalue()."""

    def __init__(self, data: bytes):
        self._data = data

    def getvalue(self) -> bytes:
        return self._data


@app.post("/foto")
async def unggah_foto(foto: UploadFile = File(...)):
    """Langkah 3-5 alur: terima foto, periksa mutunya, lalu minta pertanyaan.

    Dipisah dari /tanya karena pengguna memotret dulu dan bertanya kemudian;
    menggabungkannya memaksa keduanya terjadi dalam satu gestur.
    """
    with kunci:
        giliran = pipeline.set_photo(foto_dari_berkas(_Berkas(await foto.read())))
        audio, sr = penyuara.render(giliran.utterance)
    return {"teks": giliran.text, "intent": giliran.intent, "alasan": giliran.reason,
            "diterima": giliran.intent == "FOTO", "audio": _wav_b64(audio, sr)}


@app.get("/sehat")
def sehat():
    return {"status": status}


@app.post("/tanya")
async def tanya(
    foto: UploadFile | None = File(None),
    suara: UploadFile | None = File(None),
    teks: str | None = Form(None),
):
    """Satu giliran percakapan. Foto opsional: foto terakhir dipakai ulang bila kosong."""
    if not suara and not teks:
        return {"error": "kirim `suara` atau `teks`"}

    with kunci:
        if foto is not None:
            giliran_foto = pipeline.set_photo(foto_dari_berkas(_Berkas(await foto.read())))
            if giliran_foto.intent != "FOTO":          # ditolak quality gate
                audio, sr = penyuara.render(giliran_foto.utterance)
                return {"teks": giliran_foto.text, "intent": giliran_foto.intent,
                        "alasan": giliran_foto.reason, "audio": _wav_b64(audio, sr)}

        if suara:
            sr_in = cfg["audio"]["sample_rate"]
            giliran = pipeline.listen(suara_dari_berkas(_Berkas(await suara.read()), sr_in), sr=sr_in)
        else:
            giliran = pipeline.ask(teks)

        # Setelah menjawab pertanyaan tugas, langsung tawarkan langkah berikutnya,
        # disambung ke audio yang sama supaya tidak ada jeda bagi pengguna tunanetra.
        ucapan = list(giliran.utterance)
        if giliran.intent in ("UANG", "BACA", "KEDALUWARSA"):
            ucapan += fixed("tindak_lanjut")
        audio, sr = penyuara.render(ucapan)

    return {"teks": giliran.text, "intent": giliran.intent, "alasan": giliran.reason,
            "audio": _wav_b64(audio, sr)}
