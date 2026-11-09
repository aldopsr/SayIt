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

## Yang masih harus dikerjakan

Angka-angka di atas hanya memperbaiki **sisi evaluasi**. Foto ini tetap ikut melatih
model pada empat dari lima lipatan, dan efeknya terhadap prediksi foto lain tidak dapat
diukur tanpa melatih ulang.

Langkahnya:

1. Unggah ulang `data/label_sendiri/` ke Google Drive, **dan pastikan
   `test/images/5000_dipegang_ (3).jpeg` benar-benar hilang di sana** — bukan hanya di laptop.
2. Jalankan ulang `notebooks/04_money_kfold.ipynb` (`LATIH_MODEL_TERAKHIR = True` bila
   model aplikasi ikut diperbarui).
3. Ukur ulang, lalu perbarui seluruh lampiran: metrik per kelas, confusion matrix,
   kurva PR/F1, sapuan ambang, tabel lipatan.

Setelah dilatih ulang, dataset menjadi **80 foto**, sehingga angka ketepatannya tidak
lagi dapat dibandingkan langsung dengan 90,1% yang dihitung atas 81 foto.
