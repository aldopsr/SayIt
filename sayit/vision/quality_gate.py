"""Pemeriksaan kelayakan foto sebelum pemrosesan apa pun (PRD 8.2).

Empat pemeriksaan: buram, terlalu gelap, terlalu terang, resolusi terlalu kecil.
Semua ambang dibaca dari config/settings.yaml (bagian vision.quality_gate) dan
masing-masing pemeriksaan bisa dimatikan sendiri-sendiri untuk uji ablasi.

Catatan kalibrasi: ambang blur sangat bergantung skala gambar, karena itu citra
dinormalisasi dulu ke sisi pendek tetap sebelum variance of Laplacian dihitung.
Tanpa itu, foto HP 4000 piksel dan foto dataset 640 piksel menghasilkan nilai
yang tidak sebanding.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import cv2
import numpy as np

from sayit.response.templates import Utterance, fixed

# Urutan pelaporan. Masalah yang lebih mendasar disebut lebih dulu: foto gelap
# gulita juga menghasilkan variance Laplacian rendah, tetapi pesan yang berguna
# bagi pengguna adalah "terlalu gelap", bukan "buram".
ISSUE_ORDER = ("kecil", "gelap", "terang", "buram")

CLIP_KEYS = {
    "kecil": "foto_kecil",
    "gelap": "foto_gelap",
    "terang": "foto_terang",
    "buram": "foto_buram",
}


@dataclass(frozen=True)
class QualityIssue:
    kind: str           # salah satu dari ISSUE_ORDER
    value: float        # nilai terukur
    threshold: float    # ambang yang dilanggar

    @property
    def clip_key(self) -> str:
        return CLIP_KEYS[self.kind]


@dataclass(frozen=True)
class QualityReport:
    ok: bool
    issues: list[QualityIssue] = field(default_factory=list)
    metrics: dict[str, float] = field(default_factory=dict)

    @property
    def main_issue(self) -> QualityIssue | None:
        """Masalah yang dibacakan ke pengguna: satu saja, yang paling mendasar."""
        return self.issues[0] if self.issues else None

    @property
    def kinds(self) -> list[str]:
        return [i.kind for i in self.issues]


def to_gray(image: np.ndarray) -> np.ndarray:
    """Terima citra grayscale, BGR, atau BGRA; kembalikan grayscale uint8."""
    if image is None or image.size == 0:
        raise ValueError("Citra kosong.")
    if image.ndim == 2:
        gray = image
    elif image.ndim == 3 and image.shape[2] == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    elif image.ndim == 3 and image.shape[2] == 4:
        gray = cv2.cvtColor(image, cv2.COLOR_BGRA2GRAY)
    else:
        raise ValueError(f"Bentuk citra tidak didukung: {image.shape}")
    return gray if gray.dtype == np.uint8 else np.clip(gray, 0, 255).astype(np.uint8)


def resize_short_side(gray: np.ndarray, target: int) -> np.ndarray:
    """Skalakan agar sisi terpendek sama dengan target, rasio dipertahankan.

    Hanya memperkecil. Memperbesar foto kecil tidak menambah detail dan justru
    membuat nilai blur terlihat lebih baik daripada kenyataannya.
    """
    h, w = gray.shape[:2]
    short = min(h, w)
    if target <= 0 or short <= target:
        return gray
    scale = target / short
    size = (max(1, round(w * scale)), max(1, round(h * scale)))
    return cv2.resize(gray, size, interpolation=cv2.INTER_AREA)


def blur_variance(gray: np.ndarray, target_short_side: int) -> float:
    """Variance of Laplacian setelah normalisasi ukuran. Makin kecil makin buram."""
    norm = resize_short_side(gray, target_short_side)
    return float(cv2.Laplacian(norm, cv2.CV_64F).var())


def compute_metrics(image: np.ndarray, cfg: dict) -> dict[str, float]:
    """Semua besaran terukur dari sebuah foto. Dihitung apa pun status toggle,
    supaya bisa dicatat saat uji ablasi meskipun pemeriksaannya dimatikan."""
    gate = cfg["vision"]["quality_gate"]
    gray = to_gray(image)
    h, w = gray.shape[:2]
    sat_level = gate["bright"]["saturated_level"]
    return {
        "short_side": float(min(h, w)),
        "mean": float(gray.mean()),
        "blur_variance": blur_variance(gray, gate["blur"]["resize_short_side"]),
        "saturated_ratio": float((gray >= sat_level).mean()),
    }


def check_quality(image: np.ndarray, cfg: dict) -> QualityReport:
    """Periksa kelayakan foto. Selalu mengembalikan laporan, tidak pernah melempar
    kecuali citranya memang tidak valid."""
    gate = cfg["vision"]["quality_gate"]
    metrics = compute_metrics(image, cfg)
    if not gate.get("enabled", True):
        return QualityReport(ok=True, metrics=metrics)

    found: dict[str, QualityIssue] = {}

    res = gate["resolution"]
    if res.get("enabled", True) and metrics["short_side"] < res["min_short_side"]:
        found["kecil"] = QualityIssue("kecil", metrics["short_side"], float(res["min_short_side"]))

    dark = gate["dark"]
    if dark.get("enabled", True) and metrics["mean"] < dark["max_mean"]:
        found["gelap"] = QualityIssue("gelap", metrics["mean"], float(dark["max_mean"]))

    bright = gate["bright"]
    if bright.get("enabled", True):
        if metrics["mean"] > bright["min_mean"]:
            found["terang"] = QualityIssue("terang", metrics["mean"], float(bright["min_mean"]))
        elif metrics["saturated_ratio"] > bright["max_saturated_ratio"]:
            # Silau lokal: rata-rata masih wajar, tetapi sebagian besar frame jenuh.
            found["terang"] = QualityIssue("terang", metrics["saturated_ratio"],
                                           float(bright["max_saturated_ratio"]))

    blur = gate["blur"]
    if blur.get("enabled", True) and metrics["blur_variance"] < blur["min_variance"]:
        found["buram"] = QualityIssue("buram", metrics["blur_variance"], float(blur["min_variance"]))

    issues = [found[k] for k in ISSUE_ORDER if k in found]
    return QualityReport(ok=not issues, issues=issues, metrics=metrics)


def quality_response(report: QualityReport) -> Utterance:
    """Ujaran saran perbaikan untuk foto yang ditolak."""
    issue = report.main_issue
    if issue is None:
        raise ValueError("Foto lolos quality gate, tidak ada saran yang perlu dibacakan.")
    return fixed(issue.clip_key)

# --------------------------------------------------------------------------- pembingkaian

def terpotong_tepi(boxes, shape, margin_ratio: float) -> bool:
    """True bila ada kotak yang menempel tepi bingkai, artinya objeknya terpotong.

    Fungsi murni atas koordinat, jadi bisa dipakai modul mana pun yang punya kotak.

    SENGAJA tidak menyebut arah (kiri/kanan/atas/bawah). Kamera bawaan aplikasi
    adalah kamera DEPAN (`facingMode: 'user'`) dan pratinjaunya dicerminkan lewat
    CSS, sedangkan gambar yang dikirim ke server tidak dicerminkan - jadi "kanan"
    pada gambar bukan "kanan" bagi pengguna. Memberi arah yang salah kepada
    pengguna tunanetra lebih buruk daripada tidak memberi arah sama sekali, sebab
    ia tidak punya cara memeriksanya. "Mundurkan kamera" benar untuk semua sisi.
    Untuk arah yang sah, klien harus mengirim `facingMode` lebih dulu.
    """
    h, w = shape[:2]
    if not boxes or h <= 0 or w <= 0:
        return False
    mx, my = margin_ratio * w, margin_ratio * h
    return any(x1 <= mx or y1 <= my or x2 >= w - mx or y2 >= h - my
               for x1, y1, x2, y2 in boxes)
