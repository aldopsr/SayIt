# Jawaban permintaan data — jurnal kedaluwarsa SayIt

Dijawab **22 November 2026**, dari repo pada commit `b988ada` (`origin/main`).
Penomoran mengikuti berkas permintaanmu persis.

Penanda asal tiap jawaban:

| penanda | arti |
|---|---|
| **[UKUR]** | diukur ulang hari ini di laptop pengembang, perintahnya disebut |
| **[REPO]** | dibaca langsung dari kode, notebook, EXIF berkas, atau API Roboflow |
| **[DRIVE]** | diambil dari Google Drive (keluaran Colab yang tersimpan otomatis) |
| **[JURNAL]** | disalin dari `docs/keputusan-teknis.md`, tanggal aslinya disebut |
| **[TIDAK TERCATAT]** | datanya memang tidak ada — tidak diperkirakan |
| **[KAMU]** | hanya pemilik datanya yang tahu, belum terjawab |

---

# BACA INI DULU — tiga hal yang tidak kamu tanyakan tapi memengaruhi naskah

## A. Tiga dari 16 foto uji adalah TANGKAPAN LAYAR, bukan foto kamera

| berkas | resolusi | bukti |
|---|---|---|
| `202804_tolakangin2.PNG` | 828×1792 | PNG, tanpa EXIF kamera, ada bilah hitam atas-bawah |
| `20290821_tisu1.PNG` | 828×1792 | PNG, tanpa EXIF kamera, ada bilah hitam atas-bawah |
| `20290821_tisu2.PNG` | 828×1792 | PNG, tanpa EXIF, **antarmuka aplikasi Foto iOS terlihat jelas di dalam gambarnya** — jam 09.41, label "Today", tombol bagikan/suka/info/hapus, dan deretan mini foto di bawah |

828×1792 adalah resolusi layar iPhone 11/XR tepat. Ketiganya juga bertanda waktu
berkas 09.40–09.42, terpisah dari rombongan foto kamera pukul 15.29–15.34.

Dua berkas lain, `tidakada_permen1.jpeg` dan `tidakada_permen2.jpeg`, beresolusi
960×1280 tanpa EXIF sama sekali — bukan keluaran langsung kamera iPhone, tetapi
asal persisnya tidak dapat dipastikan dari berkasnya.

**Kenapa ini penting:** repo sudah punya pelajaran tertulis soal ini. Catatan
30 September meralat kesimpulan "model zona tidak bekerja" yang ternyata diambil
dari foto berupa tangkapan layar. Ketiga berkas itu masih ada di set uji yang
menghasilkan angka 81%, dan kebetulan justru ketiganya yang paling bermasalah:
`tolakangin2` adalah satu-satunya jawaban KOSONG sekaligus berkas terlambat
(90–149 detik), sementara `tisu1` dan `tisu2` memakan 23–42 detik.

Saran: sebutkan komposisi set uji apa adanya di subbab data, atau ganti ketiganya
dengan foto kamera lalu ukur ulang. Jangan dibiarkan diam-diam.

## B. "Dengan / tanpa pra-pemrosesan" pada 2 Oktober dan hari ini MENGUKUR HAL BERBEDA

| | kolom "dgn pra" berarti | kolom "tanpa pra" berarti |
|---|---|---|
| **02-10** | rangkaian `kedaluwarsa` = `[upscale, clahe]` | tanpa apa-apa |
| **hari ini** | `expiry.preprocess_chain: hanya_resize` = `[resize]` | tanpa apa-apa |

Jadi pengukuran 02-10 membuktikan **upscale+CLAHE merusak** (69% lawan 81%),
sedangkan pengukuran hari ini membuktikan **resize membantu** (+6%). Keduanya
benar dan tidak bertentangan — rangkaiannya memang sudah diganti sejak itu.

Dan "tanpa resize" bukan kondisi netral: keluaran PaddleOCR hari ini memasang
peringatannya sendiri, `Resized image size (3024x4032) exceeds max_side_limit of
4000`, artinya ia tetap memperkecil gambar hanya dengan ukuran berbeda. Jadi
kolom itu sebenarnya "pakai pengecilan bawaan PaddleOCR", bukan "tanpa
pra-pemrosesan".

**Jangan satukan angka 02-10 dan angka hari ini ke dalam satu tabel tanpa
menyebut perbedaan ini.**

