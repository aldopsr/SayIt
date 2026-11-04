# Bahan jurnal SayIt - permintaan kedua

**Disusun 4 November 2026.** Menjawab 5 permintaan.

Semua angka terukur. Yang tidak ada datanya ditulis **TIDAK TERSEDIA** dan tidak diisi
tebakan.

---

## Status tiap permintaan

| # | Permintaan | Status | Berkas |
| :--- | :--- | :--- | :--- |
| 1 | Pemetaan nama foto | **Lengkap untuk nama evaluasi**, nama kamera tidak tersedia | `01_pemetaan_nama.csv` |
| 2 | Pembagian tiap lipatan | **Lengkap untuk foto sendiri**, kelompok kemiripan dan data publik tidak tersedia | `02_pembagian_lipatan.csv` |
| 3 | Label foto evaluasi | **Lengkap** (81 label, dua penamaan) | `03_label_evaluasi.zip` |
| 4 | Foto beranotasi cacat | **Sebagian** - "sebelum" ada, "sesudah" **belum ada** | `04_anotasi_cacat/` |
| 5 | Penjelasan selisih data | **Lengkap** | `05_selisih_84_lawan_82.md` |

---

## 1. Pemetaan nama - bagaimana ini diperoleh

**81 baris, lengkap.** Kolom `nama_evaluasi` (`SENDIRI_01194.jpeg` dan seterusnya)
dipasangkan dengan `nama_lokal` (`100000_dipegang_ (2).jpeg` dan seterusnya).

Pemetaan ini **bukan dugaan**. Dua bukti yang saling menguatkan:

1. **Kodenya sendiri.** Notebook sel 24 menamai berkas salinan dengan
   `stem = f"{r['dataset']}_{i:05d}"`, yaitu nomor urut dalam daftar `records`.
   Daftar itu diisi lewat `image_files()` yang membaca `sorted(d.iterdir())`.
   Jadi urutannya adalah urutan nama berkas lokal.
2. **Pencocokan ulang.** Setelah dipasangkan menurut urutan itu, **81 dari 81 cocok
   pada tiga penanda sekaligus**: nominal harapan, jumlah lembar, dan ekstensi berkas.

### Yang TIDAK tersedia: nama asli kamera

Kolom `nama_asli_kamera` seluruhnya **TIDAK TERSEDIA**, dan ini perlu dijelaskan karena
permintaanmu menyebut `IMG_XXXX.JPG`.

Rantai penamaannya ada **tiga lapis**, bukan dua:

```
IMG_XXXX.HEIC  ->  5000_dipegang_ (3).jpeg  ->  SENDIRI_01262.jpeg
   (kamera)            (nama kerja)              (nama evaluasi)
```

Lapis kedua ke ketiga: **tersedia dan terverifikasi** (isi berkas ini).
Lapis pertama ke kedua: **tidak pernah dicatat.** Penggantian namanya dilakukan manual
saat foto dipindahkan dari iPhone, tanpa menyimpan daftar. Selain itu hanya **23 berkas
asli** yang masih ada di `data/uji_sendiri/asli/`, sedangkan fotonya 81 - jadi sebagian
besar aslinya memang sudah tidak ada.

Kami **tidak merekonstruksinya dari perkiraan**. Mencocokkan 23 berkas HEIC ke 81 foto
berdasarkan urutan atau cap waktu akan menghasilkan daftar yang tampak rapi tetapi tidak
bisa dibuktikan benar.

---

## 2. Pembagian lipatan - apa yang lengkap dan apa yang tidak

**405 baris** = 81 foto x 5 lipatan. Format panjang, satu baris per (foto, lipatan).

| Lipatan | test | train |
| ---: | ---: | ---: |
| 0 | 17 | 64 |
| 1 | 16 | 65 |
| 2 | 16 | 65 |
| 3 | 16 | 65 |
| 4 | 16 | 65 |

### Kenapa tidak ada baris `validation` untuk foto sendiri

Ini bukan data yang hilang, melainkan memang begitu rancangannya. Notebook sel 26
menetapkan: grup yang sedang diuji jadi `test`, grup yang masuk `grup_val` jadi `val`,
sisanya `train`. Dan `grup_val` **diambil hanya dari grup data publik**. Jadi foto
sendiri tidak pernah menjadi validasi - ia `test` di satu lipatan dan `train` di empat
lipatan lainnya.

