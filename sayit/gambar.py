"""Pembacaan gambar yang tahan format dan orientasi kamera ponsel.

Dua hal yang ditangani di sini, dan keduanya pernah menggigit proyek ini:

1. **HEIC.** Foto iPhone berformat HEIC tidak terbaca `cv2` maupun PIL polos.
   Tanpa penanganan, `cv2.imdecode` mengembalikan None dan foto dilewati diam-diam.
2. **Orientasi EXIF.** Ponsel menyimpan rotasi di metadata, bukan pada pikselnya.
   `cv2.imdecode` mengabaikannya, sehingga foto bisa terbaca miring 90 derajat
   padahal terlihat tegak di galeri. Untuk model yang peka rotasi, itu fatal.

Seluruh skrip pengukuran dan aplikasi memakai modul ini, supaya perilakunya sama
di mana pun.
"""
from __future__ import annotations

import io
from pathlib import Path

import numpy as np
import pillow_heif
from PIL import Image, ImageOps

pillow_heif.register_heif_opener()

EKSTENSI = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".heic", ".heif"}


def _ke_bgr(im: Image.Image) -> np.ndarray:
    """PIL -> ndarray BGR, dengan rotasi EXIF sudah diterapkan ke pikselnya."""
    im = ImageOps.exif_transpose(im).convert("RGB")
    return np.asarray(im)[:, :, ::-1].copy()


def baca(p: str | Path) -> np.ndarray:
    """Baca berkas gambar menjadi citra BGR seperti yang dipakai modul vision."""
    p = Path(p)
    try:
        with Image.open(p) as im:
            return _ke_bgr(im)
    except Exception as e:                      # noqa: BLE001 - pesannya yang penting
        raise ValueError(f"Tidak bisa dibaca sebagai gambar: {p} ({type(e).__name__})") from e


def dari_bytes(data: bytes) -> np.ndarray:
    """Sama seperti `baca`, tetapi dari byte (unggahan Streamlit)."""
    if not data:
        raise ValueError("Berkas gambar kosong.")
    try:
        with Image.open(io.BytesIO(data)) as im:
            return _ke_bgr(im)
    except Exception as e:                      # noqa: BLE001
        raise ValueError(f"Tidak bisa dibaca sebagai gambar ({type(e).__name__}).") from e


def daftar_gambar(folder: str | Path) -> list[Path]:
    """Berkas gambar di sebuah folder, mengabaikan nama berawalan garis bawah.

    Awalan garis bawah dipakai untuk berkas bantuan seperti lembar verifikasi,
    yang tidak boleh ikut terukur.
    """
    return sorted(p for p in Path(folder).iterdir()
                  if p.is_file() and p.suffix.lower() in EKSTENSI
                  and not p.stem.startswith("_"))