## C. Dua jawaban salah berbeda ARAH, dan bahayanya tidak sama

| berkas | acuan | dijawab | arah | akibat bagi pengguna |
|---|---|---|---|---|
| `chees` | 2027-03-21 | 2026-05-21 | **lebih awal ~10 bulan** | produk layak dikira basi — makanan terbuang |
| `ovaltine` | 2027-09-27 | 2027-09-30 | **lebih lambat 3 hari** | produk basi dikira layak — **arah yang berbahaya** |

Menyebut keduanya hanya sebagai "2 salah" menghilangkan perbedaan yang paling
penting bagi pengguna tunanetra.

---

# 0. Konfirmasi

## 0.1 Perubahan setelah `b988ada` yang memengaruhi modul kedaluwarsa?

**[REPO]** Tidak ada. `git log b988ada..HEAD` kosong — `b988ada` commit terakhir.

Pertanyaan yang lebih tepat adalah apa yang berubah **setelah pengukuran
17 November**, dan ada dua yang menyentuh jalur kode modul kedaluwarsa:

| commit | tanggal | apa | pengaruh pada 13/2/1 |
|---|---|---|---|
| `361e119` | 20-11 | `date_parser.negative_markers` ditambahkan | **Nol.** A/B 16 kemasan: daftar kosong 13/2/1, daftar terisi 13/2/1, identik per berkas |
| `1d79f07` | 20-11 | `expiry.zone_classes_date` / `zone_classes_reject` | **Nol** selama bobot 1 kelas dipakai. `Zone.cls` berisi `expired_date_zone`, tidak ada di daftar tolak sehingga lolos; lalu karena tidak ada kelas `date`, pilihan kembali ke skor tertinggi — perilaku lama persis. Dikunci 7 tes |

**[UKUR]** Dan ini tidak perlu dipercaya begitu saja: pengukuran ulang hari ini
pada `b988ada` memberi **13 / 2 / 1 = 81%**, sama persis dengan 17 November
(rinciannya di bagian 2).

Dua commit lain di rentang itu (`3b198cc` ambang buram, `f5b9bda` quality gate)
**tidak menyentuh pengukuran ini sama sekali**: `scripts/ukur_kedaluwarsa.py`
memanggil `ExpiryReader.read()` langsung, tanpa melewati quality gate.

## 0.2 Apakah 16 foto uji masih sama persis?

**[REPO]** Ya. Seluruh berkas di `data/uji_kedaluwarsa/` bertanggal ubah
**29 September 2026** dan tidak ada yang berubah sejak itu.

---

# 1. Yang kosong di naskah

## 1.1 Data foto uji

**[REPO]** Dari EXIF, dan dari melihat tiap fotonya.

| # | Nama berkas | Jenis produk (tanpa merek) | Bahan kemasan | Resolusi |
|---|---|---|---|---|
| 1 | `20260411_ajinomoto.JPG` | penyedap rasa, sachet | plastik (sachet) | 4032×3024 |
| 2 | `20261008.JPG` | penganan tradisional (santan, tepung ketan) | plastik (bungkus putih) | 4032×3024 |
| 3 | `20270120_miesedap.JPG` | mi instan | plastik (bungkus) | 4032×3024 |
| 4 | `20270311_mentega.JPG` | margarin sachet | plastik berlapis foil | 4032×3024 |
| 5 | `20270321_chees.JPG` | keju oles | **karton** (kotak) | 4032×3024 |
| 6 | `20270602_indofood.JPG` | bumbu/kecap sachet | plastik berlapis foil | 4032×3024 |
| 7 | `20270906.JPG` | sachet bungkus putih polos | plastik (bungkus putih) | 4032×3024 |
| 8 | `20270927_ovaltine.JPG` | minuman serbuk sachet | plastik berlapis foil | 4032×3024 |
| 9 | `202804_tolakangin1.HEIC` | jamu cair sachet | plastik berlapis foil | 3024×4032 |
| 10 | `202804_tolakangin2.PNG` | jamu cair sachet (**tangkapan layar**) | plastik berlapis foil | 828×1792 |
| 11 | `20290211_kecapasin.JPG` | kecap asin botol | **botol**, tanggal tercetak di **tutup plastik** | 4032×3024 |
| 12 | `20290306_merica.JPG` | merica bubuk sachet | plastik (sachet) | 4032×3024 |
| 13 | `20290821_tisu1.PNG` | tisu basah (**tangkapan layar**) | plastik (kemasan lunak) | 828×1792 |
| 14 | `20290821_tisu2.PNG` | tisu basah (**tangkapan layar**) | plastik (kemasan lunak) | 828×1792 |
| 15 | `tidakada_permen1.jpeg` | permen mint, tanpa tanggal | plastik (bungkus) | 960×1280 |
| 16 | `tidakada_permen2.jpeg` | permen mint, tanpa tanggal | plastik (bungkus) | 960×1280 |

