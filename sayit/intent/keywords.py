"""Kata kunci per intent (PRD 8.5, diperbarui dengan temuan Fase 0).

Bobot 2 = kata kunci kuat, bobot 1 = kata kunci lemah.
Frasa boleh terdiri dari beberapa kata dan dicocokkan berurutan.
"""
from __future__ import annotations

UANG = "UANG"
BACA = "BACA"
KEDALUWARSA = "KEDALUWARSA"
ULANGI = "ULANGI"
LANJUT = "LANJUT"
FOTO_BARU = "FOTO_BARU"
KELUAR = "KELUAR"
PUTAR_KAMERA = "PUTAR_KAMERA"
PILIH_BERKAS = "PILIH_BERKAS"
SENTER_NYALA = "SENTER_NYALA"
SENTER_MATI = "SENTER_MATI"
BANTUAN = "BANTUAN"
TIDAK_DIKENALI = "TIDAK_DIKENALI"

# Urutan prioritas jika skor seri (PRD 8.5 aturan 3)
TASK_INTENTS = [KEDALUWARSA, UANG, BACA]
CONTROL_INTENTS = [ULANGI, LANJUT, FOTO_BARU, KELUAR, PUTAR_KAMERA, PILIH_BERKAS,
                   # SENTER_MATI sebelum SENTER_NYALA: lihat catatan bobot di KEYWORDS
                   SENTER_MATI, SENTER_NYALA, BANTUAN]

