"""Tes aplikasi Streamlit dan penghubung berkasnya.

Halaman dijalankan tanpa peramban lewat `streamlit.testing`, dengan seluruh
model diganti tiruan. Tidak ada model yang dimuat dan tidak ada internet dipakai.
"""
import io

import cv2
import numpy as np
import pytest
import soundfile as sf

import sayit.audio.stt as modul_stt
import sayit.audio.tts as modul_tts
import sayit.vision.document as modul_doc
import sayit.vision.money as modul_money
from sayit.appkit import foto_dari_berkas, sidik, suara_dari_berkas
from sayit.config import PROJECT_ROOT
from sayit.vision.document import TextBox, build_result
from sayit.vision.money import Detection, MoneyResult

streamlit = pytest.importorskip("streamlit")
AppTest = pytest.importorskip("streamlit.testing.v1").AppTest


# --------------------------------------------------------------------------- berkas tiruan

class Berkas:
    """Meniru berkas unggahan Streamlit: yang dipakai hanya getvalue()."""

    def __init__(self, data: bytes):
        self._data = data

    def getvalue(self) -> bytes:
        return self._data


def berkas_gambar(lebar=800, tinggi=800, nilai=200, ext=".png") -> Berkas:
    img = np.full((tinggi, lebar, 3), nilai, np.uint8)
    cv2.rectangle(img, (100, 100), (400, 300), (30, 30, 30), -1)
    ok, buf = cv2.imencode(ext, img)
    assert ok
    return Berkas(buf.tobytes())


def berkas_suara(detik=1.0, sr=48000, saluran=1) -> Berkas:
    n = int(sr * detik)
    nada = (0.2 * np.sin(2 * np.pi * 220 * np.arange(n) / sr)).astype(np.float32)
    data = nada if saluran == 1 else np.stack([nada, nada], axis=1)
    buf = io.BytesIO()
    sf.write(buf, data, sr, format="WAV")
    return Berkas(buf.getvalue())


# --------------------------------------------------------------------------- penghubung berkas

def test_sidik_membedakan_isi():
    a, b = berkas_gambar(nilai=200), berkas_gambar(nilai=201)
    assert sidik(a) == sidik(berkas_gambar(nilai=200))
    assert sidik(a) != sidik(b)


def test_gambar_didekode_menjadi_bgr():
    img = foto_dari_berkas(berkas_gambar(640, 480))
    assert img.shape == (480, 640, 3)
    assert img.dtype == np.uint8


@pytest.mark.parametrize("ext", [".png", ".jpg", ".bmp"])
def test_beberapa_format_gambar(ext):
    assert foto_dari_berkas(berkas_gambar(ext=ext)).shape[2] == 3


def test_berkas_bukan_gambar_ditolak():
    with pytest.raises(ValueError, match="(?i)dibaca sebagai gambar"):
        foto_dari_berkas(Berkas(b"ini bukan gambar"))


def test_berkas_kosong_ditolak():
    with pytest.raises(ValueError, match="(?i)kosong"):
        foto_dari_berkas(Berkas(b""))


def test_rekaman_diubah_ke_laju_whisper():
    """st.audio_input memberi WAV 48 kHz; Whisper minta 16 kHz mono."""
    audio = suara_dari_berkas(berkas_suara(detik=1.0, sr=48000), 16000)
    assert audio.ndim == 1
    assert audio.dtype == np.float32
    assert len(audio) == pytest.approx(16000, rel=0.01)


def test_rekaman_stereo_dijadikan_mono():
    audio = suara_dari_berkas(berkas_suara(sr=16000, saluran=2), 16000)
    assert audio.ndim == 1


def test_laju_yang_sudah_sama_tidak_diubah():
    audio = suara_dari_berkas(berkas_suara(detik=2.0, sr=16000), 16000)
    assert len(audio) == 32000


def test_rekaman_kosong_ditolak():
    buf = io.BytesIO()
    sf.write(buf, np.zeros(0, np.float32), 16000, format="WAV")
    with pytest.raises(ValueError, match="kosong"):
        suara_dari_berkas(Berkas(buf.getvalue()), 16000)


# --------------------------------------------------------------------------- tiruan untuk halaman

class SttPalsu:
    def __init__(self, cfg, **k):
        self.cfg = cfg

    def load(self, *a, **k):
        return self

    def transcribe(self, audio, sr=16000):
        from sayit.audio.stt import Transcript
        return Transcript("ini uang berapa", False, 1.2, 1.0)