Ringkas untuk narasi: **14 dari 16 berkemasan plastik atau plastik berlapis
foil**, satu karton (`chees`), satu botol yang tanggalnya tercetak di tutup
plastik (`kecapasin`). **Tidak ada kaleng sama sekali** — itu batas set uji yang
layak disebut.

**Tipe ponsel [REPO]:** dua perangkat, dari EXIF.

- **Apple iPhone 12** — 10 berkas, semuanya 4032×3024, dipotret **28 September
  2026 pukul 15.29–15.34** (satu sesi, rentang 6 menit).
- **Apple iPhone 11** — 1 berkas (`tolakangin1.HEIC`), 3024×4032, dipotret
  **28 September 2026 pukul 08.30**.
- 5 berkas sisanya tanpa EXIF kamera (tiga tangkapan layar + dua foto permen).

**Pemotret [KAMU]:** EXIF hanya menyebut perangkat, bukan orangnya.

## 1.2 Lisensi dan asal dataset zona

**[REPO]** Diperiksa ulang lewat API Roboflow Universe pada 22 November 2026.

- **Dataset:** `coolstuff-rfnc5/expiry-date-detection-i3bav`, nama tampilan
  "Expiry Date Detection", workspace "CoolSTuff", **versi 1**. Itu satu-satunya
  entri aktif di `DATASETS` pada `notebooks/03_zone_build_and_train.ipynb`;
  empat kandidat lain ada di berkas yang sama tetapi dikomentari.
- **Lisensi: TIDAK TERCANTUM.** API mengembalikan `license: null`. Ini bukan
  "belum dicek" — halaman datasetnya memang tidak menyatakan lisensi apa pun.
- **Jumlah citra: 998**, satu kelas bernama `Label`, terakhir diperbarui
  20 Oktober 2024.
- **Split latih/validasi/uji: [TIDAK TERCATAT] sebagai angka**, dan alasannya
  perlu ditulis: notebook **tidak memakai split bawaan Roboflow**. Ia mengunduh
  seluruh citra, membuang duplikat dengan pHash, lalu membagi ulang **per
  kelompok kemiripan** memakai `SPLIT_RATIO = (0.7, 0.2, 0.1)` dan `SEED = 42`.
  Jumlah akhir tiap split hanya tercetak saat notebook dijalankan, dan keluaran
  itu tidak tersimpan (lihat 1.3).

**Risiko untuk jurnal:** lisensi yang tidak tercantum adalah masalah nyata, bukan
detail administratif. Alternatif terdekat yang lisensinya jelas:
`expiry-label-detection/expiry-date-detection-egbf3` — **1.014 citra**, satu
kelas `Label`, **CC BY 4.0**. Ukurannya hampir sama, jadi melatih ulang dengan
dataset itu layak dipertimbangkan sebelum submit.

## 1.3 Pengaturan pelatihan model zona satu kelas

**[REPO]** Dari `notebooks/03_zone_build_and_train.ipynb`:

| hal | nilai |
|---|---|
| Bobot awal | `yolov8n.pt` |
| **Epoch** | **100** (setelan), dengan `patience=20` |
| **Ukuran masukan** | **640 px** |
| Batch | 16 |
| Seed | 42 |
| Nama run | `zone_v1` |
| Augmentasi | `degrees=180`, `perspective=0.0005`, `scale=0.6`, `translate=0.2`, `hsv_v=0.5`, `hsv_s=0.8`, `fliplr=0.5` |

Dua catatan yang mudah salah kutip:

1. **"100 epoch" adalah SETELAN, belum tentu yang benar-benar berjalan.**
   `patience=20` menghentikan latihan lebih awal bila validasi berhenti membaik.
