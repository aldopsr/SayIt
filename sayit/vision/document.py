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
from dataclasses import dataclass, field, replace
from statistics import median
from typing import Any, Callable, Sequence

import cv2
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
    def center_x(self) -> float:
        return (self.box[0] + self.box[2]) / 2

    @property
    def height(self) -> float:
        return self.box[3] - self.box[1]


@dataclass
class DocumentResult:
    text: str = ""
    chunks: list[str] = field(default_factory=list)
    boxes: list[TextBox] = field(default_factory=list)      # yang lolos ambang skor
    notes: dict[str, Any] = field(default_factory=dict)
    # Bacaan berhasil tetapi mutunya diragukan - lihat `bacaan_meragukan`.
    # Disimpan sebagai field, bukan dihitung ulang, karena penilaiannya butuh
    # config sedangkan `chunk_utterance` sengaja tidak menerima config.
    unclear: bool = False

    @property
    def found(self) -> bool:
        return bool(self.chunks)

    @property
    def total_chunks(self) -> int:
        return len(self.chunks)


# --------------------------------------------------------------------------- rotasi

# Hanya kelipatan 90 derajat: cv2.rotate menukar piksel tanpa interpolasi, jadi
# tidak ada detail cetakan yang hilang dan biayanya nyaris gratis.
_PUTARAN = {90: cv2.ROTATE_90_CLOCKWISE,
            180: cv2.ROTATE_180,
            270: cv2.ROTATE_90_COUNTERCLOCKWISE}


def rotate_image(image: np.ndarray, degrees: int) -> np.ndarray:
    """Putar citra sebesar kelipatan 90 derajat searah jarum jam."""
    derajat = int(degrees) % 360
    if derajat == 0:
        return image
    if derajat not in _PUTARAN:
        raise ValueError(f"Rotasi hanya kelipatan 90 derajat, bukan {degrees}.")
    return cv2.rotate(image, _PUTARAN[derajat])


# --------------------------------------------------------------------------- bentuk kotak

def quad_to_box(quad: Quad) -> tuple[float, float, float, float]:
    """Ubah empat titik EasyOCR menjadi kotak tegak (x1, y1, x2, y2)."""
    xs = [float(t[0]) for t in quad]
    ys = [float(t[1]) for t in quad]
    return (min(xs), min(ys), max(xs), max(ys))


def filter_by_score(boxes: Sequence[TextBox], score_min: float) -> list[TextBox]:
    return [b for b in boxes if b.score >= score_min]


# --------------------------------------------------------------------------- baris dan paragraf

def estimate_text_slope(boxes: Sequence[TextBox], gap_ratio: float,
                       max_slope: float) -> float:
    """Kemiringan baris teks (dy/dx) ditaksir dari kotak yang bersebelahan mendatar.

    Dibutuhkan karena `deskew` SALAH UKUR pada foto buku yang dipegang: ia
    memakai `minAreaRect` atas seluruh piksel, sehingga bentuk yang dominan
    adalah halaman dan latar meja, bukan baris teksnya - persis jebakan yang
    sudah ditulis di docstring-nya sendiri. Akibatnya terukur 31-10 pada
    `tulisanbukubaru (2)`: satu baris membentang dari y=99 di kiri sampai y=56
    di kanan, miring sekitar 6 derajat, dan pengelompokan baris menyisipkan
    baris-baris yang berbeda menjadi "cara yang dapat digunakan untuk mencegah
    3b. Ada beberapa berdarah".

    Kotak OCR sendiri sudah memuat jawabannya, jadi taksiran ini tidak perlu
    menyentuh citra sama sekali. Dipakai MEDIAN atas pasangan bersebelahan:
    pasangan yang menyeberang baris memberi kemiringan liar, dan median
    membuang keduanya tanpa perlu ambang.
    """
    if len(boxes) < 2:
        return 0.0
    tinggi = median([b.height for b in boxes if b.height > 0] or [1.0])
    batas_celah = gap_ratio * tinggi

    kemiringan = []
    for a in boxes:
        # tetangga terdekat di kanan yang masih masuk akal sebagai kata berikutnya
        kanan = [b for b in boxes
                 if b.left > a.left
                 and 0 <= b.left - a.box[2] <= batas_celah
                 and abs(b.center_y - a.center_y) <= tinggi]
        if not kanan:
            continue
        b = min(kanan, key=lambda w: w.left)
        dx = b.center_x - a.center_x
        if dx > 0:
            kemiringan.append((b.center_y - a.center_y) / dx)

    if not kemiringan:
        return 0.0
    s = float(median(kemiringan))
    # Taksiran liar dibuang: teks yang benar-benar miring lebih dari ini bukan
    # urusan pengelompokan baris, melainkan urusan percobaan ulang rotasi.
    return s if abs(s) <= max_slope else 0.0


