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
    assert hasil.notes == {"raw_boxes": 2, "kept_boxes": 1, "chunks": 1,
                           "layout_mode": "dokumen"}


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


# ------------------------------------------------------- percobaan ulang dengan memutar gambar

class ReaderPerSudut:
    """OCR tiruan yang jawabannya bergantung bentuk citra.

    Meniru temuan 31-10: gambar terbalik hampir tidak TERDETEKSI (193 kotak
    lawan 887), jadi yang kembali sedikit dan skornya rendah. Di sini bentuk
    citra menjadi penanda sudut, karena rotasi 90/270 menukar tinggi dan lebar.
    """

    def __init__(self, *args, **kwargs):
        self.bentuk = []

    def readtext(self, image, **kwargs):
        self.bentuk.append(image.shape[:2])
        tinggi, lebar = image.shape[:2]
        if tinggi > lebar:      # tegak setelah diputar 90 derajat
            return [([[10, 10], [300, 10], [300, 30], [10, 30]],
                     "Rapat dimulai pukul sembilan pagi", 0.93)]
        return [([[10, 10], [60, 10], [60, 30], [10, 30]], "wejes", 0.52)]


def pabrik_per_sudut():
    def buat(*args, **kwargs):
        buat.reader = ReaderPerSudut(*args, **kwargs)
        return buat.reader
    return buat


def tanpa_pra(c):
    """Matikan pra-pemrosesan supaya bentuk citra tidak ikut diubah resize."""
    c["vision"]["document"]["preprocess_chain"] = None
    return c


def test_gambar_dengan_skor_rendah_diputar_dan_pulih(cfg):
    """Bacaan berskor rendah memicu rotasi, dan jawaban berkata terbanyak yang dipakai."""
    f = pabrik_per_sudut()
    r = DOC.DocumentReader(tanpa_pra(cfg), reader_factory=f)
    hasil = r.read(np.zeros((400, 900, 3), np.uint8))

    assert hasil.text == "Rapat dimulai pukul sembilan pagi."
    assert hasil.notes["rotated_deg"] in (90, 270)
    assert hasil.notes["rotations_tried"] == [180, 90, 270]
    assert len(f.reader.bentuk) == 4                 # satu lintasan awal + tiga sudut


def test_bacaan_berskor_tinggi_tidak_membayar_rotasi(cfg):
    """Foto yang sudah tegak harus menjawab di lintasan pertama.

    Ini separuh alasan ambangnya konservatif: 4x lintasan pada foto tegak adalah
    biaya sia-sia, dan latensi dokumen sudah menyimpang dari NFR-01.
    """
    f = pabrik(JAWABAN)                       # skor 0,95 dan 0,91
    r = DOC.DocumentReader(cfg, reader_factory=f)
    hasil = r.read(np.zeros((600, 800, 3), np.uint8))

    assert len(f.reader.panggilan) == 1
    assert "rotated_deg" not in hasil.notes


def test_rotasi_bisa_dimatikan_lewat_config(cfg):
    """Dua saklar, dan masing-masing cukup untuk mematikannya."""
    for kunci, nilai in (("rotate_retry", []), ("rotate_trigger_score", None)):
        c = tanpa_pra(copy.deepcopy(cfg))
        c["vision"]["document"][kunci] = nilai
        f = pabrik_per_sudut()
        hasil = DOC.DocumentReader(c, reader_factory=f).read(np.zeros((400, 900, 3), np.uint8))
        assert len(f.reader.bentuk) == 1, kunci
        assert "rotated_deg" not in hasil.notes, kunci


def test_ambang_pemicu_memakai_nilai_terkalibrasi(cfg):
    """0,75 dikalibrasi 31-10 pada 13 dokumen; rentang tegak dan keliru bertumpang.

    Kalau angka ini diubah, akurasi DAN latensi wajib diukur ulang bersamaan.
    """
    assert cfg["vision"]["document"]["rotate_trigger_score"] == 0.75
    assert cfg["vision"]["document"]["rotate_retry"] == [180, 90, 270]


def test_tanpa_kotak_sama_sekali_tetap_memicu_rotasi(cfg):
    """OCR yang tidak mengembalikan apa pun adalah kasus paling mencurigakan."""
    r = DOC.DocumentReader(cfg, reader_factory=pabrik())
    assert r._perlu_putar(DOC.DocumentResult()) is True


def test_rotate_image_dipakai_bersama_modul_kedaluwarsa():
    """Satu implementasi saja: expiry mengekspor ulang nama dari document."""
    from sayit.vision import expiry as E
    assert E.rotate_image is DOC.rotate_image


