# Bahan jurnal "Pengenalan Nominal Rupiah menggunakan YOLOv8n pada Aplikasi SayIt"

**Disusun 30 Oktober 2026.** Menjawab 14 permintaan bahan.

Semua angka di sini **terukur**. Yang tidak ada datanya ditulis **TIDAK TERSEDIA** dan
tidak diisi tebakan.

---

## Daftar isi dan status

| # | Bahan | Status | Letak |
| :--- | :--- | :--- | :--- |
| 1 | Anotasi cacat dan perbaikannya | **Sebagian** — "sebelum" ada, "sesudah" belum ada | `01_anotasi_cacat/` |
| 2 | Status pengujian ulang | **Lengkap** | `02_status_pengujian_ulang.md` |
| 3 | Hasil evaluasi per foto | **Lengkap** (81 baris) | `03_hasil_per_foto.csv` |
| 4 | Pembagian data lima lipatan | **Sebagian** — hanya subset test | `04_pembagian_lipatan.csv` |
| 5 | Konfigurasi pelatihan v2 | **Lengkap** (5 lipatan + final) | `05_konfigurasi_pelatihan/` |
| 6 | Log pelatihan v2 | **Lengkap** (5 lipatan + final) | `06_log_pelatihan/` |
| 7 | Sumber dan lisensi dataset | **Sebagian** — lisensi tidak tercatat | `07_sumber_lisensi_dataset.md` |
| 8 | Rekap dataset | **Sebagian** — hanya foto sendiri | `08_rekap_dataset.csv` |
| 9 | Penentuan ambang | **Lengkap** | `09_penentuan_ambang/` |
| 10 | Konfigurasi aplikasi | **Lengkap** | `10_konfigurasi_aplikasi/` |
| 11 | Perangkat dan versi pustaka | **Lengkap** | `11_perangkat_versi.md` |
| 12 | Grafik pelatihan terbaru | **Lengkap** (v2, 100 epoch) | `12_grafik_pelatihan/` |
| 13 | Contoh prediksi | **Lengkap, dengan syarat** | `13_contoh_prediksi/` |
| 14 | Bukti keluaran suara | **Sebagian** — audio ada, video belum | `14_bukti_suara/` |

---

## Yang TIDAK TERSEDIA, dan sebabnya

Empat hal berikut tidak bisa dilengkapi tanpa menjalankan ulang notebook di Colab atau
tanpa data yang memang tidak pernah dicatat.

1. **Nama berkas asal tiap foto evaluasi.** Notebook menyalin setiap foto dengan nama
   baru berpola `SENDIRI_0xxxx`, dan penomorannya mengikuti urutan pembacaan direktori.
   Pemetaan baliknya tidak disimpan. Akibatnya kolom `nama_foto_asal` dan
   `kelompok_kemiripan` pada bahan nomor 4 kosong.
2. **Pembagian train/validation untuk 1.314 gambar bukan foto sendiri.** Yang tercatat
   hanya subset *test*, karena hanya itu yang masuk berkas hasil.
3. **Lisensi dan tanggal unduh dataset publik.** Tidak pernah dicatat saat mengunduh.
4. **Perincian 1.314 gambar** ke dataset publik kedua dan gambar latar COCO128.

Ketiga hal pertama bisa diadakan dengan menjalankan ulang notebook dan menyimpan manifest
sebelum pelatihan. Yang keempat perlu membuka kembali sumber dataset di Roboflow.

---

## Tiga hal yang perlu dipahami sebelum memakai angkanya

### A. Angka resmi penelitian adalah 90,1%, bukan 97,5%

| Angka | Dari mana | Boleh dipakai? |
| :--- | :--- | :--- |
| **90,1%** (73 benar / 8 salah / 0 diam dari 81 foto) | Validasi silang lima lipatan. Tiap foto diuji oleh model yang **belum pernah melihatnya** | **Ya — ini hasil utama** |
| 97,5% (79 / 2 / 0 dari 81 foto) | Model akhir diuji pada foto yang **ikut melatihnya** | Tidak sebagai bukti generalisasi |
| mAP50 0,9751 | Split validasi **data publik**, bukan foto sendiri | Tidak sebagai akurasi sistem |

Bahan nomor 13 (contoh prediksi) berasal dari **model akhir pada foto pelatihannya**,
jadi termasuk kategori kedua. Dipakai untuk memperlihatkan bentuk keluaran, bukan untuk
mengklaim akurasi.

### B. Metrik yang dipakai adalah ketepatan TOTAL, bukan mAP

Yang dinilai adalah **apakah jumlah rupiah yang diucapkan ke pengguna benar**. Satu
lembar Rp100.000 yang terdeteksi dua kali tetap benar menurut metrik kelas, tetapi
diucapkan "dua ratus ribu rupiah" — dan itulah yang dialami pengguna.

Kategori **benar / salah / diam** dilaporkan terpisah dan saling eksklusif. Bagi pengguna
tunanetra, nominal yang **salah** jauh lebih berbahaya daripada sistem yang **diam**,
karena ia tidak punya cara memeriksanya.

### C. Satu anotasi cacat ikut terpakai dan belum diperbaiki

Rinciannya di bahan nomor 1 dan 2. Ringkasnya: satu dari 81 foto punya anotasi yang
tidak lengkap dan kotaknya hampir sebesar bingkai. Foto itu **ikut melatih dan ikut
menguji** model v2.

Batas pengaruhnya dapat dinyatakan: bila foto itu dikeluarkan, ketepatan menjadi
**72/80 (90,0%) atau 73/80 (91,25%)**, bergantung pada apakah foto itu semula dinilai
benar. Penilaiannya sendiri tidak dapat ditelusuri karena alasan nomor 1 di atas.

---

## Catatan privasi

Foto `5000_dipegang_ (3).jpeg` memuat **dua orang di latar belakang**. Salinan yang
disertakan di sini sudah **disamarkan wajahnya**. Berkas asli yang tidak disamarkan ada
di dataset dan **jangan dilampirkan ke naskah jurnal**.

Periksa juga foto lain sebelum dipublikasikan: dataset ini dipotret di tempat umum dan
sebagian memuat orang atau layar laptop berisi aplikasi lain.