### Yang TIDAK tersedia

**a. Kolom `kelompok_kemiripan`.** Pengelompokan pHash tidak pernah disimpan ke berkas.

Dan ia **tidak bisa dihitung ulang di laptop**, bukan karena malas, melainkan karena
hasilnya pasti berbeda: ambang jaraknya menyusut dalam perulangan sampai kelompok
terbesar <= `max(10, 0.03 x N)`, dengan `N` jumlah SELURUH gambar - termasuk sekitar
1.194 gambar dataset publik yang tidak ada di laptop. Dengan N=81 ambang berhentinya
berbeda, sehingga kelompoknya berbeda.

**Cara mendapatkannya:** jalankan ulang `notebooks/04_money_kfold.ipynb` sel 0-18 di
Colab dengan `SEED` yang sama, lalu simpan `[(r['asal'], r['grup']) for r in records]`
ke CSV. Pengelompokannya deterministik, jadi hasilnya akan sama dengan saat pelatihan.

**b. Baris untuk data publik.** Dataset publik (sekitar 1.194 gambar) ada di Colab dan
Drive, tidak di laptop. Yang ada di berkas ini hanya 81 foto sendiri.

---

## 3. Label foto evaluasi

`03_label_evaluasi.zip` berisi **162 berkas** dalam dua folder, isinya sama persis,
hanya penamaannya berbeda:

| Folder | Penamaan | Untuk |
| :--- | :--- | :--- |
| `label_evaluasi/` | `SENDIRI_01194.txt` dan seterusnya | dicocokkan dengan CSV evaluasi |
| `label_evaluasi_nama_lokal/` | `100000_dipegang_ (2).txt` dan seterusnya | dicocokkan dengan berkas foto |

Ini **label yang benar-benar dipakai** untuk melatih dan menguji v2, disalin apa adanya
dari `data/label_sendiri/test/labels/`. Jumlahnya **82 kotak pada 81 label**.

Format YOLO: `kelas x_tengah y_tengah lebar tinggi`, dinormalkan 0-1.
Indeks kelas: `0=1000, 1=2000, 2=5000, 3=10000, 4=20000, 5=50000, 6=100000`.

---

## 4. Foto beranotasi cacat

| | |
| :--- | :--- |
| Nama lokal | `5000_dipegang_ (3).jpeg` |
| Nama evaluasi | **`SENDIRI_01262.jpeg`** |
| Lipatan uji | 2 |
| Status evaluasi | BENAR |

Isi `04_anotasi_cacat/`:

- `sebelum/` - label lama, foto berkotak label, dan foto dengan wajah disamarkan
- `sesudah/BELUM_ADA.md` - **label perbaikan belum ada**

**Apakah perbaikannya sudah diikuti pelatihan dan evaluasi ulang? BELUM.**
Anotasinya belum diperbaiki sama sekali, jadi tidak ada yang bisa diikuti.

Kami memeriksa ulang hari ini: label di laptop **masih identik** dengan versi
"sebelum" (`2 0.499893 0.485510 0.998700 0.708150`, menutupi 99,87% lebar bingkai pada
foto yang memuat dua lembar).

Pelatihan ulang dan evaluasi ulang memang pernah terjadi pada 26 Oktober, **tetapi
keduanya berjalan di atas anotasi yang masih cacat**. Jadi jangan menuliskan bahwa
"anotasi diperbaiki lalu diuji ulang". Rinciannya di
`bahan_untuk_rekan/02_status_pengujian_ulang.md`.

---

## 5. Selisih 84 lawan 82

**Tidak ada selisih** - ketiga sumber mencatat 82 kotak. Satu-satunya angka 84 di
seluruh bahan adalah **84,0% ketepatan**, yang juga sudah usang (berlaku: 90,1%).
Rinciannya di `05_selisih_84_lawan_82.md`.

---

## Yang tidak dikirim ulang

Sesuai permintaan: `args_v2.yaml`, `results_v2.csv`, grafik pelatihan, dan CSV hasil
evaluasi tidak disertakan - semuanya masih ada di `bahan_untuk_rekan/` dari kiriman
pertama dan **tidak berubah**. Tidak ada pengujian ulang baru sejak 30 Oktober.