2. **`degrees=180` dan `fliplr=0.5` disengaja, dan berbeda dari model uang.**
   Alasannya ada di komentar notebook: kemasan bisa dipegang pada sudut apa pun,
   dan model ini hanya mencari **letak** tanggalnya, bukan bacaannya — jadi
   tanggal yang tercermin tetap contoh latih yang sah.

- **GPU / lingkungan: [TIDAK TERCATAT].** Notebook tersimpan tanpa keluaran sama
  sekali (0 dari 25 sel punya `outputs`).
- **Tanggal latih [REPO]:** `models/best_zone.pt` bertanggal **28 September 2026
  08:18**, 6.256.362 bita. Itu tanggal bobotnya masuk ke repo; tanggal latihnya
  sama atau sedikit lebih awal.
- **mAP50 validasi: [TIDAK TERCATAT].** **[KAMU]** Kalau folder `runs/zone_v1`
  masih ada di Google Drive, angkanya ada di `results.csv` di dalamnya. Berbeda
  dari model 4 kelas, notebook 03 belum menulis ringkasan metrik ke Drive —
  kebiasaan itu baru dipakai sejak notebook 05.

## 1.4 Kemasan kedua yang salah

**[UKUR]**

- **Berkas:** `20270321_chees.JPG` (keju oles, kemasan karton)
- **Tanggal acuan:** 21 Maret 2027
- **Tanggal yang diucapkan:** **21 Mei 2026**
- **Lebih awal / lebih lambat:** **lebih awal**, selisih sekitar 10 bulan

Lihat juga blok C di atas — arah kedua kesalahan berbeda dan itu layak dibahas.

---

# 2. Rincian hasil per foto (konfigurasi akhir)

**[UKUR]** `python scripts\ukur_kedaluwarsa.py data\uji_kedaluwarsa --rinci`,
dijalankan 22 November 2026 pada commit `b988ada`. Hasil: **13 BENAR / 2 SALAH /
1 KOSONG = 81%**.

Kolom "jalur" menggabungkan dua pengukuran: alasan parser dari `--rinci`, dan
skor deteksi zona mentah per berkas (diukur 20 November pada ambang 0,01 agar
seluruh deteksi terlihat).

| # | Berkas | Acuan | Dijawab | Nilai | Jalur |
|---|---|---|---|---|---|
| 1 | `20260411_ajinomoto.JPG` | 2026-04-11 | 2026-04-11 | BENAR | potongan zona (skor 0,76) |
| 2 | `20261008.JPG` | 2026-10-08 | 2026-10-08 | BENAR | **zona ketemu (0,70), potongan gagal, mundur ke seluruh gambar** |
| 3 | `20270120_miesedap.JPG` | 2027-01-20 | 2027-01-20 | BENAR | potongan zona (0,62) |
| 4 | `20270311_mentega.JPG` | 2027-03-11 | 2027-03-11 | BENAR | potongan zona (0,56) |
| 5 | `20270321_chees.JPG` | 2027-03-21 | **2026-05-21** | **SALAH** | potongan zona (0,72) |
| 6 | `20270602_indofood.JPG` | 2027-06-02 | 2027-06-02 | BENAR | potongan zona (0,77) |
| 7 | `20270906.JPG` | 2027-09-06 | 2027-09-06 | BENAR | **zona ketemu (0,43), potongan gagal, mundur ke seluruh gambar** |
| 8 | `20270927_ovaltine.JPG` | 2027-09-27 | **2027-09-30** | **SALAH** | potongan zona (0,76) |
| 9 | `202804_tolakangin1.HEIC` | 2028-04 | 2028-04 | BENAR | tanpa zona (0,14), seluruh gambar |
| 10 | `202804_tolakangin2.PNG` | 2028-04 | — | **KOSONG** | tanpa zona (0,03), seluruh gambar |
| 11 | `20290211_kecapasin.JPG` | 2029-02-11 | 2029-02-11 | BENAR | potongan zona (0,65) |
| 12 | `20290306_merica.JPG` | 2029-03-06 | 2029-03-06 | BENAR | tanpa zona (0,28), seluruh gambar |
| 13 | `20290821_tisu1.PNG` | 2029-08-21 | 2029-08-21 | BENAR | tanpa zona (0,27), seluruh gambar |
| 14 | `20290821_tisu2.PNG` | 2029-08-21 | 2029-08-21 | BENAR | tanpa zona (0,20), seluruh gambar |
| 15 | `tidakada_permen1.jpeg` | kosong | — | BENAR | tanpa zona (0,00), seluruh gambar |
| 16 | `tidakada_permen2.jpeg` | kosong | — | BENAR | tanpa zona (0,02), seluruh gambar |

