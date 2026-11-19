"""Modul uang (PRD 8.6): inferensi YOLOv8 dan pasca-pemrosesannya.

Seluruh logika pasca-pemrosesan berupa fungsi murni atas daftar `Detection`,
jadi bisa diuji tanpa memuat bobot model. `MoneyDetector` menerima
`model_factory` agar model asli bisa diganti tiruan di tes, seperti pola
`Transcriber` di `sayit/audio/stt.py`.

Urutan pasca-pemrosesan sesuai PRD 8.6:
1. Buang deteksi dengan skor di bawah ambang (PRD 8.9).
2. Buang kotak bersarang: kotak yang >= 85% luasnya berada di dalam kotak lain
   berkelas sama adalah bagian dari lembar yang sama (potret dan angka nominal
   kerap dianotasi terpisah pada dataset publik).
3. Bila dua kotak berkelas berbeda tumpang tindih (IoU > 0,5), hasil ditandai
   tidak yakin, karena satu lembar tidak mungkin punya dua nominal.
4. Hitung jumlah per nominal dan totalnya.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable, Sequence

import numpy as np

from sayit.config import project_path
from sayit.vision.quality_gate import terpotong_tepi
from sayit.response.templates import VALID_NOMINALS, Utterance, fixed, money_response
from sayit.vision import preprocess as pre

Box = tuple[float, float, float, float]      # x1, y1, x2, y2


@dataclass(frozen=True)
class Detection:
    nominal: int
    score: float
    box: Box


@dataclass
class MoneyResult:
    counts: dict[int, int] = field(default_factory=dict)
    total: int = 0
    detections: list[Detection] = field(default_factory=list)   # yang dipakai untuk berhitung
    confident: bool = True
    reason: str = ""                                            # alasan bila tidak yakin
    notes: dict[str, Any] = field(default_factory=dict)         # bukti terukur untuk laporan

    @property
    def sheets(self) -> int:
        return sum(self.counts.values())


# --------------------------------------------------------------------------- geometri

def area(box: Box) -> float:
    x1, y1, x2, y2 = box
    return max(0.0, x2 - x1) * max(0.0, y2 - y1)


def intersection_area(a: Box, b: Box) -> float:
    x1 = max(a[0], b[0])
    y1 = max(a[1], b[1])
    x2 = min(a[2], b[2])
    y2 = min(a[3], b[3])
    return max(0.0, x2 - x1) * max(0.0, y2 - y1)


def iou(a: Box, b: Box) -> float:
    irisan = intersection_area(a, b)
    gabungan = area(a) + area(b) - irisan
    return 0.0 if gabungan <= 0 else irisan / gabungan


def contained_ratio(inner: Box, outer: Box) -> float:
    """Berapa bagian luas `inner` yang berada di dalam `outer` (0..1)."""
    luas = area(inner)
    return 0.0 if luas <= 0 else intersection_area(inner, outer) / luas


# --------------------------------------------------------------------------- pasca-pemrosesan

def filter_by_score(dets: Sequence[Detection], score_min: float) -> list[Detection]:
    return [d for d in dets if d.score >= score_min]


def drop_nested(dets: Sequence[Detection], ratio: float) -> list[Detection]:
    """Buang kotak yang bersarang di dalam kotak lain berkelas sama.

    Kotak diperiksa dari yang terluas, sehingga yang dipertahankan adalah lembar
    utuhnya, bukan potongan di dalamnya. Untuk dua kotak yang nyaris identik,
    skor tertinggi yang menang.
    """
    urut = sorted(dets, key=lambda d: (-area(d.box), -d.score))
    disimpan: list[Detection] = []
    for d in urut:
        bersarang = any(k.nominal == d.nominal and contained_ratio(d.box, k.box) >= ratio
                        for k in disimpan)
        if not bersarang:
            disimpan.append(d)
    return disimpan


def merge_same_class(dets: Sequence[Detection], iou_min: float) -> list[Detection]:
    """Gabungkan kotak berkelas SAMA yang saling tumpang tindih; skor tertinggi menang.

    `drop_nested` hanya menangkap kotak yang benar-benar BERSARANG (>= 85% luasnya
    di dalam kotak lain). Terbukti 06-10 pada `100000_dipegang_03`: satu lembar
    terdeteksi tiga kali dengan luasan 632x616, 590x507, dan 806x704 - saling
    tumpang tindih tetapi tidak ada yang bersarang, sehingga lolos semua dan
    pengguna diberi tahu "dua lembar seratus ribu, totalnya dua ratus ribu".

    Bagi pengguna tunanetra, salah hitung lembar sama berbahayanya dengan salah
    kenal nominal: keduanya menghasilkan jumlah uang yang salah. Ambang 0 mematikan
    penggabungan ini.
    """
    if iou_min <= 0:
        return list(dets)
    urut = sorted(dets, key=lambda d: (-d.score, -area(d.box)))
    disimpan: list[Detection] = []
    for d in urut:
        kembar = any(k.nominal == d.nominal and iou(d.box, k.box) >= iou_min for k in disimpan)
        if not kembar:
            disimpan.append(d)
    return disimpan


def find_conflicts(dets: Sequence[Detection], iou_min: float) -> list[tuple[Detection, Detection]]:
    """Pasangan kotak berkelas berbeda yang tumpang tindih melebihi ambang."""
    konflik = []
    for i, a in enumerate(dets):
        for b in dets[i + 1:]:
            if a.nominal != b.nominal and iou(a.box, b.box) > iou_min:
                konflik.append((a, b))
    return konflik


def count_by_nominal(dets: Sequence[Detection]) -> dict[int, int]:
    counts: dict[int, int] = {}
    for d in dets:
        counts[d.nominal] = counts.get(d.nominal, 0) + 1
    return dict(sorted(counts.items(), key=lambda kv: -kv[0]))


def filter_by_relative_score(dets: Sequence[Detection], ratio: float) -> list[Detection]:
    """Buang deteksi yang skornya jauh di bawah deteksi TERKUAT di foto yang sama.

    Ambang mutlak (`score_min`) tidak menangkap pola kesalahan yang sebenarnya:
    deteksi palsu lolos dengan skor 0,59-0,68 SEMENTARA lembar aslinya 0,90-0,94
    di foto yang sama. Yang membedakan bukan nilainya, melainkan jaraknya.

    Diukur 22-10 pada 35 foto sendiri: semua kesalahan menggelembungkan jumlah
    (5.000 diucapkan 25.000), tidak pernah mengecilkan. Bagi pengguna tunanetra
    arah itu yang paling berbahaya - ia menyerahkan uang lebih banyak daripada
    yang dikiranya.

    ratio <= 0 mematikan aturan ini.
    """
    if ratio <= 0 or len(dets) < 2:
        return list(dets)
    terbaik = max(d.score for d in dets)
    return [d for d in dets if d.score >= terbaik * ratio]


def postprocess(dets: Sequence[Detection], cfg: dict) -> MoneyResult:
    """Terapkan seluruh aturan PRD 8.6 pada deteksi mentah."""
    m = cfg["vision"]["money"]
    mentah = list(dets)
    kuat = filter_by_score(mentah, float(m["score_min"]))
    tanpa_sarang = drop_nested(kuat, float(m["nested_area_ratio"]))
    # Ambang relatif WAJIB sesudah drop_nested, bukan sebelum. Lembar utuh bisa
    # berskor lebih rendah daripada potret di dalamnya (terkunci oleh tes
    # test_lembar_utuh_dipertahankan_walau_skornya_lebih_rendah); kalau diurutkan
    # terbalik, justru lembar aslinya yang terbuang dan potretnya yang bertahan.
    tanpa_sarang = filter_by_relative_score(tanpa_sarang, float(m.get("relative_score_min", 0.0)))
    bersih = merge_same_class(tanpa_sarang, float(m.get("same_class_iou", 0.0)))
    konflik = find_conflicts(bersih, float(m["conflict_iou"]))

    catatan = {
        "raw": len(mentah),
        "after_score": len(kuat),
        "after_nested": len(tanpa_sarang),
        "after_merge": len(bersih),
        "conflicts": len(konflik),
    }

    if konflik:
        pasangan = sorted({f"{a.nominal}/{b.nominal}" for a, b in konflik})
        return MoneyResult(detections=bersih, confident=False, notes=catatan,
                           reason=f"kotak berbeda kelas bertindihan: {', '.join(pasangan)}")

    if not kuat and mentah:
        skor_tertinggi = max(d.score for d in mentah)
        catatan["best_score"] = skor_tertinggi
        return MoneyResult(detections=[], confident=False, notes=catatan,
                           reason=f"semua deteksi di bawah ambang skor (tertinggi {skor_tertinggi:.2f})")

    counts = count_by_nominal(bersih)
    total = sum(n * j for n, j in counts.items())
    return MoneyResult(counts=counts, total=total, detections=bersih, notes=catatan)


def money_utterance(hasil: MoneyResult) -> Utterance:
    """Ujaran untuk pengguna. Tidak yakin -> minta foto ulang, bukan menyebut angka.

    Bila kotaknya menempel tepi bingkai, sarannya diganti yang lebih spesifik:
    "tidak yakin, foto ulang" tidak memberi tahu APA yang harus diubah, sedangkan
    pengguna tunanetra tidak bisa melihat bahwa uangnya terpotong. Terbukti pada
    uji lapangan 12-11: foto dua lembar menghasilkan tiga kotak seluruh bingkai,
    yaitu persis kasus yang penanda ini tangkap.
    """
    if not hasil.confident:
        return fixed("uang_terpotong" if hasil.notes.get("terpotong") else "tidak_yakin_uang")
    return money_response(hasil.counts)


# --------------------------------------------------------------------------- inferensi

def as_float_array(x) -> np.ndarray:
    """Terima tensor torch maupun array numpy dari model tiruan di tes."""
    if hasattr(x, "detach"):
        x = x.detach()
    if hasattr(x, "cpu"):
        x = x.cpu()
    return np.asarray(x, dtype=np.float64)


def parse_nominal(nama: str) -> int:
    """Nama kelas model berupa string nominal ("50000"). Nama lain ditolak tegas."""
    try:
        nominal = int(str(nama).strip())
    except ValueError as e:
        raise ValueError(f"Nama kelas model bukan nominal: {nama!r}") from e
    if nominal not in VALID_NOMINALS:
        raise ValueError(f"Nominal di luar 7 kelas yang disepakati: {nominal}")
    return nominal


def extract_detections(results, names: dict[int, str]) -> list[Detection]:
    """Ubah hasil ultralytics menjadi daftar Detection biasa."""
    if not results:
        return []
    boxes = getattr(results[0], "boxes", None)
    if boxes is None:
        return []
    # sengaja hanya menyentuh tiga atribut array, bukan API Boxes selengkapnya,
    # agar model tiruan di tes cukup menyediakan itu saja
    xyxy = as_float_array(boxes.xyxy).reshape(-1, 4)
    conf = as_float_array(boxes.conf).ravel()
    cls = as_float_array(boxes.cls).ravel()
    if xyxy.shape[0] == 0:
        return []
    keluar = []
    for kotak, skor, kelas in zip(xyxy, conf, cls):
        nominal = parse_nominal(names[int(kelas)])
        keluar.append(Detection(nominal=nominal, score=float(skor),
                                box=(float(kotak[0]), float(kotak[1]),
                                     float(kotak[2]), float(kotak[3]))))
    return keluar


class MoneyDetector:
    """Membungkus YOLOv8. Model dimuat sekali, lalu dipanaskan sekali.

    Panggilan inferensi pertama jauh lebih lambat daripada berikutnya
    (terukur 2,0 detik lawan 40 ms pada CPU i7-13650HX), karena itu `load()`
    sebaiknya dipanggil saat aplikasi mulai, bukan saat pengguna menunggu.
    """

    def __init__(self, cfg: dict, model_factory: Callable | None = None):
        self.cfg = cfg
        self.m = cfg["vision"]["money"]
        self._factory = model_factory
        self._model = None
        self.load_s: float | None = None

    @property
    def weights_path(self):
        return project_path(self.m["weights"])

    def load(self, warmup: bool = True):
        if self._model is not None:
            return self._model
        t = time.perf_counter()
        if self._factory is None:
            if not self.weights_path.exists():
                raise FileNotFoundError(
                    f"Bobot model tidak ditemukan: {self.weights_path}. "
                    "Lihat models/README.md untuk cara menyalinnya.")
            from ultralytics import YOLO
            self._factory = YOLO
        self._model = self._factory(str(self.weights_path))
        if warmup:
            kosong = np.zeros((int(self.m["imgsz"]), int(self.m["imgsz"]), 3), np.uint8)
            self._predict(kosong)
        self.load_s = time.perf_counter() - t
        return self._model

    def _predict(self, image: np.ndarray):
        # `augment` = test-time augmentation: ultralytics menjalankan inferensi pada
        # beberapa skala dan cerminan lalu menggabungkan hasilnya. Lebih lambat,
        # tetapi modul uang punya anggaran latensi besar yang belum terpakai
        # (1,4 detik dari batas NFR-01 8 detik), jadi di sinilah akurasi bisa dibeli
        # dengan waktu - hal yang tidak mungkin di modul dokumen dan kedaluwarsa.
        return self._model(image, device=self.m["device"], imgsz=int(self.m["imgsz"]),
                           max_det=int(self.m["max_det"]),
                           augment=bool(self.m.get("augment", False)), verbose=False)

    def raw_detections(self, image: np.ndarray,
                       preprocess: bool = True) -> tuple[list[Detection], dict[str, Any]]:
        """Deteksi apa adanya dari model, **sebelum** ambang skor dan pasca-pemrosesan.

        Dipakai untuk mendiagnosis salah tebak: tanpa ini, deteksi yang kalah
        tipis tidak terlihat sama sekali karena sudah terbuang ambang 0,5.
        """
        if image is None or image.size == 0:
            raise ValueError("Citra kosong.")
        self.load()
        catatan: dict[str, Any] = {}
        rantai = self.m.get("preprocess_chain")
        if preprocess and rantai:
            hasil_pra = pre.run_chain(image, self.cfg, rantai)
            image = hasil_pra.image
            catatan["preprocess_steps"] = hasil_pra.steps

        t = time.perf_counter()
        results = self._predict(image)
        catatan["inference_s"] = time.perf_counter() - t
        names = getattr(self._model, "names", None) or results[0].names
        return extract_detections(results, names), catatan

    def detect(self, image: np.ndarray, preprocess: bool = True) -> MoneyResult:
        """Deteksi nominal pada satu foto. Selalu mengembalikan MoneyResult."""
        mentah, catatan = self.raw_detections(image, preprocess=preprocess)
        hasil = postprocess(mentah, self.cfg)
        hasil.notes.update(catatan)
        # Dipakai deteksi MENTAH, bukan yang lolos ambang: saat jawabannya tidak
        # yakin justru kotak mentah itulah satu-satunya petunjuk letak yang ada.
        bingkai = self.cfg["vision"]["quality_gate"].get("framing") or {}
        if bingkai.get("enabled", True):
            hasil.notes["terpotong"] = terpotong_tepi(
                [d.box for d in mentah], image.shape, float(bingkai["edge_margin_ratio"]))
        return hasil