def group_lines(boxes: Sequence[TextBox], tolerance_ratio: float,
                slope: float = 0.0) -> list[list[TextBox]]:
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

    # Pada teks miring, pusat vertikal mentah menyesatkan: ujung kanan sebuah
    # baris bisa lebih tinggi daripada awal baris berikutnya. `y` diluruskan
    # dulu terhadap kemiringan supaya perbandingannya kembali sah.
    def y_lurus(w: TextBox) -> float:
        return w.center_y - slope * w.center_x

    baris: list[list[TextBox]] = []
    for w in sorted(boxes, key=lambda w: (y_lurus(w), w.left)):
        if baris and abs(y_lurus(w) - median([y_lurus(x) for x in baris[-1]])) <= toleransi:
            baris[-1].append(w)
        else:
            baris.append([w])
    return [sorted(b, key=lambda w: w.left) for b in baris]


def group_lines_chain(boxes: Sequence[TextBox], tolerance_ratio: float,
                      gap_ratio: float) -> list[list[TextBox]]:
    """Bentuk baris dengan MENGIKUTI tetangga terdekat, bukan membandingkan y global.

    Dibuat setelah dua dugaan sebelumnya terbantah datanya (31-10):

    - "dua halaman melengkung berlawanan" SALAH. Membelah halaman di selokan
      terlebarnya hampir tidak mengubah taksiran kemiringan: -0,0276 untuk sisi
      kiri lawan -0,0282 untuk seluruh halaman.
    - "gugus menggumpal jadi satu" juga SALAH. Pengelompokan gugus sudah
      memisahkan halaman seberang dengan benar (121 kotak lawan 18).

    Yang tersisa sebagai penjelasan: halamannya MELENGKUNG, bukan miring rata.
    Di tengah halaman barisnya hampir datar, mendekati jilidan ia menukik tajam,
    sehingga satu angka kemiringan tidak akan pernah muat - median justru
    memilih bagian yang paling datar karena itu yang paling banyak.

    Karena itu di sini tidak ada taksiran kemiringan sama sekali. Tiap kotak
    menyambung ke baris yang ujung kanannya PALING DEKAT dan masih sejajar
    dengannya. Perbandingannya selalu terhadap kotak tepat sebelumnya, jadi
    baris yang melengkung diikuti apa adanya seberapa pun lengkungnya.
    """
    if not boxes:
        return []
    tinggi = median([b.height for b in boxes if b.height > 0] or [1.0])
    toleransi, batas_celah = tolerance_ratio * tinggi, gap_ratio * tinggi

    baris: list[list[TextBox]] = []
    for w in sorted(boxes, key=lambda w: (w.left, w.center_y)):
        terbaik, selisih_terbaik = None, None
        for b in baris:
            ujung = b[-1]
            celah = w.left - ujung.box[2]
            if celah > batas_celah:
                continue                    # terlalu jauh: baris lain, atau halaman seberang
            selisih = abs(w.center_y - ujung.center_y)
            if selisih <= toleransi and (selisih_terbaik is None or selisih < selisih_terbaik):
                terbaik, selisih_terbaik = b, selisih
        if terbaik is None:
            baris.append([w])
        else:
            terbaik.append(w)

    # Urutan bacaan antar-baris diambil dari kotak PERTAMA tiap baris: pada teks
    # melengkung, tepi kiri jauh lebih dapat dipercaya daripada nilai tengahnya.
    return sorted(baris, key=lambda b: (b[0].center_y, b[0].left))


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