**Foto yang KOSONG: `202804_tolakangin2.PNG`**, satu-satunya — dan itu salah satu
dari tiga tangkapan layar (blok A).

**Rekap jalur:** 7 berkas dijawab dari potongan zona, 2 berkas zonanya ketemu
tetapi potongannya gagal sehingga mundur ke OCR seluruh gambar, dan 7 berkas
tidak punya zona di atas ambang 0,40 sehingga langsung memakai seluruh gambar.
Jadi **zona ditemukan pada 9 dari 16 berkas**, atau 9 dari 14 kemasan bertanggal.

---

# 3. Angka yang tidak lengkap di catatan repo

## 3.1 EasyOCR tanpa pra-pemrosesan, pipeline penuh (Tabel 3)

**[UKUR]** `python scripts\ukur_kedaluwarsa.py data\uji_kedaluwarsa --rinci
--mesin easyocr`, 22 November 2026.

| kondisi | BENAR | SALAH | KOSONG | akurasi |
|---|---|---|---|---|
| EasyOCR **dengan** pra (`[resize]`) | 7 | **0** | 9 | 44% |
| EasyOCR **tanpa** pra | **6** | **0** | **10** | **38%** |

Jadi jawaban yang kamu minta: **6 benar / 0 salah / 10 kosong**.

**Yang paling layak dibahas di jurnal dari tabel ini bukan 38%-nya, melainkan
kolom SALAH yang NOL.** Profil kegagalan kedua mesin berbeda jenis:

- **EasyOCR gagal dengan DIAM.** Nol jawaban salah pada kedua kondisi — ia
  nyaris tidak membaca cetakan kemasan sama sekali, jadi tidak ada angka untuk
  disalahtafsirkan parser.
- **PaddleOCR gagal dengan JAWABAN SALAH.** Ia membaca lebih banyak, termasuk
  nomor produksi, dan di situlah dua kesalahan yang tersisa lahir.

Artinya lompatan 44% → 81% tidak gratis, dan dua akibatnya bisa dipisahkan per
berkas:

- **Enam berkas berubah KOSONG → BENAR** berkat PaddleOCR: `20261008`,
  `mentega`, `20270906`, `tolakangin1`, `kecapasin`, `merica`.
- **Dua berkas berubah KOSONG → SALAH**: `chees` dan `ovaltine`. Pada EasyOCR
  keduanya diam; PaddleOCR membaca angkanya lalu parser menafsirkannya keliru.

Jadi pindah mesin menukar **6 diam menjadi benar** dengan harga **2 diam menjadi
salah** — dan satu dari dua itu (`ovaltine`) ke arah yang berbahaya. Itu
pertukaran yang layak, tetapi harus ditulis sebagai pertukaran, bukan sebagai
perbaikan murni.

**Ingat blok B:** "tanpa pra" di sini berarti tanpa `resize`, bukan tanpa
rangkaian `upscale+clahe` seperti pada catatan 02-10.

## 3.2 PaddleOCR 1200 px, mesin terisolasi (Tabel 5)

**[UKUR]** Diukur 22 November 2026, PaddleOCR 1200 px, mesin terisolasi, dua
kondisi penanda. Saklarnya disetel di memori — `config/settings.yaml` tidak
disentuh — dan nilainya dicetak di tiap kondisi.

| kondisi | nilai saklar | BENAR | SALAH | DIAM | akurasi |
|---|---|---|---|---|---|
| penanda **wajib** | `require_marker_for_compact = True` | 8 | **1** | 7 | 50% |
| penanda **dilonggarkan** | `require_marker_for_compact = False` | **11** | **1** | 4 | **69%** |

### Jawaban atas ketidakcocokan yang kamu temukan

**Tabelnya yang benar; kalimat narasinya yang keliru.**

Catatan 2 Oktober mencatat **SALAH = 1 pada KEDUA kondisi** (6/1/9 dan 9/1/6).
Jadi menurut tabelnya sendiri, pelonggaran penanda **tidak pernah menambah
jawaban salah** di ukuran 1200 px — ia hanya mengubah DIAM menjadi BENAR.
Kalimat narasi yang menyebut "pelonggaran menambah satu jawaban salah di ukuran
ini" tidak didukung angka di sebelahnya.

