"""Ukur Character Error Rate (CER) modul dokumen, sekaligus uji ablasi pra-pemrosesan.

Metrik PRD Bagian 11: CER <= 15%. Ablasi PRD Bagian 11 nomor 1: OCR dengan vs
tanpa pra-pemrosesan.

Susunan berkas di folder uji:

    data/uji_dokumen/
        surat_domisili.jpg      <- fotonya
        surat_domisili.txt      <- teks sebenarnya, apa adanya

Cara paling murah menyiapkan teks acuan: cetak berkas teks yang sudah kamu
punya, potret hasil cetakannya, lalu salin berkas aslinya menjadi `.txt`.
Tidak perlu mengetik ulang apa pun.

Privasi: jangan memakai dokumen pribadi. Isi dokumen dikirim ke Google saat
gTTS membacakannya.

Pemakaian:
    python scripts\\ukur_dokumen.py
    python scripts\\ukur_dokumen.py data\\uji_dokumen --rinci
"""
from __future__ import annotations

import argparse
import re
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sayit.config import load_config, project_path            # noqa: E402
from sayit.gambar import baca, daftar_gambar                  # noqa: E402
from sayit.vision.document import DocumentReader              # noqa: E402

# Berkas acuan boleh .txt atau .md: keduanya sama-sama teks polos, dan tim
# sering sudah punya bahannya dalam bentuk .md.
ACUAN = (".txt", ".md")


# Markup Markdown yang TIDAK terlihat pada foto. Membiarkannya di teks acuan
# berarti menghukum OCR karena tidak membaca karakter yang memang tidak ada.
# Penanda daftar ("-", "1.") sengaja TIDAK dibuang: penanda itu biasanya memang
# tercetak dan terbaca OCR.
_MARKUP = [
    (re.compile(r"^\s{0,3}#{1,6}\s+", re.M), ""),              # judul
    (re.compile(r"\*\*|__"), ""),                              # tebal
    (re.compile(r"(?<![\w*])\*(?=\S)|(?<=\S)\*(?![\w*])"), ""),  # miring
    (re.compile(r"`+"), ""),                                    # kode
    (re.compile(r"\[([^\]]*)\]\([^)]*\)"), r"\1"),           # tautan
]


def buang_markup(teks: str) -> str:
    for pola, ganti in _MARKUP:
        teks = pola.sub(ganti, teks)
    return teks


def normalkan(teks: str) -> str:
    """Samakan hal-hal yang tidak adil dinilai sebagai kesalahan OCR.

    Huruf besar/kecil, jenis tanda kutip, jumlah spasi, dan markup Markdown
    tidak mengubah apa yang terlihat di foto, jadi tidak dihitung sebagai galat.
    """
    teks = buang_markup(teks)
    teks = unicodedata.normalize("NFKC", teks).lower()
    teks = teks.replace("’", "'").replace("‘", "'")
    teks = teks.replace("“", '"').replace("”", '"')
    teks = teks.replace("–", "-").replace("—", "-")
    return re.sub(r"\s+", " ", teks).strip()


def jarak_edit(a: str, b: str) -> int:
    """Levenshtein dengan dua baris, cukup untuk teks sepanjang satu halaman."""
    if a == b:
        return 0
    if not a:
        return len(b)
    sebelum = list(range(len(b) + 1))
    for i, ca in enumerate(a, start=1):
        kini = [i]
        for j, cb in enumerate(b, start=1):
            kini.append(min(sebelum[j] + 1,          # hapus
                            kini[j - 1] + 1,          # sisip
                            sebelum[j - 1] + (ca != cb)))   # ganti
        sebelum = kini
    return sebelum[-1]


def cer(acuan: str, hasil: str) -> float:
    """Character Error Rate. 0 berarti sempurna; bisa melebihi 1 bila hasilnya kacau."""
    acuan, hasil = normalkan(acuan), normalkan(hasil)
    return 0.0 if not acuan else jarak_edit(acuan, hasil) / len(acuan)


def _kunci(nama: str) -> str:
    """Nama tanpa spasi dan tanpa beda huruf besar/kecil.

    Windows menamai berkas salinan `r (1).JPG`, sedangkan teks acuan biasanya
    diketik `r(1).txt`. Beda satu spasi itu membuat seluruh pasangan terlewat
    tanpa suara, jadi lebih baik pencocokannya yang longgar.
    """
    return "".join(nama.split()).lower()


def pasangan(folder: Path) -> list[tuple[Path, Path]]:
    """(gambar, teks acuan) untuk tiap foto yang punya pasangan .txt atau .md."""
    acuan_per_kunci: dict[str, Path] = {}
    for a in sorted(folder.iterdir()):
        if a.is_file() and a.suffix.lower() in ACUAN:
            acuan_per_kunci.setdefault(_kunci(a.stem), a)

    keluar = []
    for p in daftar_gambar(folder):
        acuan = acuan_per_kunci.get(_kunci(p.stem))
        if acuan:
            keluar.append((p, acuan))
        else:
            print(f"  DILEWATI {p.name}: tidak ada {p.stem}.txt maupun {p.stem}.md")
    return keluar


