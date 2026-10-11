"""Modul dokumen (PRD 8.7): OCR lalu penyusunan teks untuk dibacakan.

Alur PRD 8.7:
1. Pra-pemrosesan dokumen (rangkaian `dokumen` di `vision.preprocess.chains`).
2. OCR seluruh gambar.
3. Buang kotak teks berskor rendah (PRD 8.9: < 0,40). Catatan: EasyOCR
   mengembalikan kotak setingkat BARIS, bukan kata, jadi yang terbuang adalah
   satu baris utuh. PRD menulisnya "per kata"; itu tidak sesuai kenyataan mesin.
4. Urutkan kotak teks atas ke bawah, kiri ke kanan, lalu kelompokkan menjadi
   baris dan paragraf.
5. Bagi teks menjadi potongan sekitar 40 kata.
6. Bacakan potongan pertama, lalu tawarkan "lanjut".

Pengelompokan baris dan paragraf adalah fungsi murni atas daftar `TextBox`, jadi
seluruh aturannya bisa diuji tanpa memuat model OCR. `DocumentReader` menerima
`reader_factory` agar OCR asli bisa diganti tiruan di tes, sama seperti pola
`Transcriber` dan `MoneyDetector`.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from statistics import median
from typing import Any, Callable, Sequence

import numpy as np

from sayit.config import project_path
from sayit.response.templates import (Utterance, document_chunk_response, fixed, split_chunks)
from sayit.vision import preprocess as pre

Quad = Sequence[Sequence[float]]         # 4 titik [[x, y], ...] seperti keluaran EasyOCR


@dataclass(frozen=True)
class TextBox:
    text: str
    score: float
    box: tuple[float, float, float, float]      # x1, y1, x2, y2

    @property
    def top(self) -> float:
        return self.box[1]

    @property
    def bottom(self) -> float:
        return self.box[3]

    @property
    def left(self) -> float:
        return self.box[0]

    @property
    def center_y(self) -> float:
        return (self.box[1] + self.box[3]) / 2

    @property
    def height(self) -> float:
        return self.box[3] - self.box[1]


@dataclass
class DocumentResult:
    text: str = ""
    chunks: list[str] = field(default_factory=list)
    boxes: list[TextBox] = field(default_factory=list)      # yang lolos ambang skor
    notes: dict[str, Any] = field(default_factory=dict)

    @property
    def found(self) -> bool:
        return bool(self.chunks)

    @property
    def total_chunks(self) -> int:
        return len(self.chunks)


# --------------------------------------------------------------------------- bentuk kotak

def quad_to_box(quad: Quad) -> tuple[float, float, float, float]:
    """Ubah empat titik EasyOCR menjadi kotak tegak (x1, y1, x2, y2)."""
    xs = [float(t[0]) for t in quad]
    ys = [float(t[1]) for t in quad]
    return (min(xs), min(ys), max(xs), max(ys))


def filter_by_score(boxes: Sequence[TextBox], score_min: float) -> list[TextBox]:
    return [b for b in boxes if b.score >= score_min]


# --------------------------------------------------------------------------- baris dan paragraf

def group_lines(boxes: Sequence[TextBox], tolerance_ratio: float) -> list[list[TextBox]]:
    """Kelompokkan kotak teks menjadi baris, lalu urutkan tiap baris dari kiri ke kanan.

    Toleransi dihitung relatif terhadap tinggi huruf, bukan piksel tetap, agar
    aturan yang sama berlaku untuk dokumen yang difoto dari dekat maupun jauh.

    EasyOCR biasanya sudah mengembalikan satu kotak per baris, sehingga langkah
    ini jarang menggabungkan apa pun. Aturannya tetap ada karena mesin OCR lain
    (dan EasyOCR dengan parameter berbeda) mengembalikan kotak per kata.
    """
    if not boxes:
        return []
    tinggi = median([b.height for b in boxes if b.height > 0] or [1.0])
    toleransi = tolerance_ratio * tinggi

    baris: list[list[TextBox]] = []
    for w in sorted(boxes, key=lambda w: (w.center_y, w.left)):
        if baris and abs(w.center_y - median([x.center_y for x in baris[-1]])) <= toleransi:
            baris[-1].append(w)
        else:
            baris.append([w])
    return [sorted(b, key=lambda w: w.left) for b in baris]


def group_paragraphs(lines: Sequence[Sequence[TextBox]], gap_ratio: float) -> list[list[list[TextBox]]]:
    """Baris yang jaraknya jauh dari baris sebelumnya memulai paragraf baru."""
    if not lines:
        return []
    tinggi = median([w.height for b in lines for w in b if w.height > 0] or [1.0])
    batas = gap_ratio * tinggi

    paragraf: list[list[list[TextBox]]] = [[list(lines[0])]]
    for sebelum, sekarang in zip(lines, lines[1:]):
        jarak = median([w.top for w in sekarang]) - median([w.bottom for w in sebelum])
        if jarak > batas:
            paragraf.append([list(sekarang)])
        else:
            paragraf[-1].append(list(sekarang))
    return paragraf


def compose_text(boxes: Sequence[TextBox], cfg: dict) -> str:
    """Susun kotak teks menjadi teks utuh: baris digabung, paragraf dipisah titik.

    Paragraf yang tidak diakhiri tanda baca diberi titik, supaya `split_chunks`
    di `response/templates.py` bisa memotong per kalimat dan suaranya tidak
    terdengar menyambung tanpa jeda.
    """
    d = cfg["vision"]["document"]
    baris = group_lines(boxes, float(d["line_tolerance_ratio"]))
    paragraf = group_paragraphs(baris, float(d["paragraph_gap_ratio"]))

    keluar = []
    for p in paragraf:
        isi = " ".join(" ".join(w.text for w in b) for b in p).strip()
        if not isi:
            continue
        if isi[-1] not in ".!?:,;":
            isi += "."
        keluar.append(isi)
    return " ".join(keluar)


def build_result(boxes: Sequence[TextBox], cfg: dict) -> DocumentResult:
    """Dari kotak hasil OCR menjadi teks dan potongan siap baca."""
    d = cfg["vision"]["document"]
    kuat = filter_by_score(boxes, float(d["text_score_min"]))
    teks = compose_text(kuat, cfg)
    potongan = split_chunks(teks, max_words=int(d["max_words_per_chunk"])) if teks else []
    catatan = {"raw_boxes": len(boxes), "kept_boxes": len(kuat), "chunks": len(potongan)}
    return DocumentResult(text=teks, chunks=potongan, boxes=kuat, notes=catatan)


def result_dari_teks(teks: str, cfg: dict, sumber: str = "teks") -> DocumentResult:
    """DocumentResult dari teks yang SUDAH ada, tanpa OCR.

    Dipakai PDF dan DOCX yang punya lapisan teks: teksnya sudah akurat, jadi
    yang dibutuhkan hanya pemotongan 40 kata yang sama dengan jalur OCR.
    """
    d = cfg["vision"]["document"]
    teks = (teks or "").strip()
    potongan = split_chunks(teks, max_words=int(d["max_words_per_chunk"])) if teks else []
    return DocumentResult(text=teks, chunks=potongan,
                          notes={"sumber": sumber, "chunks": len(potongan)})


# --------------------------------------------------------------------------- ujaran

def chunk_utterance(hasil: DocumentResult, index: int = 0) -> Utterance:
    """Ujaran untuk satu potongan. `index` dikelola pemanggil lewat intent LANJUT."""
    if not hasil.found:
        return fixed("tidak_ada_tulisan")
    if index >= hasil.total_chunks:
        return fixed("tidak_ada_lanjutan")
    return document_chunk_response(hasil.chunks[index], has_more=index + 1 < hasil.total_chunks)


# --------------------------------------------------------------------------- OCR

def extract_boxes(raw) -> list[TextBox]:
    """Ubah keluaran EasyOCR `readtext(detail=1)` menjadi daftar TextBox.

    Bentuknya (quad, teks, skor). Kotak kosong dibuang di sini agar tidak
    menghasilkan spasi ganda saat teks disusun.
    """
    kotak: list[TextBox] = []
    for butir in raw or []:
        quad, teks, skor = butir[0], butir[1], butir[2]
        teks = str(teks).strip()
        if not teks:
            continue
        kotak.append(TextBox(text=teks, score=float(skor), box=quad_to_box(quad)))
    return kotak


def extract_boxes_paddle(raw) -> list[TextBox]:
    """Ubah keluaran PaddleOCR 3.x `predict()` menjadi daftar TextBox.

    Bentuknya berbeda dari EasyOCR: satu kamus per halaman, dengan daftar
    `rec_texts`, `rec_scores`, dan `rec_polys` yang sejajar posisinya, bukan
    daftar tupel per kotak. `rec_boxes` dipakai bila ada karena sudah berupa
    kotak tegak; kalau tidak, poligonnya dipetakan lewat `quad_to_box`.
    """
    kotak: list[TextBox] = []
    for halaman in raw or []:
        teks_semua = halaman.get("rec_texts") or []
        skor_semua = halaman.get("rec_scores") or []
        poli_semua = halaman.get("rec_polys")
        if poli_semua is None or len(poli_semua) == 0:
            poli_semua = halaman.get("dt_polys") or []
        for i, teks in enumerate(teks_semua):
            teks = str(teks).strip()
            if not teks:
                continue
            skor = float(skor_semua[i]) if i < len(skor_semua) else 1.0
            quad = poli_semua[i] if i < len(poli_semua) else None
            if quad is None:
                continue
            kotak.append(TextBox(text=teks, score=skor, box=quad_to_box(quad)))
    return kotak


def _buat_paddle(d: dict):
    """Pabrik PaddleOCR dengan penangkal dua jebakan yang sudah ketemu (30-09).

    1. paddlepaddle 3.3.1 menabrak `NotImplementedError` di oneDNN saat memakai
       model PP-OCRv6 bawaan, jadi oneDNN dimatikan DAN versi model dipaksa v5.
    2. Saklar lingkungan harus dipasang sebelum paddle diimpor, jadi impornya
       sengaja ditaruh di dalam fungsi ini, bukan di puncak modul.
    """
    import os

    p = d.get("paddle") or {}
    if not p.get("enable_mkldnn", False):
        os.environ.setdefault("FLAGS_use_mkldnn", "0")
    from paddleocr import PaddleOCR
    extra = {}
    # Model deteksi bawaan PaddleOCR adalah versi `server` yang berat. Terukur 02-10
    # pada kecapasin: server 10,9 s (800 px) dan 18,5 s (1200 px), mobile 2,5 s pada
    # kedua ukuran, dan tanggalnya tetap terbaca. Jadi `mobile` yang dipakai.
    if p.get("text_detection_model_name"):
        extra["text_detection_model_name"] = p["text_detection_model_name"]
    return PaddleOCR(
        lang=p.get("lang", "id"),
        ocr_version=p.get("ocr_version", "PP-OCRv5"),
        enable_mkldnn=bool(p.get("enable_mkldnn", False)),
        use_doc_orientation_classify=False,
        use_doc_unwarping=False,
        use_textline_orientation=False,
        **extra,
    )


class DocumentReader:
    """Membungkus mesin OCR (EasyOCR atau PaddleOCR, lihat `document.engine`).

    Pembacaan pertama memuat bobot, jadi panggil `load()` lebih awal.
    """

    ENGINES = ("easyocr", "paddleocr")

    def __init__(self, cfg: dict, reader_factory: Callable | None = None):
        self.cfg = cfg
        self.d = cfg["vision"]["document"]
        self._factory = reader_factory
        self._reader = None
        self.load_s: float | None = None

    @property
    def model_dir(self):
        return project_path(self.d["model_dir"])

    @property
    def engine(self) -> str:
        mesin = self.d.get("engine", "easyocr")
        if mesin not in self.ENGINES:
            raise ValueError(f"Mesin OCR belum didukung: {mesin!r} "
                             f"(ada: {', '.join(self.ENGINES)})")
        return mesin

    def load(self):
        if self._reader is not None:
            return self._reader
        mesin = self.engine
        t = time.perf_counter()
        if self._factory is not None:
            # tes mengoper pabrik tiruan; bentuk panggilannya mengikuti EasyOCR
            self._reader = self._factory(
                list(self.d["languages"]),
                gpu=bool(self.d["gpu"]),
                model_storage_directory=str(self.model_dir),
                download_enabled=bool(self.d["download_enabled"]),
                verbose=False,
            )
        elif mesin == "paddleocr":
            self._reader = _buat_paddle(self.d)
        else:
            self.model_dir.mkdir(parents=True, exist_ok=True)
            import easyocr
            self._reader = easyocr.Reader(
                list(self.d["languages"]),
                gpu=bool(self.d["gpu"]),
                model_storage_directory=str(self.model_dir),
                download_enabled=bool(self.d["download_enabled"]),
                verbose=False,
            )
        self.load_s = time.perf_counter() - t
        return self._reader

    def ocr_boxes(self, image: np.ndarray) -> tuple[list[TextBox], float]:
        """OCR mentah tanpa pra-pemrosesan dan tanpa penyusunan teks.

        Dipakai modul kedaluwarsa agar mesin OCR yang sama bisa dipakai ulang;
        memuat EasyOCR dua kali memakan 4 detik dan memori dua kali lipat.
        """
        if image is None or image.size == 0:
            raise ValueError("Citra kosong.")
        self.load()
        t = time.perf_counter()
        if self._factory is None and self.engine == "paddleocr":
            kotak = extract_boxes_paddle(self._reader.predict(image))
        else:
            kotak = extract_boxes(self._reader.readtext(image, detail=1))
        return kotak, time.perf_counter() - t

    def read(self, image: np.ndarray, preprocess: bool = True) -> DocumentResult:
        """Baca seluruh tulisan pada satu foto. Selalu mengembalikan DocumentResult."""
        if image is None or image.size == 0:
            raise ValueError("Citra kosong.")
        catatan_pra: dict[str, Any] = {}
        rantai = self.d.get("preprocess_chain")
        if preprocess and rantai:
            hasil_pra = pre.run_chain(image, self.cfg, rantai)
            image = hasil_pra.image
            catatan_pra = {"preprocess_steps": hasil_pra.steps, **hasil_pra.notes}

        kotak, elapsed = self.ocr_boxes(image)
        hasil = build_result(kotak, self.cfg)
        hasil.notes.update(catatan_pra)
        hasil.notes["ocr_s"] = elapsed
        return hasil
