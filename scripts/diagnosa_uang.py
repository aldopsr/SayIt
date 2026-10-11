"""Diagnosis salah tebak nominal uang pada foto sendiri.

Bukan alat demo, melainkan alat pemeriksa: ia menampilkan apa yang sebenarnya
dilihat model sebelum ambang skor memotong apa pun, lalu membandingkan beberapa
kondisi agar penyebab salah tebak bisa dipersempit.

Pemakaian:
    python scripts\\diagnosa_uang.py data\\uji_sendiri\\10000_a.jpg
    python scripts\\diagnosa_uang.py data\\uji_sendiri --harapan-dari-nama
    python scripts\\diagnosa_uang.py foto.jpg --simpan-kotak hasil.jpg

Nama berkas boleh diawali nominal sebenarnya ("10000_meja_siang.jpg"); dengan
`--harapan-dari-nama` skrip membandingkannya dengan tebakan model.
"""
from __future__ import annotations

import argparse
import hashlib
import sys
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sayit.gambar import baca, daftar_gambar
from sayit.config import load_config                                    # noqa: E402
from sayit.response.templates import VALID_NOMINALS, to_plain_text      # noqa: E402
from sayit.vision import quality_gate as qg                             # noqa: E402
from sayit.vision.money import MoneyDetector, money_utterance, postprocess   # noqa: E402

WARNA = {True: (0, 200, 0), False: (0, 0, 220)}


def lapor_model(bobot: Path) -> None:
    """Sidik jari bobot yang benar-benar dipakai.

    Tanpa ini, mudah sekali mengukur model lama dan mengira itu hasil latihan
    baru, karena keluarannya terlihat masuk akal. Sudah pernah terjadi.
    """
    if not bobot.exists():
        return
    st = bobot.stat()
    sidik = hashlib.sha1(bobot.read_bytes()).hexdigest()[:12]
    waktu = datetime.fromtimestamp(st.st_mtime).strftime("%d-%m-%Y %H:%M")
    print(f"Model   : {bobot.name}  ({st.st_size:,} byte, diubah {waktu}, sha1 {sidik})")


def kumpulkan(jalur: Path) -> list[Path]:
    return daftar_gambar(jalur) if jalur.is_dir() else [jalur]


def nominal_dari_nama(p: Path) -> int | None:
    kepala = p.stem.split("_")[0]
    return int(kepala) if kepala.isdigit() and int(kepala) in VALID_NOMINALS else None


def gambar_kotak(img: np.ndarray, dets, tujuan: Path) -> None:
    salinan = img.copy()
    tebal = max(2, round(max(img.shape[:2]) / 600))
    for d in dets:
        x1, y1, x2, y2 = (int(v) for v in d.box)
        warna = WARNA[d.score >= 0.5]
        cv2.rectangle(salinan, (x1, y1), (x2, y2), warna, tebal)
        cv2.putText(salinan, f"{d.nominal} {d.score:.2f}", (x1, max(20, y1 - 8)),
                    cv2.FONT_HERSHEY_SIMPLEX, tebal / 3, warna, tebal)
    tujuan.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(tujuan), salinan)
    print(f"    kotak digambar ke {tujuan}")


