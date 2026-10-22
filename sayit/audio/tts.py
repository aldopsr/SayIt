"""Text-to-Speech hibrida (keputusan Fase 0: gTTS).

- Clip  -> diputar dari file MP3 di assets/tts (dibuat sekali oleh scripts/build_tts_cache.py)
- Text  -> disintesis gTTS saat itu juga (butuh internet). Tanpa internet, diganti pesan "butuh_internet".
- Pause -> hening

Hasil akhirnya satu array audio mono, sehingga bisa diputar langsung atau disimpan sebagai WAV
(misalnya untuk st.audio di Streamlit).
"""
from __future__ import annotations

import hashlib
import re
import socket
import tempfile
from pathlib import Path

import numpy as np
import soundfile as sf

from sayit.audio import io
from sayit.config import project_path
from sayit.response.templates import CLIP_TEXTS, Clip, Pause, Text, Utterance

DEFAULT_SR = 24000   # laju sampel MP3 gTTS; klip lain disesuaikan ke nilai ini


class MissingClipError(RuntimeError):
    pass


def internet_available(timeout: float = 1.5) -> bool:
    try:
        socket.create_connection(("8.8.8.8", 53), timeout=timeout).close()
        return True
    except OSError:
        return False


def gtts_save(text: str, path: Path, lang: str = "id", tld: str = "com", timeout: float = 8) -> None:
    from gtts import gTTS
    path.parent.mkdir(parents=True, exist_ok=True)
    gTTS(text, lang=lang, tld=tld, lang_check=False, timeout=timeout).save(str(path))


# dipakai bersama dengan sayit/audio/io.py agar logikanya tidak bercabang
_to_mono = io.to_mono
_resample = io.resample


# Kata yang seluruhnya kapital dibaca gTTS HURUF PER HURUF. Pada hasil OCR itu
# sering: judul, penekanan, dan kop surat lazim ditulis kapital semua, dan
# "KETENTUAN" terdengar sebagai "ka-e-te-en-te-u-a-en" - tidak bisa dipahami.
#
# Singkatan pendek justru BENAR dieja (PT, CV, RI, SMA), jadi ambangnya panjang:
# empat huruf ke atas dianggap kata biasa yang kebetulan ditulis kapital.
# ponytail: aturan panjang, bukan kamus singkatan - kamus tidak akan pernah lengkap
# dan salahnya tidak kelihatan sampai ada yang mendengarnya.
PANJANG_KAPITAL_DIEJA = 4

_KATA = re.compile(r"[A-Za-zÀ-ÿ]+")


def rapikan_untuk_suara(teks: str) -> str:
    """Siapkan teks bebas supaya terdengar wajar, bukan dieja.

    Hanya memengaruhi yang DIUCAPKAN; teks yang tampil di layar tetap asli.
    """
    def satu(m: re.Match) -> str:
        kata = m.group(0)
        if kata.isupper() and len(kata) >= PANJANG_KAPITAL_DIEJA:
            return kata.capitalize()
        return kata

    return _KATA.sub(satu, teks)


def _trim_silence(audio: np.ndarray, sr: int, threshold: float = 0.01, keep_ms: int = 20) -> np.ndarray:
    """Buang hening di awal dan akhir klip agar rangkaian kata tidak terdengar terputus-putus."""
    idx = np.flatnonzero(np.abs(audio) > threshold)
    if len(idx) == 0:
        return audio
    keep = int(sr * keep_ms / 1000)
    return audio[max(0, idx[0] - keep): min(len(audio), idx[-1] + keep)]


class SpeechRenderer:
    def __init__(self, cfg: dict, online: bool | None = None, synth=gtts_save):
        self.cfg = cfg["tts"]
        self.clip_dir = project_path(self.cfg["cache_dir"])
        self.online = online          # None = cek koneksi otomatis saat dibutuhkan
        self._synth = synth
        self.sr = DEFAULT_SR

    # ------------------------------------------------------------------ koneksi & sintesis

    def is_online(self) -> bool:
        return internet_available() if self.online is None else self.online

    def _synth_kwargs(self) -> dict:
        return {"lang": self.cfg.get("lang", "id"), "tld": self.cfg.get("tld", "com"),
                "timeout": self.cfg.get("timeout_s", 8)}

    def clip_path(self, key: str) -> Path:
        return self.clip_dir / f"{key}.mp3"

    def ensure_clip(self, key: str) -> Path:
        path = self.clip_path(key)
        if path.exists():
            return path
        if key not in CLIP_TEXTS:
            raise MissingClipError(f"Klip tidak dikenal: {key}")
        if not self.is_online():
            raise MissingClipError(f"Klip '{key}' belum dibuat dan tidak ada internet. "
                                   "Jalankan scripts/build_tts_cache.py saat online.")
        self._synth(CLIP_TEXTS[key], path, **self._synth_kwargs())
        return path

    def _load(self, path: Path, trim: bool) -> np.ndarray:
        audio, sr = sf.read(str(path), dtype="float32")
        audio = _resample(_to_mono(audio), sr, self.sr)
        return _trim_silence(audio, self.sr) if trim else audio

    def _render_text(self, text: str) -> np.ndarray | None:
        """None berarti tidak bisa disintesis (offline atau gagal)."""
        if not self.is_online():
            return None
        text = rapikan_untuk_suara(text)
        try:
            if self.cfg.get("cache_dynamic_text", False):
                path = self.clip_dir.parent / "tts_dynamic" / (hashlib.sha1(text.encode()).hexdigest() + ".mp3")
                if not path.exists():
                    self._synth(text, path, **self._synth_kwargs())
                return self._load(path, trim=False)
            with tempfile.TemporaryDirectory() as tmp:     # tidak meninggalkan jejak isi dokumen di disk
                path = Path(tmp) / "t.mp3"
                self._synth(text, path, **self._synth_kwargs())
                return self._load(path, trim=False)
        except Exception:
            return None

    # ------------------------------------------------------------------ render

    def render(self, utt: Utterance) -> tuple[np.ndarray, int]:
        gap = np.zeros(int(self.sr * self.cfg.get("word_gap_ms", 40) / 1000), np.float32)
        pauses = {"short": self.cfg.get("pause_short_ms", 250), "long": self.cfg.get("pause_long_ms", 450)}
        pieces: list[np.ndarray] = []
        prev_clip = False
        for part in utt:
            if isinstance(part, Clip):
                if prev_clip:
                    pieces.append(gap)
                pieces.append(self._load(self.ensure_clip(part.key), trim=True))
                prev_clip = True
            elif isinstance(part, Pause):
                pieces.append(np.zeros(int(self.sr * pauses.get(part.kind, 250) / 1000), np.float32))
                prev_clip = False
            elif isinstance(part, Text):
                audio = self._render_text(part.text)
                if audio is None:
                    audio = self._load(self.ensure_clip("butuh_internet"), trim=True)
                pieces.append(audio)
                prev_clip = False
            else:
                raise TypeError(f"Bagian ujaran tidak dikenal: {part!r}")
        audio = np.concatenate(pieces) if pieces else np.zeros(0, np.float32)
        return audio.astype(np.float32), self.sr

    def save_wav(self, utt: Utterance, path: str | Path) -> Path:
        audio, sr = self.render(utt)
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        sf.write(str(path), audio, sr)
        return path

    def speak(self, utt: Utterance) -> None:
        from sayit.audio.io import play
        audio, sr = self.render(utt)
        play(audio, sr)
