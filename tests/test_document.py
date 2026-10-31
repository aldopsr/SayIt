"""Tes modul dokumen (PRD 8.7).

Semua tes memakai kotak kata buatan dan OCR tiruan, jadi lulus tanpa bobot
EasyOCR dan tanpa internet.
"""
import copy
from pathlib import Path

import numpy as np
import pytest

from sayit.config import load_config, project_path
from sayit.response import templates as T
from sayit.vision import document as DOC


@pytest.fixture
def cfg():
    return copy.deepcopy(load_config())


def baris(teks, y, tinggi=20, x0=50, lebar_huruf=12, jarak=10, skor=0.9):
    """Kata-kata satu baris, dengan kotak yang lebarnya mengikuti jumlah huruf."""
    kata, x = [], x0
    for t in teks.split():
        w = lebar_huruf * len(t)
        kata.append(DOC.TextBox(t, skor, (x, y, x + w, y + tinggi)))
        x += w + jarak
    return kata


@pytest.fixture
def surat():
    """Dokumen dua paragraf: tiga baris rapat, lalu jarak besar, lalu dua baris."""
    kata = []
    for i, t in enumerate(["Surat Keterangan Domisili",
                           "Yang bertanda tangan di bawah",
                           "ini menerangkan bahwa"]):
        kata += baris(t, 100 + i * 28)
    for i, t in enumerate(["Nama Budi Santoso",
                           "Alamat Jalan Melati nomor tiga"]):
        kata += baris(t, 250 + i * 28)
    return kata


# --------------------------------------------------------------------------- bentuk kotak

def test_empat_titik_menjadi_kotak_tegak():
    quad = [[10, 20], [110, 22], [112, 50], [12, 48]]      # sedikit miring
    assert DOC.quad_to_box(quad) == (10.0, 20.0, 112.0, 50.0)


def test_sifat_kata():
    w = DOC.TextBox("halo", 0.9, (10, 20, 110, 50))
    assert w.left == 10 and w.top == 20 and w.bottom == 50
    assert w.height == 30 and w.center_y == 35


# --------------------------------------------------------------------------- ambang skor

def test_kata_berskor_rendah_dibuang(cfg):
    kata = [DOC.TextBox("jelas", 0.9, (0, 0, 50, 20)),
            DOC.TextBox("buram", 0.2, (60, 0, 110, 20))]
    hasil = DOC.build_result(kata, cfg)
    assert hasil.text == "jelas."
    assert hasil.notes == {"raw_boxes": 2, "kept_boxes": 1, "chunks": 1}


def test_tepat_di_ambang_diterima(cfg):
    kata = [DOC.TextBox("pas", 0.4, (0, 0, 50, 20))]
    assert DOC.build_result(kata, cfg).text == "pas."


def test_ambang_diambil_dari_config(cfg):
    kata = [DOC.TextBox("ragu", 0.5, (0, 0, 50, 20))]
    assert DOC.build_result(kata, cfg).found is True
    cfg["vision"]["document"]["text_score_min"] = 0.6
    assert DOC.build_result(kata, cfg).found is False


# --------------------------------------------------------------------------- baris

def test_kata_dikelompokkan_menjadi_baris(cfg, surat):
    baris_baris = DOC.group_lines(surat, cfg["vision"]["document"]["line_tolerance_ratio"])
    assert len(baris_baris) == 5
    assert " ".join(w.text for w in baris_baris[0]) == "Surat Keterangan Domisili"


def test_urutan_baca_atas_ke_bawah_kiri_ke_kanan(cfg, surat):
    """PRD 8.7 langkah 4. Urutan masukan sengaja diacak."""
    acak = list(reversed(surat))
    baris_baris = DOC.group_lines(acak, cfg["vision"]["document"]["line_tolerance_ratio"])
    teks = [" ".join(w.text for w in b) for b in baris_baris]
    assert teks == ["Surat Keterangan Domisili",
                    "Yang bertanda tangan di bawah",
                    "ini menerangkan bahwa",
                    "Nama Budi Santoso",
                    "Alamat Jalan Melati nomor tiga"]


