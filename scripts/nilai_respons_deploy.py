"""Nilai BENAR / SALAH / KOSONG dari jawaban yang BENAR-BENAR diucapkan deploy.

Kenapa ini ada: angka 81% di jurnal diukur dengan memanggil `ExpiryReader.read()`
langsung di laptop. Jalur produksi berbeda - foto melewati `/foto` (quality gate,
yang mengubah ukuran gambar) sebelum `/tanya`. Belum pernah ada yang memeriksa
apakah kedua jalur itu memberi jawaban yang sama.

Penilaian dilakukan dengan membandingkan teks yang diucapkan terhadap ujaran
yang SEHARUSNYA keluar untuk tanggal acuan - dibangun memakai fungsi ujaran
proyek sendiri (`expiry_response`), bukan dengan mencocokkan kata secara manual.
Jadi kalau kalimatnya kelak berubah, penilaian ini ikut berubah dengan benar.

Pemakaian:
    python scripts\\nilai_respons_deploy.py docs\\jurnal_bahan\\waktu_respons_deploy.csv
"""
from __future__ import annotations

import argparse
import csv
import statistics
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(AKAR), str(AKAR / "scripts")]

from sayit.response.templates import expiry_response, to_plain_text   # noqa: E402
from ukur_kedaluwarsa import harapan_dari_nama             # noqa: E402


def ujaran_untuk(nilai: date, hari_ini: date, hanya_bulan: bool) -> str:
    """Kalimat yang SEHARUSNYA diucapkan untuk tanggal ini, dari fungsi proyek."""
    u = expiry_response(nilai, hari_ini, month_only=hanya_bulan, confident=True)
    return to_plain_text(u).lower()


def inti_tanggal(kalimat: str) -> str:
    """Buang pembuka ('tanggal kedaluwarsa', 'saya kurang yakin ...') dan sisa
    kalimat setelah tanggalnya, supaya yang dibandingkan hanya bagian tanggal."""
    k = kalimat.lower()
    for pembuka in ("tanggal yang terbaca adalah ", "tanggal kedaluwarsa ",
                    "berlaku sampai "):
        if pembuka in k:
            k = k.split(pembuka, 1)[1]
            break
    return k.split(".")[0].strip()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("csv", type=Path)
    ap.add_argument("--hari-ini", default=None,
                    help="tanggal acuan 'hari ini' (YYYY-MM-DD); bawaan: hari ini")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    hari_ini = date.fromisoformat(args.hari_ini) if args.hari_ini else date.today()
    baris = list(csv.DictReader(open(args.csv, encoding="utf-8")))
    if not baris:
        print("CSV kosong")
        return 1

    per_gambar: dict[str, list] = defaultdict(list)
    for r in baris:
        per_gambar[r["gambar"]].append(r)

    print(f"{len(baris)} percobaan, {len(per_gambar)} gambar unik, "
          f"hari ini = {hari_ini.isoformat()}\n")
    print(f"{'gambar':<30} {'acuan':>12} {'nilai':>7} {'median s':>9} {'maks s':>8}  jawaban")
    print("-" * 118)

    tally = Counter()
    sebab_per: dict[str, str] = {}
    semua_total = []
    for nama in sorted(per_gambar):
        rows = per_gambar[nama]
        harapan, hanya_bulan = harapan_dari_nama(Path(nama))
        jawab = (rows[0]["jawaban"] or "").lower()
        status = rows[0].get("status", "")

        # SEBAB dipisah dari NILAI. Tiga hal yang sama-sama berakhir "tanpa
        # tanggal" punya sebab yang sama sekali berbeda, dan menyatukannya
        # menyembunyikan justru yang paling penting untuk jurnal:
        #   - proksi Vercel menyerah (502) -> kegagalan INFRASTRUKTUR
        #   - antrean server penuh         -> kegagalan INFRASTRUKTUR
        #   - quality gate menolak fotonya -> foto tidak pernah sampai ke OCR
        #   - OCR/parser tidak menemukan   -> kegagalan PENGENALAN
        if "502" in status:
            sebab = "proksi Vercel 502 (>120 s)"
        elif not jawab.strip():
            sebab = "server sibuk (antrean penuh)"
        elif "terlalu gelap" in jawab or "terlalu buram" in jawab or "mundurkan kamera" in jawab:
            sebab = "DITOLAK quality gate"
        elif "tidak menemukan" in jawab:
            sebab = "tidak menemukan tanggal"
        elif "tidak yakin itu tanggal" in jawab or "kurang jelas" in jawab:
            sebab = "tulisan terbaca, bukan tanggal"
        else:
            sebab = ""

        # "Tidak menyebutkan tanggal" mencakup SEMUA kalimat di atas. Skrip
        # lokal menilainya dari `value is None`, jadi penilaian teks ini harus
        # mencakup hal yang sama - kalau tidak, selisih lokal-vs-deploy akan
        # memuat cacat penilai, bukan cuma cacat sistem.
        tanpa_tanggal = bool(sebab)

        if harapan == "kosong":
            nilai = "BENAR" if tanpa_tanggal else "SALAH"
        elif tanpa_tanggal:
            nilai = "KOSONG"
        else:
            diharap = inti_tanggal(ujaran_untuk(harapan, hari_ini, hanya_bulan))
            nilai = "BENAR" if diharap and diharap in jawab else "SALAH"
        tally[nilai] += 1
        sebab_per[nama] = sebab

        tot = [float(r["total_s"]) for r in rows if r["total_s"]]
        semua_total += tot
        med = statistics.median(tot) if tot else 0.0
        mx = max(tot) if tot else 0.0
        teks_h = "kosong" if harapan == "kosong" else (
            f"{harapan.year}-{harapan.month:02d}" if hanya_bulan else harapan.isoformat())
        print(f"{nama:<30} {teks_h:>12} {nilai:>7} {med:>8.2f}s {mx:>7.2f}s  "
              f"{sebab_per[nama] or jawab[:42]}")

    n = sum(tally.values())
    print("-" * 118)
    print(f"LEWAT DEPLOY: {tally['BENAR']} BENAR / {tally['SALAH']} SALAH / "
          f"{tally['KOSONG']} KOSONG dari {n} = {tally['BENAR'] / n:.0%}")
    print("Pembanding pengukuran LOKAL (ExpiryReader.read langsung): 13 / 2 / 1 = 81%")
    if semua_total:
        print(f"\nTOTAL per giliran: median {statistics.median(semua_total):.2f} s   "
              f"rerata {statistics.fmean(semua_total):.2f} s   "
              f"maks {max(semua_total):.2f} s   n={len(semua_total)}")
    inf = [n for n, s in sebab_per.items() if "Vercel" in s or "sibuk" in s]
    gate = [n for n, s in sebab_per.items() if "quality gate" in s]
    if inf:
        print(f"\nKegagalan INFRASTRUKTUR, bukan pengenalan: {len(inf)} gambar")
        for n in inf:
            print(f"  {n:<30} {sebab_per[n]}")
    if gate:
        print(f"DITOLAK quality gate sebelum OCR: {len(gate)} gambar")
        for n in gate:
            print(f"  {n:<30} {sebab_per[n]}")
    print("\nPenilaian memakai fungsi ujaran proyek sendiri, bukan pencocokan kata tangan.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
