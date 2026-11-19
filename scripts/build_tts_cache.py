"""Buat semua klip suara tetap (kalimat, frasa, kata angka, nama bulan) dengan mesin di config.

Jalankan sekali saat online:
    python scripts/build_tts_cache.py
    python scripts/build_tts_cache.py --force      # buat ulang semua klip
    python scripts/build_tts_cache.py --kunci foto_gelap   # buat ulang klip tertentu saja

`assets/tts/*.mp3` SENGAJA di-commit, jadi `--force` mengubah ke-91 berkas biner
sekaligus walau yang berubah teksnya cuma satu kalimat. Pakai `--kunci` untuk itu.
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sayit.audio.tts import SpeechRenderer, internet_available  # noqa: E402
from sayit.config import load_config  # noqa: E402
from sayit.response.templates import CLIP_TEXTS  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--delay", type=float, default=0.3, help="jeda antar-permintaan (detik)")
    # Klip mp3 ikut di-commit, jadi `--force` membuat diff 91 berkas biner untuk satu
    # kalimat yang berubah. Dengan `--kunci` hanya klip yang teksnya memang berubah
    # yang dibuat ulang.
    ap.add_argument("--kunci", nargs="+", metavar="KUNCI", default=None,
                    help="buat ulang hanya klip ini (nama kunci di CLIP_TEXTS)")
    args = ap.parse_args()

    if not internet_available():
        sys.exit("Tidak ada koneksi internet. Klip hanya bisa dibuat saat online.")

    cfg = load_config()
    renderer = SpeechRenderer(cfg, online=True)
    kwargs = renderer._synth_kwargs()
    if args.kunci:
        asing = [k for k in args.kunci if k not in CLIP_TEXTS]
        if asing:
            sys.exit(f"Kunci tidak terdaftar di CLIP_TEXTS: {', '.join(asing)}")
        todo = list(args.kunci)
    else:
        todo = [k for k in CLIP_TEXTS if args.force or not renderer.clip_path(k).exists()]
    print(f"{len(CLIP_TEXTS)} klip terdaftar, {len(todo)} akan dibuat -> {renderer.clip_dir}")

    failed = []
    for i, key in enumerate(todo, 1):
        for attempt in range(3):
            try:
                renderer._synth(CLIP_TEXTS[key], renderer.clip_path(key), **kwargs)
                print(f"[{i}/{len(todo)}] {key}")
                break
            except Exception as e:  # noqa: BLE001
                if attempt == 2:
                    failed.append(key)
                    print(f"[{i}/{len(todo)}] GAGAL {key}: {e}")
                else:
                    time.sleep(2 * (attempt + 1))
        time.sleep(args.delay)

    if failed:
        sys.exit(f"{len(failed)} klip gagal dibuat. Jalankan ulang perintah ini.")
    print("Selesai. Semua klip tersedia.")


if __name__ == "__main__":
    main()
