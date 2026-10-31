"""Aplikasi SayIt (Streamlit).

Jalankan dari root repo:
    .venv\\Scripts\\activate
    streamlit run app.py

Aksesibilitas (PRD Prinsip Desain 1: suara adalah antarmuka utama):

- Setiap jawaban diumumkan dengan suara (autoplay) dan dimasukkan ke wilayah
  `aria-live` supaya pembaca layar membacakannya tanpa perlu menelusuri halaman.
- Intent yang lambat (baca dokumen, kedaluwarsa) memutar penanda "sedang saya
  proses" LEBIH DULU, sehingga tidak ada hening 5 detik tanpa keterangan.
  Terbukti di peramban: elemen audio sampai ke DOM dan berbunyi saat proses
  masih berjalan.

Yang MASIH menjadi keterbatasan, dan disebut juga di PRD Bagian 3: urutan fokus
keyboard dan pelabelan widget bawaan Streamlit tidak sepenuhnya terkendali.
Alur yang sama sekali tidak butuh layar tetap `python scripts/demo_voice.py`.
"""
from __future__ import annotations

import time
from datetime import date

import streamlit as st

from sayit.appkit import foto_dari_berkas, sidik, suara_dari_berkas
from sayit.audio.stt import Transcriber
from sayit.audio.tts import MissingClipError, SpeechRenderer
from sayit.config import load_config
from sayit.pipeline import Pipeline
from sayit.response.templates import to_plain_text
from sayit.vision.document import DocumentReader
from sayit.vision.money import MoneyDetector

st.set_page_config(page_title="SayIt", page_icon="🔊", layout="centered")

CONTOH_PERTANYAAN = [
    "ini uang berapa",
    "tolong bacakan tulisannya",
    "kapan kedaluwarsanya",
    "lanjut",
    "ulangi",
    "kamu bisa apa",
]


# --------------------------------------------------------------------------- pemuatan

@st.cache_resource(show_spinner="Memuat model, sekitar 10 detik pada percobaan pertama...")
def muat_komponen():
    """Model dimuat sekali untuk seluruh sesi peramban.

    Terukur pada i7-13650HX CPU (02-10): total sekitar 10 detik - STT 3,4 detik,
    uang 2,8 detik, OCR dokumen 1,5 detik, OCR kedaluwarsa 3,9 detik. Dua mesin OCR
    dimuat karena modul kedaluwarsa memakai PaddleOCR sementara modul dokumen tetap
    EasyOCR; lihat `vision.expiry.engine`. Waktu ini DI LUAR PRD NFR-01, yang mengukur
    per giliran percakapan, bukan waktu mulai aplikasi.
    """
    cfg = load_config()
    return cfg, Transcriber(cfg), MoneyDetector(cfg), DocumentReader(cfg)


def pipeline() -> Pipeline:
    if "pipeline" not in st.session_state:
        cfg, stt, money, ocr = muat_komponen()
        p = Pipeline(cfg, transcriber=stt, money=money, ocr=ocr)
        st.session_state.pipeline = p
        st.session_state.status = p.load()      # modul yang sudah dimuat langsung kembali
        st.session_state.riwayat = []
    return st.session_state.pipeline


def penyuara(offline: bool) -> SpeechRenderer:
    kunci = f"tts_{offline}"
    if kunci not in st.session_state:
        st.session_state[kunci] = SpeechRenderer(load_config(), online=None if not offline else False)
        st.session_state[kunci].warmup()
    return st.session_state[kunci]


# --------------------------------------------------------------------------- tampilan

def umumkan(utt, offline: bool):
    """Putar penanda suara SEBELUM proses lambat dimulai.

    Diuji di peramban: pada detik ke-3 dari kerja 6 detik, elemen audio sudah
    ada di DOM dan sudah berbunyi, sementara jawabannya belum digambar.
    Streamlit mengalirkan elemen sambil skrip berjalan, tidak menunggu selesai.
    """
    try:
        audio, sr = penyuara(offline).render(utt)
        st.audio(audio, sample_rate=sr, autoplay=True)
    except Exception:                                    # noqa: BLE001 - penanda tidak boleh menggagalkan proses
        pass
    lapor_status(to_plain_text(utt))


def lapor_status(teks: str, mendesak: bool = False) -> None:
    """Wilayah aria-live supaya pembaca layar mengumumkan perubahan status.

    Streamlit tidak menyediakan ini, jadi disisipkan sebagai HTML. Tanpa itu,
    pengguna pembaca layar tidak tahu apa pun berubah sampai ia menelusuri
    halaman sendiri.
    """
    sifat = "assertive" if mendesak else "polite"
    st.markdown(
        f'<div role="status" aria-live="{sifat}" '
        f'style="position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0)">'
        f'{teks}</div>', unsafe_allow_html=True)


def tampilkan_jawaban(giliran, offline: bool):
    lapor_status(giliran.text, mendesak=True)
    st.markdown(f"### {giliran.text}")
    st.caption(f"Intent: `{giliran.intent}` — {giliran.reason}")
    try:
        audio, sr = penyuara(offline).render(giliran.utterance)
        st.audio(audio, sample_rate=sr, autoplay=True)
    except MissingClipError as e:
        st.warning(f"Suara belum bisa diputar: {e}\n\n"
                   "Jalankan `python scripts/build_tts_cache.py` sekali saat ada internet.")
    except Exception as e:                               # noqa: BLE001 - jangan sampai demo mati
        st.warning(f"Suara gagal dibuat: {e}")