def test_kata_sedikit_bergeser_tetap_sebaris(cfg):
    """Baris hasil OCR tidak pernah rata sempurna; pergeseran kecil harus dimaafkan."""
    kata = [DOC.TextBox("satu", 0.9, (0, 100, 50, 120)),
            DOC.TextBox("dua", 0.9, (60, 104, 110, 124)),        # bergeser 4 px
            DOC.TextBox("tiga", 0.9, (120, 97, 170, 117))]       # bergeser -3 px
    baris_baris = DOC.group_lines(kata, cfg["vision"]["document"]["line_tolerance_ratio"])
    assert len(baris_baris) == 1
    assert [w.text for w in baris_baris[0]] == ["satu", "dua", "tiga"]


def test_toleransi_baris_relatif_terhadap_tinggi_huruf(cfg):
    """Aturan yang sama harus berlaku untuk foto dekat maupun jauh."""
    tol = cfg["vision"]["document"]["line_tolerance_ratio"]
    kecil = [DOC.TextBox("a", 0.9, (0, 100, 10, 110)),
             DOC.TextBox("b", 0.9, (20, 104, 30, 114))]          # geser 4 px, tinggi 10
    besar = [DOC.TextBox("a", 0.9, (0, 200, 100, 300)),
             DOC.TextBox("b", 0.9, (200, 240, 300, 340))]        # geser 40 px, tinggi 100
    assert len(DOC.group_lines(kecil, tol)) == 1
    assert len(DOC.group_lines(besar, tol)) == 1


def test_baris_kosong_aman(cfg):
    assert DOC.group_lines([], 0.6) == []
    assert DOC.group_paragraphs([], 1.6) == []


# --------------------------------------------------------------------------- paragraf

def test_jarak_besar_memulai_paragraf_baru(cfg, surat):
    d = cfg["vision"]["document"]
    baris_baris = DOC.group_lines(surat, d["line_tolerance_ratio"])
    paragraf = DOC.group_paragraphs(baris_baris, d["paragraph_gap_ratio"])
    assert len(paragraf) == 2
    assert len(paragraf[0]) == 3 and len(paragraf[1]) == 2


def test_ambang_paragraf_diambil_dari_config(cfg, surat):
    d = cfg["vision"]["document"]
    baris_baris = DOC.group_lines(surat, d["line_tolerance_ratio"])
    assert len(DOC.group_paragraphs(baris_baris, 1.6)) == 2
    assert len(DOC.group_paragraphs(baris_baris, 20.0)) == 1     # toleransi longgar: satu paragraf
    assert len(DOC.group_paragraphs(baris_baris, 0.1)) == 5      # ketat: tiap baris jadi paragraf


def test_paragraf_diberi_titik_agar_ada_jeda(cfg, surat):
    """Tanpa titik, `split_chunks` tidak bisa memotong dan suaranya menyambung tanpa jeda."""
    teks = DOC.compose_text(surat, cfg)
    assert teks == ("Surat Keterangan Domisili Yang bertanda tangan di bawah ini menerangkan bahwa. "
                    "Nama Budi Santoso Alamat Jalan Melati nomor tiga.")


def test_tanda_baca_yang_sudah_ada_tidak_digandakan(cfg):
    kata = baris("Selesai sudah.", 100)
    assert DOC.compose_text(kata, cfg) == "Selesai sudah."


# --------------------------------------------------------------------------- potongan bacaan

def test_teks_panjang_dipotong_sekitar_empat_puluh_kata(cfg):
    kata = []
    for i in range(12):
        kata += baris("satu dua tiga empat lima enam tujuh delapan sembilan sepuluh", 100 + i * 28)
    hasil = DOC.build_result(kata, cfg)
    assert hasil.total_chunks > 1
    for potongan in hasil.chunks:
        assert len(potongan.split()) <= cfg["vision"]["document"]["max_words_per_chunk"]


def test_jumlah_kata_per_potongan_diambil_dari_config(cfg, surat):
    assert DOC.build_result(surat, cfg).total_chunks == 1
    cfg["vision"]["document"]["max_words_per_chunk"] = 5
    assert DOC.build_result(surat, cfg).total_chunks > 1


def test_tanpa_tulisan(cfg):
    hasil = DOC.build_result([], cfg)
    assert hasil.found is False
    assert hasil.text == "" and hasil.chunks == []


# --------------------------------------------------------------------------- ujaran

def test_potongan_pertama_menawarkan_lanjut(cfg, surat):
    cfg["vision"]["document"]["max_words_per_chunk"] = 5
    hasil = DOC.build_result(surat, cfg)
    utt = DOC.chunk_utterance(hasil, 0)
    assert T.Clip("katakan_lanjut") in utt
    assert "Katakan lanjut" in T.to_plain_text(utt)


