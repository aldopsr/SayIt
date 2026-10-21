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

from sayit import berkas as bk
from sayit.appkit import foto_dari_berkas, suara_dari_berkas
from sayit.audio.stt import Transcriber
from sayit.audio.tts import SpeechRenderer
from sayit.config import load_config, project_path
from sayit.pipeline import Pipeline
from sayit.response.templates import CLIP_TEXTS, fixed

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


def _galat(klip: str) -> dict:
    """Galat yang harus DIDENGAR, bukan hanya tampil.

    Penggunanya tunanetra: galat yang hanya dikirim sebagai teks sama saja dengan
    tidak dikirim. Teksnya diambil dari klip itu sendiri supaya yang terdengar dan
    yang tertulis tidak pernah berbeda, dan tiap kalimatnya menyebutkan jalan keluar.
    """
    audio, sr = penyuara.render(fixed(klip))
    return {"error": CLIP_TEXTS[klip], "audio": _wav_b64(audio, sr)}


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
            "diterima": giliran.diterima, "audio": _wav_b64(audio, sr)}


@app.post("/berkas")
async def unggah_berkas(berkas: UploadFile = File(...)):
    """Unggah gambar, PDF, atau DOCX dari penyimpanan.

    PDF dan DOCX yang punya lapisan teks tidak di-OCR: teksnya sudah akurat,
    dan meng-OCR hasil render justru lebih lambat sekaligus lebih salah.
    OCR hanya dipakai untuk PDF hasil pindai, yang memang tidak punya teks.
    """
    nama = berkas.filename or ""
    tipe = bk.jenis(nama)
    if not tipe:
        return _galat("berkas_tidak_didukung")
    data = await berkas.read()

    with kunci:
        try:
            if tipe == "gambar":
                giliran = pipeline.set_photo(foto_dari_berkas(_Berkas(data)))
            elif tipe == "docx":
                giliran = pipeline.set_document_text(bk.teks_dari_docx(data), "DOCX")
            else:
                teks = bk.teks_dari_pdf(data)
                if teks:
                    giliran = pipeline.set_document_text(teks, "PDF")
                else:
                    # PDF hasil pindai: tidak ada jalan lain selain merender lalu OCR
                    giliran = pipeline.set_photo(bk.gambar_dari_pdf(data))
                    if giliran.diterima:
                        giliran = pipeline.ask("bacakan tulisannya")
        except ValueError:
            # berkas rusak, .doc lama, atau citra kosong - semuanya satu jalan keluar
            # bagi pengguna: pilih berkas lain.
            return _galat("berkas_rusak")

        diterima = giliran.diterima and giliran.intent in ("FOTO", "BACA")
        teks, ucapan = giliran.text, list(giliran.utterance)
        if giliran.intent in ("UANG", "BACA", "KEDALUWARSA"):
            ucapan += fixed("tindak_lanjut")
        elif not diterima:
            # Klip quality gate menyuruh "coba foto ulang" - saran yang salah bagi
            # orang yang baru saja MEMILIH berkas. Jalan keluar yang benar disambung
            # di sini, ke audio maupun ke teksnya, supaya pembaca layar ikut dapat.
            ucapan += fixed("berkas_lain")
            teks = f"{teks} {CLIP_TEXTS['berkas_lain']}"
        audio, sr = penyuara.render(ucapan)

    return {"teks": teks, "intent": giliran.intent, "alasan": giliran.reason,
            "diterima": diterima, "audio": _wav_b64(audio, sr)}


@app.get("/sehat")
def sehat():
    return {"status": status}


@app.get("/klip-teks")
def klip_teks():
    """Teks tiap klip, supaya klien bisa menaruhnya di wilayah aria-live tanpa
    menyalin kalimatnya. Salinan di sisi klien pasti menyimpang dari
    templates.py cepat atau lambat, dan aturan proyek menaruh kalimat di satu
    tempat saja."""
    return CLIP_TEXTS


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
            if not giliran_foto.diterima:              # ditolak quality gate
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

        # PUTAR_KAMERA tidak dirender: hasilnya baru diketahui SETELAH klien memutar
        # kameranya, dan klien yang mengucapkan "kamera depan/belakang aktif".
        # Merender di sini berarti dua kalimat berturut-turut untuk satu tindakan,
        # plus satu detik gTTS yang terbuang.
        if giliran.intent == "PUTAR_KAMERA":
            return {"teks": giliran.text, "intent": giliran.intent,
                    "alasan": giliran.reason, "audio": None}

        audio, sr = penyuara.render(ucapan)

    return {"teks": giliran.text, "intent": giliran.intent, "alasan": giliran.reason,
            "audio": _wav_b64(audio, sr)}
