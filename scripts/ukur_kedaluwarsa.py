"""Ukur akurasi tanggal kedaluwarsa end-to-end, sekaligus uji ablasi pra-pemrosesan.

Metrik PRD Bagian 11: akurasi exact match tanggal >= 70%. Ablasi PRD Bagian 11
nomor 1 untuk jalur kedaluwarsa.

Tanggal sebenarnya ditulis di NAMA BERKAS, sehingga tidak perlu berkas label
terpisah:

    data/uji_kedaluwarsa/
        20261203_kopi_bubuk.jpg      -> 3 Desember 2026
        202612_susu_kotak.jpg        -> Desember 2026 (kemasan tanpa tanggal)
        tidakada_keripik.jpg         -> kemasan tanpa tanggal kedaluwarsa sama sekali

Kemasan tanpa hari (hanya bulan dan tahun) dinilai benar bila parser juga
menjawab bulan yang sama. Kemasan tanpa tanggal dinilai benar bila sistem
memang tidak menemukan tanggal.

Pemakaian:
    python scripts\\ukur_kedaluwarsa.py
    python scripts\\ukur_kedaluwarsa.py data\\uji_kedaluwarsa --rinci
"""
from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sayit.config import load_config, project_path            # noqa: E402
from sayit.gambar import baca, daftar_gambar                  # noqa: E402
from sayit.vision.document import DocumentReader              # noqa: E402
from sayit.vision.expiry import ExpiryReader                  # noqa: E402

