# Keadaan "sesudah" — anotasi cacat sudah dikeluarkan

**Diperbaiki 9 November 2026.** Folder `sebelum/` sekarang benar-benar berisi keadaan
lama, bukan keadaan yang masih berlaku.

## Apa yang dilakukan

Foto `5000_dipegang_ (3).jpeg` **dikeluarkan dari dataset**, bukan dilabeli ulang.
Alasannya tidak berubah dari catatan sebelumnya: fotonya memuat lebih dari satu objek
uang dan jumlah lembar tumpukan Rp20.000 tidak dapat dihitung dari gambar, sehingga
melabeli ulang berarti menebak.

Gambar dan berkas labelnya dipindah ke `data/label_sendiri/_dikeluarkan/`.
**Gambarnya ikut dipindah, bukan hanya berkas `.txt`** — menghapus `.txt` saja sudah
pernah dicoba 23 Oktober 2026 dan gagal, karena berkasnya tersalin balik dari Google
Drive dan ikut melatih model v2 tanpa ketahuan.

Notebook memindai hanya `root/{train,valid,val,test}/images` dan tidak rekursif, jadi
folder `_dikeluarkan/` aman diabaikan.

## Keadaan dataset sebelum dan sesudah

| | Sebelum | Sesudah |
| :--- | ---: | ---: |
| Gambar | 81 | **80** |
| Berkas label | 81 | **80** |
| Kotak | 82 | **81** |
| Kotak kelas Rp5.000 | 21 | **20** |
| Label kosong | 0 | **0** |

Kelas lain tidak berubah: 1000:4, 2000:21, 10000:10, 20000:7, 50000:6, 100000:13.

## Satu ralat terhadap catatan sebelumnya

Catatan `sebelum/` menulis bahwa penilaian foto ini "tidak dapat ditelusuri karena nama
berkas tersalin tidak dapat dipetakan balik". **Itu sudah tidak benar.** Pemetaannya
ada di `01_pemetaan_nama.csv`:

    5000_dipegang_ (3).jpeg  ->  SENDIRI_01262.jpeg  ->  lipatan uji 2

Dan di `money_kfold_v2_kfold_totals.csv` baris `SENDIRI_01262.jpeg` tercatat **benar**.

Jadi batas pengaruhnya tidak lagi berupa rentang, melainkan satu angka pasti:

| Perlakuan | Hasil | Target 85% |
| :--- | :--- | :--- |
| Seperti dilaporkan di jurnal | 73 benar / 8 salah / 0 diam dari 81 = **90,1%** | tercapai |
| Foto ini dikeluarkan dari evaluasi | 72 / 8 / 0 dari 80 = **90,0%** | tercapai |
| Foto ini dipaksa dihitung salah | 72 / 9 / 0 dari 81 = **88,9%** | tercapai |

Kelas Rp5.000 bergerak dari 20/21 menjadi 19/20.

**Kesimpulan jurnal tidak berubah pada ketiga perlakuan.**

## Hasil latih ulang (10 November 2026) — SUDAH ADA

Notebook `04_money_kfold.ipynb` dijalankan ulang di Colab dengan `RUN_PREFIX =
'money_kfold_v3'`, dataset bersih 80 foto, `percaya_label`, `sendiri=True`,
`LATIH_MODEL_TERAKHIR = True`. Sidik lipatan `1b34f76a…`, `n_foto` 1.394.

Lipatan 0 sempat tercemar latihan yang terputus di CPU dan **dijalankan ulang bersih**;
lipatan 1-4 tidak berubah satu baris pun. Lihat baris 2026-11-10 di
`docs/keputusan-teknis.md`.

### Angka utama

| Pengukuran | Benar | Salah | Diam | n | Akurasi |
| :--- | ---: | ---: | ---: | ---: | ---: |
| v2, seperti dilaporkan jurnal | 73 | 8 | 0 | 81 | **90,1%** |
| v2, dasar sebanding (foto cacat dikeluarkan dari evaluasi) | 72 | 8 | 0 | 80 | **90,0%** |
| **v3, dataset bersih, latih ulang penuh, ambang 0,30** | **68** | **11** | **1** | **80** | **85,0%** |
| v3, ambang 0,15 / 0,20 / 0,25 (ketiganya identik) | 69 | 11 | 0 | 80 | **86,25%** |

