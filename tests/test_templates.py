from datetime import date

import pytest

from sayit.response import templates as T


def test_uang_satu_lembar():
    assert T.to_plain_text(T.money_response({50000: 1})) == "Uang lima puluh ribu rupiah."


def test_uang_banyak_lembar():
    text = T.to_plain_text(T.money_response({10000: 1, 50000: 2}))
    assert text == ("Terdeteksi tiga lembar, dua lembar lima puluh ribu rupiah, "
                    "dan satu lembar sepuluh ribu rupiah. Totalnya seratus sepuluh ribu rupiah.")


def test_uang_tiga_nominal_hanya_dan_di_akhir():
    text = T.to_plain_text(T.money_response({1000: 1, 2000: 1, 100000: 1}))
    assert text.count(" dan ") == 1
    assert "Totalnya seratus tiga ribu rupiah." in text


def test_uang_kosong_dan_nominal_tidak_valid():
    assert T.money_response({}) == [T.Clip("tidak_ada_uang")]
    assert T.money_response({5000: 0}) == [T.Clip("tidak_ada_uang")]
    with pytest.raises(ValueError):
        T.money_response({75000: 1})


def test_kedaluwarsa_masih_berlaku():
    """Diubah 22-10: dulu "sisa tujuh puluh delapan hari". Angka harian sebesar
    itu tidak bisa dibayangkan siapa pun, apalagi tanpa melihat kalender."""
    text = T.to_plain_text(T.expiry_response(date(2026, 12, 3), date(2026, 9, 16)))
    assert text == ("Tanggal kedaluwarsa tiga Desember dua ribu dua puluh enam. "
                    "Produk masih berlaku, sisa sekitar tiga bulan.")


def test_kedaluwarsa_hari_ini_dan_lewat():
    assert "hari terakhir" in T.to_plain_text(T.expiry_response(date(2026, 9, 16), date(2026, 9, 16)))
    text = T.to_plain_text(T.expiry_response(date(2026, 9, 11), date(2026, 9, 16)))
    assert text.endswith("Produk sudah melewati tanggal kedaluwarsa sejak lima hari lalu.")


def test_kedaluwarsa_bulan_saja_dan_kurang_yakin():
    text = T.to_plain_text(T.expiry_response(date(2027, 12, 31), date(2026, 9, 16), month_only=True))
    assert text.startswith("Berlaku sampai Desember dua ribu dua puluh tujuh.")
    text = T.to_plain_text(T.expiry_response(date(2027, 1, 5), date(2026, 9, 16), confident=False))
    assert text.startswith("Saya kurang yakin, tetapi tanggal yang terbaca adalah lima Januari")


def test_semua_klip_yang_dipakai_templat_terdaftar():
    keys = set()
    for nominals in ([1000], [2000, 5000], [10000, 20000, 50000, 100000]):
        for n in range(1, 12):
            keys |= T.clip_keys(T.money_response({k: n for k in nominals}))
    for day in range(1, 29):
        for month in range(1, 13):
            keys |= T.clip_keys(T.expiry_response(date(2027, month, day), date(2026, 9, 16)))
            keys |= T.clip_keys(T.expiry_response(date(2025, month, day), date(2026, 9, 16), confident=False))
    keys |= T.clip_keys(T.document_chunk_response("x", has_more=True))
    assert keys <= set(T.CLIP_TEXTS), keys - set(T.CLIP_TEXTS)


def test_split_chunks():
    text = "Kalimat satu pendek. " * 5 + "Ini kalimat " + "sangat " * 50 + "panjang."
    chunks = T.split_chunks(text, max_words=10)
    assert all(len(c.split()) <= 10 for c in chunks)
    assert " ".join(chunks).split() == text.split()


def test_dokumen_dengan_lanjutan():
    utt = T.document_chunk_response("Halo.", has_more=True)
    assert T.to_plain_text(utt) == "Halo. Katakan lanjut untuk mendengar bagian berikutnya."


# --------------------------------------------------------------------------- satuan durasi

@pytest.mark.parametrize("hari,harap", [
    (0, "nol hari"), (1, "satu hari"), (6, "enam hari"),          # di bawah seminggu: tetap hari
    (7, "sekitar satu minggu"), (10, "sekitar satu minggu"), (45, "sekitar enam minggu"),
    (60, "sekitar dua bulan"), (140, "sekitar lima bulan"), (333, "sekitar sebelas bulan"),
    (365, "sekitar satu tahun"), (842, "sekitar dua tahun"),
])
def test_durasi_memakai_satuan_yang_bisa_dibayangkan(hari, harap):
    """"Tiga ratus tiga puluh tiga hari" tidak bisa dibayangkan siapa pun."""
    assert T.to_plain_text(T.durasi_clips(hari)).lower() == harap


def test_durasi_lampau_memakai_bentuk_lalu():
    assert T.to_plain_text(T.durasi_clips(3, lampau=True)).lower() == "tiga hari lalu"
    assert T.to_plain_text(T.durasi_clips(51, lampau=True)).lower() == "sekitar tujuh minggu lalu"


def test_pembulatan_tidak_pernah_menghasilkan_nol():
    for hari in (T.BATAS_MINGGU, T.BATAS_BULAN, T.BATAS_TAHUN):
        teks = T.to_plain_text(T.durasi_clips(hari)).lower()
        assert not teks.startswith("sekitar nol"), teks


def test_kata_sekitar_hanya_muncul_saat_dibulatkan():
    """Sistem tidak boleh terdengar lebih yakin daripada yang sebenarnya: angka
    hasil pembagian bukan tanggal pasti, dan pengguna tunanetra tidak punya cara
    lain memeriksanya."""
    assert "sekitar" not in T.to_plain_text(T.durasi_clips(5)).lower()
    assert "sekitar" in T.to_plain_text(T.durasi_clips(140)).lower()


def test_jawaban_kedaluwarsa_panjang_tidak_lagi_menyebut_ratusan_hari():
    teks = T.to_plain_text(T.expiry_response(date(2027, 3, 11), date(2026, 10, 22))).lower()
    assert "sekitar lima bulan" in teks
    assert "hari" not in teks.split("sisa")[-1]
