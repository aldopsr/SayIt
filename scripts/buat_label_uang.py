"""Buat label YOLO untuk foto uang sendiri, tanpa melabeli manual.

Idenya memakai dua sumber yang masing-masing bisa dipercaya:

- **Kotaknya** diambil dari model. Lokalisasi model terbukti baik pada foto uji
  (kotak selalu tepat di uangnya), walaupun klasifikasinya sering salah.
- **Kelasnya** diambil dari nama berkas, yang kamu sendiri yang menulis.

Jadi bagian yang modelnya tidak bisa dipercaya justru tidak dipakai, dan label
yang dihasilkan tidak mewarisi kesalahan model.

Foto yang meragukan tidak dilabeli otomatis, melainkan didaftar agar kamu
kerjakan manual: foto yang tidak terdeteksi sama sekali, dan foto yang
terdeteksi lebih dari satu lembar (tidak mungkin tahu lembar mana yang mana
hanya dari nama berkas).

Keluarannya berbentuk dataset YOLO siap pakai, bisa langsung diunggah ke Google
Drive atau diimpor ke Roboflow.

Pemakaian:
    python scripts\\buat_label_uang.py
    python scripts\\buat_label_uang.py data\\uji_sendiri --keluar data\\label_sendiri
    python scripts\\buat_label_uang.py --ambang 0.15
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sayit.gambar import baca, daftar_gambar
from sayit.config import load_config, project_path                 # noqa: E402
from sayit.response.templates import VALID_NOMINALS                # noqa: E402
from sayit.vision.money import MoneyDetector, iou                  # noqa: E402

HIJAU, MERAH = (0, 200, 0), (0, 0, 220)


def nominal_dari_nama(p: Path) -> int | None:
    kepala = p.stem.split("_")[0]
    return int(kepala) if kepala.isdigit() and int(kepala) in VALID_NOMINALS else None


def kotak_berbeda(dets, iou_max: float) -> list:
    """Satu kotak per lembar uang, apa pun kelas tebakannya.

    Kelas sengaja diabaikan di sini: model kerap memberi dua tebakan kelas
    berbeda untuk lembar yang sama, dan yang kita butuhkan hanya letaknya.
    """
    disimpan = []
    for d in sorted(dets, key=lambda d: -d.score):
        if not any(iou(d.box, k.box) > iou_max for k in disimpan):
            disimpan.append(d)
    return disimpan


def ke_yolo(box, lebar: int, tinggi: int) -> tuple[float, float, float, float]:
    """(x1, y1, x2, y2) piksel menjadi (xc, yc, w, h) ternormalisasi 0..1."""
    x1, y1, x2, y2 = box
    x1, x2 = sorted((max(0.0, x1), min(float(lebar), x2)))
    y1, y2 = sorted((max(0.0, y1), min(float(tinggi), y2)))
    return ((x1 + x2) / 2 / lebar, (y1 + y2) / 2 / tinggi,
            (x2 - x1) / lebar, (y2 - y1) / tinggi)


def gambar_pratinjau(img: np.ndarray, dets, nominal: int, tujuan: Path, dipakai: bool) -> None:
    salinan = img.copy()
    tebal = max(2, round(max(img.shape[:2]) / 600))
    warna = HIJAU if dipakai else MERAH
    for d in dets:
        x1, y1, x2, y2 = (int(v) for v in d.box)
        cv2.rectangle(salinan, (x1, y1), (x2, y2), warna, tebal)
        teks = f"{nominal} (model: {d.nominal} {d.score:.2f})"
        cv2.putText(salinan, teks, (x1, max(24, y1 - 10)),
                    cv2.FONT_HERSHEY_SIMPLEX, tebal / 3, warna, tebal)
    tujuan.parent.mkdir(parents=True, exist_ok=True)
    cv2.imencode(".jpg", salinan)[1].tofile(str(tujuan))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("sumber", type=Path, nargs="?", default=Path("data/uji_sendiri"),
                    help="folder berisi foto, nama berkas diawali nominal")
    ap.add_argument("--keluar", type=Path, default=Path("data/label_sendiri"),
                    help="folder dataset YOLO yang dihasilkan")
    ap.add_argument("--ambang", type=float, default=0.25,
                    help="skor minimum untuk menerima sebuah kotak; rendah tidak apa-apa "
                         "karena kelas tebakan model memang tidak dipakai")
    ap.add_argument("--bersihkan", action="store_true",
                    help="hapus isi folder keluaran lebih dulu; wajib bila foldernya sudah berisi")
    ap.add_argument("--iou-maks", type=float, default=0.5,
                    help="dua kotak dianggap lembar yang sama di atas nilai ini")
    args = ap.parse_args()

    sumber = project_path(args.sumber)
    if not sumber.is_dir():
        print(f"Folder tidak ada: {sumber}")
        return 1
    berkas = daftar_gambar(sumber)
    if not berkas:
        print(f"Tidak ada gambar di {sumber}")
        return 1

    cfg = load_config()
    detector = MoneyDetector(cfg)
    try:
        model = detector.load()
    except FileNotFoundError as e:
        print(e)
        return 1

    # Urutan kelas harus sama persis dengan CLASSES di notebook, kalau tidak
    # seluruh label yang ditulis akan bergeser tanpa ketahuan.
    urutan = [str(n) for n in VALID_NOMINALS]
    nama_model = getattr(model, "names", None)
    if nama_model:
        dari_model = [str(nama_model[i]) for i in sorted(nama_model)]
        assert dari_model == urutan, (
            f"Urutan kelas model {dari_model} berbeda dari {urutan}. "
            "Label yang ditulis akan salah; samakan dulu.")

    keluar = project_path(args.keluar)
    img_dir, lbl_dir, pra_dir = keluar / "test" / "images", keluar / "test" / "labels", keluar / "pratinjau"

    # Menulis ke folder yang sudah berisi akan MENCAMPUR label baru dengan label lama,
    # dan hasilnya tidak bisa diverifikasi. Terbukti merusak 06-10: folder berisi 15
    # label KOSONG yang ditambahkan di luar skrip ini, lalu ikut terpakai sebagai data
    # latih. Dalam YOLO label kosong berarti 'tidak ada uang di gambar ini', bukan
    # 'belum dilabeli', jadi model justru diajari bahwa uang 5000, 50000, dan 100000
    # adalah latar belakang - persis kelas yang paling lemah.
    berisi = [q for q in (img_dir, lbl_dir) if q.exists() and any(q.iterdir())]
    if berisi and not args.bersihkan:
        print("Folder keluaran sudah berisi:")
        for q in berisi:
            print(f"    {q}")
        print("Menulis ke situ akan mencampur label baru dengan label lama, dan hasilnya")
        print("tidak bisa diverifikasi. Jalankan ulang dengan --bersihkan, atau pilih")
        print("--keluar yang lain.")
        return 1
    if args.bersihkan and keluar.exists():
        shutil.rmtree(keluar)
        print(f"Folder keluaran dibersihkan: {keluar}")
    for d in (img_dir, lbl_dir, pra_dir):
        d.mkdir(parents=True, exist_ok=True)

    dibuat, manual, dilewati = 0, [], []
    for p in berkas:
        nominal = nominal_dari_nama(p)
        if nominal is None:
            dilewati.append((p.name, "nama berkas tidak diawali nominal yang sah"))
            continue

        img = baca(p)
        tinggi, lebar = img.shape[:2]
        # preprocess=False agar koordinat kotak tetap dalam ukuran foto asli
        mentah, _ = detector.raw_detections(img, preprocess=False)
        kuat = [d for d in mentah if d.score >= args.ambang]
        lembar = kotak_berbeda(kuat, args.iou_maks)

        if len(lembar) != 1:
            alasan = ("tidak terdeteksi" if not lembar
                      else f"terdeteksi {len(lembar)} lembar, tidak bisa ditebak mana yang mana")
            manual.append((p.name, alasan))
            gambar_pratinjau(img, lembar, nominal, pra_dir / f"MANUAL_{p.stem}.jpg", dipakai=False)
            continue

        xc, yc, w, h = ke_yolo(lembar[0].box, lebar, tinggi)
        shutil.copy(p, img_dir / p.name)
        (lbl_dir / f"{p.stem}.txt").write_text(
            f"{urutan.index(str(nominal))} {xc:.6f} {yc:.6f} {w:.6f} {h:.6f}\n", encoding="utf-8")
        gambar_pratinjau(img, lembar, nominal, pra_dir / f"{p.stem}.jpg", dipakai=True)
        dibuat += 1

    (keluar / "data.yaml").write_text(
        "train: test/images\nval: test/images\ntest: test/images\n"
        "names:\n" + "".join(f"  {i}: '{n}'\n" for i, n in enumerate(urutan)),
        encoding="utf-8")

    kosong = [q.name for q in lbl_dir.glob("*.txt") if q.stat().st_size == 0]
    assert not kosong, (
        f"{len(kosong)} label kosong tertulis: {kosong[:5]}. Itu tidak boleh terjadi: "
        "label kosong berarti 'tidak ada uang di gambar ini'.")

    print(f"\n{dibuat} label dibuat di {lbl_dir}")
    print(f"Pratinjau berkotak di {pra_dir} - periksa sekilas, buang yang kotaknya meleset.")
    if manual:
        print(f"\n{len(manual)} foto perlu dilabeli manual:")
        print("   Foto ini TIDAK disalin dan TIDAK diberi label kosong. Labeli manual,")
        print("   atau biarkan di luar dataset. JANGAN membuat .txt kosong untuk")
        print("   melengkapinya - itu mengajari model bahwa uangnya adalah latar.")
        for nama, alasan in manual:
            print(f"  {nama:40s} {alasan}")
    if dilewati:
        print(f"\n{len(dilewati)} foto dilewati:")
        for nama, alasan in dilewati:
            print(f"  {nama:40s} {alasan}")
    print(f"\nUnggah folder {keluar.name} ke Google Drive (MyDrive/sayit/data/), lalu daftarkan "
          f"di DATASETS notebook dengan lokal='/content/drive/MyDrive/sayit/data/{keluar.name}'.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