# --------------------------------------------------------------------------- gugus spasial

def box_gap(a: TextBox, b: TextBox) -> tuple[float, float]:
    """Jarak KOSONG mendatar dan tegak antara dua kotak; 0 bila keduanya bertindih."""
    dx = max(0.0, max(a.left, b.left) - min(a.box[2], b.box[2]))
    dy = max(0.0, max(a.top, b.top) - min(a.bottom, b.bottom))
    return dx, dy


def group_clusters(boxes: Sequence[TextBox], x_gap_ratio: float,
                   y_gap_ratio: float) -> list[list[TextBox]]:
    """Kelompokkan kotak menjadi gugus teks yang berdekatan (single-linkage).

    Dibutuhkan karena `group_lines` membandingkan pusat vertikal di SELURUH lebar
    bingkai. Pada kertas A4 satu kolom itu benar, tetapi pada kemasan, papan tulis,
    atau papan nama dua blok teks yang kebetulan sejajar tingginya akan digabung
    menjadi satu baris dan dibacakan berselang-seling. Contoh nyata pada foto
    mentega: "kedekatan BlueBand sebagai enak banan karena rasa bertekstur lemout".

    Ambangnya relatif terhadap tinggi huruf, sama seperti aturan baris, supaya
    berlaku untuk foto dekat maupun jauh.
    """
    if not boxes:
        return []
    tinggi = median([b.height for b in boxes if b.height > 0] or [1.0])
    batas_x, batas_y = x_gap_ratio * tinggi, y_gap_ratio * tinggi

    # ponytail: O(n^2) atas kotak setingkat BARIS - satu halaman padat memberi
    # ratusan, bukan puluhan ribu. Pakai indeks spasial bila pernah jadi penghambat.
    sisa = list(boxes)
    gugus: list[list[TextBox]] = []
    while sisa:
        aktif, sisa = [sisa[0]], sisa[1:]
        i = 0
        while i < len(aktif):
            dekat, jauh = [], []
            for kandidat in sisa:
                dx, dy = box_gap(aktif[i], kandidat)
                (dekat if dx <= batas_x and dy <= batas_y else jauh).append(kandidat)
            aktif += dekat
            sisa = jauh
            i += 1
        gugus.append(aktif)
    return gugus