def test_potongan_terakhir_tidak_menawarkan_lanjut(cfg, surat):
    hasil = DOC.build_result(surat, cfg)
    utt = DOC.chunk_utterance(hasil, hasil.total_chunks - 1)
    assert T.Clip("katakan_lanjut") not in utt


def test_minta_lanjut_setelah_habis(cfg, surat):
    hasil = DOC.build_result(surat, cfg)
    assert DOC.chunk_utterance(hasil, hasil.total_chunks) == [T.Clip("tidak_ada_lanjutan")]


def test_ujaran_saat_tidak_ada_tulisan(cfg):
    assert DOC.chunk_utterance(DOC.build_result([], cfg)) == [T.Clip("tidak_ada_tulisan")]


def test_isi_dokumen_dibacakan_sebagai_teks_dinamis(cfg, surat):
    """Isi dokumen memakai bagian Text (gTTS langsung), bukan klip tersimpan."""
    utt = DOC.chunk_utterance(DOC.build_result(surat, cfg), 0)
    assert any(isinstance(p, T.Text) for p in utt)


# --------------------------------------------------------------------------- ekstraksi hasil OCR

def test_ekstraksi_dari_keluaran_easyocr():
    mentah = [([[10, 20], [110, 22], [112, 50], [12, 48]], "Surat", 0.95),
              ([[120, 20], [220, 20], [220, 50], [120, 50]], "Keterangan", 0.88)]
    kata = DOC.extract_boxes(mentah)
    assert [w.text for w in kata] == ["Surat", "Keterangan"]
    assert kata[0].score == pytest.approx(0.95)
    assert kata[0].box == (10.0, 20.0, 112.0, 50.0)


def test_kata_kosong_dibuang_saat_ekstraksi():
    mentah = [([[0, 0], [10, 0], [10, 10], [0, 10]], "   ", 0.9),
              ([[0, 0], [10, 0], [10, 10], [0, 10]], "isi", 0.9)]
    assert [w.text for w in DOC.extract_boxes(mentah)] == ["isi"]


def test_ekstraksi_dari_hasil_kosong():
    assert DOC.extract_boxes([]) == []
    assert DOC.extract_boxes(None) == []


# --------------------------------------------------------------------------- pembaca dengan OCR tiruan

class ReaderPalsu:
    def __init__(self, *args, jawaban=(), **kwargs):
        self.args = args
        self.kwargs = kwargs
        self.panggilan = []
        self._jawaban = list(jawaban)

    def readtext(self, image, **kwargs):
        self.panggilan.append({"shape": image.shape, **kwargs})
        return self._jawaban


def pabrik(jawaban=()):
    def buat(*args, **kwargs):
        buat.reader = ReaderPalsu(*args, jawaban=jawaban, **kwargs)
        return buat.reader
    return buat


JAWABAN = [([[50, 100], [200, 100], [200, 120], [50, 120]], "Surat Keterangan", 0.95),
           ([[50, 128], [260, 128], [260, 148], [50, 148]], "Nama Budi Santoso", 0.91)]


def test_pembaca_meneruskan_parameter_config(cfg):
    f = pabrik(JAWABAN)
    r = DOC.DocumentReader(cfg, reader_factory=f)
    r.load()
    d = cfg["vision"]["document"]
    assert f.reader.args[0] == d["languages"]
    assert f.reader.kwargs["gpu"] is False
    assert f.reader.kwargs["download_enabled"] is True
    assert Path(f.reader.kwargs["model_storage_directory"]) == project_path(d["model_dir"])


def test_pembaca_tidak_memuat_ulang(cfg):
    f = pabrik(JAWABAN)
    r = DOC.DocumentReader(cfg, reader_factory=f)
    pertama = r.load()
    assert r.load() is pertama
    assert r.load_s is not None


def test_pembaca_menghasilkan_teks(cfg):
    r = DOC.DocumentReader(cfg, reader_factory=pabrik(JAWABAN))
    hasil = r.read(np.zeros((600, 800, 3), np.uint8))
    assert hasil.text == "Surat Keterangan Nama Budi Santoso."
    assert hasil.notes["raw_boxes"] == 2
    assert hasil.notes["ocr_s"] >= 0


