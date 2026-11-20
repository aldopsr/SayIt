# Bahan jurnal — modul pembacaan tanggal kedaluwarsa SayIt

Berkas ini **mandiri**: ditulis untuk penulis jurnal yang tidak mengikuti pengembangan
harian. Semua angka di sini berasal dari `docs/keputusan-teknis.md` dan dapat dilacak ke
tanggal pengukurannya. Tidak ada angka di berkas ini yang diperkirakan.

Disusun 20 November 2026.

---

## 1. Apa yang modul ini kerjakan

Pengguna tunanetra memotret kemasan produk dan bertanya dengan suara ("kapan
kedaluwarsanya?"). Sistem membaca tanggal kedaluwarsa dari foto itu lalu membacakannya.

Alurnya (PRD 8.8), dari foto sampai jawaban:

1. **Deteksi zona** — YOLOv8n mencari wilayah yang memuat tanggal (`models/best_zone.pt`).
2. **Potong** zona itu dengan margin 10%.
3. **Pra-pemrosesan** potongan (saat ini hanya `resize`).
4. **OCR** pada potongan (PaddleOCR).
5. **Parser tanggal** — aturan pola, bukan pembelajaran mesin (`sayit/vision/date_parser.py`).
6. **Jalur cadangan**: bila zona tidak ketemu atau potongannya gagal, OCR seluruh gambar.
7. **Percobaan ulang rotasi**: bila seluruh alur gagal, diulang pada foto yang diputar
   180°, 90°, 270°.

---

## 2. Metrik dan cara mengukurnya

**WAJIB dilaporkan sebagai tiga angka, bukan satu persentase:**

| label | arti |
|---|---|
| **BENAR** | tanggal yang dijawab sama dengan tanggal di kemasan |
| **SALAH** | sistem menjawab sebuah tanggal, tetapi tanggalnya keliru |
| **DIAM** | sistem menjawab "tidak menemukan tanggal" |

**Alasannya harus ditulis di jurnal, karena ini keputusan rancangan, bukan gaya
pelaporan:** bagi pengguna tunanetra, tanggal kedaluwarsa yang **salah lebih berbahaya
daripada tidak ada jawaban** — ia bisa memakan produk kedaluwarsa tanpa curiga,
sementara jawaban "tidak terbaca" membuatnya mencari bantuan. Jadi dua kondisi dengan
akurasi sama belum tentu sama baiknya.

Prinsip ini **sudah tiga kali terbukti perlu** di proyek ini:

- 29-09: kondisi tanpa pra-pemrosesan berskor lebih TINGGI (25% lawan 19%) tetapi
  mengarang tiga tanggal salah (`mentega` 2027-03-11 dijawab 2022-02-28, `chees`
  2027-03-21 dijawab 2023-08-31, `tolakangin2` 2028-04 dijawab 2022-01).
- 01-10: melonggarkan satu syarat parser menambah satu benar **dan** satu salah.
- 02-10: perbaikan parser yang keliru menambah dua salah tanpa mengubah jumlah benar.

**Data uji:** 16 foto kemasan yang dipotret sendiri, di `data/uji_kedaluwarsa/`.
14 di antaranya punya tanggal kedaluwarsa; 2 sengaja tidak punya (`tidakada_permen1`,
`tidakada_permen2`) untuk menguji bahwa sistem tidak mengarang tanggal.
Tanggal harapan dibaca dari **nama berkas** (misalnya `20270311_mentega.JPG` =
11 Maret 2027), jadi tidak ada anotasi manual yang bisa menyimpang.

**Skrip:** `python scripts\ukur_kedaluwarsa.py`

---

## 3. Hasil utama

| metrik | hasil | target PRD | |
|---|---|---|---|
| Akurasi tanggal kedaluwarsa | **81%** (BENAR 13 / SALAH 2 / DIAM 1) | ≥ 70% | **TERCAPAI** |
| mAP@0,5 model zona | **tidak diukur** (lihat 3.1) | ≥ 0,75 | **tidak dapat disimpulkan** |

### 3.1 mAP model zona: tidak diukur, dan alasannya harus ditulis apa adanya

PRD Bagian 11 menargetkan mAP@0,5 ≥ 0,75 untuk model deteksi zona. **Angka itu tidak
ada, dan sengaja tidak diisi dengan pengganti.** Tiga sebabnya:

1. **Tidak ada kotak acuan.** mAP menghitung IoU antara kotak prediksi dan kotak
   sebenarnya. 16 kemasan uji hanya punya tanggal harapan di nama berkasnya, bukan
   koordinat kotak. Folder `data/zona_sendiri/` yang disiapkan untuk itu masih kosong.
2. Dataset yang melatih `best_zone.pt` ada di Roboflow, tidak di repositori.
3. **Yang paling menentukan:** mAP dari split test dataset itu **sesumber dengan data
   latihnya**, jadi nilainya optimistis — persis jebakan yang sudah tiga kali terjadi di
   proyek ini. Mengisi sel PRD dengan angka seperti itu lebih buruk daripada
   membiarkannya kosong, karena pembaca akan membacanya sebagai bukti tentang kemasan
   Indonesia.

**Pengganti yang SAH dan terukur** (sapuan ambang pada 16 kemasan sendiri, tanpa OCR):

| ambang skor | zona ketemu / 14 bertanggal | laju | deteksi palsu / 2 tanpa-tanggal |
|---|---|---|---|
| 0,15 | 12 / 14 | 86% | **0 / 2** |
| 0,25 | 11 / 14 | 79% | **0 / 2** |
| **0,40 (dipakai)** | **9 / 14** | **64%** | **0 / 2** |
| 0,50 | 8 / 14 | 57% | **0 / 2** |
| 0,60 | 7 / 14 | 50% | **0 / 2** |

Dua hal yang layak disebut:

- **Nol deteksi palsu di SELURUH ambang**, bahkan 0,15. Model tidak mengarang zona pada
  kemasan yang tidak punya tanggal.
- Angka ini **mereproduksi persis** catatan 30-09 ("9 dari 14, skor 0,43–0,77") setelah
  hampir dua bulan — skor terendah yang lolos 0,43, tertinggi 0,77. Reproduksi
  independen, dan layak disebut justru karena angka 81% **tidak** dapat direproduksi.

**WAJIB ditulis bahwa 64% itu BUKAN recall dan BUKAN mAP.** Tanpa kotak acuan, sebuah
"ketemu" tidak berarti kotaknya di tempat yang benar. Buktinya ada di data yang sama:
**`chees` terdeteksi dengan skor 0,72 — tertinggi ketiga — dan kotaknya menunjuk NOMOR
PRODUKSI**, yang justru sebab jawabannya salah. Dalam mAP sungguhan berkas itu dihitung
*false positive*. Jadi **64% adalah batas atas**, dan recall sebenarnya lebih rendah.

Cara mendapatkan mAP sungguhan: labeli 14 kemasan bertanggal itu dengan kotak YOLO
(kotak mengelilingi **tanggalnya saja**, bukan seluruh kemasan) sesuai petunjuk di
`data/zona_sendiri/README.md`. Itu juga akan memberi angka pada distribusi yang benar —
kemasan Indonesia — bukan pada dataset latihnya.

Diukur 17 November 2026. **Versi perangkat yang WAJIB ikut ditulis di jurnal**
(tanpa ini angkanya tidak bisa direproduksi siapa pun):

- paddleocr **3.7.0**, paddlepaddle **3.3.1**
- model deteksi teks **PP-OCRv5_mobile_det**
- model pengenal teks **PP-OCRv6_medium_rec**
- bobot zona `models/best_zone.pt` (YOLOv8n, 1 kelas)
- `line_grouping: rantai`, `expiry.preprocess_chain: hanya_resize`,
  `resize.max_side: 1600`, `zone_score_min: 0.40`

### Riwayat akurasi

| tanggal | akurasi | rincian | penyebab perubahan |
|---|---|---|---|
| 29-09 | **19%** | — | dasar awal, mesin EasyOCR |
| 30-09 | **31%** | 5 / 0 / 11 | syarat penanda pada format rapat dimatikan |
| 30-09 | **44%** | 7 / 2 / 7 | dua bug diperbaiki (lihat bagian 4.2) |
| 02-10 | **81%** | 13 / 1 / 2 | **pindah mesin OCR ke PaddleOCR** |
| 17-11 | **81%** | 13 / 2 / 1 | `line_grouping: rantai` jadi bawaan |

**Peringatan penulisan:** kelima baris itu **tidak diukur pada kondisi yang identik** —
sebagiannya pada 21 foto, sebagiannya pada 16 kemasan, sebagian dengan jalur zona
dimatikan. Jangan menyajikannya sebagai satu progresi terkendali. Yang sah dikatakan:
"akurasi naik dari 19% menjadi 81% melalui empat perubahan, dan lompatan terbesar
berasal dari penggantian mesin OCR."

Perhatikan juga **arah kesalahan** berubah antara 02-10 dan 17-11: komposisinya 13/1/2
menjadi 13/2/1 pada akurasi yang sama. Ini jujur harus disebut dan tidak dapat
ditelusuri, karena riwayat Git proyek baru mulai 11 Oktober sedangkan angka 02-10
diukur sembilan hari sebelumnya.

---

## 4. Uji ablasi — ini bagian terpenting untuk jurnal

### 4.1 TEMUAN TERKUAT: nilai pra-pemrosesan BERBALIK ARAH tergantung mesin OCR

| modul | mesin OCR | dengan pra-pemrosesan | tanpa | arah |
|---|---|---|---|---|
| Kedaluwarsa | EasyOCR | 44% | 38% | **MEMBANTU +6%** |
| Kedaluwarsa | PaddleOCR | 69% | **81%** | **MERUGIKAN −12%** |
| Dokumen | PaddleOCR | CER 9,4% | CER 12,3% | MEMBANTU +2,9% |

**Jadi pertanyaan "apakah pra-pemrosesan citra meningkatkan akurasi OCR" tidak punya
satu jawaban.** Ia bergantung pada mesin OCR dan pada modulnya. Ini temuan ablasi
terkuat di seluruh proyek dan layak jadi inti jurnal.

Penjelasan mekanismenya: PaddleOCR punya normalisasi internalnya sendiri, dan rangkaian
`kedaluwarsa` yang meng-*upscale* 2× menambahkan kerusakan di atas normalisasi itu.

**Konsekuensi untuk aplikasi:** pra-pemrosesan kedaluwarsa dikurangi menjadi `resize`
saja. `resize` tetap wajib ada — ia pengendali latensi untuk foto ponsel 3024×4032.

### 4.2 Pra-pemrosesan agresif TERBANTAH: binarisasi dan morfologi dibuang

PRD 8.8 langkah 3 merencanakan binarisasi + morfologi untuk menyambung cetakan
dot-matrix yang terputus-putus. **Diuji pada 9 potongan zona sungguhan: binarisasi
memberi 0 jawaban benar** dan hampir selalu menghasilkan teks kosong.

Empat rangkaian diuji. Threshold + morfologi justru merusak (keluarannya berupa
potongan tak bermakna seperti "r 1." dan "1 8 1 4.", atau kosong).
**Binarisasi menghapus cetakan tipis alih-alih menyambungnya** — kebalikan dari dugaan
PRD. Rangkaian tanpa binarisasi paling banyak berhasil.

Dua bug yang diperbaiki 30-09 (31% → 44%):

- (a) binarisasi dibuang dari rangkaian `kedaluwarsa`
- (b) `full_image_fallback`: jalur zona kini **mundur** ke OCR seluruh gambar bila
  potongannya tidak menghasilkan tanggal — karena zona adalah **petunjuk letak, bukan
  komitmen**

### 4.3 Ablasi mesin OCR (PRD ablasi nomor 2)

Rancangan sengaja **mengisolasi mesin**: jalur zona dan percobaan rotasi dimatikan,
gambar diseragamkan, sehingga yang dibandingkan benar-benar mesinnya.

| kondisi | EasyOCR | PaddleOCR |
|---|---|---|
| penanda wajib | 3 / 2 / 11 **(19%)** | 7 / 0 / 9 **(44%)** |
| penanda dilonggarkan | 5 / 2 / 9 **(31%)** | 8 / 1 / 7 **(50%)** |
| detik per foto | **3,5** | 24,9 |

Diulang pada 1600 px dengan `mobile_det`: PaddleOCR **11 / 0 / 5 = 69%**, 12,9 s/foto.

**PaddleOCR 7 benar dengan NOL salah adalah profil keamanan terbaik yang pernah
terukur di proyek ini.** Pemilihan EasyOCR sebelumnya dilakukan **tanpa perbandingan
sama sekali**, dan itu terbukti mahal — layak ditulis sebagai pelajaran metodologi.

**PENTING:** angka 19%–69% di tabel ini untuk membandingkan **MESIN**, bukan untuk
dilaporkan sebagai akurasi sistem. Akurasi sistem adalah **81%** dari pipeline penuh.

### 4.4 Temuan metodologi: hasil uji mesin TERISOLASI tidak berpindah ke pipeline penuh

Ablasi terisolasi menyarankan agar syarat penanda (`require_marker_for_compact`)
**dinyalakan** bersama PaddleOCR. Diuji di pipeline sungguhan 16-11:

| saklar | hasil | median latensi |
|---|---|---|
| `false` (dipakai) | **12 / 3 / 1 = 75%** | 10,5 s |
| `true` | 9 / 2 / 5 = 56% | 19,1 s |

Menyalakannya **menukar 3 jawaban benar demi 1 jawaban salah** (`ajinomoto`,
`miesedap`, `merica` menjadi DIAM), dan latensi naik karena tiap DIAM memicu percobaan
rotasi.

Pola yang sama terulang pada pola parser `dmy_spasi`: +1 benar di uji mesin, **nol
efek** di pipeline. **Kesimpulan metodologis yang layak jurnal: uji komponen terisolasi
berguna untuk memilih komponen, tetapi keputusan konfigurasi wajib diukur di pipeline
penuh.**

### 4.5 Ablasi lain yang dijalankan, semuanya NEGATIF atau NETRAL

| yang diuji | hasil | kesimpulan |
|---|---|---|
| Resolusi gambar (`max_side` 1600 / 2600 / 4032) | hasil **tidak berubah**, waktu 39 → 75 detik | resolusi bukan penghambat |
| Rotasi foto | bukan penyebab kegagalan | sudah dieliminasi |
| Pengelompokan baris `pita` lawan `rantai` | 75% lawan **81%** | `rantai` dipakai |
| Penanda negatif parser | 13/2/1 lawan **13/2/1, identik per berkas** | NETRAL; dipertahankan demi tes bahaya |
| `zone_score_min` 0,40 lawan 0,25 | **81%** lawan 75% | 0,40 dipertahankan |
| Model zona 4 kelas | lihat bagian 4.6 | NEGATIF |
| Rotasi potongan (`rotate_crop`) | **tidak terukur** — 0 dari 16 kemasan mencapai langkah itu | tidak bisa disimpulkan |

### 4.6 Percobaan model zona 4 kelas — temuan negatif (20 November 2026)

**Hipotesis:** model zona sekarang hanya mengenal satu kelas (`expired_date_zone`).
Dataset publik ExpDate memakai empat kelas (`date`, `code`, `due`, `prod`). Dengan empat
kelas, wilayah **kode produksi** bisa ditolak **sebelum OCR** — menyerang akar jawaban
salah `chees`, yang menjawab dari nomor produksi 210526.

Dua model dilatih, empat kondisi diukur pada 16 kemasan:

| bobot | BENAR | SALAH | DIAM | median | zona ketemu |
|---|---|---|---|---|---|
| **1 kelas (dipakai)** | **13** | 2 | 1 | **7,82 s** | **7/16** |
| 4 kelas, satu dataset | 13 | **0** | 3 | 20,23 s | 2/16 |
| 4 kelas, dua dataset digabung | 13 | **0** | 3 | 20,18 s | 3/16 |
| gabungan, ambang diturunkan 0,25 | 12 | 1 | 3 | 10,43 s | 4/16 |

**Hasilnya negatif: model 1 kelas menang di akurasi (81% lawan 75%) DAN latensi.**
Tiga hipotesis terbantah datanya:

1. Menggabungkan dua dataset akan memulihkan cakupan zona — **tidak**, 2/16 → 3/16.
2. Ambang 0,40 membuang zona `date` yang sah — **tidak**; kotak berskor rendah itu
   wilayah yang memang salah, dan menurunkan ambang menukar satu jawaban benar jadi
   salah.
3. Latensi 20 detik adalah harga model 4 kelas — **bukan**; deteksi zonanya 6,6 ms.
   20 detik itu **gejala** cakupan zona yang runtuh, sehingga 13 berkas jatuh ke jalur
   cadangan yang jauh lebih lambat.

**Yang dibelinya pengetahuan, bukan model**, dan ketiganya layak ditulis:

- Kesadaran kelas **memang bekerja**. Dibuktikan dengan menjalankan deteksi pada ambang
  0,01: `chees` memberi `code` 0,75 / `date` 0,54 / `date` 0,47; `code` ditolak,
  `date` 0,54 dipakai, dan jawabannya berubah dari SALAH menjadi DIAM. Mekanismenya
  benar — yang gagal cakupannya.
- Kelas `due` layak ditolak: ia penanda ("EXP"), bukan tanggalnya.
- Jalur zona terbukti ulang sebagai optimasi **latensi**, bukan akurasi.

---

## 5. Penghambat sejati: pengenalan cetakan, bukan pembidikan

Ini kesimpulan teknis terpenting modul ini, dan **sudah dibuktikan dua kali, termasuk
membantah dugaan tim sendiri.**

Dugaan awal: pengguna tunanetra tidak tahu tanggal tercetak di sebelah mana, jadi
masalahnya pembidikan. **Diuji 30-09 dengan memotong foto tepat pada tanggalnya:
0 benar dari 5.** Keluaran OCR pada potongan yang sempurna berupa deretan angka dan
tanda acak, dan pada satu kemasan kosong sama sekali.

**Jadi memotret dari dekat adalah alat DIAGNOSIS, bukan perbaikan.** Diperkuat lagi oleh
uji lapangan 12-11 pada kemasan Indomie: zona ketemu dengan skor 0,755 (pembidikan
benar), potongan benar, tetapi OCR membaca sampah di keempat rotasi.

Penyebabnya **cetakan dot-matrix / inkjet pada kemasan**, yang karakternya terputus
titik-titik, sering di atas plastik mengkilap dengan refleksi. Ini di luar kemampuan
pengenal OCR umum yang dilatih pada teks cetak rapi.

Dua jawaban salah yang tersisa, keduanya kegagalan **parser** bukan OCR — OCR membaca
angkanya dengan benar, penafsirannya yang keliru:

- `chees`: menjawab dari **nomor produksi** 210526 padahal MAR ada di sebelahnya.
- `ovaltine`: teks LOT 2 09.27 dibaca menjadi 2027-09-30, meleset **tiga hari**.

---

## 6. Latensi — dan cara mengutipnya tanpa menyesatkan

| intent | latensi end-to-end | target NFR-01 | |
|---|---|---|---|
| Uang | 1,4 s | ≤ 8 s | LOLOS |
| Kendali | 1,3 s | ≤ 8 s | LOLOS |
| Dokumen | 11,5 s | ≤ 8 s | **penyimpangan** |
| Kedaluwarsa | 11,4 s | ≤ 8 s | **penyimpangan** |

**Penyimpangan NFR-01 diterima dengan sengaja**, dan dasarnya harus ditulis: PRD baris
154 menyatakan target latensi bersifat awal dan boleh direvisi setelah pengukuran, dan
FR-14 (pengumuman "sedang saya proses") sudah diimplementasikan sehingga pengguna tidak
menunggu dalam kesunyian.

Tiga tuas dicoba untuk menurunkannya dan **semuanya gagal**:

| tuas | akibat |
|---|---|
| Perkecil gambar ke 800 px | akurasi 81% → 56% **dan** latensi 11,4 → 20,2 s |
| Matikan percobaan rotasi | akurasi −12% |
| Matikan jalur zona | latensi 11,4 → 27,3 s |

**Temuan yang menjelaskan kenapa ketiganya gagal, dan ini layak jurnal: akurasi dan
latensi TERKAIT lewat mekanisme percobaan ulang.** Gambar lebih kecil lebih cepat per
panggilan OCR, tetapi menurunkan akurasi; dan setiap kegagalan memicu empat lintasan
rotasi — sehingga totalnya justru **lebih lambat**. Kesimpulan metodologis: **jangan
mengoptimasi latensi tanpa mengukur akurasi pada saat yang sama.**

### Cara mengutip angka latensi

1. **Sebutkan median DAN terburuknya.** Median 7,82 detik, tetapi `tolakangin2` memakan
   **90 detik** dan `tolakangin1` 41 detik. Menulis median saja membuat pembaca
   menyangka setiap pengguna menunggu 8 detik.
2. **Latensi modul ini berderau besar antar-sesi pengukuran.** Kondisi yang sama persis
   memberi median 6,54 s dan 10,46 s pada hari yang sama, dan 9,96 s lawan 7,82 s pada
   hari lain — simpangan sampai 60% dari beban laptop. **Yang sah dikutip adalah
   perbandingan DI DALAM satu sesi pengukuran, bukan angka detiknya secara mutlak.**

---

## 7. Batas klaim — apa yang TIDAK boleh ditulis

| jangan tulis | tulis ini |
|---|---|
| "Pra-pemrosesan citra meningkatkan akurasi OCR" | "Arah pengaruhnya berbalik tergantung mesin OCR: membantu +6% pada EasyOCR, merugikan −12% pada PaddleOCR" |
| "Akurasi sistem 81%" tanpa rincian | "BENAR 13 / SALAH 2 / DIAM 1 dari 16 kemasan" |
| "Sistem bekerja pada kemasan Indonesia" | "Diukur pada 16 kemasan yang dipotret sendiri; n kecil, satu lingkungan, satu perangkat" |
| "Latensi 11,4 detik" | "Median 11,4 detik dengan kasus terburuk puluhan detik; pengukuran berderau sampai 60% antar-sesi" |
| "Jalur zona meningkatkan akurasi" | "Jalur zona adalah optimasi latensi: akurasi 81% dengan maupun tanpa, tetapi mematikannya memperburuk latensi median 11,4 → 27,3 detik" |
| "Masalahnya pengguna tidak bisa membidik" | "Pembidikan terbukti BUKAN penghambat utama: foto yang dipotong tepat pada tanggalnya pun 0 benar dari 5. Penghambatnya pengenalan cetakan dot-matrix" |
| Angka 81% sebagai hasil yang reproducible | "81% diukur 17-11 dengan paddleocr 3.7.0 dan pengenal PP-OCRv6_medium_rec; pengenal itu tersimpan di luar repositori, jadi angka ini tidak dapat direproduksi dari repositori saja" |

### Keterbatasan yang wajib disebut

1. **n = 16 kemasan.** Terlalu kecil untuk pengujian signifikansi. Selisih satu foto =
   6 poin persentase. Beberapa temuan di berkas ini bersandar pada satu-dua berkas dan
   sudah ditandai begitu.
2. **Satu lingkungan, satu perangkat, satu pemotret.** Tidak ada variasi pencahayaan,
   latar, atau model ponsel yang terkendali.
3. **Belum ada tolok ukur publik.** Dataset publik ExpDate (Seker & Ahn 2022, KIST,
   CC BY 4.0, 1.767 gambar nyata) sudah ditemukan tetapi belum dipakai untuk mengukur.
   Memakainya akan menjawab langsung kelemahan n kecil ini.
4. **Angka 81% tidak dapat direproduksi dari repositori saja** (lihat tabel di atas).
5. **Lisensi dataset yang dipakai melatih model zona belum tercatat** — dataset
   `coolstuff-rfnc5/expiry-date-detection-i3bav` di Roboflow mencantumkan
   `license: null`. **Harus diperiksa dan dicatat sebelum jurnal disubmit, jangan
   ditebak.**

---

## 8. Pelajaran metodologi yang layak masuk jurnal

Enam di antaranya datang dari kesalahan yang benar-benar terjadi di proyek ini, dan
itulah sebabnya layak ditulis:

1. **Jangan menilai model dari data uji yang buruk.** Kesimpulan awal "model zona tidak
   bekerja pada kemasan Indonesia, 0 deteksi" **salah** — diambil dari foto berupa
   tangkapan layar dan bidikan jauh. Diukur ulang pada foto yang layak: **9 dari 14**
   kemasan terdeteksi, skor 0,43–0,77. Kesalahan yang sama pernah terjadi pada modul
   uang (dataset Roboflow yang labelnya tertukar) dan pada kalibrasi ambang keburaman.
2. **Uji komponen terisolasi tidak berpindah ke pipeline penuh** (bagian 4.4).
3. **Akurasi dan latensi dapat terkait lewat mekanisme percobaan ulang** (bagian 6).
4. **Satu angka akurasi menyembunyikan arah kesalahan**, dan arah itu yang menentukan
   keamanan bagi pengguna tunanetra (bagian 2).
5. **Diagnosis wajib lewat jalur yang sama dengan produksi.** Satu perbaikan dirancang
   berdasarkan teks OCR dari skrip diagnosis terpisah; di pipeline sungguhan teksnya
   berbeda sama sekali, dan perbaikan itu tidak pernah punya kesempatan bekerja.
6. **Setiap uji sapuan wajib mencetak NILAI parameter yang diuji, bukan namanya.**
   Satu sapuan pernah menukar hanya judul kolomnya sementara parameter yang benar-benar
   diuji tidak berubah — dan hasilnya terlihat masuk akal sepenuhnya.

---

## 9. Dari mana angkanya diambil

| sumber | isi |
|---|---|
| `docs/keputusan-teknis.md` | jurnal lengkap, 450 baris, setiap keputusan dengan bukti dan tanggalnya |
| `CLAUDE.md` bagian "Titik sambung" | tabel metrik PRD Bagian 11 |
| `docs/PRD_SayIt_v2_1.md` | persyaratan, target, dan rencana ablasi |
| `scripts/ukur_kedaluwarsa.py` | skrip pengukuran akurasi |
| `scripts/banding_ocr.py` | skrip ablasi mesin OCR (`--mesin`, `--sisi`) |
| `data/uji_kedaluwarsa/` | 16 foto kemasan uji |

**Catatan menjalankan ulang:** satu proses Python = **satu mesin OCR, selalu**.
Memuat PaddleOCR dan EasyOCR dalam satu proses dapat **gagal diam-diam dengan angka
yang masih terlihat masuk akal** — terukur: satu proses campuran memberi CER dokumen
10,28% dan median 77 detik, padahal proses bersih pada hari yang sama memberi 14,89%
dan 8,10 detik. Gagal diam-diam lebih berbahaya daripada *crash*, karena angkanya ikut
dipakai.