class MoneyPalsu:
    def __init__(self, cfg, **k):
        pass

    def load(self, *a, **k):
        return self

    def detect(self, image, preprocess=True):
        return MoneyResult(counts={50000: 1}, total=50000,
                           detections=[Detection(50000, 0.9, (0, 0, 10, 10))], notes={"raw": 1})


class OcrPalsu:
    def __init__(self, cfg, **k):
        self.cfg = cfg
        self.d = cfg["vision"]["document"]

    def load(self, *a, **k):
        return self

    def ocr_boxes(self, image):
        return [TextBox("EXP 03/12/2026", 0.9, (10, 10, 200, 40))], 0.01

    def read(self, image, preprocess=True):
        return build_result([TextBox("Surat Keterangan Domisili", 0.9, (10, 10, 300, 40))], self.cfg)


class PenyuaraPalsu:
    """Tidak menyentuh assets/tts maupun gTTS."""

    def __init__(self, cfg, online=None, **k):
        self.online = online

    def render(self, utt):
        # bukan hening total: st.audio membagi dengan amplitudo puncak,
        # dan array nol membuatnya membagi dengan nol
        n = 2400
        nada = 0.1 * np.sin(2 * np.pi * 440 * np.arange(n) / 24000)
        return nada.astype(np.float32), 24000


@pytest.fixture
def halaman(monkeypatch):
    monkeypatch.setattr(modul_stt, "Transcriber", SttPalsu)
    monkeypatch.setattr(modul_money, "MoneyDetector", MoneyPalsu)
    monkeypatch.setattr(modul_doc, "DocumentReader", OcrPalsu)
    monkeypatch.setattr(modul_tts, "SpeechRenderer", PenyuaraPalsu)
    streamlit.cache_resource.clear()
    yield AppTest.from_file(str(PROJECT_ROOT / "app.py"), default_timeout=60)
    streamlit.cache_resource.clear()


def tanya(at, kalimat):
    at.text_input[0].set_value(kalimat)
    at.button[0].click().run()
    return at


# --------------------------------------------------------------------------- halaman

def test_halaman_terbuka_tanpa_kesalahan(halaman):
    at = halaman.run()
    assert not at.exception
    assert at.title[0].value == "SayIt"
    assert "1. Ambil foto" in [s.value for s in at.subheader]


def test_status_modul_ditampilkan(halaman):
    """Keempat modul harus muncul di sidebar.

    Isi statusnya sengaja tidak diuji: status `zone` bergantung pada ada atau
    tidaknya `models/best_zone.pt` di disk, dan tes tidak boleh berubah hasilnya
    hanya karena seseorang menyalin berkas bobot.
    """
    at = halaman.run()
    tulisan = " ".join(m.value for m in at.sidebar.markdown)
    for modul in ("stt", "money", "ocr", "zone"):
        assert modul in tulisan, f"modul {modul} tidak muncul di sidebar"


def test_tanpa_foto_pengguna_diberi_tahu(halaman):
    at = halaman.run()
    assert any("Belum ada foto" in i.value for i in at.info)


def test_bertanya_lewat_teks(halaman):
    at = tanya(halaman.run(), "kamu bisa apa")
    assert not at.exception
    jawaban = " ".join(m.value for m in at.markdown)
    assert "Saya bisa membantu tiga hal" in jawaban


def test_intent_tugas_tanpa_foto(halaman):
    at = tanya(halaman.run(), "ini uang berapa")
    jawaban = " ".join(m.value for m in at.markdown)
    assert "Belum ada foto" in jawaban


def test_pertanyaan_kosong_diabaikan(halaman):
    at = tanya(halaman.run(), "   ")
    assert not at.exception
    assert "3. Jawaban" not in [s.value for s in at.subheader]


def test_riwayat_bertambah(halaman):
    at = tanya(halaman.run(), "kamu bisa apa")
    at = tanya(at, "halo apa kabar")
    assert len(at.session_state.riwayat) == 2


def test_jawaban_menampilkan_intent(halaman):
    at = tanya(halaman.run(), "kamu bisa apa")
    keterangan = " ".join(c.value for c in at.caption)
    assert "BANTUAN" in keterangan


def test_mode_offline_bisa_dinyalakan(halaman):
    at = halaman.run()
    at.sidebar.checkbox[0].check().run()
    assert not at.exception
    assert at.sidebar.checkbox[0].value is True


def test_suara_gagal_tidak_mematikan_halaman(halaman, monkeypatch):
    """Cache TTS kosong tidak boleh membuat demo berhenti; cukup diberi peringatan."""
    class PenyuaraRusak(PenyuaraPalsu):
        def render(self, utt):
            raise modul_tts.MissingClipError("klip 'menu_bantuan' belum dibuat")

    monkeypatch.setattr(modul_tts, "SpeechRenderer", PenyuaraRusak)
    at = tanya(halaman.run(), "kamu bisa apa")
    assert not at.exception
    assert any("build_tts_cache" in w.value for w in at.warning)


