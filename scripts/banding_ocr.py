"""Ablasi PRD Bagian 11 nomor 2: EasyOCR lawan PaddleOCR.

Menjalankan kedua mesin OCR pada data uji yang sama, lalu melaporkan:

* Dokumen  - Character Error Rate (target PRD <= 15%) dan waktu per halaman.
* Kemasan  - dipecah menjadi BENAR / SALAH / DIAM, bukan satu persentase.

Pemecahan tiga arah itu disengaja. Bagi pengguna tunanetra, tanggal kedaluwarsa
yang SALAH jauh lebih berbahaya daripada sistem yang DIAM: yang pertama bisa
membuat orang memakan makanan basi, yang kedua hanya membuat orang bertanya ke
orang lain. Mesin yang akurasinya lebih tinggi tetapi salahnya lebih banyak
belum tentu mesin yang lebih baik.

Arah kesalahan juga dilaporkan. Menjawab "sudah kedaluwarsa" padahal belum itu
merugikan tetapi aman; kebalikannya berbahaya.

PENTING - satu mesin per proses. Memuat EasyOCR (torch) dan PaddleOCR bersamaan
dalam satu proses membuatnya **crash native** (keluar kode 4, tanpa traceback),
terbukti 30-09. Jalankan dua kali dengan `--mesin`, lalu bandingkan keluarannya:

    python scripts\\banding_ocr.py --mesin easyocr   --hanya kemasan
    python scripts\\banding_ocr.py --mesin paddleocr --hanya kemasan

Tanpa `--mesin` skrip menjalankan keduanya dan akan memperingatkan lebih dulu.

Catatan PaddleOCR di lingkungan ini (diukur 01-10): oneDNN tidak bisa dinyalakan
pada paddlepaddle 3.3.1, sehingga akselerasi CPU hilang dan latensinya 101 detik
per foto bahkan pada 800 px (EasyOCR: 1,5 detik). Paddle juga crash bila diberi
foto 3024x4032 utuh, jadi `--sisi` memperkecil gambar lebih dulu.
"""
from __future__ import annotations

import argparse
import copy
import sys
import time
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sayit.config import load_config, project_path            # noqa: E402
from sayit.gambar import baca, daftar_gambar                  # noqa: E402
from sayit.vision.document import DocumentReader              # noqa: E402
from sayit.vision.expiry import ExpiryReader                  # noqa: E402
from scripts.ukur_dokumen import cer, pasangan                # noqa: E402
from scripts.ukur_kedaluwarsa import harapan_dari_nama        # noqa: E402

MESIN = ("easyocr", "paddleocr")


def perkecil(img, sisi: int | None):
    """Perkecil agar sisi terpanjang <= `sisi`. None berarti biarkan apa adanya.

    PaddleOCR crash native bila diberi foto 3024x4032 utuh, jadi pembandingan
    yang jujur harus memberi kedua mesin gambar berukuran sama.
    """
    import cv2
    if not sisi or max(img.shape[:2]) <= sisi:
        return img
    skala = sisi / max(img.shape[:2])
    return cv2.resize(img, (max(1, int(img.shape[1] * skala)), max(1, int(img.shape[0] * skala))),
                      interpolation=cv2.INTER_AREA)


def pembaca_untuk(mesin: str, cfg_dasar: dict):
    cfg = copy.deepcopy(cfg_dasar)
    cfg["vision"]["document"]["engine"] = mesin
    ocr = DocumentReader(cfg)
    t = time.perf_counter()
    ocr.load()
    return cfg, ocr, time.perf_counter() - t


def nilai_tanggal(jawaban, harapan, hanya_bulan) -> str:
    if harapan == "kosong":
        return "BENAR" if jawaban is None else "SALAH"
    if jawaban is None:
        return "DIAM"
    if hanya_bulan:
        return "BENAR" if (jawaban.year, jawaban.month) == (harapan.year, harapan.month) else "SALAH"
    return "BENAR" if jawaban == harapan else "SALAH"


def arah_salah(jawaban, harapan, hari_ini) -> str:
    """Apakah kesalahannya mengarah ke sisi yang aman?

    "sudah kedaluwarsa" padahal belum  -> aman (makanan layak terbuang)
    "belum kedaluwarsa" padahal sudah  -> BERBAHAYA
    """
    if harapan == "kosong" or jawaban is None:
        return "mengarang" if harapan == "kosong" else ""
    sudah_h, sudah_j = harapan < hari_ini, jawaban < hari_ini
    if sudah_h == sudah_j:
        return "sisi sama"
    return "aman" if sudah_j else "BERBAHAYA"


