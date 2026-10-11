import pytest

from sayit.response.terbilang import NUMBER_WORDS, terbilang, terbilang_tokens


@pytest.mark.parametrize("n, expected", [
    (0, "nol"), (1, "satu"), (9, "sembilan"), (10, "sepuluh"), (11, "sebelas"), (12, "dua belas"),
    (19, "sembilan belas"), (20, "dua puluh"), (21, "dua puluh satu"), (78, "tujuh puluh delapan"),
    (100, "seratus"), (101, "seratus satu"), (110, "seratus sepuluh"), (115, "seratus lima belas"),
    (200, "dua ratus"), (999, "sembilan ratus sembilan puluh sembilan"),
    (1000, "seribu"), (1001, "seribu satu"), (2000, "dua ribu"), (5000, "lima ribu"),
    (10000, "sepuluh ribu"), (11000, "sebelas ribu"), (20000, "dua puluh ribu"),
    (50000, "lima puluh ribu"), (100000, "seratus ribu"), (110000, "seratus sepuluh ribu"),
    (185000, "seratus delapan puluh lima ribu"), (2026, "dua ribu dua puluh enam"),
    (1_000_000, "satu juta"), (1_250_000, "satu juta dua ratus lima puluh ribu"),
    (2_000_000_000, "dua miliar"),
])
def test_terbilang(n, expected):
    assert terbilang(n) == expected


def test_semua_token_ada_di_kosakata():
    for n in list(range(0, 3000)) + list(range(0, 2_000_001, 997)):
        assert set(terbilang_tokens(n)) <= set(NUMBER_WORDS), n


@pytest.mark.parametrize("bad", [-1, 10**12, 1.5, True])
def test_input_tidak_valid(bad):
    with pytest.raises((ValueError, TypeError)):
        terbilang_tokens(bad)
