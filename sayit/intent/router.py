"""Intent router berbasis kata kunci berbobot (PRD 8.5).

Aturan (hasil perbaikan dari simulasi Fase 0):
1. Normalisasi: huruf kecil, tanda baca dibuang.
2. Akhiran -nya/-kah/-lah dipotong saat mencocokkan ("dokumennya" -> "dokumen").
3. Dua kata berurutan juga dicoba sebagai satu kata ("di minum" -> "diminum").
4. Fuzzy matching hanya untuk kata kunci >= fuzzy_min_len huruf. Kata pendek wajib persis,
   karena "uang" dan "ulang" terlalu mirip.
5. Intent kendali (ulangi, lanjut, foto baru, bantuan) hanya dicocokkan persis, dan hanya
   dipakai jika tidak ada intent tugas yang mencapai skor minimum.
6. Skor tertinggi menang; seri diputus dengan prioritas KEDALUWARSA > UANG > BACA.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from rapidfuzz import fuzz

from sayit.intent import keywords as K

_PUNCT = re.compile(r"[^\w\s]")
_SPACE = re.compile(r"\s+")


@dataclass
class RouteResult:
    intent: str
    text: str
    scores: dict[str, int]
    matched: dict[str, list[str]] = field(default_factory=dict)


def normalize(text: str) -> list[str]:
    text = _SPACE.sub(" ", _PUNCT.sub(" ", (text or "").lower())).strip()
    return text.split() if text else []


def _strip_suffix(word: str) -> str:
    for s in K.SUFFIXES:
        if word.endswith(s) and len(word) - len(s) >= 4:
            return word[: -len(s)]
    return word


class IntentRouter:
    def __init__(self, min_score: int = 2, fuzzy_min_len: int = 6, fuzzy_threshold: int = 85,
                 keywords: dict[str, dict[str, int]] | None = None):
        self.min_score = min_score
        self.fuzzy_min_len = fuzzy_min_len
        self.fuzzy_threshold = fuzzy_threshold
        self.keywords = keywords or K.KEYWORDS

    @classmethod
    def from_config(cls, cfg: dict) -> "IntentRouter":
        r = cfg.get("router", {})
        return cls(min_score=r.get("min_score", 2), fuzzy_min_len=r.get("fuzzy_min_len", 6),
                   fuzzy_threshold=r.get("fuzzy_threshold", 85))

    # ------------------------------------------------------------------ pencocokan

    def _word_match(self, word: str, kw: str, allow_fuzzy: bool) -> bool:
        base = _strip_suffix(word)
        if word == kw or base == kw:
            return True
        if not allow_fuzzy or len(kw) < self.fuzzy_min_len or len(word) < self.fuzzy_min_len - 1:
            return False
        return (fuzz.ratio(base, kw) >= self.fuzzy_threshold
                or fuzz.ratio(word, kw) >= self.fuzzy_threshold)

    def _phrase_match(self, words: list[str], phrase: str, allow_fuzzy: bool) -> bool:
        parts = phrase.split()
        n = len(parts)
        for i in range(len(words) - n + 1):
            if all(self._word_match(words[i + j], parts[j], allow_fuzzy) for j in range(n)):
                return True
        return False

    # ------------------------------------------------------------------ routing

    def route(self, text: str) -> RouteResult:
        words = normalize(text)
        # kandidat tambahan: gabungan dua kata berurutan
        joined = [words[i] + words[i + 1] for i in range(len(words) - 1)]
        candidates = words + joined

        scores: dict[str, int] = {}
        matched: dict[str, list[str]] = {}
        for intent, kws in self.keywords.items():
            allow_fuzzy = intent not in K.CONTROL_INTENTS
            pool = words if intent in K.CONTROL_INTENTS else candidates
            hits = [kw for kw in kws if self._phrase_match(pool, kw, allow_fuzzy)]
            scores[intent] = sum(kws[kw] for kw in hits)
            if hits:
                matched[intent] = hits

        clean = " ".join(words)
        task_best = max(scores.get(i, 0) for i in K.TASK_INTENTS)

        if task_best < self.min_score:
            ctrl = max(K.CONTROL_INTENTS, key=lambda i: scores.get(i, 0))
            if scores.get(ctrl, 0) >= self.min_score:
                return RouteResult(ctrl, clean, scores, matched)
            return RouteResult(K.TIDAK_DIKENALI, clean, scores, matched)
        intent = next(i for i in K.TASK_INTENTS if scores.get(i, 0) == task_best)
        return RouteResult(intent, clean, scores, matched)
