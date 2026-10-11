"""Penghubung antara berkas unggahan Streamlit dan modul SayIt.

Dipisah dari `app.py` supaya bisa diuji tanpa menjalankan seluruh halaman dan
tanpa memuat model. Fungsi di sini menerima objek apa pun yang punya
`getvalue() -> bytes`, seperti hasil `st.camera_input`, `st.file_uploader`,
dan `st.audio_input`.
"""
from __future__ import annotations

import hashlib
import io

import numpy as np
import soundfile as sf

from sayit import gambar
from sayit.audio import io as aio


def sidik(berkas) -> str:
    """Sidik isi berkas, untuk membedakan unggahan baru dari gambar ulang halaman.

    Streamlit menjalankan ulang seluruh skrip pada setiap interaksi dan
    mengembalikan berkas yang sama, jadi tanpa penanda ini foto yang sama akan
    diproses berkali-kali.
    """
    return hashlib.sha1(berkas.getvalue()).hexdigest()


def foto_dari_berkas(berkas) -> np.ndarray:
    """Dekode berkas gambar menjadi citra BGR, seperti yang dipakai modul vision.

    Lewat `sayit.gambar` supaya foto HEIC terbaca dan rotasi EXIF diterapkan;
    pengguna mengunggah langsung dari ponsel, jadi keduanya lazim ditemui.
    """
    return gambar.dari_bytes(berkas.getvalue())


def suara_dari_berkas(berkas, sr_target: int) -> np.ndarray:
    """Dekode rekaman menjadi mono float32 pada laju sampel yang diminta Whisper."""
    audio, sr = sf.read(io.BytesIO(berkas.getvalue()), dtype="float32")
    if audio.size == 0:
        raise ValueError("Rekaman kosong.")
    return aio.resample(aio.to_mono(audio), sr, sr_target).astype(np.float32)
