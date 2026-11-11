"""Tes API web: antrean dan pemanasan TTS.

Dua hal yang diuji di sini sama-sama soal AKSESIBILITAS, bukan performa:

1. **Antrean.** Satu `Pipeline` dipakai bersama di belakang satu kunci, jadi
   permintaan kedua menunggu. `with kunci` tanpa batas membuat penantian itu
   berupa DIAM, dan bagi pengguna tunanetra diam tidak bisa dibedakan dari
   server mati. Di atas batas tunggu harus ada jawaban yang BERBUNYI.
2. **Pemanasan TTS.** Sintesis pertama edge-tts ~9 detik karena membangun sesi.
   Bila server start tanpa internet, pemanasan gagal dan 9 detik itu jatuh
   tepat di pembacaan dokumen pertama pengguna.

Model tidak dimuat: `server.app` hanya membangun objeknya (0,8 detik), sedangkan
`Pipeline.load()` berjalan di event startup yang tidak dipicu di sini.
"""
from __future__ import annotations

import inspect
import threading

import pytest

from server import app as A


# --------------------------------------------------------------------- antrean

def test_antre_berhasil_dan_melepas_kunci():
    with A.antre():
        assert A.kunci.locked()
    assert not A.kunci.locked()


def test_antre_melepas_kunci_walau_isinya_gagal():
    """Kunci yang tidak dilepas akan mematikan server untuk SEMUA pengguna,
    jadi pelepasannya tidak boleh bergantung pada jalur yang mulus."""
    with pytest.raises(ZeroDivisionError):
        with A.antre():
            1 / 0
    assert not A.kunci.locked()


def test_antre_menyerah_jadi_sibuk_saat_kunci_dipegang(monkeypatch):
    monkeypatch.setitem(A.cfg["server"], "antre_timeout_s", 0.05)
    A.kunci.acquire()
    try:
        with pytest.raises(A.Sibuk):
            with A.antre():
                pytest.fail("tidak boleh masuk: kunci sedang dipegang")
    finally:
        A.kunci.release()


def test_antre_tetap_menunggu_di_bawah_batas():
    """Permintaan cepat (uang 1,4 detik) harus tetap lolos mengantre, bukan ditolak."""
    A.kunci.acquire()
    threading.Timer(0.05, A.kunci.release).start()
    with A.antre():                 # batas bawaan 1,5 detik > 0,05 detik
        pass
    assert not A.kunci.locked()


def test_jaga_antrean_menjawab_dengan_klip_berbunyi(monkeypatch):
    """Jawaban sibuk wajib punya audio, bukan hanya teks - itu aturan proyek."""
    monkeypatch.setattr(A, "_galat", lambda klip: {"error": A.CLIP_TEXTS[klip], "audio": "x"})

    @A.jaga_antrean
    def sibuk():
        raise A.Sibuk

    hasil = sibuk()
    assert hasil["audio"]                            # berbunyi
    assert "tanyakan lagi" in hasil["error"]         # menyebut tindakan berikutnya


def test_klip_sibuk_terdaftar_dan_menyebut_tindakan():
    teks = A.CLIP_TEXTS["server_sibuk"]
    assert "tunggu" in teks.lower()
    assert teks.rstrip().endswith(".")


# ------------------------------------------------------------- pemanasan TTS

class _Penyuara:
    """Gagal `gagal_dulu` kali, lalu berhasil. Meniru start tanpa internet."""

    def __init__(self, gagal_dulu: int):
        self.gagal_dulu = gagal_dulu
        self.panggilan = 0

    def warmup(self) -> bool:
        self.panggilan += 1
        return self.panggilan > self.gagal_dulu


def test_hangatkan_berhasil_setelah_beberapa_percobaan():
    p, tidur = _Penyuara(gagal_dulu=2), []
    assert A._hangatkan(p, threading.Lock(), coba=5, jeda_s=30, tidur=tidur.append)
    assert p.panggilan == 3
    assert tidur == [30, 30]        # tidur hanya DI ANTARA percobaan


def test_hangatkan_menyerah_dan_tidak_tidur_setelah_percobaan_terakhir():
    p, tidur = _Penyuara(gagal_dulu=99), []
    assert not A._hangatkan(p, threading.Lock(), coba=3, jeda_s=5, tidur=tidur.append)
    assert p.panggilan == 3
    assert len(tidur) == 2          # bukan 3: menyerah tanpa tidur sia-sia


def test_hangatkan_memegang_kunci_saat_mencoba():
    """Pemanasan yang berjalan bersamaan dengan permintaan pengguna membuat
    keduanya membangun sesi edge-tts sendiri; kuncinya yang mencegah itu."""
    kunci, terlihat = threading.Lock(), []

    class _Pencatat(_Penyuara):
        def warmup(self):
            terlihat.append(kunci.locked())
            return super().warmup()

    A._hangatkan(_Pencatat(gagal_dulu=0), kunci, coba=1, jeda_s=0, tidur=lambda _: None)
    assert terlihat == [True]
    assert not kunci.locked()


def test_endpoint_berat_sinkron_bukan_async():
    """Penjaga regresi. `async def` menjalankan kerja blocking di event loop,
    sehingga SELURUH server membeku: terukur `GET /sehat` 6,57 detik saat satu
    dokumen dibaca, dan permintaan kedua belum diterima sehingga klip
    "server_sibuk" mustahil terkirim. Jangan dikembalikan ke `async def`.
    """
    for fn in (A.unggah_foto, A.unggah_berkas, A.tanya):
        asli = inspect.unwrap(fn)
        assert not inspect.iscoroutinefunction(asli), f"{fn.__name__} jangan async def"
