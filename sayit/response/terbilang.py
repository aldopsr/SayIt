"""Konversi angka ke kata Bahasa Indonesia.

Keluarannya berupa daftar token kata (bukan satu string) agar setiap kata bisa
diputar dari klip suara yang sudah disimpan. Kosakata tokennya terbatas
(lihat NUMBER_WORDS), sehingga semua klip bisa dibuat sekali di awal.
"""
from __future__ import annotations

SATUAN = ["nol", "satu", "dua", "tiga", "empat", "lima", "enam", "tujuh", "delapan", "sembilan"]

NUMBER_WORDS = sorted(set(SATUAN) | {
    "sepuluh", "sebelas", "belas", "puluh", "seratus", "ratus", "seribu", "ribu", "juta", "miliar",
})

_MAX = 999_999_999_999


def _below_thousand(n: int) -> list[str]:
    assert 0 <= n < 1000
    words: list[str] = []
    ratus, sisa = divmod(n, 100)
    if ratus == 1:
        words.append("seratus")
    elif ratus > 1:
        words += [SATUAN[ratus], "ratus"]

    if sisa == 0:
        return words
    if sisa < 10:
        words.append(SATUAN[sisa])
    elif sisa == 10:
        words.append("sepuluh")
    elif sisa == 11:
        words.append("sebelas")
    elif sisa < 20:
        words += [SATUAN[sisa - 10], "belas"]
    else:
        puluh, satuan = divmod(sisa, 10)
        words += [SATUAN[puluh], "puluh"]
        if satuan:
            words.append(SATUAN[satuan])
    return words


def terbilang_tokens(n: int) -> list[str]:
    """Contoh: 110000 -> ['seratus', 'sepuluh', 'ribu']."""
    if not isinstance(n, int) or isinstance(n, bool):
        raise TypeError("n harus bilangan bulat")
    if n < 0 or n > _MAX:
        raise ValueError(f"n harus di antara 0 dan {_MAX}")
    if n == 0:
        return ["nol"]

    miliar, n = divmod(n, 1_000_000_000)
    juta, n = divmod(n, 1_000_000)
    ribu, sisa = divmod(n, 1000)

    words: list[str] = []
    if miliar:
        words += _below_thousand(miliar) + ["miliar"]
    if juta:
        words += _below_thousand(juta) + ["juta"]
    if ribu == 1:
        words.append("seribu")
    elif ribu:
        words += _below_thousand(ribu) + ["ribu"]
    if sisa:
        words += _below_thousand(sisa)
    return words


def terbilang(n: int) -> str:
    """Contoh: 110000 -> 'seratus sepuluh ribu'."""
    return " ".join(terbilang_tokens(n))