KEYWORDS: dict[str, dict[str, int]] = {
    KEDALUWARSA: {
        "kedaluwarsa": 2, "kadaluarsa": 2, "kadaluwarsa": 2, "kedaluarsa": 2,
        "expired": 2, "ekspayer": 2, "exp": 2, "best before": 2, "sampai kapan": 2,
        "basi": 2, "masih layak": 2,
        "tanggal": 1, "masih bisa dimakan": 1, "masih bisa diminum": 1,
    },
    UANG: {
        "uang": 2, "duit": 2, "nominal": 2, "rupiah": 2, "kembalian": 2, "pecahan": 2,
        "berapa": 1, "lembar": 1, "ribu": 1,
    },
    BACA: {
        "bacakan": 2, "tulisan": 2, "dokumen": 2, "surat": 2, "teks": 2, "membaca": 2, "tertulis": 2,
        "baca": 1, "isi": 1, "kertas": 1,
    },
    # Intent kendali: hanya dicocokkan persis (tanpa fuzzy), karena kata pendek mudah tertukar
    ULANGI: {"ulangi": 2, "sekali lagi": 2, "apa tadi": 2, "ulang lagi": 2},
    LANJUT: {"lanjut": 2, "lanjutkan": 2, "berikutnya": 2, "selanjutnya": 2},
    FOTO_BARU: {"foto lagi": 2, "foto ulang": 2, "ambil ulang": 2, "foto baru": 2, "ambil foto lagi": 2},
    # "sudah" sengaja TIDAK dipakai: terlalu lazim muncul di kalimat lain.
    KELUAR: {"keluar": 2, "selesai": 2, "tutup": 2, "berhenti": 2, "sudah cukup": 2},
    # Kendali tombol layar kamera. Pengguna tunanetra tidak bisa mencari tombolnya,
    # jadi tiap tombol harus bisa dipanggil dengan suara.
    # "putar" sendirian TIDAK dipakai: terlalu umum ("putar lagu", "putar balik").
    PUTAR_KAMERA: {"putar kamera": 2, "ganti kamera": 2, "balik kamera": 2, "tukar kamera": 2,
                   "kamera depan": 2, "kamera belakang": 2, "kamera lain": 2},
    # "galeri" dan "berkas" cukup khas, tetapi "file" sengaja ditulis dua ejaan
    # karena STT Indonesia sering menuliskannya sebagai "fail".
    PILIH_BERKAS: {"pilih berkas": 2, "pilih file": 2, "pilih fail": 2, "dari galeri": 2,
                   "buka galeri": 2, "ambil dari galeri": 2, "unggah": 2, "upload": 2},
    # Senter dipisah menjadi DUA intent, bukan satu toggle. Toggle akan menyalakan
    # senter ketika pengguna berkata "matikan senter" dalam keadaan sudah mati -
    # dan pengguna tunanetra tidak bisa melihat keadaan nyala atau matinya, jadi
    # kesalahan itu tidak akan pernah ia sadari. Dua intent membuat maksudnya pasti.
    # "senter" dan "flash" sendirian diarahkan ke NYALA: itu maksud yang jauh lebih
    # sering. "lampu" sendirian TIDAK dipakai - terlalu umum ("lampu kamar mati").
    SENTER_NYALA: {"nyalakan senter": 2, "hidupkan senter": 2, "senter nyala": 2, "senter on": 2,
                   "nyalakan lampu": 2, "hidupkan lampu": 2, "nyalakan flash": 2,
                   "nyalakan blitz": 2, "nyalakan lampu kamera": 2, "kasih cahaya": 2,
                   "senter": 2, "flash": 2, "blitz": 2},
    # Bobot 3, bukan 2, DAN urutannya di depan SENTER_NYALA di CONTROL_INTENTS.
    # Keduanya diperlukan: "matikan senter" memuat kata "senter" yang juga kata kunci
    # SENTER_NYALA, jadi pada bobot sama skornya SERI dan pemenangnya ditentukan urutan.
    # Terukur sebelum diperbaiki: "matikan senter" dan "senternya matikan" keduanya
    # terbaca SENTER_NYALA - yaitu menyalakan senter ketika pengguna minta dimatikan,
    # dan pengguna tunanetra tidak akan pernah menyadarinya.
    SENTER_MATI: {"matikan senter": 3, "senter mati": 3, "senter off": 3, "matikan lampu": 3,
                  "matikan flash": 3, "matikan blitz": 3, "matikan lampu kamera": 3,
                  "senternya matikan": 3, "senternya mati": 3, "sudah terang": 3},
    # "apa itu sayit" adalah pintu bantuan yang diumumkan sambutan, jadi ejaannya
    # harus longgar: STT menulis nama aplikasi ini bermacam-macam.
    # BANTUAN paling butuh toleransi justru karena isinya NAMA APLIKASI, yang
    # tidak ada di kamus Whisper. Diukur 22-10: 10 dari 15 ucapan wajar gagal.
    # Melonggarkannya aman - salah memicu BANTUAN hanya membacakan satu kalimat,
    # tidak seperti KELUAR yang menutup aplikasi atau FOTO_BARU yang membuang foto.
    BANTUAN: {"bantuan": 2, "bisa apa": 2, "bantu apa": 2, "cara pakai": 2, "cara menggunakan": 2,
              "belum paham": 2, "tidak paham": 2, "kurang paham": 2,
              # ejaan nama aplikasi yang keluar dari STT
              "apa itu sayit": 2, "apa itu say it": 2, "apa itu sai it": 2, "apa itu seyit": 2,
              "apa itu sait": 2, "apa itu sayid": 2, "apa itu sae it": 2, "apa itu seit": 2,
              "apa itu cyit": 2, "apa itu sayit itu": 2,
              # susunan kalimat lain yang sama maksudnya
              "sayit itu apa": 2, "say it itu apa": 2, "apa sih sayit": 2,
              "apa itu aplikasi ini": 2, "ini aplikasi apa": 2, "aplikasi apa ini": 2,
              "aplikasi ini buat apa": 2, "aplikasi ini untuk apa": 2,
              "fitur apa saja": 2, "ada fitur apa": 2, "kamu bisa apa": 2, "siapa kamu": 2},
}

SUFFIXES = ("nya", "kah", "lah")
