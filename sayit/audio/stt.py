"""Speech-to-Text dengan faster-whisper (PRD 8.4, keputusan Fase 0: small + prompt)."""
from __future__ import annotations

import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import numpy as np

_WORD = re.compile(r"\w+")


@dataclass
class Transcript:
    text: str
    empty: bool
    elapsed_s: float
    audio_s: float
    reason: str = ""          # alasan jika transkrip dianggap kosong


def _words(text: str) -> list[str]:
    return _WORD.findall(text.lower())


def longest_common_run(a: list[str], b: list[str]) -> int:
    """Panjang deret kata berurutan terpanjang yang sama di a dan b."""
    best = 0
    prev = [0] * (len(b) + 1)
    for x in a:
        cur = [0] * (len(b) + 1)
        for j, y in enumerate(b, start=1):
            if x == y:
                cur[j] = prev[j - 1] + 1
                best = max(best, cur[j])
        prev = cur
    return best


class Transcriber:
    """Membungkus faster-whisper. Model dimuat sekali saat pertama dipakai."""

    def __init__(self, cfg: dict, model_factory: Callable | None = None):
        self.cfg = cfg["stt"]
        self._factory = model_factory
        self._model = None
        self.load_s: float | None = None
        self._prompt_words = _words(self.cfg.get("initial_prompt", ""))

    def load(self):
        if self._model is None:
            t = time.perf_counter()
            if self._factory is None:
                from faster_whisper import WhisperModel
                self._factory = WhisperModel
            self._model = self._factory(self.cfg["model_size"], device=self.cfg["device"],
                                        compute_type=self.cfg["compute_type"])
            self.load_s = time.perf_counter() - t
        return self._model

    def _is_prompt_echo(self, text: str) -> bool:
        """Whisper kadang hanya mengulang isi prompt saat audio hening atau tidak jelas."""
        if not self._prompt_words:
            return False
        return longest_common_run(_words(text), self._prompt_words) >= 4

    def transcribe(self, audio: str | Path | np.ndarray, sr: int = 16000) -> Transcript:
        model = self.load()
        if isinstance(audio, np.ndarray):
            audio_s = len(audio) / sr
            src = audio.astype(np.float32)
        else:
            src = str(audio)
            audio_s = 0.0

        t = time.perf_counter()
        prompt = self.cfg.get("initial_prompt") if self.cfg.get("use_prompt", True) else None
        segments, info = model.transcribe(src, language=self.cfg["language"], beam_size=self.cfg["beam_size"],
                                          vad_filter=self.cfg["vad_filter"], initial_prompt=prompt)
        max_ns = self.cfg.get("max_no_speech_prob", 0.6)
        kept = [s.text.strip() for s in segments if getattr(s, "no_speech_prob", 0.0) <= max_ns]
        elapsed = time.perf_counter() - t
        text = " ".join(k for k in kept if k).strip()
        audio_s = audio_s or float(getattr(info, "duration", 0.0) or 0.0)

        if len(text) < self.cfg.get("min_chars", 2):
            return Transcript("", True, elapsed, audio_s, "tidak ada ucapan")
        if self._is_prompt_echo(text):
            return Transcript("", True, elapsed, audio_s, "transkrip hanya mengulang prompt")
        return Transcript(text, False, elapsed, audio_s)
