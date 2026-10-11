import numpy as np
import pytest
import soundfile as sf

from sayit.audio import tts as TTS
from sayit.config import load_config
from sayit.response import templates as T

SR = 24000


def fake_synth(calls):
    def synth(text, path, **kwargs):
        calls.append(text)
        path.parent.mkdir(parents=True, exist_ok=True)
        tone = (np.sin(np.linspace(0, 300, SR // 4)) * 0.3).astype(np.float32)
        sf.write(str(path), np.concatenate([np.zeros(2400, np.float32), tone, np.zeros(2400, np.float32)]),
                 SR, format="MP3")
    return synth


@pytest.fixture
def cfg(tmp_path):
    base = load_config()
    return {**base, "tts": {**base["tts"], "cache_dir": str(tmp_path / "tts")}}


def test_render_uang_membuat_klip_saat_online(cfg):
    calls = []
    r = TTS.SpeechRenderer(cfg, online=True, synth=fake_synth(calls))
    audio, sr = r.render(T.money_response({50000: 1}))
    assert sr == SR and audio.dtype == np.float32 and len(audio) > SR // 2
    assert calls == ["Uang", "lima", "puluh", "ribu", "rupiah"]
    # render kedua memakai klip yang sudah ada, tanpa sintesis baru
    r.render(T.money_response({50000: 1}))
    assert len(calls) == 5


def test_offline_memakai_klip_tersimpan(cfg):
    TTS.SpeechRenderer(cfg, online=True, synth=fake_synth([])).render(T.money_response({50000: 1}))
    calls = []
    audio, _ = TTS.SpeechRenderer(cfg, online=False, synth=fake_synth(calls)).render(T.money_response({50000: 1}))
    assert calls == [] and len(audio) > 0


def test_offline_klip_belum_ada_error(cfg):
    r = TTS.SpeechRenderer(cfg, online=False, synth=fake_synth([]))
    with pytest.raises(TTS.MissingClipError):
        r.render(T.fixed("foto_diambil"))


def test_teks_dinamis_offline_diganti_pesan_butuh_internet(cfg):
    TTS.SpeechRenderer(cfg, online=True, synth=fake_synth([])).ensure_clip("butuh_internet")
    calls = []
    r = TTS.SpeechRenderer(cfg, online=False, synth=fake_synth(calls))
    audio, _ = r.render([T.Text("isi surat rahasia")])
    assert calls == [] and len(audio) > 0


def test_teks_dinamis_online_tidak_disimpan(cfg, tmp_path):
    calls = []
    r = TTS.SpeechRenderer(cfg, online=True, synth=fake_synth(calls))
    r.render([T.Text("isi surat rahasia")])
    assert calls == ["isi surat rahasia"]
    assert not any(p.suffix == ".mp3" for p in tmp_path.rglob("*"))


def test_jeda_dan_simpan_wav(cfg, tmp_path):
    r = TTS.SpeechRenderer(cfg, online=True, synth=fake_synth([]))
    audio, _ = r.render([T.Pause("long")])
    assert len(audio) == int(SR * cfg["tts"]["pause_long_ms"] / 1000) and not audio.any()
    out = r.save_wav(T.money_response({1000: 2}), tmp_path / "out.wav")
    data, sr = sf.read(str(out))
    assert sr == SR and len(data) > 0


def test_resample_dan_trim():
    x = np.ones(1000, np.float32)
    assert len(TTS._resample(x, 16000, 24000)) == 1500
    y = np.concatenate([np.zeros(5000), np.ones(100), np.zeros(5000)]).astype(np.float32)
    assert len(TTS._trim_silence(y, SR)) < 2000
