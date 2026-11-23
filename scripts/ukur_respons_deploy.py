"""Ukur waktu respons SayIt lewat DEPLOY SUNGGUHAN, bukan pemanggilan lokal.

Jalur yang diukur: klien -> Vercel -> tunnel ngrok -> FastAPI di laptop, dan
kembali. Jadi angkanya memuat jaringan, proksi, antrean kunci server, inferensi,
dan render suara - bukan hanya `ExpiryReader.read()`.

Dua tahap diukur terpisah karena pengguna memang mengalaminya terpisah:

    A. POST /api/foto   - quality gate + render suara "silakan bertanya"
    B. POST /api/tanya  - deteksi zona + OCR + parser + render suara jawaban

TOTAL = A + B, yaitu jeda sejak rana ditekan sampai jawaban terdengar.

YANG TIDAK TERUKUR dan wajib disebut saat mengutip angkanya:

1. **Pengenalan suara (STT) tidak ikut.** Pertanyaan dikirim sebagai `teks`,
   bukan rekaman. Di pemakaian nyata ada tambahan perekaman (jeda hening 1,5-3
   detik) dan transkripsi Whisper.
2. **Klien ada di laptop yang sama dengan server.** Lalu lintasnya tetap keluar
   ke tepi ngrok dan kembali, jadi bukan localhost - tetapi ponsel di jaringan
   seluler akan menambah latensi lagi di atas angka ini.
3. Pemutaran audio di sisi klien tidak ikut (durasi bicaranya sendiri).

Pemakaian:
    python scripts\\ukur_respons_deploy.py
    python scripts\\ukur_respons_deploy.py --ulang 3 --keluar hasil.csv
"""
from __future__ import annotations

import argparse
import csv
import statistics
import sys
import time
from pathlib import Path

import requests

AKAR = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(AKAR), str(AKAR / "scripts")]

from sayit.gambar import daftar_gambar                  # noqa: E402
from ukur_kedaluwarsa import harapan_dari_nama          # noqa: E402

BASIS = "https://sayit-app-phi.vercel.app/api"
KEPALA = {"ngrok-skip-browser-warning": "1"}
PERTANYAAN = "kapan kedaluwarsanya"


def satu_percobaan(sesi: requests.Session, jalur: Path) -> dict:
    """Satu giliran lengkap: unggah foto, lalu tanya. Mengembalikan detik tiap tahap."""
    bita = jalur.read_bytes()

    t0 = time.perf_counter()
    r1 = sesi.post(f"{BASIS}/foto", headers=KEPALA,
                   files={"foto": (jalur.name, bita, "image/jpeg")}, timeout=300)
    a = time.perf_counter() - t0
    j1 = r1.json() if r1.ok else {}

    t1 = time.perf_counter()
    r2 = sesi.post(f"{BASIS}/tanya", headers=KEPALA,
                   files={"foto": (jalur.name, bita, "image/jpeg")},
                   data={"teks": PERTANYAAN}, timeout=300)
    b = time.perf_counter() - t1
    j2 = r2.json() if r2.ok else {}

    return {
        "foto_s": round(a, 2),
        "tanya_s": round(b, 2),
        "total_s": round(a + b, 2),
        "diterima": j1.get("diterima"),
        "intent": j2.get("intent"),
        "jawaban": (j2.get("teks") or "").replace("\n", " ")[:160],
        "status": f"{r1.status_code}/{r2.status_code}",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--folder", type=Path, default=AKAR / "data" / "uji_kedaluwarsa")
    ap.add_argument("--ulang", type=int, default=3, help="pengulangan per gambar")
    ap.add_argument("--keluar", type=Path,
                    default=AKAR / "docs" / "jurnal_bahan" / "waktu_respons_deploy.csv")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    berkas = sorted(p for p in daftar_gambar(args.folder)
                    if harapan_dari_nama(p)[0] is not None)
    if not berkas:
        print(f"Tidak ada gambar yang bisa dinilai di {args.folder}")
        return 1

    sesi = requests.Session()
    sehat = sesi.get(f"{BASIS}/sehat", headers=KEPALA, timeout=60)
    if not sehat.ok:
        print(f"Server tidak sehat lewat {BASIS}: {sehat.status_code}")
        return 1
    print(f"Server siap lewat {BASIS}")
    print(f"{len(berkas)} gambar unik x {args.ulang} pengulangan = "
          f"{len(berkas) * args.ulang} giliran, tiap giliran 2 permintaan HTTP\n")

    args.keluar.parent.mkdir(parents=True, exist_ok=True)
    baris: list[dict] = []
    with open(args.keluar, "w", newline="", encoding="utf-8") as f:
        tulis = csv.DictWriter(f, fieldnames=[
            "gambar", "pengulangan", "foto_s", "tanya_s", "total_s",
            "diterima", "intent", "status", "jawaban"])
        tulis.writeheader()
        for ulang in range(1, args.ulang + 1):
            print(f"--- pengulangan {ulang} dari {args.ulang} ---")
            for p in berkas:
                try:
                    h = satu_percobaan(sesi, p)
                except Exception as e:                      # noqa: BLE001
                    h = {"foto_s": "", "tanya_s": "", "total_s": "", "diterima": "",
                         "intent": "GAGAL", "jawaban": str(e)[:160], "status": "-"}
                r = {"gambar": p.name, "pengulangan": ulang, **h}
                baris.append(r)
                tulis.writerow(r)
                f.flush()                                   # hasil separuh tetap selamat
                print(f"  {p.name:<30} foto {str(h['foto_s']):>6}s  "
                      f"tanya {str(h['tanya_s']):>6}s  total {str(h['total_s']):>6}s  "
                      f"{h['intent']}")

    sah = [r for r in baris if isinstance(r["total_s"], float)]
    if not sah:
        print("\nTidak ada percobaan yang berhasil.")
        return 1
    tot = [r["total_s"] for r in sah]
    print(f"\n{'=' * 70}")
    print(f"{len(sah)} percobaan berhasil dari {len(baris)}")
    print(f"TOTAL (foto + tanya)  median {statistics.median(tot):.2f} s   "
          f"rerata {statistics.fmean(tot):.2f} s   "
          f"min {min(tot):.2f} s   maks {max(tot):.2f} s")
    for kunci, nama in (("foto_s", "tahap A /foto "), ("tanya_s", "tahap B /tanya")):
        v = [r[kunci] for r in sah]
        print(f"{nama}        median {statistics.median(v):.2f} s   "
              f"rerata {statistics.fmean(v):.2f} s   maks {max(v):.2f} s")
    print(f"\nCSV: {args.keluar}")
    print("Median DAN maksimum dua-duanya wajib dikutip: sebaran modul ini besar.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