def test_pembaca_menjalankan_pra_pemrosesan(cfg):
    f = pabrik(JAWABAN)
    r = DOC.DocumentReader(cfg, reader_factory=f)
    hasil = r.read(np.zeros((1800, 2400, 3), np.uint8))
    assert "resize" in hasil.notes["preprocess_steps"]
    assert f.reader.panggilan[-1]["shape"][1] <= cfg["vision"]["preprocess"]["steps"]["resize"]["max_side"]


def test_pra_pemrosesan_bisa_dilewati_untuk_ablasi(cfg):
    f = pabrik(JAWABAN)
    r = DOC.DocumentReader(cfg, reader_factory=f)
    r.read(np.zeros((1800, 2400, 3), np.uint8), preprocess=False)
    assert f.reader.panggilan[-1]["shape"] == (1800, 2400, 3)


def test_citra_kosong_ditolak(cfg):
    r = DOC.DocumentReader(cfg, reader_factory=pabrik())
    with pytest.raises(ValueError):
        r.read(np.zeros((0, 0, 3), np.uint8))


def test_mesin_ocr_tak_dikenal_ditolak_tegas(cfg):
    """Salah tulis di config harus gagal keras, bukan diam-diam memakai bawaan."""
    cfg["vision"]["document"]["engine"] = "tesseract"
    r = DOC.DocumentReader(cfg, reader_factory=pabrik())
    with pytest.raises(ValueError, match="belum didukung"):
        r.load()


@pytest.mark.parametrize("mesin", ["easyocr", "paddleocr"])
def test_kedua_mesin_diterima(mesin, cfg):
    """Sejak 30-09 PaddleOCR ikut didukung (ablasi PRD nomor 2)."""
    cfg["vision"]["document"]["engine"] = mesin
    r = DOC.DocumentReader(cfg, reader_factory=pabrik())
    assert r.engine == mesin
    r.load()                                    # pabrik tiruan, tidak memuat bobot asli


def test_keluaran_paddle_diubah_menjadi_textbox():
    """Bentuk keluaran PaddleOCR 3.x: satu kamus per halaman dengan daftar sejajar."""
    mentah = [{
        "rec_texts": ["110426", "", "EXP"],
        "rec_scores": [0.99, 0.5, 0.83],
        "rec_polys": [[[10, 20], [60, 20], [60, 40], [10, 40]],
                      [[0, 0], [5, 0], [5, 5], [0, 5]],
                      [[70, 20], [90, 20], [90, 40], [70, 40]]],
    }]
    kotak = DOC.extract_boxes_paddle(mentah)
    assert [k.text for k in kotak] == ["110426", "EXP"]      # teks kosong dibuang
    assert kotak[0].score == pytest.approx(0.99)
    assert kotak[0].box == (10, 20, 60, 40)


def test_keluaran_paddle_kosong_aman():
    assert DOC.extract_boxes_paddle(None) == []
    assert DOC.extract_boxes_paddle([]) == []
    assert DOC.extract_boxes_paddle([{"rec_texts": [], "rec_scores": []}]) == []


def test_keluaran_paddle_memakai_dt_polys_bila_rec_polys_kosong(cfg):
    """Sebagian versi hanya mengisi `dt_polys`."""
    mentah = [{"rec_texts": ["EXP"], "rec_scores": [0.9], "rec_polys": [],
               "dt_polys": [[[1, 2], [3, 2], [3, 4], [1, 4]]]}]
    kotak = DOC.extract_boxes_paddle(mentah)
    assert [k.text for k in kotak] == ["EXP"]
    assert kotak[0].box == (1, 2, 3, 4)


def test_rotation_info_mati_secara_bawaan(cfg):
    """Ditolak datanya 31-10: pada dokumen tegak CER 15,3% -> 40,3% dan 13,5x lebih lambat.

    Saklarnya tetap ada supaya bisa diablasi lagi, tetapi bawaannya WAJIB kosong.
    """
    assert DOC.DocumentReader(cfg)._rotasi_kwargs() == {}


def test_rotation_info_dioper_bila_diisi(cfg):
    c = copy.deepcopy(cfg)
    c["vision"]["document"]["rotation_info"] = [90, 180, 270]
    assert DOC.DocumentReader(c)._rotasi_kwargs() == {"rotation_info": [90, 180, 270]}
