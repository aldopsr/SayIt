"""Demo alur suara tanpa kamera: rekam -> STT -> intent -> jawaban suara contoh.

    python scripts/demo_voice.py             # deteksi internet otomatis
    python scripts/demo_voice.py --offline   # uji perilaku tanpa internet

Tekan Enter untuk bicara setelah bunyi bip. Ketik q lalu Enter untuk keluar.
"""
from __future__ import annotations

import argparse
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sayit.audio.io import record_from_config  # noqa: E402
from sayit.audio.stt import Transcriber  # noqa: E402
from sayit.audio.tts import SpeechRenderer  # noqa: E402
from sayit.config import load_config  # noqa: E402
from sayit.intent import keywords as K  # noqa: E402
from sayit.intent.router import IntentRouter  # noqa: E402
from sayit.response import templates as T  # noqa: E402

CONTOH_DOKUMEN = ("Surat pemberitahuan. Rapat warga akan diadakan pada hari Sabtu pukul sembilan pagi "
                  "di balai desa. Mohon kehadiran bapak dan ibu tepat waktu.")


def jawaban_contoh(intent: str, state: dict) -> T.Utterance:
    """Jawaban palsu per intent, hanya untuk menguji alur suara sebelum modul citra siap."""
    if intent == K.UANG:
        return T.money_response({50000: 2, 10000: 1})
    if intent == K.KEDALUWARSA:
        today = date.today()
        return T.expiry_response(today + timedelta(days=78), today)
    if intent == K.BACA:
        state["chunks"] = T.split_chunks(CONTOH_DOKUMEN, max_words=10)
        state["pos"] = 1
        return T.document_chunk_response(state["chunks"][0], has_more=len(state["chunks"]) > 1)
    if intent == K.LANJUT:
        chunks, pos = state.get("chunks", []), state.get("pos", 0)
        if pos >= len(chunks):
            return T.fixed("tidak_ada_lanjutan")
        state["pos"] = pos + 1
        return T.document_chunk_response(chunks[pos], has_more=pos + 1 < len(chunks))
    if intent == K.ULANGI:
        return state.get("last") or T.fixed("tidak_ada_ulangan")
    if intent == K.FOTO_BARU:
        return T.fixed("silakan_foto")
    if intent == K.BANTUAN:
        return T.fixed("menu_bantuan")
    return T.fixed("tidak_mengerti")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true")
    args = ap.parse_args()

    cfg = load_config()
    stt = Transcriber(cfg)
    router = IntentRouter.from_config(cfg)
    tts = SpeechRenderer(cfg, online=False if args.offline else None)

    print("Memuat model STT...")
    stt.load()
    print(f"Model siap ({stt.load_s:.1f} s).")
    tts.speak(T.fixed("foto_diambil"))

    state: dict = {}
    while True:
        if input("\nEnter = bicara setelah bip, q = keluar: ").strip().lower() == "q":
            break
        audio = record_from_config(cfg)
        tr = stt.transcribe(audio, sr=cfg["audio"]["sample_rate"])
        if tr.empty:
            print(f"  (transkrip kosong: {tr.reason})")
            tts.speak(T.fixed("suara_tidak_jelas"))
            continue
        res = router.route(tr.text)
        utt = jawaban_contoh(res.intent, state)
        if res.intent != K.ULANGI:
            state["last"] = utt
        print(f"  STT   : {tr.text}  ({tr.elapsed_s:.1f} s)")
        print(f"  Intent: {res.intent}  skor={ {k: v for k, v in res.scores.items() if v} }")
        print(f"  Jawab : {T.to_plain_text(utt)}")
        tts.speak(utt)


if __name__ == "__main__":
    main()