# --------------------------------------------------------------------------- penanda suara

def beri_foto(at):
    """Sisipkan foto langsung ke pipeline: AppTest tidak bisa mengisi camera_input."""
    yy, xx = np.indices((800, 800))
    abu = np.where(((yy // 8) + (xx // 8)) % 2 == 0, 60, 200).astype(np.uint8)
    at.session_state.pipeline.set_photo(cv2.cvtColor(abu, cv2.COLOR_GRAY2BGR))
    return at


def test_intent_lambat_mengumumkan_sebelum_menjawab(halaman):
    """PRD Prinsip Desain 1: setiap status diumumkan dengan suara.

    Penanda harus muncul mendahului jawaban, bukan bersamaan. Urutan elemen di
    halaman mencerminkan urutan penulisannya, jadi indeksnya yang diperiksa.
    """
    at = beri_foto(halaman.run())
    at = tanya(at, "tolong bacakan tulisannya")
    assert not at.exception
    tulisan = [m.value for m in at.markdown]
    penanda = next(i for i, t in enumerate(tulisan) if "sedang saya proses" in t.lower())
    jawaban = next(i for i, t in enumerate(tulisan) if "Surat Keterangan" in t)
    assert penanda < jawaban, "penanda harus diumumkan sebelum jawaban"


def test_intent_cepat_tidak_mengumumkan(halaman):
    """Jawaban uang hanya 0,2 detik; penanda justru akan menumpuk jawabannya."""
    at = beri_foto(halaman.run())
    at = tanya(at, "ini uang berapa")
    assert not any("sedang saya proses" in m.value.lower() for m in at.markdown)


def test_jawaban_diumumkan_ke_pembaca_layar(halaman):
    at = tanya(halaman.run(), "kamu bisa apa")
    hidup = [m.value for m in at.markdown if 'aria-live="assertive"' in m.value]
    assert hidup, "jawaban harus masuk wilayah aria-live agar dibacakan pembaca layar"
    assert "Saya bisa membantu tiga hal" in hidup[0]


def test_wilayah_status_tersembunyi_secara_visual(halaman):
    """Hanya untuk pembaca layar; tidak boleh mengganggu tampilan."""
    at = tanya(halaman.run(), "kamu bisa apa")
    hidup = next(m.value for m in at.markdown if 'aria-live' in m.value)
    assert "clip:rect(0 0 0 0)" in hidup


# --------------------------------------------------------------------------- pembaca gambar bersama

def test_orientasi_exif_diterapkan(tmp_path):
    """Foto ponsel menyimpan rotasi di metadata, bukan pada pikselnya.

    `cv2.imdecode` mengabaikannya, sehingga foto bisa terbaca miring 90 derajat
    padahal terlihat tegak di galeri. Untuk model yang peka rotasi itu fatal.
    """
    from PIL import Image
    from sayit import gambar

    tegak = Image.new("RGB", (100, 300), (200, 10, 10))
    p = tmp_path / "miring.jpg"
    # orientasi 6 berarti "putar 90 derajat searah jarum jam saat ditampilkan"
    exif = tegak.getexif()
    exif[274] = 6
    tegak.save(p, exif=exif)

    hasil = gambar.baca(p)
    assert hasil.shape[:2] == (100, 300), "rotasi EXIF tidak diterapkan"


def test_heic_terbaca(tmp_path):
    """Foto iPhone berformat HEIC tidak terbaca cv2 maupun PIL polos."""
    import pillow_heif
    from PIL import Image
    from sayit import gambar

    asal = Image.new("RGB", (80, 60), (10, 200, 10))
    p = tmp_path / "foto.heic"
    pillow_heif.from_pillow(asal).save(str(p))

    hasil = gambar.baca(p)
    assert hasil.shape[:2] == (60, 80)
    assert hasil.ndim == 3 and hasil.shape[2] == 3


def test_daftar_gambar_melewati_berkas_bantuan(tmp_path):
    from PIL import Image
    from sayit import gambar

    for nama in ("a.jpg", "_verifikasi.jpg", "catatan.txt"):
        if nama.endswith(".jpg"):
            Image.new("RGB", (10, 10)).save(tmp_path / nama)
        else:
            (tmp_path / nama).write_text("x")
    assert [p.name for p in gambar.daftar_gambar(tmp_path)] == ["a.jpg"]
