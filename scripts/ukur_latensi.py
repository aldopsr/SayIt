"""Ukur PRD NFR-01: latensi end-to-end <= 8 detik di laptop tanpa GPU.

NFR-01 mengukur dari **pengguna selesai bicara sampai suara jawaban mulai**, jadi
yang dijumlahkan adalah tiga tahap:

    STT  (faster-whisper)  +  pipeline (router + visi)  +  TTS render

Pemuatan model TIDAK dihitung: itu terjadi sekali saat aplikasi mulai, bukan per
giliran percakapan.

KETERBATASAN yang harus disebut bila angkanya dilaporkan:
* Suara pertanyaan dibuat dengan gTTS, bukan rekaman manusia. Untuk latensi itu
  cukup adil karena waktu STT ditentukan oleh panjang audio, bukan oleh sulitnya
  suara - tetapi akurasi transkripsinya optimistis.
* Diukur pada satu laptop (i7-13650HX, CPU). Anggota tim lain perlu mengukur sendiri.
* Median diambil dari SELURUH foto uji tiap modul, bukan satu foto. Versi pertama skrip
  ini memakai foto pertama saja dan angkanya optimistis: foto dokumen pertama hanya
  2592x1068, sedangkan seri `r` berukuran 3024x4032 dan jauh lebih lambat.
* Jawaban dokumen memakai gTTS langsung, jadi tahap TTS-nya bergantung jaringan.

Pemakaian:
    python scripts\\ukur_latensi.py
    python scripts\\ukur_latensi.py --putaran 5
"""
from __future__ import annotations

import argparse
import io
import os
import statistics
import sys
import time
import warnings
from pathlib import Path

os.environ.setdefault("FLAGS_use_mkldnn", "0")
warnings.filterwarnings("ignore")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np                                                  # noqa: E402
import soundfile as sf                                              # noqa: E402

from sayit.audio import io as aio                                   # noqa: E402
from sayit.audio.stt import Transcriber                             # noqa: E402
from sayit.audio.tts import SpeechRenderer, gtts_save               # noqa: E402
from sayit.config import load_config, project_path                  # noqa: E402
from sayit.gambar import baca, daftar_gambar                        # noqa: E402
from sayit.pipeline import Pipeline                                 # noqa: E402

# Pertanyaan yang diucapkan, dipilih mewakili tiap kemampuan ditambah satu intent kendali.
PERTANYAAN = [
    ("uang", "berapa nilai uang ini"),
    ("dokumen", "tolong bacakan tulisannya"),
    ("kedaluwarsa", "kapan tanggal kedaluwarsanya"),
    ("kendali", "ulangi"),
]


def suara_pertanyaan(teks: str, sr: int, cache: Path) -> np.ndarray:
    """Audio pertanyaan dari gTTS, disimpan supaya putaran berikutnya tidak memanggil jaringan."""
    berkas = cache / (teks.replace(" ", "_") + ".mp3")
    if not berkas.exists():
        gtts_save(teks, berkas)
    audio, sr_asli = sf.read(io.BytesIO(berkas.read_bytes()), dtype="float32")
    return aio.resample(aio.to_mono(audio), sr_asli, sr).astype(np.float32)


