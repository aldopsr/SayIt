"""API web SayIt: membungkus Pipeline yang sudah ada.

Satu endpoint, satu Pipeline. Klien mengirim foto + pertanyaan (suara atau teks),
server menjawab dengan teks DAN audio dalam satu respons, supaya pengguna tunanetra
tidak menunggu dua perjalanan jaringan.

Jalankan lokal:  uvicorn server.app:app --reload
"""
from __future__ import annotations

import base64
import contextlib
import functools
import io
import threading
import time

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
#
# PENTING: endpoint berat sengaja `def`, BUKAN `async def`. Isinya kerja blocking
# (OCR, YOLO, Whisper), dan `async def` menjalankannya di event loop sehingga
# SELURUH server membeku selama pekerjaan itu. Terukur 11-11-2026: saat satu
# dokumen dibaca, `GET /sehat` yang hanya mengembalikan dict memakan 6,57 detik,
# dan permintaan kedua bahkan belum DITERIMA - sehingga klip "server_sibuk"
# mustahil terkirim dan kunci di bawah ini tidak pernah berebut. Dengan `def`,
# Starlette memindahkannya ke threadpool: event loop tetap bebas melayani
# /sehat dan /klip, permintaan benar-benar bersamaan, dan kunci ini bekerja.
kunci = threading.Lock()


class Sibuk(Exception):
    """Antrean penuh: permintaan lain sedang dilayani lebih lama dari batas tunggu."""


def jaga_antrean(fn):
    """Ubah `Sibuk` menjadi jawaban berbunyi, sehingga `antre()` boleh dipakai
    di mana pun di dalam endpoint tanpa tiap blok membungkus try/except sendiri."""
    @functools.wraps(fn)
    def bungkus(*a, **kw):
        try:
            return fn(*a, **kw)
        except Sibuk:
            return _galat("server_sibuk")
    return bungkus


@contextlib.contextmanager
def antre():
    """Kunci dengan batas tunggu, supaya menunggu TIDAK pernah berupa diam.

    `with kunci` tanpa batas membuat permintaan kedua menunggu tanpa kabar.
    Bagi pengguna tunanetra diam 20 detik tidak bisa dibedakan dari server mati,
    dan aturan aksesibilitas proyek mewajibkan tiap peringatan berbunyi serta
    menyebut tindakan berikutnya. Jadi di atas batas tunggu kita menjawab
    klip "server_sibuk", bukan membiarkan pengguna menebak.
    """
    if not kunci.acquire(timeout=cfg["server"]["antre_timeout_s"]):
        raise Sibuk
    try:
        yield
    finally:
        kunci.release()


def _hangatkan(penyuara_, kunci_, coba: int, jeda_s: float, tidur=time.sleep) -> bool:
    """Ulangi warmup sampai berhasil. True bila sesi TTS akhirnya terbangun.

    Kuncinya diambil saat mencoba: kalau tidak, pemanasan bisa berjalan bersamaan
    dengan permintaan pengguna dan keduanya membangun sesi edge-tts sendiri.
    Menahan kunci selama percobaan tidak merugikan - permintaan yang terhalang
    justru akan membayar 9 detik itu sendiri bila pemanasannya dilewati.
    """
    for sisa in range(coba, 0, -1):
        with kunci_:
            if penyuara_.warmup():
                return True
        if sisa > 1:
            tidur(jeda_s)
    return False

app = FastAPI(title="SayIt")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# Klip tetap disajikan apa adanya supaya klien bisa memutar "sedang saya proses"
# sendiri saat menunggu, tanpa perjalanan jaringan tambahan.
app.mount("/klip", StaticFiles(directory=str(project_path(cfg["tts"]["cache_dir"]))), name="klip")


@app.middleware("http")
async def klip_wajib_divalidasi(request, call_next):
    """Paksa peramban memeriksa ulang klip sebelum memakainya.

    StaticFiles mengirim ETag tetapi TIDAK mengirim Cache-Control. Tanpa itu
    peramban memakai tebakan kesegarannya sendiri dan bisa memutar klip lama
    berhari-hari - terbukti di HP: sambutan yang sudah dipendekkan tetap
    terdengar versi panjangnya. "no-cache" bukan berarti jangan disimpan,
    melainkan tanyakan dulu: kalau belum berubah jawabannya 304 yang murah.
    """
    respons = await call_next(request)
    if request.url.path.startswith("/klip"):
        respons.headers["Cache-Control"] = "no-cache"
    return respons


