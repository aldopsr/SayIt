# 14. Bukti keluaran suara

## Isi

Tiga berkas WAV berisi jawaban yang **benar-benar dihasilkan sistem**, bukan ilustrasi
antarmuka. Masing-masing disertai foto masukannya.

| Berkas | Harapan | Diucapkan | Status |
| :--- | ---: | ---: | :--- |
| `100000_dipegang_ (2)__diucapkan.wav` | Rp100.000 | Rp100.000 | BENAR |
| `20000_dipegang_1__diucapkan.wav` | Rp20.000 | Rp20.000 | BENAR |
| `100000_dipegang_ (4)__diucapkan.wav` | Rp100.000 | **Rp101.000** | **SALAH** |

Contoh ketiga sengaja disertakan. Sistem mendeteksi satu lembar Rp100.000 **dan** satu
deteksi tambahan Rp1.000, lalu menjumlahkannya. Pengguna mendengar "seratus satu ribu
rupiah" dengan nada seyakin jawaban yang benar — inilah bentuk kegagalan yang paling
berbahaya bagi pengguna tunanetra, dan karena itu layak ditampilkan apa adanya.

Perhatikan durasinya: jawaban benar 3,4 dan 3,7 detik, sedangkan jawaban salah 14,7
detik karena harus menyebutkan rincian dua jenis lembar beserta totalnya.

## Cara berkas ini dibuat

Keluaran deteksi dialirkan ke fungsi ujaran aplikasi, lalu dirender memakai klip suara
tersimpan (mode luring). Jalurnya sama persis dengan yang didengar pengguna di aplikasi.

Jawaban nominal, jumlah lembar, dan total memakai **klip MP3 tersimpan** sehingga tidak
memerlukan internet. Hanya pembacaan teks dokumen yang memakai gTTS daring, dan itu di
luar lingkup modul uang.

## Yang belum ada

**Video demonstrasi (MP4) belum dibuat.** Merekam video memerlukan orang yang
mengoperasikan aplikasi, memotret, dan berbicara ke mikrofon, jadi belum dapat
disertakan di sini.

---

## Catatan tambahan untuk contoh ketiga

Berkas `100000_dipegang_ (4)__diucapkan.wav` dihasilkan dari **foto asli yang belum
disamarkan**, sehingga isinya benar-benar jawaban salah yang terjadi (Rp101.000).

Foto masukan yang disertakan di folder ini sudah **disamarkan bagian layarnya** untuk
privasi. Jadi bila foto tersebut dideteksi ulang, hasilnya akan berbeda (Rp100.000,
benar) — justru karena penyebab kesalahannya ikut tertutup.

Rinciannya di `../13_contoh_prediksi/BACA_DULU.md`.