def ablasi_per_langkah(ocr, cfg: dict, berkas, acuan_teks: dict) -> None:
    """Buang satu langkah pra-pemrosesan sekaligus, lihat CER-nya bergerak ke mana.

    Ablasi "semua nyala lawan semua mati" hanya memberi tahu bahwa rangkaiannya
    merugikan, bukan langkah mana penyebabnya. Tanpa ini tidak ada dasar untuk
    memperbaiki rangkaiannya, hanya untuk mematikannya.
    """
    rantai_asli = cfg["vision"]["preprocess"]["chains"]["dokumen"]

    def rerata(rantai) -> float:
        cfg["vision"]["preprocess"]["chains"]["dokumen"] = list(rantai)
        nilai = [cer(acuan_teks[g], ocr.read(baca(g), preprocess=bool(rantai)).text)
                 for g, _ in berkas]
        return sum(nilai) / len(nilai)

    try:
        print(f"\n\nABLASI PER LANGKAH (PRD Bagian 11 nomor 1), {len(berkas)} dokumen")
        print(f"{'kondisi':<28} {'CER':>8} {'selisih':>9}")
        print("-" * 48)
        dasar = rerata(rantai_asli)
        print(f"{'rangkaian penuh':<28} {dasar:>7.1%} {'':>9}")
        for langkah in rantai_asli:
            nilai = rerata([s for s in rantai_asli if s != langkah])
            arah = "MEMBAIK" if nilai < dasar - 0.01 else ("memburuk" if nilai > dasar + 0.01 else "-")
            print(f"{'tanpa ' + langkah:<28} {nilai:>7.1%} {nilai - dasar:>+8.1%}  {arah}")
        kosong = rerata([])
        print(f"{'tanpa pra-pemrosesan':<28} {kosong:>7.1%} {kosong - dasar:>+8.1%}")
    finally:
        cfg["vision"]["preprocess"]["chains"]["dokumen"] = rantai_asli

    print("\nBaca: nilai NEGATIF berarti membuang langkah itu MENURUNKAN galat,\n"
          "yaitu langkah tersebut merugikan pada kumpulan foto ini.")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("folder", type=Path, nargs="?", default=Path("data/uji_dokumen"))
    ap.add_argument("--rinci", action="store_true", help="tampilkan teks hasil OCR")
    ap.add_argument("--mesin", choices=("easyocr", "paddleocr"), default=None,
                    help="timpa vision.document.engine untuk pengukuran ini saja")
    ap.add_argument("--per-langkah", action="store_true",
                    help="ablasi satu langkah dibuang bergantian (lambat: satu OCR per langkah per foto)")
    args = ap.parse_args()

    # konsol Windows memakai cp1252 dan meledak pada karakter di luar itu
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    folder = project_path(args.folder)
    if not folder.is_dir():
        print(f"Folder tidak ada: {folder}\n"
              f"Buat foldernya, isi dengan pasangan <nama>.jpg dan <nama>.txt.")
        return 1
    berkas = pasangan(folder)
    if not berkas:
        print(f"Tidak ada pasangan gambar + .txt di {folder}")
        return 1

    cfg = load_config()
    if args.mesin:
        cfg["vision"]["document"]["engine"] = args.mesin
        print(f"Mesin OCR ditimpa menjadi {args.mesin!r} untuk pengukuran ini.")
    ocr = DocumentReader(cfg)
    ocr.load()

    print(f"\n{'berkas':<34} {'CER dgn pra':>12} {'CER tanpa':>12} {'kata':>6}")
    print("-" * 68)
    kumpulan = {True: [], False: []}
    acuan_teks: dict[Path, str] = {}
    markup = 0
    for gambar, acuan_p in berkas:
        teks_acuan = acuan_teks[gambar] = acuan_p.read_text(encoding="utf-8")
        if acuan_p.suffix.lower() == ".md" and buang_markup(teks_acuan) != teks_acuan:
            markup += 1
        img = baca(gambar)
        nilai = {}
        for pakai in (True, False):
            hasil = ocr.read(img, preprocess=pakai)
            nilai[pakai] = cer(teks_acuan, hasil.text)
            kumpulan[pakai].append(nilai[pakai])
            if args.rinci and pakai:
                print(f"    acuan : {normalkan(teks_acuan)[:110]}")
                print(f"    hasil : {normalkan(hasil.text)[:110]}")
        print(f"{gambar.name:<34} {nilai[True]:>11.1%} {nilai[False]:>11.1%} "
              f"{len(teks_acuan.split()):>6}")

    print("-" * 68)
    n = len(berkas)
    rerata = {k: sum(v) / len(v) for k, v in kumpulan.items()}
    print(f"{'RERATA (' + str(n) + ' dokumen)':<34} {rerata[True]:>11.1%} {rerata[False]:>11.1%}")
    print(f"\nTarget PRD Bagian 11: CER <= 15%. "
          f"{'TERCAPAI' if rerata[True] <= 0.15 else 'BELUM TERCAPAI'} pada kondisi apa adanya.")
    selisih = rerata[False] - rerata[True]
    arah = ("membantu" if selisih > 0 else "memperburuk") if abs(selisih) > 0.01 else "tidak berpengaruh"
    print(f"Ablasi pra-pemrosesan: {arah} (selisih CER {selisih:+.1%}).")
    if markup:
        print(f"Catatan: {markup} berkas acuan berformat .md dan markup-nya dibuang "
              f"sebelum dibandingkan (judul, tebal, miring, kode, tautan).")
    if n < 5:
        print(f"PERINGATAN: baru {n} dokumen. Terlalu sedikit untuk disimpulkan; "
              f"kumpulkan setidaknya 10.")
    if args.per_langkah:
        ablasi_per_langkah(ocr, cfg, berkas, acuan_teks)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