def daftar_foto(folder: str, maks: int | None) -> list:
    """Semua foto uji di folder, dibatasi `maks` bila diberikan."""
    berkas = daftar_gambar(project_path(folder))
    return berkas[:maks] if maks else berkas


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--maks-foto", type=int, default=None,
                    help="batasi jumlah foto per modul (bawaan: semua)")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    cfg = load_config()
    sr = cfg["audio"]["sample_rate"]
    cache = project_path("data/_suara_uji")
    cache.mkdir(parents=True, exist_ok=True)

    print("menyiapkan audio pertanyaan (gTTS, sekali saja)...", flush=True)
    audio = {nama: suara_pertanyaan(teks, sr, cache) for nama, teks in PERTANYAAN}
    for nama, a in audio.items():
        print(f"  {nama:<12} {len(a) / sr:.1f} detik", flush=True)

    print("\nmemuat model (TIDAK dihitung dalam NFR-01)...", flush=True)
    t = time.perf_counter()
    p = Pipeline(cfg, transcriber=Transcriber(cfg))
    status = p.load()
    penyuara = SpeechRenderer(cfg)
    muat_s = time.perf_counter() - t
    print(f"  selesai dalam {muat_s:.1f} detik", flush=True)
    for k, v in status.items():
        print(f"    {k:<16} {v}", flush=True)

    foto = {"uang": daftar_foto("data/uji_sendiri", args.maks_foto),
            "dokumen": daftar_foto("data/uji_dokumen", args.maks_foto),
            "kedaluwarsa": daftar_foto("data/uji_kedaluwarsa", args.maks_foto)}
    for nama, daftar in foto.items():
        print(f"  {nama:<12} {len(daftar)} foto uji", flush=True)

    print(f"\n{'=' * 76}\nNFR-01: dari selesai bicara sampai suara jawaban mulai\n{'=' * 76}")
    print(f"{'intent':<13} {'foto':<22} {'STT':>6} {'pipeline':>9} {'TTS':>6} {'TOTAL':>7}  NFR-01")
    print("-" * 76)

    ringkas: dict[str, list[float]] = {}
    for nama, _ in PERTANYAAN:
        # intent kendali tidak memakai foto; sisanya diukur pada SETIAP foto uji
        berkas = [None] * 3 if nama == "kendali" else foto.get(nama) or []
        if not berkas:
            print(f"{nama:<13} dilewati: tidak ada foto uji")
            continue
        for jalur in berkas:
            if jalur is not None:
                giliran_foto = p.set_photo(baca(jalur))
                if giliran_foto.intent != "FOTO":
                    # quality gate menolak foto ini; latensinya tidak mewakili
                    print(f"{nama:<13} {jalur.stem[:22]:<22} ditolak quality gate "
                          f"({giliran_foto.reason})", flush=True)
                    continue
            t0 = time.perf_counter()
            giliran = p.listen(audio[nama], sr=sr)
            t1 = time.perf_counter()
            try:
                penyuara.render(giliran.utterance)
            except Exception as exc:
                print(f"{nama:<13} {'-' if jalur is None else jalur.stem[:22]:<22} "
                      f"TTS gagal: {type(exc).__name__}", flush=True)
                continue
            t2 = time.perf_counter()
            stt_s = giliran.notes.get("stt_s") or 0.0
            total = t2 - t0
            ringkas.setdefault(nama, []).append(total)
            label = "-" if jalur is None else jalur.stem[:22]
            print(f"{nama:<13} {label:<22} {stt_s:>5.1f}s {t1 - t0 - stt_s:>8.1f}s "
                  f"{t2 - t1:>5.1f}s {total:>6.1f}s  {'LOLOS' if total <= 8 else 'LEWAT'}",
                  flush=True)

    print("-" * 76)
    print(f"{'intent':<13} {'n':>4} {'median':>8} {'p90':>7} {'maks':>7}  NFR-01 <= 8 detik")
    lolos_semua = True
    for nama, nilai in ringkas.items():
        urut = sorted(nilai)
        med = statistics.median(urut)
        p90 = urut[min(len(urut) - 1, int(round(0.9 * (len(urut) - 1))))]
        lolos = med <= 8
        lolos_semua = lolos_semua and lolos
        tanda = "LOLOS" if lolos else "LEWAT"
        if lolos and max(urut) > 8:
            tanda = "LOLOS (median), ada foto yang lewat"
        print(f"{nama:<13} {len(urut):>4} {med:>7.1f}s {p90:>6.1f}s {max(urut):>6.1f}s  {tanda}")
    print(f"\nPRD Bagian 11 menilai dari MEDIAN. "
          f"{'Semua intent lolos.' if lolos_semua else 'Ada intent yang melewati 8 detik.'}")
    print(f"Pemuatan model {muat_s:.1f} detik, sekali saat aplikasi mulai, di luar NFR-01.")
    print("\nKeterbatasan: suara pertanyaan dari gTTS (bukan manusia), satu laptop, "
          "dan jawaban dokumen memakai gTTS langsung sehingga bergantung jaringan.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