def order_clusters(clusters: Sequence[Sequence[TextBox]], band_ratio: float) -> list[list[TextBox]]:
    """Urutkan gugus seperti orang membaca: atas ke bawah, lalu kiri ke kanan.

    Membandingkan tepi atas mentah membuat dua gugus bersebelahan yang selisih
    beberapa piksel terbaca dalam urutan acak. Karena itu tepi atasnya dibulatkan
    ke pita setinggi `band_ratio` x tinggi huruf lebih dulu: gugus dalam pita yang
    sama dianggap sebaris dan diurutkan dari kiri.
    """
    if not clusters:
        return []
    tinggi = median([w.height for g in clusters for w in g if w.height > 0] or [1.0])
    pita = max(1.0, band_ratio * tinggi)

    def kunci(g: Sequence[TextBox]) -> tuple[int, float]:
        return (int(min(w.top for w in g) // pita), min(w.left for w in g))

    return [list(g) for g in sorted(clusters, key=kunci)]


# --------------------------------------------------------------------------- penyusunan teks

def _teks_satu_gugus(boxes: Sequence[TextBox], d: dict) -> list[str]:
    """Paragraf-paragraf dari satu gugus, memakai aturan baris yang sama."""
    if str(d.get("line_grouping", "pita")).lower() == "rantai":
        baris = group_lines_chain(boxes, float(d["line_tolerance_ratio"]),
                                  float(d["line_slope_gap_ratio"]))
    else:
        miring = 0.0
        if d.get("line_slope_correct"):
            miring = estimate_text_slope(boxes, float(d["line_slope_gap_ratio"]),
                                         float(d["line_slope_max"]))
        baris = group_lines(boxes, float(d["line_tolerance_ratio"]), miring)
    paragraf = group_paragraphs(baris, float(d["paragraph_gap_ratio"]))
    keluar = []
    for p in paragraf:
        isi = " ".join(" ".join(w.text for w in b) for b in p).strip()
        if isi:
            keluar.append(isi)
    return keluar


def compose_text(boxes: Sequence[TextBox], cfg: dict, mode: str = "dokumen") -> str:
    """Susun kotak teks menjadi teks utuh: baris digabung, paragraf dipisah titik.

    Paragraf yang tidak diakhiri tanda baca diberi titik, supaya `split_chunks`
    di `response/templates.py` bisa memotong per kalimat dan suaranya tidak
    terdengar menyambung tanpa jeda.

    Dua mode tata letak, karena satu aturan tidak muat untuk keduanya:

    - `dokumen`: teks mengalir satu kolom dari kiri atas. Berlaku untuk kertas,
      halaman buku, surat.
    - `tersebar`: teks berupa blok-blok terpisah yang letaknya tidak berurutan -
      kemasan, papan tulis, papan nama. Tiap gugus disusun sendiri lalu
      diurutkan atas ke bawah, kiri ke kanan.

    Mode `dokumen` sengaja TIDAK melewati pengelompokan gugus, supaya hasil yang
    sudah terukur pada 13 dokumen (CER 15,3%) tidak ikut berubah.
    """
    d = cfg["vision"]["document"]
    if mode == "tersebar":
        gugus = group_clusters(boxes, float(d["cluster_x_gap_ratio"]),
                               float(d["cluster_y_gap_ratio"]))
        gugus = order_clusters(gugus, float(d["cluster_band_ratio"]))
        keluar = [isi for g in gugus for isi in _teks_satu_gugus(g, d)]
    else:
        keluar = _teks_satu_gugus(boxes, d)

    # Titik di ujung tiap paragraf memberi jeda saat dibacakan. Pada mode
    # tersebar jeda itu justru yang memisahkan satu blok teks dari blok lain.
    return " ".join(isi if isi[-1] in ".!?:,;" else isi + "." for isi in keluar)


def build_result(boxes: Sequence[TextBox], cfg: dict, mode: str = "dokumen") -> DocumentResult:
    """Dari kotak hasil OCR menjadi teks dan potongan siap baca."""
    d = cfg["vision"]["document"]
    kuat = filter_by_score(boxes, float(d["text_score_min"]))
    teks = compose_text(kuat, cfg, mode)
    potongan = split_chunks(teks, max_words=int(d["max_words_per_chunk"])) if teks else []
    catatan = {"raw_boxes": len(boxes), "kept_boxes": len(kuat),
               "chunks": len(potongan), "layout_mode": mode}
    return DocumentResult(text=teks, chunks=potongan, boxes=kuat, notes=catatan)


def bacaan_meragukan(hasil: DocumentResult, cfg: dict) -> tuple[bool, dict]:
    """Apakah bacaan ini terlalu meragukan untuk dibacakan seolah-olah benar?

    Membacakan susunan kata acak dengan nada seyakin jawaban benar lebih
    berbahaya bagi pengguna tunanetra daripada berkata "tulisannya kurang
    jelas" - pengguna tidak punya cara memeriksanya sendiri. Modul uang dan
    tanggal sudah punya penjaga semacam ini; modul tulisan belum.

    Dua penanda, dan masing-masing cukup:

    1. **Skor rata-rata baris rendah.** Penanda langsung bahwa mesin OCR
       sendiri tidak yakin.
    2. **Sedikit baris yang lolos ambang skor dibanding yang terdeteksi.**
       Ini sengaja ditambahkan karena penanda pertama BUTA pada satu kasus
       nyata: foto papan nama yang hanya menghasilkan satu kata tetapi berskor
       0,769. Rasio tidak menghukum teks yang memang pendek - papan nama yang
       terbaca jelas akan meloloskan hampir semua kotaknya.

    Keduanya dapat dimatikan sendiri-sendiri (null di config) supaya bisa
    diablasi terpisah.
    """
    d = cfg["vision"]["document"]
    catatan: dict[str, Any] = {}
    if not hasil.found:
        return False, catatan          # "tidak ada tulisan" sudah punya jawabannya sendiri

    alasan = []
    ambang_skor = d.get("unclear_score_min")
    if ambang_skor is not None and hasil.boxes:
        rata = float(np.mean([b.score for b in hasil.boxes]))
        catatan["mean_score"] = rata
        if rata < float(ambang_skor):
            alasan.append("skor_rendah")

    ambang_rasio = d.get("unclear_kept_ratio_min")
    mentah = int(hasil.notes.get("raw_boxes") or 0)
    if ambang_rasio is not None and mentah:
        rasio = len(hasil.boxes) / mentah
        catatan["kept_ratio"] = rasio
        if rasio < float(ambang_rasio):
            alasan.append("banyak_terbuang")

    if alasan:
        catatan["unclear_reason"] = alasan
    return bool(alasan), catatan


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
    # Penjaga mutu diperiksa SEBELUM potongan pertama, bukan sebelum tiap
    # potongan: sekali dinyatakan kurang jelas, tidak ada yang dibacakan.
    if hasil.unclear:
        return fixed("tulisan_kurang_jelas")
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
    # Model PENGENALAN sengaja bisa dipilih juga. Biaya PaddleOCR pada dokumen padat
    # teks ada di tahap pengenalan PER BARIS (terukur 02-10: 41,8 detik/halaman, dan
    # memperkecil gambar hampir tidak menolong karena biayanya bukan per piksel).
    # Mengganti model deteksi saja - yang sudah dilakukan - mempercepat tahap yang
    # bukan penghambatnya.
    if p.get("text_recognition_model_name"):
        extra["text_recognition_model_name"] = p["text_recognition_model_name"]
    if p.get("text_recognition_batch_size"):
        extra["text_recognition_batch_size"] = int(p["text_recognition_batch_size"])
    # Backend inferensi. Bawaan PaddlePaddle; `onnxruntime` memakai varian ONNX dari
    # model yang sama (paddlex mengunduhnya sendiri sebagai `<nama>_onnx`, tidak perlu
    # paddle2onnx). `onnxruntime` sudah ikut terpasang, jadi ini bukan dependensi baru.
    if p.get("engine"):
        extra["engine"] = p["engine"]
    return PaddleOCR(
        lang=p.get("lang", "id"),
        ocr_version=p.get("ocr_version", "PP-OCRv5"),
        enable_mkldnn=bool(p.get("enable_mkldnn", False)),
        use_doc_orientation_classify=False,
        use_doc_unwarping=False,
        # Pengklasifikasi orientasi BARIS: menegakkan teks terbalik sebelum dikenali.
        # Dimatikan selama modul ini hanya membaca kertas A4; dinyalakan lewat config
        # sejak sasarannya meluas ke tulisan di dunia nyata.
        use_textline_orientation=bool(p.get("use_textline_orientation", False)),
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
            kotak = extract_boxes(self._reader.readtext(image, detail=1, **self._rotasi_kwargs()))
        return kotak, time.perf_counter() - t

    def _ocr_pita(self, image: np.ndarray) -> tuple[list[TextBox], float]:
        """OCR per PITA mendatar, lalu kotaknya digabung dalam koordinat gambar penuh.

        Memotong, bukan memperkecil. Sapuan `resize.max_side` 16-11 menunjukkan
        memperkecil gambar membuat deteksi MEMECAH baris (`r (4)` 76 kotak menjadi
        156) sehingga CER runtuh; memotong tidak menyentuh tinggi huruf sama sekali,
        sementara biaya deteksi tetap turun karena ia dibayar per piksel.

        Pita ke-k MEMILIKI baris yang pusatnya jatuh di `[k*H/n, (k+1)*H/n)`, tetapi
        di-OCR atas potongan yang dilebihkan `band_pad_ratio` di atas dan bawah. Jadi
        baris yang terbelah batas pita tetap utuh di pita yang memiliki pusatnya, dan
        tidak perlu dedupe - penyaring pusat itu sendiri yang mencegah kotak ganda.

        Penyusunan teks TIDAK berubah: `build_result` tetap dipanggil sekali atas
        gabungan seluruh kotak, jadi urutan bacaan, mode tata letak, dan penjaga mutu
        bekerja persis seperti sebelumnya. Yang berubah hanya cara kotak diperoleh.
        Terukur pada 13 dokumen beracuan (prototipe, jalur detect+recognize terpisah):
        2 pita memberi CER 14,57% lawan 14,89%, kata pertama 4,67 s lawan 13,58 s,
        total 8,59 s lawan 13,58 s - menang di ketiga sisi. 3 pita MERUGIKAN (17,36%).
        """
        n = int(self.d.get("bands") or 1)
        if n <= 1:
            return self.ocr_boxes(image)

        tinggi = image.shape[0]
        pad = int(float(self.d.get("band_pad_ratio") or 0.0) * tinggi)
        kotak: list[TextBox] = []
        total = 0.0
        for k in range(n):
            milik0, milik1 = k * tinggi // n, (k + 1) * tinggi // n
            y0, y1 = max(0, milik0 - pad), min(tinggi, milik1 + pad)
            potongan = image[y0:y1]
            if potongan.size == 0:
                continue
            sebagian, dt = self.ocr_boxes(potongan)
            total += dt
            kotak += [replace(b, box=(b.box[0], b.box[1] + y0, b.box[2], b.box[3] + y0))
                      for b in sebagian if milik0 <= b.center_y + y0 < milik1]
        return kotak, total

    def _rotasi_kwargs(self) -> dict:
        """Sudut tambahan yang dicoba EasyOCR untuk tiap baris teks.

        Pada foto dokumen hampir tidak berguna: halamannya sudah tegak dan deskew
        meluruskan sisanya. Pada foto dunia nyata (kemasan, papan nama) justru
        menentukan - teks terbalik terbaca huruf demi huruf menjadi sampah seperti
        'wejes BundoL uejues'. Dibuat dapat dimatikan supaya bisa diuji ablasi, dan
        karena tiap sudut tambahan membayar satu lintasan pengenalan lagi.
        """
        sudut = self.d.get("rotation_info") or []
        return {"rotation_info": list(sudut)} if sudut else {}

    def read(self, image: np.ndarray, preprocess: bool = True) -> DocumentResult:
        """Baca seluruh tulisan pada satu foto, memutar gambarnya bila perlu.

        Percobaan ulang rotasi memutar SELURUH gambar, bukan tiap baris teks.
        Keduanya sudah diukur pada 13 dokumen yang diputar 180 derajat (31-10):
        `rotation_info` EasyOCR per baris hanya memulihkan CER 96,2% -> 68,8%
        dengan biaya 5,2x, sedangkan memutar seluruh gambar memulihkannya ke
        15,3% - sama persis dengan baseline tegak. Sebabnya: yang gagal pada
        gambar terbalik adalah tahap DETEKSI (193 kotak lawan 887), dan deteksi
        butuh gambar tegak. Memutar baris yang tidak pernah terdeteksi tidak
        menolong apa pun.
        """
        if image is None or image.size == 0:
            raise ValueError("Citra kosong.")

        hasil = self._read_once(image, preprocess)
        sudut = [int(s) for s in (self.d.get("rotate_retry") or [])]
        if not sudut or not self._perlu_putar(hasil):
            return self._nilai_mutu(hasil)

        # Pemilih "kata terbanyak" diukur 31-10 pada 13 dokumen: menebak sudut
        # benar 13/13, setara batas atas oracle. Sudut keliru menghasilkan banyak
        # potongan pendek tak bermakna; sudut benar menghasilkan kalimat utuh.
        # Skor rata-rata hanya 12/13, jumlah kotak 12/13.
        kandidat = [(0, hasil)]
        for derajat in sudut:
            kandidat.append((derajat, self._read_once(rotate_image(image, derajat), preprocess)))
        derajat, hasil = max(kandidat, key=lambda k: len(k[1].text.split()))
        hasil.notes["rotated_deg"] = derajat
        hasil.notes["rotations_tried"] = sudut
        return self._nilai_mutu(hasil)

    def _nilai_mutu(self, hasil: DocumentResult) -> DocumentResult:
        """Pasang penanda mutu pada hasil AKHIR, sesudah rotasi diselesaikan.

        Urutannya penting: rotasi memperbaiki mutu bacaan, jadi menilai sebelum
        rotasi akan menyatakan foto miring "kurang jelas" padahal ia bisa pulih
        sepenuhnya - terukur 31-10, pemulihannya sampai 8x jumlah kata.
        """
        hasil.unclear, catatan = bacaan_meragukan(hasil, self.cfg)
        hasil.notes.update(catatan)
        return hasil

    def _perlu_putar(self, hasil: DocumentResult) -> bool:
        """Apakah bacaan ini cukup mencurigakan untuk membayar percobaan rotasi?

        Ambangnya 0,75, dikalibrasi 31-10 pada 14 foto buku dari HP pengguna -
        lima di antaranya terpotret miring tanpa disengaja, jadi datanya bukan
        rotasi buatan skrip. Pemisahannya BERSIH: foto tegak berskor serendah
        0,768, foto miring setinggi 0,715, dan 0,75 jatuh di celah itu. Hasil:
        5/5 foto miring terdeteksi, 0/9 foto tegak salah terpicu.

        Yang terpicu salah hanya muncul pada gambar beresolusi kecil bukan-HP
        (papantulis/plang, 310x142 sampai 613x377), yang skornya memang rendah
        karena OCR hampir tidak membaca apa pun di situ - rotasi pada foto
        semacam itu merugikan latensi tanpa memulihkan apa-apa.
        """
        ambang = self.d.get("rotate_trigger_score")
        if ambang is None:
            return False
        if not hasil.boxes:
            return True
        return float(np.mean([b.score for b in hasil.boxes])) < float(ambang)

    def _read_once(self, image: np.ndarray, preprocess: bool = True) -> DocumentResult:
        """Satu lintasan pra-pemrosesan + OCR, tanpa percobaan rotasi."""
        catatan_pra: dict[str, Any] = {}
        rantai = self.d.get("preprocess_chain")
        if preprocess and rantai:
            hasil_pra = pre.run_chain(image, self.cfg, rantai)
            image = hasil_pra.image
            catatan_pra = {"preprocess_steps": hasil_pra.steps, **hasil_pra.notes}

        kotak, elapsed = self._ocr_pita(image)
        hasil = build_result(kotak, self.cfg, self._mode_tata_letak(catatan_pra))
        hasil.notes.update(catatan_pra)
        hasil.notes["ocr_s"] = elapsed
        return hasil

    def _mode_tata_letak(self, catatan_pra: dict) -> str:
        """Pilih aturan urutan bacaan: `dokumen` atau `tersebar`.

        Petunjuknya sudah ada dan gratis: koreksi perspektif mencari lembar
        kertas dan mencatat `document_found`. Kertas ketemu berarti teksnya
        mengalir satu kolom; tidak ketemu berarti foto kemasan, papan tulis,
        atau papan nama - teksnya tersebar dan aturan dokumen merusaknya.

        Bila langkah perspektif dimatikan, petunjuknya tidak ada, dan modenya
        jatuh ke `dokumen` - yaitu perilaku yang sudah terukur sebelumnya.
        """
        pilihan = str(self.d.get("layout_mode", "auto")).lower()
        if pilihan in ("dokumen", "tersebar"):
            return pilihan
        return "tersebar" if catatan_pra.get("document_found") is False else "dokumen"