def periksa(detector: MoneyDetector, cfg: dict, img: np.ndarray, label: str) -> list:
    """Jalankan satu kondisi, cetak deteksi mentah dan hasil akhirnya."""
    pakai_pra = label != "tanpa pra-pemrosesan"
    mentah, catatan = detector.raw_detections(img, preprocess=pakai_pra)
    hasil = postprocess(mentah, cfg)

    print(f"  [{label}] {catatan['inference_s']:.2f} s, {len(mentah)} deteksi mentah")
    for d in sorted(mentah, key=lambda d: -d.score):
        tanda = "  " if d.score >= cfg["vision"]["money"]["score_min"] else "x "
        lebar = d.box[2] - d.box[0]
        tinggi = d.box[3] - d.box[1]
        print(f"    {tanda}{d.nominal:>6}  skor {d.score:.3f}  kotak {lebar:.0f}x{tinggi:.0f}")
    if not mentah:
        print("      (model tidak melihat apa pun)")
    print(f"    -> {to_plain_text(money_utterance(hasil))}")
    return mentah


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("jalur", type=Path, help="berkas gambar atau folder berisi gambar")
    ap.add_argument("--harapan-dari-nama", action="store_true",
                    help="bandingkan dengan nominal di awal nama berkas")
    ap.add_argument("--simpan-kotak", type=Path, default=None,
                    help="tulis gambar berkotak (berkas untuk satu foto, folder untuk banyak)")
    ap.add_argument("--ambang", type=float, default=None,
                    help="timpa ambang skor, untuk melihat pengaruhnya")
    args = ap.parse_args()

    cfg = load_config()
    if args.ambang is not None:
        cfg["vision"]["money"]["score_min"] = args.ambang
        print(f"Ambang skor ditimpa menjadi {args.ambang}\n")

    berkas = kumpulkan(args.jalur)
    if not berkas:
        print(f"Tidak ada gambar di {args.jalur}")
        return 1

    detector = MoneyDetector(cfg)
    lapor_model(detector.weights_path)
    try:
        detector.load()
    except FileNotFoundError as e:
        print(e)
        return 1

    # DUA metrik, karena keduanya menjawab pertanyaan berbeda:
    #   kelas  - apakah MODEL mengenali nominalnya (berguna untuk mendiagnosis model)
    #   total  - apakah JAWABAN yang diucapkan benar (yang sebenarnya didengar pengguna)
    # Keduanya bisa berbeda: satu lembar 100.000 yang terdeteksi dua kali tetap
    # benar secara kelas, tetapi diucapkan "totalnya dua ratus ribu rupiah".
    # Sampai 06-10 skrip ini hanya melaporkan metrik kelas, sehingga salah hitung
    # lembar tidak pernah terlihat.
    benar = salah = tanpa_tebakan = 0
    benar_t = salah_t = tanpa_t = 0
    salah_total_rinci = []
    for p in berkas:
        print(f"\n=== {p.name}")
        img = baca(p)
        print(f"  ukuran {img.shape[1]}x{img.shape[0]}")

        laporan = qg.check_quality(img, cfg)
        m = laporan.metrics
        print(f"  quality gate: {'lolos' if laporan.ok else 'DITOLAK ' + str(laporan.kinds)}"
              f"  (blur {m['blur_variance']:.0f}, mean {m['mean']:.0f}, jenuh {m['saturated_ratio']:.2f})")

        mentah = periksa(detector, cfg, img, "apa adanya")
        periksa(detector, cfg, img, "tanpa pra-pemrosesan")

        if args.simpan_kotak:
            tujuan = (args.simpan_kotak / f"{p.stem}_kotak.jpg"
                      if len(berkas) > 1 or args.simpan_kotak.is_dir() else args.simpan_kotak)
            gambar_kotak(img, mentah, tujuan)

        if args.harapan_dari_nama:
            harapan = nominal_dari_nama(p)
            if harapan is None:
                print("  harapan: nama berkas tidak diawali nominal, dilewati")
                continue
            hasil = postprocess(mentah, cfg)
            tebakan = max(hasil.counts, key=hasil.counts.get) if hasil.counts else None
            if tebakan is None:
                tanpa_tebakan += 1
                print(f"  harapan {harapan}, model tidak menjawab")
            elif tebakan == harapan:
                benar += 1
                print(f"  harapan {harapan}, tebakan kelas {tebakan}  BENAR")
            else:
                salah += 1
                print(f"  harapan {harapan}, tebakan kelas {tebakan}  SALAH")

            # metrik kedua: total yang benar-benar diucapkan ke pengguna
            if not hasil.total:
                tanpa_t += 1
            elif hasil.total == harapan:
                benar_t += 1
            else:
                salah_t += 1
                salah_total_rinci.append(
                    f"{p.stem}: harapan {harapan}, total diucapkan {hasil.total} "
                    f"(counts {hasil.counts})")
            print(f"  total diucapkan {hasil.total}  "
                  f"{'BENAR' if hasil.total == harapan else 'SALAH'}")

    if args.harapan_dari_nama:
        total = benar + salah + tanpa_tebakan
        print(f"\n=== Ringkasan: {benar} benar, {salah} salah, {tanpa_tebakan} tidak menjawab "
              f"dari {total} foto")
        if total:
            print(f"    akurasi {benar / total:.1%} (pada foto sendiri, bukan split dataset)")

        print(f"\n=== Ringkasan metrik TOTAL (yang benar-benar diucapkan ke pengguna):")
        print(f"    {benar_t} benar, {salah_t} salah, {tanpa_t} tidak menjawab "
              f"dari {total} foto")
        if total:
            print(f"    akurasi {benar_t / total:.1%}")
        if salah_total_rinci:
            print("    salah hitung lembar:")
            for baris in salah_total_rinci:
                print(f"      {baris}")
        print("\n    Metrik KELAS menjawab 'apakah model mengenali nominalnya'.")
        print("    Metrik TOTAL menjawab 'apakah jawaban yang diucapkan benar'.")
        print("    Yang masuk laporan sebagai akurasi sistem adalah metrik TOTAL:")
        print("    satu lembar yang terdeteksi dua kali diucapkan sebagai dua lembar.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
