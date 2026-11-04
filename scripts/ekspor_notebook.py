"""Ekspor sel kode notebook menjadi berkas .py yang bisa dibaca AST.

Alasannya: graphify (dan linter, dan `grep -n`) tidak mengenal `.ipynb` sama
sekali - `.ipynb` tidak ada di 114 ekstensi kode maupun 10 ekstensi dokumen yang
didukungnya. Akibatnya keempat notebook proyek ini TIDAK TERLIHAT oleh knowledge
graph, termasuk `04_money_kfold.ipynb` yang memuat logika k-fold penghasil angka
90,1%. Yang masuk graph hanya prosa CLAUDE.md *tentang* notebook itu.

Keluarannya berkas turunan, jadi ditaruh di `notebooks/_ekspor/` dan diabaikan
Git - sama seperti `graphify-out/`. Jalankan ulang setiap kali notebook berubah:

    python scripts\\ekspor_notebook.py

Baris ajaib IPython (`!pip`, `!nvidia-smi`) dikomentari, bukan dibuang, supaya
nomor barisnya tetap sejajar dengan sel aslinya dan hasilnya tetap sah sebagai
Python. Penjaganya: tiap berkas keluaran WAJIB lolos `ast.parse`, dan skrip ini
berhenti dengan galat bila ada yang tidak.
"""
from __future__ import annotations

import argparse
import ast
import json
import sys
from pathlib import Path

AKAR = Path(__file__).resolve().parents[1]
SUMBER = AKAR / "notebooks"
TUJUAN = SUMBER / "_ekspor"


def baris_aman(baris: str) -> str:
    """Komentari baris ajaib IPython; sisanya dibiarkan apa adanya."""
    if baris.lstrip().startswith(("!", "%")):
        return "# [ajaib ipython] " + baris
    return baris


def ekspor_satu(nb_path: Path) -> tuple[str, int, int]:
    """Ubah satu notebook menjadi teks Python. -> (teks, jumlah_sel, jumlah_ajaib)."""
    nb = json.loads(nb_path.read_text(encoding="utf-8"))
    potongan = [
        f'"""Hasil ekspor otomatis dari {nb_path.name}.',
        "",
        "JANGAN SUNTING BERKAS INI - suntingannya akan tertimpa.",
        "Sumbernya notebook; jalankan scripts/ekspor_notebook.py setelah notebook berubah.",
        '"""',
        "",
    ]
    n_sel = n_ajaib = 0
    for i, sel in enumerate(nb.get("cells", [])):
        if sel.get("cell_type") != "code":
            continue
        isi = "".join(sel.get("source", []))
        if not isi.strip():
            continue
        n_sel += 1
        aman = []
        for baris in isi.splitlines():
            baru = baris_aman(baris)
            n_ajaib += baru != baris
            aman.append(baru)
        potongan.append(f"# %% sel {i}")
        potongan.extend(aman)
        potongan.append("")
    return "\n".join(potongan) + "\n", n_sel, n_ajaib


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--periksa", action="store_true",
                    help="hanya periksa apakah hasil ekspor sudah mutakhir, tanpa menulis")
    args = ap.parse_args()

    if not SUMBER.is_dir():
        print(f"Folder {SUMBER} tidak ada.", file=sys.stderr)
        return 1

    notebooks = sorted(SUMBER.glob("*.ipynb"))
    if not notebooks:
        print(f"Tidak ada .ipynb di {SUMBER}.", file=sys.stderr)
        return 1

    TUJUAN.mkdir(parents=True, exist_ok=True)
    basi, gagal = [], []
    for nb in notebooks:
        teks, n_sel, n_ajaib = ekspor_satu(nb)
        keluar = TUJUAN / (nb.stem + ".py")

        # Penjaga utama: keluaran yang tidak bisa di-parse tidak berguna bagi AST
        # mana pun, dan kegagalannya harus KERAS - skrip ukur yang gagal diam-diam
        # sudah dua kali merugikan proyek ini.
        try:
            ast.parse(teks, filename=str(keluar))
        except SyntaxError as e:
            gagal.append((nb.name, e))
            print(f"  GAGAL  {nb.name}: baris {e.lineno}: {e.msg}", file=sys.stderr)
            continue

        lama = keluar.read_text(encoding="utf-8") if keluar.exists() else None
        if lama == teks:
            print(f"  tetap  {keluar.relative_to(AKAR)}  ({n_sel} sel)")
            continue
        if args.periksa:
            basi.append(keluar)
            print(f"  BASI   {keluar.relative_to(AKAR)}")
            continue
        keluar.write_text(teks, encoding="utf-8")
        catatan = f", {n_ajaib} baris ajaib dikomentari" if n_ajaib else ""
        print(f"  tulis  {keluar.relative_to(AKAR)}  ({n_sel} sel{catatan})")

    if gagal:
        print(f"\n{len(gagal)} notebook tidak menghasilkan Python yang sah.", file=sys.stderr)
        return 1
    if basi:
        print(f"\n{len(basi)} hasil ekspor sudah basi. Jalankan tanpa --periksa.", file=sys.stderr)
        return 1
    print(f"\n{len(notebooks)} notebook diekspor ke {TUJUAN.relative_to(AKAR)}; semuanya lolos ast.parse.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