Pengukuran hari ini menegaskannya: **SALAH tetap 1 pada kedua kondisi**, dan
bahkan **berkas yang sama** — `20270927_ovaltine`, acuan 2027-09-27, dijawab
`2029-03-26`. Pelonggaran menukar **3 DIAM menjadi BENAR** tanpa menyentuh kolom
SALAH sama sekali.

### Kenapa angka hari ini berbeda dari angka 2 Oktober

| | penanda wajib | penanda dilonggarkan |
|---|---|---|
| 02-10 | 6 / 1 / 9 (38%) | 9 / 1 / 6 (56%) |
| **22-11** | **8 / 1 / 7 (50%)** | **11 / 1 / 4 (69%)** |

Selisihnya **+2 BENAR di kedua kondisi**, dan itu wajar: pengenal
`PP-OCRv6_medium_rec` dan paddleocr 3.7.0 yang terpasang sekarang berbeda dari
yang dipakai 2 Oktober, ditambah parser sudah menerima beberapa perbaikan pola
sejak itu (`my_spasi`, penanda negatif).

**Untuk jurnal, pilih satu dan sebutkan tanggalnya.** Jangan mencampur baris
02-10 dan 22-11 dalam satu tabel. Kalau Tabel 5 mengutip angka 02-10, tulis
bahwa angka itu **tidak dapat direproduksi hari ini** karena versi pengenal
berubah — itu konsisten dengan catatan reproduksibilitas di bagian 4.1.

**Jangan kutip latensi dari pengukuran ini.** Kondisi pertama melaporkan
50,42 detik/foto dan kedua 48,13 detik/foto, sementara proses terpisah pada hari
yang sama memberi 32,95 detik/foto untuk kondisi yang sama persis. Beban laptop
mendominasi, seperti peringatan di bagian 3.4.

## 3.3 Ambang skor zona 0,25 pada pipeline penuh (Tabel 6)

**[UKUR, 20 November]** Rinciannya **12 BENAR / 1 SALAH / 3 KOSONG = 75%**.

Dua hal yang wajib ikut ditulis agar tabelnya tidak disalahartikan:

1. Angka itu diukur pada **bobot 4 kelas gabungan**, bukan pada `best_zone.pt`
   yang dipakai produksi. Pada bobot 1 kelas, ambang 0,25 **belum pernah
   diukur**.
2. Dua daftar kelas tolak memberi hasil **identik per berkas**: tolak
   `[code, prod]` 12/1/3 median 14,97 s; tolak `[code, prod, due]` 12/1/3 median
   11,12 s. Jadi menolak `due` hanya memperbaiki latensi, bukan akurasi.

Pembanding pada ambang 0,40 (bobot gabungan): **13 / 0 / 3**. Jadi menurunkan
ambang ke 0,25 **menukar satu jawaban benar menjadi satu jawaban salah**
(`ajinomoto`), sementara cakupan zona hanya naik dari 3/16 ke 4/16.

## 3.4 Latensi

**[JURNAL]** Jawaban per pertanyaan, dengan batas keabsahannya:

- **11,4 detik rerata atau median? [TIDAK TERCATAT].** Catatan 2 Oktober hanya
  menulis "latensi end-to-end 11,4–11,5 detik" tanpa menyebut statistiknya.
  Jangan ditulis sebagai median maupun rerata — tulis "sekitar 11,4 detik"
  beserta tanggal pengukurannya.
- **Berapa yang diukur?** **64 foto**, dengan STT + pipeline + render suara;
  pemuatan model tidak dihitung.
- **Apakah 7,82 detik hanya `ExpiryReader.read()`?** **Ya** — tanpa pengenalan
  suara, tanpa render suara, tanpa jaringan. Jadi **7,82 detik dan 11,4 detik
  tidak boleh dibandingkan langsung**; keduanya mengukur hal yang berbeda.
- **Median dan terburuk per sesi pada konfigurasi akhir:** median **7,82 detik**,
  terburuk **90,0 detik** (`tolakangin2`), total 262,1 detik untuk 16 kemasan
  (diukur 20 November, satu proses).