def harapan_dari_nama(p: Path):
    """(tanggal, hanya_bulan) dari awalan nama berkas. None berarti tidak bisa dibaca.

    'tidakada' berarti kemasan itu memang tidak punya tanggal kedaluwarsa, dan
    jawaban yang benar adalah tidak menemukan apa pun.
    """
    kepala = p.stem.split("_")[0].lower()
    if kepala in ("tidakada", "tanpatanggal"):
        return "kosong", False
    if not kepala.isdigit():
        return None, False
    if len(kepala) == 8:
        return date(int(kepala[:4]), int(kepala[4:6]), int(kepala[6:])), False
    if len(kepala) == 6:
        return date(int(kepala[:4]), int(kepala[4:]), 1), True
    return None, False


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("folder", type=Path, nargs="?", default=Path("data/uji_kedaluwarsa"))
    ap.add_argument("--rinci", action="store_true", help="tampilkan alasan parser")
    ap.add_argument("--mesin", choices=("easyocr", "paddleocr"), default=None,
                    help="timpa vision.document.engine untuk pengukuran ini saja")
    # Memutar POTONGAN zona lawan memutar gambar penuh. Uji lapangan 12-11:
    # Indomie 44,9 detik habis di rotate_retry yang mengulang deteksi zona pada
    # gambar 3000x4000 empat kali, padahal zonanya ketemu di lintasan pertama.
    ap.add_argument("--rotasi-potongan", dest="rotasi_potongan",
                    action=argparse.BooleanOptionalAction, default=None,
                    help="timpa vision.expiry.rotate_crop untuk pengukuran ini saja")
    args = ap.parse_args()

    folder = project_path(args.folder)
    if not folder.is_dir():
        print(f"Folder tidak ada: {folder}\n"
              f"Buat foldernya, beri nama berkas dengan awalan tanggal: 20261203_kopi.jpg")
        return 1
    berkas = daftar_gambar(folder)
    if not berkas:
        print(f"Tidak ada gambar di {folder}")
        return 1

    cfg = load_config()
    if args.rotasi_potongan is not None:
        cfg["vision"]["expiry"]["rotate_crop"] = args.rotasi_potongan
        print(f"vision.expiry.rotate_crop ditimpa menjadi {args.rotasi_potongan}.")
    # Modul kedaluwarsa boleh memakai mesin OCR sendiri (`vision.expiry.engine`),
    # sama seperti yang dilakukan Pipeline. Tanpa ini skrip akan mengukur mesin
    # modul dokumen dan angkanya tidak mewakili perilaku aplikasi.
    mesin = args.mesin or cfg["vision"]["expiry"].get("engine")
    if mesin:
        cfg["vision"]["document"]["engine"] = mesin
        print(f"Mesin OCR modul kedaluwarsa: {mesin!r}.")
    ocr = DocumentReader(cfg)
    ocr.load()
    pembaca = ExpiryReader(cfg, ocr=ocr)
    hari_ini = date.today()

    print(f"\n{'berkas':<32} {'harapan':>12} {'dgn pra':>12} {'tanpa pra':>12}")
    print("-" * 72)
    benar = {True: 0, False: 0}
    dinilai = 0
    for p in berkas:
        harapan, hanya_bulan = harapan_dari_nama(p)
        if harapan is None:
            print(f"{p.name:<32} {'?':>12}   nama berkas tidak berawalan tanggal, dilewati")
            continue
        dinilai += 1
        img = baca(p)
        tampil = {}
        for pakai in (True, False):
            hasil = pembaca.read(img, today=hari_ini) if pakai else baca_tanpa_pra(pembaca, img, hari_ini)
            nilai = hasil.date.value
            if harapan == "kosong":
                cocok = nilai is None
                tampil[pakai] = "-" if nilai is None else nilai.isoformat()
            elif nilai is None:
                cocok = False
                tampil[pakai] = "-"
            elif hanya_bulan:
                cocok = (nilai.year, nilai.month) == (harapan.year, harapan.month)
                tampil[pakai] = f"{nilai.year}-{nilai.month:02d}"
            else:
                cocok = nilai == harapan
                tampil[pakai] = nilai.isoformat()
            benar[pakai] += cocok
            tampil[pakai] += " OK" if cocok else ""
            if args.rinci and pakai:
                print(f"    {hasil.source}: {hasil.date.reason}")
        teks_harapan = ("kosong" if harapan == "kosong"
                        else (f"{harapan.year}-{harapan.month:02d}" if hanya_bulan
                              else harapan.isoformat()))
        print(f"{p.name:<32} {teks_harapan:>12} {tampil[True]:>12} {tampil[False]:>12}")

    print("-" * 72)
    if not dinilai:
        print("Tidak ada berkas yang bisa dinilai.")
        return 1
    a, b = benar[True] / dinilai, benar[False] / dinilai
    print(f"{'AKURASI (' + str(dinilai) + ' kemasan)':<32} {'':>12} {a:>11.0%} {b:>11.0%}")
    print(f"\nTarget PRD Bagian 11: >= 70%. {'TERCAPAI' if a >= 0.7 else 'BELUM TERCAPAI'} "
          f"pada kondisi apa adanya.")
    e = cfg["vision"]["expiry"]
    if not e.get("preprocess_chain") and not e.get("fallback_preprocess_chain"):
        # Kolom pembanding mematikan saklar global `preprocess.enabled`, tetapi
        # rangkaiannya sendiri sudah null, jadi kedua kolom identik dan selisihnya
        # bukan temuan apa pun. Tanpa peringatan ini angka 0% mudah dikutip sebagai
        # "pra-pemrosesan tidak berpengaruh", padahal tidak ada yang dibandingkan.
        print("Ablasi pra-pemrosesan: TIDAK DIUKUR.")
        print("Rangkaian expiry.preprocess_chain dan fallback_preprocess_chain dua-duanya")
        print("null, jadi kedua kolom di atas identik dan selisihnya bukan temuan apa pun.")
        print("Untuk mengukur ablasinya, isi kembali rangkaiannya di config lebih dulu.")
    else:
        selisih = a - b
        arah = ("membantu" if selisih > 0.01 else
                "memperburuk" if selisih < -0.01 else "tidak berpengaruh")
        print(f"Ablasi pra-pemrosesan: {arah} (selisih {selisih:+.0%}).")
    if pembaca.zones.available:
        print(f"Catatan: model zona dipakai bila skornya >= "
              f"{cfg['vision']['expiry']['zone_score_min']}; di bawah itu jatuh ke jalur cadangan.")
    else:
        print("Catatan: bobot zona belum ada, seluruh pengukuran memakai jalur cadangan FR-12.")
    if dinilai < 5:
        print(f"PERINGATAN: baru {dinilai} kemasan. Terlalu sedikit untuk disimpulkan.")
    return 0


def baca_tanpa_pra(pembaca: ExpiryReader, img, hari_ini):
    """Jalankan jalur cadangan tanpa langkah pra-pemrosesan, untuk pembanding ablasi."""
    cfg = pembaca.cfg
    simpan = cfg["vision"]["preprocess"]["enabled"]
    cfg["vision"]["preprocess"]["enabled"] = False
    try:
        return pembaca.read(img, today=hari_ini)
    finally:
        cfg["vision"]["preprocess"]["enabled"] = simpan


if __name__ == "__main__":
    raise SystemExit(main())