def catat(giliran):
    st.session_state.riwayat.insert(0, (time.strftime("%H:%M:%S"), giliran))


# --------------------------------------------------------------------------- halaman

p = pipeline()

st.title("SayIt")
st.caption("Foto dulu, lalu tanya dengan suara. Nominal uang, isi tulisan, atau tanggal kedaluwarsa.")

with st.sidebar:
    st.subheader("Status modul")
    for nama, keadaan in st.session_state.status.items():
        ikon = "✅" if keadaan.startswith("siap") else ("➖" if "tidak dipasang" in keadaan else "⚠️")
        st.write(f"{ikon} **{nama}** — {keadaan}")
    st.divider()
    offline = st.checkbox("Mode offline (tanpa gTTS)", value=False,
                          help="Isi dokumen tidak bisa dibacakan tanpa internet; "
                               "jawaban uang dan tanggal tetap bisa karena memakai klip tersimpan.")
    st.caption(f"Hari ini: {date.today():%d %B %Y}")
    st.divider()
    st.caption("Jawaban dan status diumumkan dengan suara. Untuk alur yang sama sekali "
               "tidak butuh layar: `python scripts/demo_voice.py`.")

# ---------------------------------------------------------------- langkah 1: foto

st.subheader("1. Ambil foto")
tab_kamera, tab_unggah = st.tabs(["Kamera", "Unggah berkas"])
with tab_kamera:
    dari_kamera = st.camera_input("Arahkan kamera, lalu tekan tombol", label_visibility="collapsed")
with tab_unggah:
    dari_berkas = st.file_uploader("Pilih gambar", type=["jpg", "jpeg", "png", "bmp", "webp"],
                                   label_visibility="collapsed")

berkas_foto = dari_kamera or dari_berkas
if berkas_foto is not None and st.session_state.get("foto_terakhir") != sidik(berkas_foto):
    st.session_state.foto_terakhir = sidik(berkas_foto)
    try:
        giliran = p.set_photo(foto_dari_berkas(berkas_foto))
    except ValueError as e:
        st.error(str(e))
    else:
        catat(giliran)
        st.session_state.jawaban = giliran

if p.has_photo:
    st.success("Foto tersimpan dan siap ditanya.")
else:
    st.info("Belum ada foto yang layak. Pertanyaan tugas akan dijawab dengan permintaan memotret.")

# ---------------------------------------------------------------- langkah 2: pertanyaan

st.subheader("2. Ajukan pertanyaan")
kolom_suara, kolom_teks = st.columns(2)

with kolom_suara:
    st.caption("Rekam suara")
    rekaman = st.audio_input("Tekan untuk merekam", label_visibility="collapsed")

with kolom_teks:
    st.caption("Atau ketik (untuk menguji tanpa mikrofon)")
    # dikosongkan setelah dikirim, agar pertanyaan berikutnya tidak menumpuk
    with st.form("tanya_teks", clear_on_submit=True):
        teks = st.text_input("Pertanyaan", label_visibility="collapsed",
                             placeholder="misalnya: ini uang berapa")
        kirim = st.form_submit_button("Tanya", use_container_width=True)

st.caption("Contoh: " + " · ".join(f"*{c}*" for c in CONTOH_PERTANYAAN))

# Penanda "sedang saya proses" diputar lewat on_progress, sebelum modul yang
# lambat dijalankan. Hanya untuk intent yang memang lama (lihat pipeline.slow_intents):
# untuk jawaban uang yang 0,2 detik, penanda justru menumpuk jawabannya.
penanda = lambda utt: umumkan(utt, offline)

if rekaman is not None and st.session_state.get("suara_terakhir") != sidik(rekaman):
    st.session_state.suara_terakhir = sidik(rekaman)
    with st.spinner("Mendengarkan dan memproses..."):
        audio = suara_dari_berkas(rekaman, p.cfg["audio"]["sample_rate"])
        giliran = p.listen(audio, on_progress=penanda)
    catat(giliran)
    st.session_state.jawaban = giliran

if kirim and teks.strip():
    with st.spinner("Sedang saya proses..."):
        giliran = p.ask(teks.strip(), on_progress=penanda)
    catat(giliran)
    st.session_state.jawaban = giliran

# ---------------------------------------------------------------- jawaban

if st.session_state.get("jawaban") is not None:
    st.subheader("3. Jawaban")
    tampilkan_jawaban(st.session_state.jawaban, offline)

    catatan = st.session_state.jawaban.notes
    if catatan:
        with st.expander("Rincian teknis (untuk laporan)"):
            if "transcript" in catatan:
                st.write(f"**Transkrip:** {catatan['transcript']}")
            waktu = {k: v for k, v in catatan.items() if k.endswith("_s")}
            if waktu:
                st.write("**Waktu:** " + ", ".join(f"{k} {v:.2f} s" for k, v in waktu.items()))
            st.json({k: v for k, v in catatan.items() if k not in ("scores", "matched")},
                    expanded=False)
            if "scores" in catatan:
                st.write("**Skor router:**")
                st.json(catatan["scores"], expanded=False)

# ---------------------------------------------------------------- riwayat

if st.session_state.get("riwayat"):
    with st.expander(f"Riwayat sesi ({len(st.session_state.riwayat)} giliran)"):
        for jam, g in st.session_state.riwayat:
            st.write(f"`{jam}` **{g.intent}** — {g.text}")