**Peringatan yang wajib menyertai angka latensi mana pun:** kondisi yang sama
persis memberi median **6,54 detik** di satu sesi dan **10,46 detik** di sesi
lain pada hari yang sama, dan **9,96 lawan 7,82 detik** pada hari lain —
simpangan sampai 60% dari beban laptop. Yang sah dikutip adalah **perbandingan
di dalam satu sesi**, bukan angka detiknya sebagai nilai mutlak.

## 3.5 Model zona empat kelas — kedua model

**[DRIVE]** Ringkasan metrik kedua model ada di `MyDrive/sayit/hasil/`, ditulis
otomatis oleh notebooknya.

| | model pertama | model kedua (gabungan) |
|---|---|---|
| Run | `zone_4kelas_v1` | `zone_gabungan_v1` |
| Waktu latih | 19-11-2026 18:37 | 20-11-2026 03:25 |
| Dataset | `esigelec-rniez/expiry v1` | `esigelec-rniez/expiry v1` **+** `coolstuff-rfnc5/expiry-date-detection-i3bav v1` |
| Jumlah citra | (tidak dicatat) | **4.478** citra, 1.609 kelompok kemiripan |
| **Epoch** | **80** | **100** |
| Ukuran masukan | 640 px | 640 px |
| Augmentasi | (tidak dicatat) | `degrees=15.0 translate=0.1 scale=0.5 fliplr=0.0 mosaic=1.0` |
| **mAP50** | **0,8643** | **0,7813** |
| mAP50-95 | 0,6766 | 0,5310 |
| **AP50 `date`** | **0,9384** | **0,6305** |
| AP50 `code` | 0,8120 | 0,7883 |
| AP50 `due` | 0,8532 | 0,8574 |
| AP50 `prod` | 0,8488 | 0,8488 |

**Angka ini menjelaskan kenapa penggabungan dataset gagal, dan itu temuan yang
layak masuk jurnal.** Menggabungkan dataset satu kelas menjatuhkan AP50 kelas
`date` dari **0,9384 ke 0,6305** — justru kelas yang paling dibutuhkan aplikasi,
sementara tiga kelas lain nyaris tidak bergerak. Sebabnya masuk akal: seluruh
kotak dataset satu kelas dipetakan menjadi `date`, padahal sebagiannya sebenarnya
kode produksi atau penanda, sehingga definisi `date` jadi kabur.

Rantai sebabnya kini utuh sampai ke tingkat model, bukan hanya tingkat sistem:
dataset digabung → `date` kabur → cakupan zona pada 16 kemasan sendiri runtuh
(3/16) → banyak berkas jatuh ke jalur cadangan yang lambat → latensi median naik
dua kali lipat.

**Peringatan:** kedua mAP50 itu diukur pada split test yang **sesumber dengan
data latihnya**, jadi optimistis untuk kemasan Indonesia. Pembanding yang sah
tetap hasil pada 16 kemasan sendiri.

---

# 4. Supaya hasil bisa diulang orang lain

## 4.1 Model pengenal PP-OCRv6 varian menengah

**[REPO]**