# --------------------------------------------------------------------------- urutan bacaan

def kotak(teks, x, y, w=60, h=20, skor=0.9):
    return DOC.TextBox(teks, skor, (x, y, x + w, y + h))


def test_dua_blok_sejajar_tidak_dibaca_berselang_seling(cfg):
    """Inilah bug yang memunculkan 'kedekatan BlueBand sebagai enak banan'.

    Dua blok teks terpisah jauh mendatar tetapi sejajar tingginya. Mode dokumen
    menggabungkannya jadi satu baris; mode tersebar membacanya satu per satu.
    """
    kiri = [kotak("Petunjuk", 0, 0), kotak("Penyimpanan", 0, 25)]
    kanan = [kotak("Baik", 600, 0), kotak("digunakan", 600, 25)]
    semua = kiri + kanan

    assert DOC.compose_text(semua, cfg, "dokumen") == "Petunjuk Baik Penyimpanan digunakan."
    assert DOC.compose_text(semua, cfg, "tersebar") == "Petunjuk Penyimpanan. Baik digunakan."


def test_gugus_diurutkan_atas_ke_bawah_lalu_kiri_ke_kanan(cfg):
    atas = [kotak("judul", 300, 0)]
    bawah_kiri = [kotak("kiri", 0, 400)]
    bawah_kanan = [kotak("kanan", 600, 400)]
    teks = DOC.compose_text(atas + bawah_kanan + bawah_kiri, cfg, "tersebar")
    assert teks == "judul. kiri. kanan."


def test_mode_dokumen_tidak_berubah_perilakunya(cfg):
    """Penjaga regresi: CER 15,3% pada 13 dokumen diukur dengan jalur ini."""
    baris_teks = baris("Surat Keterangan Nomor Satu", y=0)
    assert DOC.compose_text(baris_teks, cfg, "dokumen") == "Surat Keterangan Nomor Satu."


def test_gugus_kosong_aman(cfg):
    assert DOC.group_clusters([], 1.5, 1.0) == []
    assert DOC.order_clusters([], 2.0) == []
    assert DOC.compose_text([], cfg, "tersebar") == ""


def test_jarak_kotak_nol_bila_bertindih():
    a = DOC.TextBox("a", 0.9, (0, 0, 100, 20))
    b = DOC.TextBox("b", 0.9, (50, 10, 150, 30))
    assert DOC.box_gap(a, b) == (0.0, 0.0)
    jauh = DOC.TextBox("c", 0.9, (300, 100, 400, 120))
    dx, dy = DOC.box_gap(a, jauh)
    assert (dx, dy) == (200.0, 80.0)


def test_mode_auto_membaca_kertas_ditemukan(cfg):
    """Logika `auto` tetap ada untuk ablasi, walau bawaannya bukan itu."""
    c = copy.deepcopy(cfg)
    c["vision"]["document"]["layout_mode"] = "auto"
    r = DOC.DocumentReader(c, reader_factory=pabrik())
    assert r._mode_tata_letak({"document_found": True}) == "dokumen"
    assert r._mode_tata_letak({"document_found": False}) == "tersebar"
    # perspektif dimatikan: tidak ada petunjuk, jatuh ke perilaku lama
    assert r._mode_tata_letak({}) == "dokumen"


def test_bawaan_tersebar_bukan_auto(cfg):
    """`auto` DITOLAK datanya 31-10: memilih persis terbalik.

    `document_found` menyala pada 2 foto papan nama dan mati pada seluruh 13
    dokumen A4, karena `perspective.min_area_ratio` 0,50 sengaja ketat. Mode
    `tersebar` dipakai sebagai bawaan: pada 13 dokumen bedanya hanya 0,05 poin
    CER (15,30% lawan 15,25%), sementara pada teks tersebar ia memperbaiki urutan.
    """
    assert cfg["vision"]["document"]["layout_mode"] == "tersebar"
    r = DOC.DocumentReader(cfg, reader_factory=pabrik())
    assert r._mode_tata_letak({"document_found": True}) == "tersebar"


def test_mode_bisa_dipaksa_untuk_ablasi(cfg):
    for paksa in ("dokumen", "tersebar"):
        c = copy.deepcopy(cfg)
        c["vision"]["document"]["layout_mode"] = paksa
        r = DOC.DocumentReader(c, reader_factory=pabrik())
        assert r._mode_tata_letak({"document_found": True}) == paksa
        assert r._mode_tata_letak({"document_found": False}) == paksa


# --------------------------------------------------------------------------- penjaga mutu

