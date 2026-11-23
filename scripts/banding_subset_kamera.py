"""Akurasi pada SELURUH 16 berkas lawan subset 13 FOTO KAMERA saja.

Tiga berkas di `data/uji_kedaluwarsa/` adalah tangkapan layar, bukan keluaran
kamera: `202804_tolakangin2.PNG`, `20290821_tisu1.PNG`, `20290821_tisu2.PNG`.
Ketiganya 828x1792 - resolusi layar iPhone 11/XR tepat - tanpa EXIF kamera, dan
pada `tisu2` antarmuka aplikasi Foto terlihat di dalam gambarnya.

Daripada mengeluarkannya diam-diam atau memotret ulang, skrip ini melaporkan
KEDUA angka. Jurnal yang menyebut keduanya lebih kuat daripada yang menyebut
salah satu: pembaca bisa melihat sendiri berapa besar pengaruh mutu data uji
terhadap angkanya.

Sumber datanya hasil yang SUDAH diukur, bukan pengukuran baru:
  - lokal  : docs/lampiran-radit/01_hasil_per_gambar.csv
  - deploy : docs/lampiran-radit/06_waktu_respons_deploy.csv, dinilai ulang
             dengan logika yang sama seperti scripts/nilai_respons_deploy.py
"""
from __future__ import annotations

import csv
import sys
from collections import Counter
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(AKAR), str(AKAR / "scripts")]

TANGKAPAN_LAYAR = {
    "202804_tolakangin2.PNG",
    "20290821_tisu1.PNG",
    "20290821_tisu2.PNG",
}


def rekap(nilai_per_gambar: dict[str, str], saring: bool) -> tuple[Counter, int]:
    c = Counter()
    for nama, nilai in nilai_per_gambar.items():
        if saring and nama in TANGKAPAN_LAYAR:
            continue
        c[nilai] += 1
    return c, sum(c.values())


def baris(label: str, c: Counter, n: int) -> str:
    return (f"{label:<46} {c['BENAR']:>6} {c['SALAH']:>6} {c['KOSONG']:>7} "
            f"{n:>5} {c['BENAR'] / n:>8.0%}")


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    lokal_csv = AKAR / "docs" / "lampiran-radit" / "01_hasil_per_gambar.csv"
    lokal = {r["gambar"]: r["nilai"]
             for r in csv.DictReader(open(lokal_csv, encoding="utf-8"))}

    # Deploy dinilai ulang di sini supaya kedua kolom memakai sumber yang sama
    # dengan lampiran, bukan angka yang disalin tangan.
    from nilai_respons_deploy import ujaran_untuk, inti_tanggal          # noqa: E402
    from ukur_kedaluwarsa import harapan_dari_nama                        # noqa: E402
    from datetime import date

    deploy_csv = AKAR / "docs" / "lampiran-radit" / "06_waktu_respons_deploy.csv"
    rows = list(csv.DictReader(open(deploy_csv, encoding="utf-8")))
    pertama: dict[str, dict] = {}
    for r in rows:
        pertama.setdefault(r["gambar"], r)

    hari_ini = date(2026, 11, 24)
    deploy: dict[str, str] = {}
    for nama, r in pertama.items():
        jawab = (r["jawaban"] or "").lower()
        harapan, hanya_bulan = harapan_dari_nama(Path(nama))
        tanpa_tanggal = (
            "502" in r.get("status", "") or not jawab.strip()
            or "terlalu gelap" in jawab or "terlalu buram" in jawab
            or "mundurkan kamera" in jawab or "tidak menemukan" in jawab
            or "tidak yakin itu tanggal" in jawab or "kurang jelas" in jawab)
        if harapan == "kosong":
            deploy[nama] = "BENAR" if tanpa_tanggal else "SALAH"
        elif tanpa_tanggal:
            deploy[nama] = "KOSONG"
        else:
            diharap = inti_tanggal(ujaran_untuk(harapan, hari_ini, hanya_bulan))
            deploy[nama] = "BENAR" if diharap and diharap in jawab else "SALAH"

    print(f"{'kondisi':<46} {'BENAR':>6} {'SALAH':>6} {'KOSONG':>7} "
          f"{'n':>5} {'akurasi':>8}")
    print("-" * 84)
    for label, data in (("LOKAL (ExpiryReader.read)", lokal),
                        ("DEPLOY (lewat Vercel+ngrok)", deploy)):
        for saring, akhiran in ((False, "seluruh berkas"), (True, "foto kamera saja")):
            c, n = rekap(data, saring)
            print(baris(f"{label} - {akhiran}", c, n))
        print()

    print("Tiga berkas yang dikeluarkan di baris 'foto kamera saja':")
    for n in sorted(TANGKAPAN_LAYAR):
        print(f"  {n:<30} lokal {lokal.get(n, '?'):>6}   deploy {deploy.get(n, '?'):>6}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
