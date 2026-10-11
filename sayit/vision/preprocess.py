"""Pra-pemrosesan citra (PRD 8.3) - inti materi Pengolahan Citra.

Setiap langkah adalah fungsi murni `(citra, params) -> citra` yang bisa dipakai
dan diuji sendiri. Urutan langkah per modul diatur lewat `vision.preprocess.chains`
di config, dan setiap langkah punya saklar `enabled` sendiri, sehingga uji ablasi
Fase 4 (dengan vs tanpa pra-pemrosesan) cukup mengubah YAML tanpa menyentuh kode.

Rangkaian bawaan:
    uang        : resize, clahe
    dokumen     : resize, perspective, deskew, clahe, denoise
    kedaluwarsa : upscale, clahe, denoise, threshold, morphology

Binarisasi sengaja tidak dipasang di rangkaian dokumen (PRD: "bila meningkatkan
akurasi"); tambahkan lewat config bila benchmark OCR nanti menunjukkan untung.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

import cv2
import numpy as np

INTERPOLATIONS = {
    "nearest": cv2.INTER_NEAREST,
    "linear": cv2.INTER_LINEAR,
    "cubic": cv2.INTER_CUBIC,
    "lanczos": cv2.INTER_LANCZOS4,
    "area": cv2.INTER_AREA,
}


@dataclass
class PreprocessResult:
    image: np.ndarray
    steps: list[str] = field(default_factory=list)       # langkah yang benar-benar mengubah citra
    skipped: list[str] = field(default_factory=list)     # dimatikan lewat config atau tidak berlaku
    notes: dict[str, Any] = field(default_factory=dict)  # bukti terukur untuk laporan ablasi


def _is_color(image: np.ndarray) -> bool:
    return image.ndim == 3 and image.shape[2] in (3, 4)


def _to_gray(image: np.ndarray) -> np.ndarray:
    if not _is_color(image):
        return image
    kode = cv2.COLOR_BGR2GRAY if image.shape[2] == 3 else cv2.COLOR_BGRA2GRAY
    return cv2.cvtColor(image, kode)


# --------------------------------------------------------------------------- langkah

def resize(image: np.ndarray, params: dict) -> np.ndarray:
    """Normalisasi ukuran: sisi terpanjang dibatasi, rasio dipertahankan.

    Hanya memperkecil. Memperbesar foto di tahap ini tidak menambah detail,
    hanya memperlambat langkah berikutnya.
    """
    max_side = params["max_side"]
    h, w = image.shape[:2]
    panjang = max(h, w)
    if max_side <= 0 or panjang <= max_side:
        return image
    skala = max_side / panjang
    ukuran = (max(1, round(w * skala)), max(1, round(h * skala)))
    return cv2.resize(image, ukuran, interpolation=cv2.INTER_AREA)


def clahe(image: np.ndarray, params: dict) -> np.ndarray:
    """CLAHE pada kanal L (LAB) agar warna tidak bergeser. Citra abu-abu diproses langsung."""
    tile = int(params["tile_grid"])
    alat = cv2.createCLAHE(clipLimit=float(params["clip_limit"]), tileGridSize=(tile, tile))
    if not _is_color(image):
        return alat.apply(image)
    punya_alpha = image.shape[2] == 4
    lab = cv2.cvtColor(image[:, :, :3], cv2.COLOR_BGR2LAB)
    lab[:, :, 0] = alat.apply(lab[:, :, 0])
    hasil = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
    return np.dstack([hasil, image[:, :, 3]]) if punya_alpha else hasil


def denoise(image: np.ndarray, params: dict) -> np.ndarray:
    """Reduksi derau. bilateral = default tim (cepat); nlm lebih bersih tapi jauh lebih lambat."""
    metode = params.get("method", "bilateral")
    if metode == "bilateral":
        p = params["bilateral"]
        return cv2.bilateralFilter(image, int(p["diameter"]),
                                   float(p["sigma_color"]), float(p["sigma_space"]))
    if metode == "nlm":
        p = params["nlm"]
        h = float(p["h"])
        tw, sw = int(p["template_window"]), int(p["search_window"])
        if _is_color(image):
            hasil = cv2.fastNlMeansDenoisingColored(image[:, :, :3], None, h, h, tw, sw)
            return np.dstack([hasil, image[:, :, 3]]) if image.shape[2] == 4 else hasil
        return cv2.fastNlMeansDenoising(image, None, h, tw, sw)
    raise ValueError(f"Metode denoise tidak dikenal: {metode!r} (pilih 'bilateral' atau 'nlm')")


def order_corners(pts: np.ndarray) -> np.ndarray:
    """Urutkan 4 titik menjadi kiri-atas, kanan-atas, kanan-bawah, kiri-bawah."""
    pts = pts.reshape(4, 2).astype(np.float32)
    jumlah = pts.sum(axis=1)
    selisih = np.diff(pts, axis=1).ravel()
    return np.array([pts[np.argmin(jumlah)], pts[np.argmin(selisih)],
                     pts[np.argmax(jumlah)], pts[np.argmax(selisih)]], dtype=np.float32)


def find_document_quad(image: np.ndarray, params: dict) -> np.ndarray | None:
    """Cari kontur segi empat terbesar yang mirip lembar kertas. None bila tidak ada.

    Kandidat yang hampir seluas gambar ditolak: pada citra ramai, Canny menghasilkan
    tepi di mana-mana dan kontur terbesarnya adalah bingkai gambar itu sendiri
    (terukur 0,977 pada citra acak). Meluruskannya pun tidak ada gunanya.
    """
    gray = _to_gray(image)
    k = int(params["blur_ksize"])
    if k > 1:
        gray = cv2.GaussianBlur(gray, (k | 1, k | 1), 0)
    tepi = cv2.Canny(gray, int(params["canny_low"]), int(params["canny_high"]))
    # tutup celah kecil agar tepi kertas menjadi kontur tertutup
    tepi = cv2.morphologyEx(tepi, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
    kontur, _ = cv2.findContours(tepi, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    luas_gambar = gray.shape[0] * gray.shape[1]
    luas_min = float(params["min_area_ratio"]) * luas_gambar
    luas_max = float(params["max_area_ratio"]) * luas_gambar
    eps_ratio = float(params["approx_epsilon_ratio"])
    for c in sorted(kontur, key=cv2.contourArea, reverse=True):
        luas = cv2.contourArea(c)
        if luas > luas_max:
            continue                                 # bingkai gambar, bukan kertas
        if luas < luas_min:
            break                                    # sisanya lebih kecil lagi
        approx = cv2.approxPolyDP(c, eps_ratio * cv2.arcLength(c, True), True)
        if len(approx) == 4 and cv2.isContourConvex(approx):
            return order_corners(approx)
    return None


def warp_to_quad(image: np.ndarray, quad: np.ndarray) -> np.ndarray:
    """Perspective transform: segi empat dipetakan menjadi persegi panjang tegak."""
    ka, kn, kb, kib = quad
    lebar = int(round(max(np.linalg.norm(kn - ka), np.linalg.norm(kb - kib))))
    tinggi = int(round(max(np.linalg.norm(kib - ka), np.linalg.norm(kb - kn))))
    lebar, tinggi = max(lebar, 1), max(tinggi, 1)
    tujuan = np.array([[0, 0], [lebar - 1, 0], [lebar - 1, tinggi - 1], [0, tinggi - 1]], np.float32)
    M = cv2.getPerspectiveTransform(quad, tujuan)
    return cv2.warpPerspective(image, M, (lebar, tinggi), flags=cv2.INTER_CUBIC)


def perspective(image: np.ndarray, params: dict) -> np.ndarray:
    """Koreksi perspektif. Bila kertas tidak ditemukan, citra dikembalikan apa adanya."""
    quad = find_document_quad(image, params)
    return image if quad is None else warp_to_quad(image, quad)


def skew_angle(image: np.ndarray, params: dict) -> float:
    """Sudut koreksi dalam derajat: citra perlu diputar sebesar nilai ini agar tegak.

    Nilai di luar +/- max_angle_deg dianggap salah ukur dan dikembalikan sebagai 0,
    karena minAreaRect mudah tertipu oleh latar yang ramai.
    """
    gray = _to_gray(image)
    biner = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)[1]
    titik = cv2.findNonZero(biner)
    if titik is None:
        return 0.0
    sudut = cv2.minAreaRect(titik)[-1]
    # Rentang sudut minAreaRect berbeda antar versi OpenCV; normalkan ke (-45, 45].
    if sudut > 45:
        sudut -= 90
    elif sudut < -45:
        sudut += 90
    batas = float(params["max_angle_deg"])
    return 0.0 if abs(sudut) > batas else float(sudut)


def rotate(image: np.ndarray, sudut: float) -> np.ndarray:
    """Putar terhadap titik tengah, ukuran dipertahankan, tepi diisi piksel pinggir."""
    h, w = image.shape[:2]
    M = cv2.getRotationMatrix2D((w / 2, h / 2), sudut, 1.0)
    return cv2.warpAffine(image, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)


def deskew(image: np.ndarray, params: dict) -> np.ndarray:
    sudut = skew_angle(image, params)
    if abs(sudut) < float(params["min_angle_deg"]):
        return image             # rotasi untuk sudut sangat kecil hanya menambah blur interpolasi
    return rotate(image, sudut)


def upscale(image: np.ndarray, params: dict) -> np.ndarray:
    """Pembesaran crop kedaluwarsa, agar cetakan kecil terbaca OCR."""
    f = float(params["factor"])
    if f == 1.0:
        return image
    interp = INTERPOLATIONS[params.get("interpolation", "cubic")]
    h, w = image.shape[:2]
    return cv2.resize(image, (max(1, round(w * f)), max(1, round(h * f))), interpolation=interp)


def threshold(image: np.ndarray, params: dict) -> np.ndarray:
    """Adaptive thresholding (Gaussian). Keluarannya selalu citra biner satu kanal."""
    blok = int(params["block_size"])
    if blok < 3:
        raise ValueError(f"block_size minimal 3, dapat {blok}")
    if blok % 2 == 0:
        raise ValueError(f"block_size harus ganjil, dapat {blok}")
    return cv2.adaptiveThreshold(_to_gray(image), 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                 cv2.THRESH_BINARY, blok, float(params["c"]))


def morphology(image: np.ndarray, params: dict) -> np.ndarray:
    """Closing atau dilation untuk menyambung titik cetakan dot-matrix.

    Citra kedaluwarsa berupa tulisan gelap di latar terang, sehingga operasi
    dikerjakan pada citra terbalik: closing di sana berarti menyambung goresan tinta.
    """
    op = params.get("op", "close")
    k = int(params["kernel"])
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (k, k))
    iterasi = int(params["iterations"])
    balik = cv2.bitwise_not(_to_gray(image))
    if op == "close":
        hasil = cv2.morphologyEx(balik, cv2.MORPH_CLOSE, kernel, iterations=iterasi)
    elif op == "dilate":
        hasil = cv2.dilate(balik, kernel, iterations=iterasi)
    else:
        raise ValueError(f"Operasi morfologi tidak dikenal: {op!r} (pilih 'close' atau 'dilate')")
    return cv2.bitwise_not(hasil)


STEPS: dict[str, Callable[[np.ndarray, dict], np.ndarray]] = {
    "resize": resize,
    "clahe": clahe,
    "denoise": denoise,
    "perspective": perspective,
    "deskew": deskew,
    "upscale": upscale,
    "threshold": threshold,
    "morphology": morphology,
}


# --------------------------------------------------------------------------- perangkai

def chain_steps(cfg: dict, chain: str) -> list[str]:
    rantai = cfg["vision"]["preprocess"]["chains"]
    if chain not in rantai:
        raise KeyError(f"Rangkaian tidak dikenal: {chain!r} (ada: {sorted(rantai)})")
    return list(rantai[chain])


def run_steps(image: np.ndarray, cfg: dict, steps: list[str]) -> PreprocessResult:
    """Jalankan daftar langkah berurutan, hormati saklar enabled masing-masing."""
    if image is None or image.size == 0:
        raise ValueError("Citra kosong.")
    pre = cfg["vision"]["preprocess"]
    hasil = PreprocessResult(image=image)
    if not pre.get("enabled", True):
        hasil.skipped = list(steps)
        hasil.notes["preprocess"] = "dimatikan seluruhnya"
        return hasil

    for nama in steps:
        if nama not in STEPS:
            raise KeyError(f"Langkah tidak dikenal: {nama!r} (ada: {sorted(STEPS)})")
        params = pre["steps"][nama]
        if not params.get("enabled", True):
            hasil.skipped.append(nama)
            continue
        sebelum = hasil.image
        if nama == "deskew":                        # sudutnya dicatat sebagai bukti ablasi
            hasil.notes["skew_angle"] = skew_angle(sebelum, params)
        elif nama == "perspective":
            hasil.notes["document_found"] = find_document_quad(sebelum, params) is not None
        hasil.image = STEPS[nama](sebelum, params)
        if hasil.image is sebelum:
            hasil.skipped.append(nama)              # langkah aktif tetapi tidak mengubah apa pun
        else:
            hasil.steps.append(nama)
    return hasil


def run_chain(image: np.ndarray, cfg: dict, chain: str) -> PreprocessResult:
    """Pra-pemrosesan satu modul: "uang", "dokumen", atau "kedaluwarsa"."""
    hasil = run_steps(image, cfg, chain_steps(cfg, chain))
    hasil.notes["chain"] = chain
    return hasil