def banding_kemasan(cfg_dasar: dict, folder: Path, hari_ini: date, mesin_dipakai,
                    sisi: int | None = None) -> None:
    berkas = [p for p in daftar_gambar(folder) if harapan_dari_nama(p)[0] is not None]
    if not berkas:
        print(f"Tidak ada kemasan yang bisa dinilai di {folder}")
        return

    print(f"\n{'=' * 92}\nKEMASAN ({len(berkas)} foto) - {folder}\n{'=' * 92}")
    hasil: dict[str, dict] = {}
    for mesin in mesin_dipakai:
        cfg, ocr, muat_s = pembaca_untuk(mesin, cfg_dasar)
        pembaca = ExpiryReader(cfg, ocr=ocr)
        tally: dict[str, int] = {}
        salah_rinci: list[str] = []
        detik = 0.0
        for p in berkas:
            harapan, hanya_bulan = harapan_dari_nama(p)
            t = time.perf_counter()
            h = pembaca.read(perkecil(baca(p), sisi), today=hari_ini)
            detik += time.perf_counter() - t
            v = nilai_tanggal(h.date.value, harapan, hanya_bulan)
            tally[v] = tally.get(v, 0) + 1
            if v == "SALAH":
                salah_rinci.append(
                    f"{p.stem} harusnya {harapan} dijawab {h.date.value} "
                    f"[{arah_salah(h.date.value, harapan, hari_ini)}]")
        hasil[mesin] = {"tally": tally, "salah": salah_rinci,
                        "detik": detik / len(berkas), "muat_s": muat_s}

    print(f"{'mesin':<12} {'BENAR':>6} {'SALAH':>6} {'DIAM':>6} {'akurasi':>9} "
          f"{'detik/foto':>11} {'muat':>7}")
    print("-" * 92)
    for mesin in mesin_dipakai:
        r = hasil[mesin]
        t = r["tally"]
        print(f"{mesin:<12} {t.get('BENAR', 0):>6} {t.get('SALAH', 0):>6} {t.get('DIAM', 0):>6} "
              f"{t.get('BENAR', 0) / len(berkas):>8.0%} {r['detik']:>10.2f}s {r['muat_s']:>6.1f}s")
    for mesin in mesin_dipakai:
        if hasil[mesin]["salah"]:
            print(f"\njawaban SALAH {mesin}:")
            for baris in hasil[mesin]["salah"]:
                print(f"  {baris}")
    print("\nTarget PRD Bagian 11: akurasi >= 70%. Bandingkan juga kolom SALAH: mesin dengan\n"
          "akurasi lebih tinggi tetapi SALAH lebih banyak belum tentu lebih baik untuk\n"
          "pengguna tunanetra. Perhatikan penanda [aman] / [BERBAHAYA] di atas.")


def banding_dokumen(cfg_dasar: dict, folder: Path, mesin_dipakai,
                    sisi: int | None = None) -> None:
    berkas = pasangan(folder)
    if not berkas:
        print(f"Tidak ada pasangan gambar + teks acuan di {folder}")
        return
    acuan = {g: a.read_text(encoding="utf-8") for g, a in berkas}
    gambar = {g: perkecil(baca(g), sisi) for g, _ in berkas}

    print(f"\n{'=' * 92}\nDOKUMEN ({len(berkas)} foto) - {folder}\n{'=' * 92}")
    nilai: dict[str, dict] = {}
    for mesin in mesin_dipakai:
        _, ocr, muat_s = pembaca_untuk(mesin, cfg_dasar)
        per_berkas, detik = {}, 0.0
        for g, _ in berkas:
            t = time.perf_counter()
            hasil = ocr.read(gambar[g])
            detik += time.perf_counter() - t
            per_berkas[g] = cer(acuan[g], hasil.text)
        nilai[mesin] = {"per_berkas": per_berkas,
                        "rerata": sum(per_berkas.values()) / len(per_berkas),
                        "detik": detik / len(berkas), "muat_s": muat_s}

    kepala = "".join(f"{m:>12}" for m in mesin_dipakai)
    print(f"{'berkas':<34}{kepala}")
    print("-" * 92)
    for g, _ in berkas:
        sel = "".join(f"{nilai[m]['per_berkas'][g]:>11.1%} " for m in mesin_dipakai)
        print(f"{g.name:<34}{sel}")
    print("-" * 92)
    for label, kunci, fmt in (("RERATA CER", "rerata", "{:>11.1%} "),
                              ("detik/halaman", "detik", "{:>11.2f} "),
                              ("detik memuat bobot", "muat_s", "{:>11.1f} ")):
        print(f"{label:<34}" + "".join(fmt.format(nilai[m][kunci]) for m in mesin_dipakai))
    print("\nTarget PRD Bagian 11: CER <= 15%.")
    for mesin, r in nilai.items():
        print(f"  {mesin:<12} {r['rerata']:>6.1%} "
              f"{'TERCAPAI' if r['rerata'] <= 0.15 else 'BELUM TERCAPAI'}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--hanya", choices=("dokumen", "kemasan"), default=None)
    ap.add_argument("--mesin", choices=MESIN, default=None,
                    help="jalankan satu mesin saja (disarankan: keduanya dalam satu proses crash)")
    ap.add_argument("--dokumen", type=Path, default=Path("data/uji_dokumen"))
    ap.add_argument("--kemasan", type=Path, default=Path("data/uji_kedaluwarsa"))
    ap.add_argument("--sisi", type=int, default=None,
                    help="perkecil sisi terpanjang ke nilai ini sebelum OCR "
                         "(wajib untuk paddleocr: crash pada 3024x4032; coba 800)")
    args = ap.parse_args()

    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    mesin_dipakai = (args.mesin,) if args.mesin else MESIN
    if not args.mesin:
        print("PERINGATAN: menjalankan kedua mesin dalam satu proses pernah crash native\n"
              "(keluar kode 4, tanpa traceback) karena torch dan paddle dimuat bersamaan.\n"
              "Disarankan memakai --mesin easyocr lalu --mesin paddleocr secara terpisah.\n")

    cfg = load_config()
    hari_ini = date.today()

    if args.hanya != "kemasan":
        banding_dokumen(cfg, project_path(args.dokumen), mesin_dipakai, args.sisi)
    if args.hanya != "dokumen":
        banding_kemasan(cfg, project_path(args.kemasan), hari_ini, mesin_dipakai, args.sisi)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