@app.on_event("startup")
def muat():
    status.update(pipeline.load())
    # Pemanasan dibayar di sini, bukan oleh pengguna. Kalau gagal - start tanpa
    # internet adalah penyebab yang nyata - dicoba lagi di latar, karena tanpa itu
    # 9 detik pembangunan sesi edge-tts jatuh tepat di pembacaan dokumen pertama.
    # Statusnya masuk /sehat supaya kegagalannya TERLIHAT, bukan diam-diam.
    if penyuara.warmup():
        status["tts"] = "siap"
        return
    status["tts"] = "belum hangat, mencoba lagi di latar"
    threading.Thread(target=_hangatkan_tts, daemon=True).start()


def _hangatkan_tts():
    srv = cfg["server"]
    if _hangatkan(penyuara, kunci, srv["warmup_retry"], srv["warmup_retry_delay_s"]):
        status["tts"] = "siap (setelah dicoba ulang)"
    else:
        status["tts"] = ("gagal dihangatkan, cek internet; "
                         "pembacaan dokumen pertama akan lambat sekitar 9 detik")


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
@jaga_antrean
def unggah_foto(foto: UploadFile = File(...)):
    """Langkah 3-5 alur: terima foto, periksa mutunya, lalu minta pertanyaan.

    Dipisah dari /tanya karena pengguna memotret dulu dan bertanya kemudian;
    menggabungkannya memaksa keduanya terjadi dalam satu gestur.
    """
    data = foto.file.read()         # dibaca sebelum mengantre: jangan tahan kunci saat I/O
    with antre():
        giliran = pipeline.set_photo(foto_dari_berkas(_Berkas(data)))
        audio, sr = penyuara.render(giliran.utterance)
    return {"teks": giliran.text, "intent": giliran.intent, "alasan": giliran.reason,
            "diterima": giliran.diterima, "audio": _wav_b64(audio, sr)}


@app.post("/berkas")
@jaga_antrean
def unggah_berkas(berkas: UploadFile = File(...)):
    """Unggah gambar, PDF, atau DOCX dari penyimpanan.

    PDF dan DOCX yang punya lapisan teks tidak di-OCR: teksnya sudah akurat,
    dan meng-OCR hasil render justru lebih lambat sekaligus lebih salah.
    OCR hanya dipakai untuk PDF hasil pindai, yang memang tidak punya teks.
    """
    nama = berkas.filename or ""
    tipe = bk.jenis(nama)
    if not tipe:
        return _galat("berkas_tidak_didukung")
    data = berkas.file.read()

    with antre():
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
@jaga_antrean
def tanya(
    foto: UploadFile | None = File(None),
    suara: UploadFile | None = File(None),
    teks: str | None = Form(None),
):
    """Satu giliran percakapan. Foto opsional: foto terakhir dipakai ulang bila kosong."""
    if not suara and not teks:
        return {"error": "kirim `suara` atau `teks`"}

    # Unggahan dibaca sebelum mengantre: menahan kunci selama I/O jaringan
    # memperpanjang antrean orang lain tanpa alasan.
    data_foto = foto.file.read() if foto is not None else None
    data_suara = suara.file.read() if suara else None

    with antre():
        if data_foto is not None:
            giliran_foto = pipeline.set_photo(foto_dari_berkas(_Berkas(data_foto)))
            if not giliran_foto.diterima:              # ditolak quality gate
                audio, sr = penyuara.render(giliran_foto.utterance)
                return {"teks": giliran_foto.text, "intent": giliran_foto.intent,
                        "alasan": giliran_foto.reason, "audio": _wav_b64(audio, sr)}

        if suara:
            sr_in = cfg["audio"]["sample_rate"]
            giliran = pipeline.listen(suara_dari_berkas(_Berkas(data_suara), sr_in), sr=sr_in)
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

    # `transcript` ikut dikembalikan: tanpa ini tidak ada cara melihat APA yang
    # didengar sistem, dan tiap bug suara harus ditebak. Pipeline sudah
    # menyimpannya di notes, hanya belum pernah diteruskan.
    return {"teks": giliran.text, "intent": giliran.intent, "alasan": giliran.reason,
            "transcript": giliran.notes.get("transcript"),
            "audio": _wav_b64(audio, sr)}
