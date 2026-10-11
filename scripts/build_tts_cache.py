"""Buat semua klip suara tetap (kalimat, frasa, kata angka, nama bulan) dengan gTTS.

Jalankan sekali saat online:
    python scripts/build_tts_cache.py
    python scripts/build_tts_cache.py --force      # buat ulang semua klip
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sayit.audio.tts import SpeechRenderer, gtts_save, internet_available  # noqa: E402
from sayit.config import load_config  # noqa: E402
from sayit.response.templates import CLIP_TEXTS  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--delay", type=float, default=0.3, help="jeda antar-permintaan (detik)")
    args = ap.parse_args()

    if not internet_available():
        sys.exit("Tidak ada koneksi internet. Klip hanya bisa dibuat saat online.")

    cfg = load_config()
    renderer = SpeechRenderer(cfg, online=True)
    kwargs = renderer._synth_kwargs()
    todo = [k for k in CLIP_TEXTS if args.force or not renderer.clip_path(k).exists()]
    print(f"{len(CLIP_TEXTS)} klip terdaftar, {len(todo)} akan dibuat -> {renderer.clip_dir}")

    failed = []
    for i, key in enumerate(todo, 1):
        for attempt in range(3):
            try:
                gtts_save(CLIP_TEXTS[key], renderer.clip_path(key), **kwargs)
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
