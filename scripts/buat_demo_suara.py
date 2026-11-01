"""Siapkan audio mode demo (?demo=1) dari sumber yang SAMA dengan aplikasi
sungguhan: klip tetap disalin apa adanya dari assets/tts, jawaban dirender
SpeechRenderer (edge-tts id-ID-GadisNeural). Butuh internet.

    python scripts/buat_demo_suara.py

Teks yang dicetak harus disalin ke JAWAB_DEMO di web/app/page.js supaya yang
terdengar dan yang dibaca pembaca layar tidak pernah berbeda."""
import shutil, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import soundfile as sf
from sayit.audio.tts import SpeechRenderer
from sayit.config import load_config
from sayit.response import templates as T

OUT = ROOT / "web" / "public" / "demo"
OUT.mkdir(parents=True, exist_ok=True)
ASET = ROOT / "assets" / "tts"

TETAP = ["sambutan", "sedang_memproses", "kamera_depan", "kamera_belakang",
         "kamera_tunggal", "sentuh_untuk_berkas", "sampai_jumpa", "foto_diambil"]
for n in TETAP:
    shutil.copy(ASET / f"{n}.mp3", OUT / f"{n}.mp3")
    print(f"salin  {n:22} :: {T.CLIP_TEXTS[n]}")

r = SpeechRenderer(load_config(), online=True)
r.warmup()

def buat(nama, utt):
    audio, sr = r.render(utt)
    sf.write(str(OUT / f"{nama}.mp3"), audio, sr, format="MP3")
    print(f"render {nama:22} :: {T.to_plain_text(utt)}")

buat("jawaban_uang", [*T.money_response({50000: 1, 2000: 2}), *T.fixed("tindak_lanjut")])
buat("jawaban_berkas", [*T.document_chunk_response(
    "Surat keterangan domisili atas nama pemohon, dikeluarkan kantor kelurahan.", False), *T.fixed("tindak_lanjut")])
print("total", sum(p.stat().st_size for p in OUT.glob('*.mp3')) // 1024, "KB,",
      len(list(OUT.glob('*.mp3'))), "berkas")