def hasil_palsu(skor, mentah, lolos=None):
    kotak_kuat = [DOC.TextBox(f"k{i}", skor, (0, i * 25, 60, i * 25 + 20))
                  for i in range(lolos if lolos is not None else mentah)]
    return DOC.DocumentResult(text="k0.", chunks=["k0."], boxes=kotak_kuat,
                              notes={"raw_boxes": mentah})


def test_ambang_penjaga_mutu_memakai_nilai_terkalibrasi(cfg):
    """0,75 dikalibrasi 31-10 pada 35 foto: 6/8 bacaan buruk tertangkap, 0/27 baik salah ditandai.

    Marginnya tipis (buruk tertinggi 0,746 lawan baik terendah 0,768), jadi
    mengubah angka ini WAJIB disertai pengukuran ulang pada kedua sisi.
    """
    d = cfg["vision"]["document"]
    assert d["unclear_score_min"] == 0.75
    # penanda rasio TIDAK TERBUKTI - nol tambahan di atas penanda skor
    assert d["unclear_kept_ratio_min"] is None


def test_penjaga_mutu_bisa_dimatikan_seluruhnya(cfg):
    c = copy.deepcopy(cfg)
    c["vision"]["document"]["unclear_score_min"] = None
    c["vision"]["document"]["unclear_kept_ratio_min"] = None
    assert DOC.bacaan_meragukan(hasil_palsu(0.2, 10, 1), c)[0] is False


def test_skor_rendah_dinyatakan_meragukan(cfg):
    c = copy.deepcopy(cfg)
    c["vision"]["document"]["unclear_score_min"] = 0.7
    meragukan, catatan = DOC.bacaan_meragukan(hasil_palsu(0.5, 5), c)
    assert meragukan is True
    assert catatan["unclear_reason"] == ["skor_rendah"]
    assert DOC.bacaan_meragukan(hasil_palsu(0.9, 5), c)[0] is False


def test_banyak_kotak_terbuang_dinyatakan_meragukan(cfg):
    """Penanda kedua menangkap kasus yang skornya BUTA: skor tinggi, isi sedikit."""
    c = copy.deepcopy(cfg)
    c["vision"]["document"]["unclear_kept_ratio_min"] = 0.5
    meragukan, catatan = DOC.bacaan_meragukan(hasil_palsu(0.95, 20, lolos=2), c)
    assert meragukan is True
    assert catatan["unclear_reason"] == ["banyak_terbuang"]
    assert DOC.bacaan_meragukan(hasil_palsu(0.95, 20, lolos=18), c)[0] is False


def test_tidak_ada_tulisan_bukan_urusan_penjaga_mutu(cfg):
    """Foto tanpa tulisan sudah punya jawabannya sendiri; jangan ditimpa."""
    c = copy.deepcopy(cfg)
    c["vision"]["document"]["unclear_score_min"] = 0.9
    assert DOC.bacaan_meragukan(DOC.DocumentResult(), c)[0] is False


def test_bacaan_meragukan_menjawab_kurang_jelas_bukan_isi():
    hasil = DOC.DocumentResult(text="kata acak.", chunks=["kata acak."], unclear=True)
    assert DOC.chunk_utterance(hasil) == T.fixed("tulisan_kurang_jelas")


def test_bacaan_jelas_tetap_dibacakan():
    hasil = DOC.DocumentResult(text="isi benar.", chunks=["isi benar."])
    assert DOC.chunk_utterance(hasil) != T.fixed("tulisan_kurang_jelas")


# --------------------------------------------------------------------------- kemiringan baris

def baris_miring(teks, y0, slope, x0=200, lebar=90, jarak=20, tinggi=30):
    """Satu baris teks yang menurun/menanjak sebesar `slope` (dy/dx)."""
    kata, x = [], x0
    for w in teks.split():
        y = y0 + slope * (x + lebar / 2 - x0)
        kata.append(DOC.TextBox(w, 0.9, (x, y, x + lebar, y + tinggi)))
        x += lebar + jarak
    return kata


def test_kemiringan_ditaksir_dari_kotak(cfg):
    kotak_miring = baris_miring("satu dua tiga empat lima", y0=100, slope=-0.1)
    s = DOC.estimate_text_slope(kotak_miring, 3.0, 0.35)
    assert s == pytest.approx(-0.1, abs=0.01)


def test_kemiringan_nol_pada_teks_lurus(cfg):
    assert DOC.estimate_text_slope(baris("satu dua tiga", y=0), 3.0, 0.35) == 0.0
    assert DOC.estimate_text_slope([], 3.0, 0.35) == 0.0
    assert DOC.estimate_text_slope([DOC.TextBox("x", 0.9, (0, 0, 10, 10))], 3.0, 0.35) == 0.0


