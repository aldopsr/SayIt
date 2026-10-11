"""Rekam, putar, dan siapkan audio lewat sounddevice."""
from __future__ import annotations

import numpy as np


def to_mono(audio: np.ndarray) -> np.ndarray:
    return audio.mean(axis=1) if audio.ndim == 2 else audio


def resample(audio: np.ndarray, sr_from: int, sr_to: int) -> np.ndarray:
    """Ubah laju sampel dengan interpolasi linear.

    Cukup untuk keperluan SayIt: menyamakan laju klip MP3 gTTS dan menyiapkan
    rekaman mikrofon untuk Whisper. Bukan resampler berkualitas tinggi.
    """
    if sr_from == sr_to or len(audio) == 0:
        return audio
    n = int(round(len(audio) * sr_to / sr_from))
    x_lama = np.linspace(0, 1, len(audio), endpoint=False)
    x_baru = np.linspace(0, 1, n, endpoint=False)
    return np.interp(x_baru, x_lama, audio).astype(np.float32)


def tone(hz: float, ms: int, sr: int, volume: float = 0.3) -> np.ndarray:
    t = np.arange(int(sr * ms / 1000)) / sr
    wave = np.sin(2 * np.pi * hz * t) * volume
    fade = min(len(wave) // 5, int(sr * 0.01))           # cegah bunyi "klik"
    if fade:
        ramp = np.linspace(0, 1, fade)
        wave[:fade] *= ramp
        wave[-fade:] *= ramp[::-1]
    return wave.astype(np.float32)


def play(audio: np.ndarray, sr: int, blocking: bool = True) -> None:
    import sounddevice as sd
    sd.play(audio, sr)
    if blocking:
        sd.wait()


def record(seconds: float, sr: int = 16000, beep: bool = True, beep_hz: int = 880,
           beep_ms: int = 150, gap_ms: int = 150) -> np.ndarray:
    """Rekam mono float32. Bip diputar dulu agar pengguna tahu kapan mulai bicara."""
    import sounddevice as sd
    if beep:
        play(np.concatenate([tone(beep_hz, beep_ms, sr), np.zeros(int(sr * gap_ms / 1000), np.float32)]), sr)
    audio = sd.rec(int(seconds * sr), samplerate=sr, channels=1, dtype="float32")
    sd.wait()
    return audio[:, 0]


def record_from_config(cfg: dict) -> np.ndarray:
    a = cfg["audio"]
    return record(a["record_seconds"], a["sample_rate"], a["beep_before_record"],
                  a["beep_hz"], a["beep_ms"], a["gap_after_beep_ms"])


def rms(audio: np.ndarray) -> float:
    return float(np.sqrt(np.mean(np.square(audio)))) if len(audio) else 0.0
