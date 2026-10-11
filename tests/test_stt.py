from types import SimpleNamespace

import numpy as np

from sayit.audio.stt import Transcriber, longest_common_run
from sayit.config import load_config

CFG = load_config()


class FakeModel:
    def __init__(self, segments):
        self.segments = segments
        self.calls = []

    def transcribe(self, audio, **kwargs):
        self.calls.append(kwargs)
        return (s for s in self.segments), SimpleNamespace(duration=4.0)


def make(segments):
    model = FakeModel(segments)
    return Transcriber(CFG, model_factory=lambda *a, **k: model), model


def seg(text, nsp=0.1):
    return SimpleNamespace(text=text, no_speech_prob=nsp)


def test_transkrip_normal_dan_parameter():
    tr, model = make([seg(" berapa nominal"), seg(" uang ini?")])
    out = tr.transcribe(np.zeros(16000, np.float32))
    assert out.text == "berapa nominal uang ini?" and not out.empty
    assert out.audio_s == 1.0
    kw = model.calls[0]
    assert kw["language"] == "id" and kw["vad_filter"] is True and kw["initial_prompt"]


def test_segmen_tanpa_suara_dibuang():
    tr, _ = make([seg("uang", 0.9), seg("", 0.1)])
    out = tr.transcribe("x.wav")
    assert out.empty and out.reason == "tidak ada ucapan"


def test_halusinasi_prompt_dianggap_kosong():
    tr, _ = make([seg("uang, rupiah, nominal, kembalian, baca")])
    out = tr.transcribe("x.wav")
    assert out.empty and "prompt" in out.reason


def test_sisipan_prompt_pendek_tidak_dibuang():
    # kasus asli Fase 0: satu kata "uang" tersisip, kalimat tetap dipakai
    tr, _ = make([seg("uang, bacakan, tulisan, di kertas, ini")])
    assert not tr.transcribe("x.wav").empty


def test_tanpa_prompt():
    cfg = {**CFG, "stt": {**CFG["stt"], "use_prompt": False}}
    model = FakeModel([seg("halo")])
    Transcriber(cfg, model_factory=lambda *a, **k: model).transcribe("x.wav")
    assert model.calls[0]["initial_prompt"] is None


def test_longest_common_run():
    assert longest_common_run("a b c d".split(), "x b c d y".split()) == 3
    assert longest_common_run([], ["a"]) == 0