- **Tempat simpan:** `C:\Users\<pengguna>\.paddlex\official_models\PP-OCRv6_medium_rec\`
  (Linux/Mac: `~/.paddlex/official_models/`). Model deteksinya,
  `PP-OCRv5_mobile_det`, ada di folder yang sama.
- **Cara mendapatkannya:** tidak perlu diunduh manual. PaddleOCR mengunduhnya
  sendiri saat pertama dipakai, asal ada internet; namanya diminta lewat
  `config/settings.yaml`. Log saat sudah ada:
  `Model files already exist. Using cached files.`
- **Versi saat angka 81% diukur:** paddleocr **3.7.0**, paddlepaddle **3.3.1**.
  (Catatan lama yang menulis "paddleocr 3.3.1" keliru — yang 3.3.1 itu
  paddlepaddle.)
- **Layak masuk `models/README.md`?** Ya. Yang perlu dicatat cuma tiga baris:
  nama kedua model, versi paddleocr dan paddlepaddle, dan catatan bahwa
  unduhannya otomatis serta butuh internet pada pemakaian pertama.

**Catatan jujur:** unduhan otomatis mengambil versi model yang tersedia **saat
itu**. Kalau PaddleOCR kelak mengubah isi `PP-OCRv6_medium_rec`, reproduksi di
masa depan bisa memberi angka berbeda tanpa ada yang berubah di repo.
Satu-satunya penutup celah itu adalah mengarsipkan berkas modelnya sendiri, dan
itu belum dilakukan.

## 4.2 Foto uji lapangan 12 November (kemasan mi instan)

**[REPO] Tidak ada.** Pencarian seluruh repo tidak menemukannya, dan catatan
17 November sudah mencatatnya hilang. **[KAMU]** Kalau fotonya masih ada di
galeri ponsel, simpan ke `data/uji_kedaluwarsa/` dengan nama bertanggal — itu
satu-satunya contoh kegagalan lapangan yang pernah terjadi.

---

# 5. Pertanyaan pendek

## 5.1 Dua kemasan tanpa tanggal, benar dijawab "tidak menemukan tanggal"?

**[UKUR] Ya, keduanya benar.** `tidakada_permen1.jpeg` dan
`tidakada_permen2.jpeg` sama-sama dijawab "tidak menemukan tanggal", dan keduanya
memang dihitung sebagai BENAR di dalam angka 13.

**Koreksi penting untuk kalimat di naskah:** 13 benar itu terdiri dari **11
tanggal yang dibaca benar + 2 penolakan yang benar**. Jadi kalimat "13 dari 16
kemasan tanggalnya terbaca benar" keliru. Yang benar: "13 dari 16 kemasan
dijawab dengan benar, termasuk 2 kemasan yang memang tidak punya tanggal".

## 5.2 Apakah "MAR" ada di dekat nomor produksi 210526 pada kemasan `chees`?

**[REPO] YA, dan terlihat jelas pada fotonya.** Yang tercetak di kemasan, dua
baris bertumpuk:

```
210526/L7A/19:48
21 MAR 2027
```

Jadi tanggal kedaluwarsa `21 MAR 2027` tercetak **tepat di baris bawah** nomor
produksi `210526`. Itu menguatkan diagnosis di jurnal: parser memilih rangkaian
angka yang salah di antara dua yang bersebelahan.

**Tetapi satu hal harus diluruskan agar tidak salah kutip:** teks yang
benar-benar diurai pipeline **tidak memuat kata "Kode Produksi" sama sekali**.
Teks OCR yang sungguhan adalah
`'man.yeg Bes 0re Cae 0 T7 回 回 WOR SUCALNED 210526/ en im ua.'` — angka `210526`
terbaca, `21 MAR 2027` **tidak**. Jadi pada berkas ini OCR gagal membaca
tanggalnya, dan yang tersisa untuk diurai hanya nomor produksinya.

## 5.3 Apakah `rantai` mengubah mentega jadi benar tanpa regresi?

**[JURNAL, 17-11] Ya.** `pita` 12 benar / 3 salah / 1 kosong lawan `rantai`
13 / 2 / 1 pada 16 kemasan. **Yang berubah hanya satu berkas**: `mentega` dari
salah menjadi benar. **Nol regresi** pada 15 berkas lainnya.

Sebabnya tercatat rinci: tanggal pada mentega tercetak **diagonal** —
`02:31`(x995,y261) `NS`(831,362) `27`(680,428) `MAR`(418,523) `11`(238,614),
jadi x menurun saat y menaik. Kemiringan sejatinya **−0,418**, di atas
`line_slope_max` 0,35 sehingga dibuang menjadi 0; sementara taksiran median
seluruh potongan hanya **−0,196** karena blok tabel gizi di atasnya hampir datar.
Satu angka kemiringan tidak muat untuk dua blok berorientasi berbeda.

Harganya di modul dokumen harus ikut disebut: CER **14,89% → 14,94%** (1 membaik,
1 memburuk, 11 tetap), sehingga margin terhadap target PRD ≤ 15% menyusut dari
0,11 ke 0,06 poin.

## 5.4 Apakah semua 16 foto dipotret orang yang sama dengan satu ponsel?

**[REPO] Tidak, dan ini pasti dari EXIF** — lihat tabel 1.1. **Dua ponsel
berbeda** (iPhone 12 untuk 10 berkas, iPhone 11 untuk 1 berkas), dalam dua sesi
terpisah tujuh jam, ditambah 5 berkas tanpa EXIF di antaranya tiga tangkapan
layar.

**[KAMU]** Apakah keduanya dipegang orang yang sama, hanya pemiliknya yang tahu.
Yang jelas, kalimat "satu pemotret, satu perangkat" tidak boleh ditulis.