def test_taksiran_liar_dibuang():
    """Di atas batas, urusannya percobaan ulang rotasi - bukan pengelompokan baris."""
    curam = baris_miring("satu dua tiga empat", y0=0, slope=0.9)
    assert DOC.estimate_text_slope(curam, 3.0, 0.35) == 0.0


def test_dua_baris_miring_tidak_saling_menyisip(cfg):
    """Cacat nyata pada `tulisanbukubaru (2)`, dikecilkan jadi kasus uji.

    Dua baris miring 6 derajat. Tanpa koreksi, ujung kanan baris pertama jatuh
    lebih tinggi daripada awal baris kedua, dan keduanya tercampur.
    """
    atas = baris_miring("Ada beberapa cara yang dapat", y0=200, slope=-0.1)
    bawah = baris_miring("Pertama adalah memberantas tempat biak", y0=240, slope=-0.1)
    semua = atas + bawah

    tercampur = DOC.group_lines(semua, 0.6)                 # tanpa koreksi
    lurus = DOC.group_lines(semua, 0.6, slope=-0.1)         # dengan koreksi

    assert [" ".join(w.text for w in b) for b in lurus] == [
        "Ada beberapa cara yang dapat",
        "Pertama adalah memberantas tempat biak",
    ]
    assert len(tercampur) != 2 or [" ".join(w.text for w in b) for b in tercampur] != [
        "Ada beberapa cara yang dapat",
        "Pertama adalah memberantas tempat biak",
    ]


def test_koreksi_kemiringan_bisa_dimatikan(cfg):
    c = copy.deepcopy(cfg)
    c["vision"]["document"]["line_slope_correct"] = False
    miring = baris_miring("satu dua tiga empat lima enam", y0=100, slope=-0.12)
    assert DOC.compose_text(miring, c, "dokumen") != "satu dua tiga empat lima enam."
    assert DOC.compose_text(miring, cfg, "dokumen") == "satu dua tiga empat lima enam."


# --------------------------------------------------- pembentukan baris dengan rantai

def test_rantai_menumpuk_simpangan_yang_melampaui_toleransi(cfg):
    """Inilah yang `pita` tidak bisa: simpangan MENUMPUK sepanjang baris.

    Tiap langkah hanya turun 15 px - di bawah toleransi 18 px - tetapi sepanjang
    enam kata totalnya 75 px, lebih dari empat kali toleransi. `pita`
    membandingkan terhadap nilai tengah baris berjalan, jadi ujung baris jatuh
    di luar jangkauan dan terputus. `rantai` membandingkan terhadap kotak tepat
    sebelumnya, jadi ia mengikuti berapa pun total simpangannya.

    Toleransi per langkah tetap berlaku: `rantai` mengikuti lengkungan landai
    sepanjang apa pun, bukan patahan tajam.
    """
    kata, x, y = [], 100, 400
    for w in "satu dua tiga empat lima enam".split():
        kata.append(DOC.TextBox(w, 0.9, (x, y, x + 80, y + 30)))
        x += 100
        y -= 15                          # 15 px < toleransi 0,6 x 30 = 18 px
    rantai = DOC.group_lines_chain(kata, 0.6, 3.0)
    assert [" ".join(w.text for w in b) for b in rantai] == ["satu dua tiga empat lima enam"]
    # pita tanpa koreksi kemiringan terputus pada data yang sama
    assert len(DOC.group_lines(kata, 0.6)) > 1


def test_rantai_tidak_menyambung_melewati_celah_lebar(cfg):
    """Celah mendatar lebar = halaman seberang atau kolom lain, bukan lanjutan baris."""
    kiri = [DOC.TextBox("kiri", 0.9, (0, 100, 80, 130))]
    jauh = [DOC.TextBox("seberang", 0.9, (900, 100, 980, 130))]
    baris = DOC.group_lines_chain(kiri + jauh, 0.6, 3.0)
    assert len(baris) == 2


def test_rantai_kosong_aman():
    assert DOC.group_lines_chain([], 0.6, 3.0) == []


def test_bawaan_pengelompokan_baris_adalah_pita(cfg):
    """`rantai` DIUKUR 31-10 dan hasilnya terbelah, jadi bawaannya belum diganti.

    Pada 13 dokumen beracuan: 14,89% -> 14,94% (1 membaik, 2 memburuk, 10 tetap)
    yaitu di dalam derau. Pada foto buku ia tampak lebih baik, tetapi itu
    penilaian mata pada 2 foto tanpa teks acuan - belum cukup untuk mengunci.
    """
    assert cfg["vision"]["document"]["line_grouping"] == "pita"
