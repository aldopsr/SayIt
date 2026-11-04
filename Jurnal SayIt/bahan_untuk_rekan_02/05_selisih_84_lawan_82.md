# 5. Penjelasan selisih data: 84 lawan 82

**Disusun 4 November 2026.**

## Jawaban singkat

**Tidak ada selisih.** Ketiga sumber yang kami pegang mencatat angka yang sama, yaitu
**82 kotak pada 81 foto**:

| Sumber | Foto | Kotak |
| :--- | ---: | ---: |
| Berkas label asli di laptop (`data/label_sendiri/test/labels/`, dihitung langsung) | 81 | **82** |
| `08_rekap_dataset.csv` baris `SEMUA` | 81 | **82** |
| `03_hasil_per_foto.csv`, jumlah kolom `lembar_benar` | 81 | **82** |

Keduanya memakai **versi dataset yang sama**. Buktinya bukan sekadar kesamaan jumlah:
saat menyusun pemetaan nama (bahan nomor 1), tiap foto dicocokkan satu per satu dan
**81 dari 81 cocok pada tiga penanda sekaligus** - nominal harapan, jumlah lembar, dan
ekstensi berkas. Kalau keduanya berasal dari versi dataset berbeda, kecocokan sempurna
pada tiga penanda itu tidak mungkin terjadi.

## Dari mana angka 84 kemungkinan berasal

Kami menyisir seluruh bahan jurnal dan lampiran. **Tidak ada satu pun berkas yang
menuliskan "84 kotak".** Satu-satunya angka 84 yang bermakna adalah:

> **84,0%** - ketepatan k-fold v2 sebelum alat ukurnya diperbaiki (lihat
> `02_status_pengujian_ulang.md`).

Angka itu **persentase ketepatan, bukan jumlah kotak**. Dugaan kami, 84,0% terbaca
sebagai jumlah objek di suatu tempat dalam draf.

Dua hal yang perlu ditegaskan tentang 84,0% itu sendiri:

1. **Angka itu sudah USANG.** Yang berlaku sekarang **90,1%** (73 benar / 8 salah /
   0 diam dari 81 foto). Kenaikannya bukan karena model - modelnya sama persis -
   melainkan karena evaluasi notebook tidak menjalankan penyaring `relative_score_min`
   yang dipakai aplikasi.
2. Jangan menuliskan 84,0% sebagai hasil, kecuali saat menjelaskan riwayat perbaikan
   alat ukur itu sendiri.

## Kalau angka 84 memang ada sumbernya

Kalau di drafmu ada berkas atau tabel yang benar-benar menuliskan 84 kotak,
**kirimkan nama berkas dan barisnya**. Kami akan telusuri. Kami sengaja tidak menebak
dari mana selisih dua kotak itu bisa muncul, karena menebak asal angka adalah persis
cara angka salah bertahan di laporan.

## Catatan: satu foto memang berisi dua kotak

Supaya tidak menjadi sumber kebingungan baru - selisih antara **81 foto** dan
**82 kotak** berasal dari satu foto:

| | |
| :--- | :--- |
| Nama evaluasi | `SENDIRI_01228.jpeg` |
| Isi | dua lembar Rp2.000 sungguhan, nomor seri berbeda |
| Status evaluasi | BENAR |

Itu satu-satunya foto banyak lembar yang berlabel, dan ia memang disengaja.