Target PRD >= 85% **tetap tercapai**, tetapi tepat di garisnya pada ambang yang
dipakai aplikasi sekarang.

### Sapuan ambang v3 selengkapnya

| Ambang | Benar | Salah | Diam | Akurasi |
| ---: | ---: | ---: | ---: | ---: |
| 0,15 | 69 | 11 | 0 | 86,25% |
| 0,20 | 69 | 11 | 0 | 86,25% |
| 0,25 | 69 | 11 | 0 | 86,25% |
| 0,30 | 68 | 11 | 1 | 85,0% |
| 0,35 | 68 | 11 | 1 | 85,0% |
| 0,40 | 67 | 11 | 2 | 83,75% |
| 0,50 | 64 | 9 | 7 | 80,0% |
| 0,60 | 61 | 8 | 11 | 76,25% |

### Per lipatan

| Lipatan | Benar | Salah | Diam |
| ---: | ---: | ---: | ---: |
| 0 | 15 | 1 | 0 |
| 1 | 16 | 0 | 0 |
| 2 | 13 | 3 | 0 |
| 3 | 11 | 4 | 1 |
| 4 | 13 | 3 | 0 |

Sebaran antar lipatan lebar: lipatan 1 sempurna, lipatan 3 hanya 11 dari 16.

### Per nominal yang diharapkan

| Harapan | Benar | Salah | Diam | n |
| ---: | ---: | ---: | ---: | ---: |
| Rp1.000 | 3 | 1 | 0 | 4 |
| Rp2.000 | 15 | 4 | 0 | 19 |
| Rp4.000 (dua lembar Rp2.000) | 1 | 0 | 0 | 1 |
| Rp5.000 | 18 | 1 | 1 | 20 |
| Rp10.000 | 7 | 3 | 0 | 10 |
| Rp20.000 | 6 | 1 | 0 | 7 |
| Rp50.000 | 5 | 1 | 0 | 6 |
| Rp100.000 | 13 | 0 | 0 | 13 |

### Cara membaca selisih 90,0% lawan 85,0%

Mengeluarkan **satu** foto mengubah pembagian kelima lipatan sepenuhnya, jadi kedua
angka itu tidak diukur pada partisi yang sama. Sebagiannya variasi pembagian, bukan
kemunduran model — dan arah sebaliknya juga mungkin: 90,1% bisa jadi ujung atas yang
beruntung, bukan titik tengah.

Yang tidak bisa dibantah: dengan n = 80 dan sekitar sepuluh kesalahan, selisih 5 poin
berada dalam jangkauan variasi antar-run. **Akurasi modul uang karena itu lebih jujur
dilaporkan sebagai rentang 85-90% daripada satu angka presisi.** Itu temuan yang layak
masuk laporan, bukan kegagalan yang perlu disembunyikan.

### Lampiran mentah

- `docs/jurnal_bahan/v3/money_kfold_v3_kfold_totals.csv` (80 baris, per foto)
- `docs/jurnal_bahan/v3/money_kfold_v3_sapuan_ambang.csv`
- Di Drive: `money_kfold_v3_fold0..4/` dan `money_kfold_v3_final/`
  (confusion matrix, kurva PR/F1/P/R, `results.csv`)

**`01_pemetaan_nama.csv` dari v2 TIDAK berlaku untuk v3.** Nama `SENDIRI_*` diberikan
menurut urutan, jadi setelah satu foto dikeluarkan seluruh penomoran bergeser.
Pemetaan baru harus dibuat ulang bila dibutuhkan.

## Yang masih harus dikerjakan

1. Memutuskan apakah bobot `money_kfold_v3_final/weights/best.pt` (6.515.946 bita,
   optimizer sudah dibuang = latihan berakhir normal) menggantikan
   `models/best_money.pt` yang sekarang masih v2. Angka yang dilaporkan dan model
   yang dipakai sebaiknya berasal dari dataset yang sama — ketidakcocokan latih-pakai
   adalah persis jebakan CLAHE 28 Oktober.
2. Mencatat lisensi dataset Roboflow A dan B di Roboflow Universe sebelum jurnal
   disubmit. Belum dicek, jangan ditebak.
