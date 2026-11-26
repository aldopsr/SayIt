# Pencerdasan: Modul Dokumen (membacakan tulisan)

**Untuk anggota kelompok, dibuat 26 November 2026.** Modul ini yang paling banyak
**berubah** sejak versi pertama — mesin OCR-nya diganti 24 November, dan hasilnya naik di
akurasi **dan** kecepatan sekaligus. Kalau kamu pernah baca catatan lama yang menyebut
EasyOCR, itu sudah tidak berlaku.

Anggap kamu belum pernah lihat kodenya. Istilah teknis dijelaskan di tempatnya.

> **Kode yang dibahas:** `sayit/vision/document.py` (777 baris — modul terbesar di proyek),
> `sayit/vision/preprocess.py`, dan `vision.document` di `config/settings.yaml`.

---

## 1. Tugas modul ini

Pengguna memotret surat, halaman buku, atau pengumuman, lalu bilang
*"bacakan tulisannya"*. Modul ini **membacakan isinya**.

Kalau tulisannya panjang, dibacakan **40 kata sekali jalan**, lalu pengguna bisa bilang
*"lanjut"* untuk potongan berikutnya. Itu PRD 8.7, dan alasannya praktis: mendengar 300
kata tanpa jeda tidak bisa diikuti, dan tidak bisa diulang sebagian.

Selain foto, modul ini juga menerima **unggahan berkas**: gambar, PDF, dan DOCX.

---

## 2. Alurnya

```
  FOTO HP
     |
     +- 1. Penjaga mutu       -> gelap / buram / silau? tolak
     +- 2. Pra-pemrosesan     -> resize, koreksi perspektif, deskew, CLAHE
     +- 3. PaddleOCR          -> kotak + teks, SETINGKAT BARIS
     +- 4. Buang skor rendah  -> text_score_min 0,4
     +- 5. Kelompokkan        -> kotak jadi BARIS, baris jadi PARAGRAF
     +- 6. Susun teks         -> paragraf diberi titik supaya ada jeda saat dibaca
     +- 7. Penjaga mutu baca  -> bacaan meragukan? jangan dibacakan
     +- 8. Potong 40 kata     -> potongan pertama dibacakan, sisanya tunggu "lanjut"
```

Langkah 5 itu bagian yang paling banyak kodenya, dan paling sering salah dipahami.
Bagian 4 di bawah menjelaskan kenapa langkah itu ada sama sekali.

---

## 3. OCR: PaddleOCR di atas ONNX Runtime

**OCR** = *Optical Character Recognition*, mengubah gambar tulisan jadi teks.

Sampai 24 November modul ini memakai **EasyOCR**. Sekarang **PaddleOCR**, dijalankan oleh
mesin **ONNX Runtime**.

> **ONNX Runtime itu bukan model baru.** Modelnya sama persis, bobotnya sama persis. Yang
> berganti hanya **program yang menjalankan** model itu. Analoginya: lagu yang sama,
> pemutar yang berbeda.
>
> | | sebelum (EasyOCR) | sesudah (PaddleOCR + ONNX) |
> | :--- | :--- | :--- |
> | Salah baca (CER) | 14,9% | **9,0%** |
> | Median detik per halaman | 8,04 | **2,08** |
> | Terburuk | 12,29 s | **2,62 s** |
> | Satu giliran dokumen penuh | 11,72 s | **3,38 s** |
>
> **Menang di dua-duanya sekaligus** — lebih akurat *dan* hampir 4 kali lebih cepat. Itu
> jarang terjadi; biasanya satu harus dikorbankan.
>
> Dan **nol dependensi baru, nol konversi, tanpa paddle2onnx**: `onnxruntime` ternyata sudah
> ikut terpasang sejak lama, dan paddlex mengunduh sendiri varian `*_onnx` dari model yang
> sama. Saklarnya cuma satu baris: `vision.document.paddle.engine: onnxruntime`.

**Model yang dipakai:** `PP-OCRv5_mobile_det` (pencari lokasi tulisan) +
`PP-OCRv5_mobile_rec` (pembaca hurufnya). Dua tahap — ini penting untuk bagian 9.

> **Pengenalnya BERBEDA dari modul kedaluwarsa, dan itu terukur.** `PP-OCRv5_mobile_rec`
> yang menang di sini **menjatuhkan akurasi kemasan dari 81% ke 62%**. Cetakan dot-matrix
> kemasan butuh pengenal yang lebih besar (`PP-OCRv6_medium_rec`); kertas A4 tidak.
> Jadi: **mesin sama, pembaca beda.**

### Apa itu CER

**CER** = *Character Error Rate*. Dari 100 huruf, berapa yang salah — salah baca, hilang,
atau ditambahkan. Jadi **semakin kecil semakin bagus**, kebalikan dari persentase akurasi
lainnya. Target PRD: **<= 15%**. Kita sekarang **9,0%**.

---

## 4. Langkah 5: kenapa kotak harus dikelompokkan jadi baris

OCR tidak mengembalikan "teks halaman". Ia mengembalikan **daftar kotak**, masing-masing
dengan teksnya, dan **tanpa urutan yang bermakna**. Kalau daftar itu digabung apa adanya,
yang keluar adalah kalimat yang teracak.

PaddleOCR (dan EasyOCR) mengembalikan kotak **setingkat BARIS**, bukan per kata. Karena itu
tipenya di kode bernama `TextBox` dan ambangnya `text_score_min`, bukan `word_score_min` —
penamaan itu sengaja, supaya tidak ada yang menyangka isinya kata.

Pengelompokannya dua tingkat, dan **semua toleransinya relatif terhadap tinggi huruf**,
bukan piksel tetap — supaya aturan yang sama berlaku untuk foto dari dekat maupun jauh:

| Pengaturan | Nilai | Artinya |
| :--- | :--- | :--- |
| `line_tolerance_ratio` | 0,6 | dua kotak sebaris kalau beda pusat vertikalnya < 0,6 x tinggi huruf |
| `line_slope_gap_ratio` | 3,0 | celah mendatar maksimum antar-kotak sebaris |
| `paragraph_gap_ratio` | 1,6 | jarak antar-baris di atas ini berarti **ganti paragraf** |

Paragraf yang tidak diakhiri tanda baca **diberi titik**, supaya pemotongan 40 kata bisa
memotong per kalimat dan suaranya tidak terdengar menyambung tanpa jeda.

### Dua cara mengelompokkan baris, dan kenapa yang kedua yang dipakai

**Cara 1: `pita`** — taksir satu angka **kemiringan** untuk seluruh halaman
(`estimate_text_slope`), luruskan nilai `y` tiap kotak terhadap kemiringan itu, lalu
kelompokkan.

**Cara 2: `rantai`** (**dipakai sekarang**, sejak 17 November) — **tidak ada taksiran
kemiringan sama sekali.** Tiap kotak menyambung ke baris yang ujung kanannya **paling
dekat** dan masih sejajar dengannya. Perbandingannya selalu terhadap kotak tepat
sebelumnya, jadi baris yang melengkung diikuti **apa adanya**, seberapa pun lengkungnya.

**Buktinya datang dari modul KEDALUWARSA, bukan dari dokumen:**

| Cara | Akurasi kedaluwarsa (16 kemasan) |
| :--- | :--- |
| `pita` | 12 / 3 / 1 = 75% |
| **`rantai`** | **13 / 2 / 1 = 81%** |

Yang berubah **hanya satu berkas**: `mentega` dari SALAH jadi BENAR, **nol regresi** pada
15 lainnya. Sebabnya: tanggal mentega tercetak **DIAGONAL** — `02:31`(x995) `NS`(831)
`27`(680) `MAR`(418) `11`(238), jadi x **turun** saat y naik. Kemiringan sejatinya
**-0,418**, di atas batas `line_slope_max` 0,35 sehingga dibuang jadi 0; sedangkan taksiran
median seluruh potongan cuma **-0,196** karena blok tabel gizi di atasnya hampir datar.

> **Satu angka kemiringan tidak muat untuk dua blok berorientasi berbeda.** Itu masalah yang
> **sama persis** dengan halaman buku melengkung, muncul di modul yang berbeda.

Harganya di modul dokumen: CER **14,89% menjadi 14,94%** (era EasyOCR) — 1 membaik,
1 memburuk, 11 tetap. Di dalam derau.

> **PENTING kalau kamu mau menyentuh ini:** saklar `line_grouping` hidup di
> `vision.document`, **tetapi modul kedaluwarsa memakai `compose_text` yang sama.** Jadi
> mengubahnya **SELALU menyentuh kedua modul**, dan keduanya wajib diukur bersamaan.

---

## 5. Dua mode tata letak

Satu aturan urutan bacaan tidak muat untuk semua foto:

| Mode | Untuk apa | Cara kerjanya |
| :--- | :--- | :--- |
| `dokumen` | kertas, surat, halaman buku | teks mengalir satu kolom dari kiri atas |
| **`tersebar`** (dipakai) | kemasan, papan tulis, papan nama | teks berupa blok terpisah; tiap gugus disusun sendiri lalu diurutkan atas-bawah, kiri-kanan |

Ada juga mode `auto` yang memilih sendiri dari petunjuk `document_found` (apakah koreksi
perspektif menemukan lembar kertas).

> **`auto` DITOLAK**, dan sebabnya lucu: ia memilih **persis terbalik** — mode `tersebar`
> untuk **seluruh 13 dokumen A4**, dan mode `dokumen` untuk **2 papan nama**. Jadi
> petunjuknya memang ada dan gratis, tetapi arahnya kebalikan dari dugaan. Bawaannya
> dipatok `tersebar`.

---

## 6. Rotasi: putar SELURUH gambar, bukan tiap baris

Kalau foto masuk terbalik, OCR menghasilkan sampah. Dua cara memperbaikinya, dan keduanya
sudah diukur pada 13 dokumen yang diputar 180 derajat (31 Oktober):

| Cara | CER setelah dipulihkan | Biaya |
| :--- | :--- | :--- |
| `rotation_info` EasyOCR (putar tiap **baris**) | 96,2% menjadi 68,8% | **5,2x** |
| **Putar seluruh GAMBAR** | 96,2% menjadi **15,3%** | 4 lintasan |

15,3% itu **sama persis dengan baseline foto tegak** — pemulihannya total.

> **Sebabnya, dan ini penjelasan yang bagus untuk ditanya:** yang gagal pada gambar terbalik
> adalah tahap **DETEKSI**, bukan pengenalan — **193 kotak lawan 887** pada gambar yang sama.
> Dan deteksi butuh gambar tegak. **Memutar baris yang tidak pernah terdeteksi tidak
> menolong apa pun.** Karena itu `rotation_info: []` (mati), dan
> `rotate_retry: [180, 90, 270]` yang dipakai.

Dua detail yang menentukan:

**(a) Kapan rotasi dicoba?** Hanya kalau bacaannya **mencurigakan** —
`rotate_trigger_score: 0.75`, yaitu skor rata-rata baris di bawah 0,75.

Ambang itu dikalibrasi pada **14 foto buku dari HP pengguna**, lima di antaranya terpotret
miring **tanpa disengaja** — jadi datanya bukan rotasi buatan skrip. Pemisahannya **bersih**:
foto tegak berskor serendah **0,768**, foto miring setinggi **0,715**, dan 0,75 jatuh tepat
di celah itu. Hasilnya **5/5 foto miring terdeteksi, 0/9 foto tegak salah terpicu.**

**(b) Sudut mana yang dipilih?** Yang menghasilkan **kata terbanyak**.
Diukur pada 13 dokumen: menebak sudut benar **13/13**, setara batas atas oracle. Skor
rata-rata cuma 12/13, jumlah kotak juga 12/13. Alasannya: sudut keliru menghasilkan banyak
potongan pendek tak bermakna, sudut benar menghasilkan kalimat utuh.

**(c) Penjaga mutu dinilai SESUDAH rotasi, bukan sebelum.** Rotasi memperbaiki mutu bacaan,
jadi menilai sebelum rotasi akan menyatakan foto miring "kurang jelas" padahal ia bisa pulih
sepenuhnya — terukur, pemulihannya sampai **8x jumlah kata**.

---

## 7. Penjaga mutu bacaan: lebih baik bilang tidak jelas daripada mengarang

`unclear_score_min: 0.75`. Kalau skor rata-rata baris di bawah itu, jawabannya
**"tulisannya kurang jelas"** — bukan membacakan susunan kata acak.

> **Kenapa ini penting:** membacakan kata acak dengan **nada seyakin jawaban benar** lebih
> berbahaya bagi pengguna tunanetra daripada berkata tidak tahu. Pengguna tidak punya cara
> memeriksanya sendiri. Modul uang dan tanggal sudah punya penjaga semacam ini sejak awal;
> modul tulisan baru dapat 31 Oktober.

Diukur pada 35 foto: **6 dari 8 bacaan buruk tertangkap, 0 dari 27 bacaan baik salah
ditandai.** Foto mentega yang OCR-nya rusak kini tidak dibacakan.

Penanda **kedua** pernah dicoba — rasio kotak yang lolos ambang dibanding yang terdeteksi
(`unclear_kept_ratio_min`). **TIDAK TERBUKTI**, dan sekarang dimatikan (`null`). Keduanya
dibuat bisa dimatikan sendiri-sendiri supaya bisa diablasi terpisah.

---

## 8. Pra-pemrosesan: di sini ia MEMBANTU, dan itu kabar bagus

Rangkaian `dokumen`: **`[resize, perspective, deskew, clahe]`**.

| Langkah | Gunanya, bahasa manusia | Catatan |
| :--- | :--- | :--- |
| `resize` | foto HP 3024x4032 diperkecil ke maks **1600** px | pengendali latensi utama |
| `perspective` | kertas yang difoto miring diluruskan jadi seperti dilihat dari atas | Canny + approxPolyDP, lalu warp |
| `deskew` | memutar foto yang sedikit miring supaya barisnya lurus | dari `minAreaRect`, batas 15 derajat |
| `clahe` | perataan kontras: bagian gelap diterangkan **tanpa** membuat bagian terang jadi putih polos | pada kanal L ruang warna LAB |

**`denoise` DIBUANG 29 September** karena **menaikkan CER 2,2%.** Ia masih ada di `STEPS`
tetapi tidak dipakai rangkaian mana pun.

**`perspective.min_area_ratio` dinaikkan 0,25 ke 0,50 pada 29 September**, setelah satu
salah kenal terbukti **merusak satu halaman utuh** — kontur yang dikira kertas ternyata
objek lain, dan warp-nya menghancurkan teksnya. Ada juga batas atas 0,95: di atas itu yang
"ditemukan" adalah bingkai gambar, bukan kertas (terbukti pada citra acak: 0,977).

### Hasil ablasi PRD nomor 1 — dan ia BERBALIK ARAH

| Mesin OCR | dengan pra-pemrosesan | tanpa |
| :--- | :--- | :--- |
| EasyOCR | 14,9% | **14,2%** (lebih baik tanpa) |
| **PaddleOCR + ONNX** | **9,0%** | 12,4% |

**Dengan mesin yang sekarang, pra-pemrosesan MEMBANTU 3,4 poin.** Dengan mesin yang lama ia
netral cenderung merugikan.

> **Jadi kesimpulan lama "Ablasi PRD nomor 1 negatif, pra-pemrosesan tidak meningkatkan
> akurasi" SUDAH TIDAK BERLAKU untuk mesin ini.** Kalau ada draf laporan yang masih menulis
> itu, perbaiki.
>
> Dan ini **kabar bagus untuk nilai mata kuliah**, karena yang dinilai justru teknik
> pengolahan citra klasiknya.
>
> Yang tetap benar, dan justru temuan paling menarik: **nilai pra-pemrosesan berbalik arah
> tergantung mesin OCR.** Pernah membantu +3,4 poin (dokumen, ONNX), pernah netral (dokumen,
> EasyOCR), pernah merugikan **-12 poin** (kedaluwarsa, PaddleOCR). Semuanya terukur, pada
> sistem yang sama, hanya beda mesin pembacanya. **Kalau mengutip angkanya, sebutkan mesin
> OCR-nya sekalian.**

Ablasi per langkah bisa diulang: `python scripts\ukur_dokumen.py --per-langkah`.

---

## 9. Tuas latensi yang sudah dicoba dan GAGAL

Ini bagian yang paling banyak percobaan nol-hasilnya, dan semuanya layak dilaporkan sebagai
temuan negatif.

### (a) Memperkecil gambar — tuasnya MATI

Sapuan `resize.max_side` pada 13 dokumen beracuan (era EasyOCR):

| Sisi | CER | Median | **Total** |
| :--- | :--- | :--- | :--- |
| **1600 (dipakai)** | **14,89%** | 7,85 s | **109,8 s** |
| 1200 | 15,42% | 6,28 s | 81,1 s |
| 1000 | 20,17% | 5,76 s | **117,0 s** |
| 800 | 39,54% | **24,12 s** | 316,9 s |

Lihat kolom total: **1000 px lebih LAMBAT daripada 1600 px**, padahal gambarnya lebih kecil.
Dan 800 px **tiga kali lebih lambat**.

> **Sebabnya: akurasi dan latensi TERKAIT lewat mekanisme percobaan ulang.** Gambar kecil
> menjatuhkan skor baris di bawah `rotate_trigger_score` 0,75, lalu `rotate_retry` membayar
> **empat lintasan penuh**. Per berkas: `r (10)` 8,4 menjadi 33,7 s, `r (4)` 7,5 menjadi
> 47,8 s.
>
> **Pelajarannya, dan ini aturan proyek: jangan pernah mengoptimasi latensi tanpa mengukur
> akurasi di saat yang sama.**

Dan yang rusak saat diperkecil **bukan** deteksi yang melewatkan baris, melainkan deteksi
yang **MEMECAH** baris. Jumlah kotaknya **NAIK**: `r (4)` dari 76 menjadi 99, 104, lalu
**156**. Itu **membantah** gagasan "deteksi resolusi rendah + pengenalan resolusi penuh" —
kotaknya sudah pecah sebelum sampai ke pengenalan.

### (b) `text_recognition_batch_size` — TERBANTAH

8 memberi **nol** perbaikan; 32 justru **lebih lambat** (22,3 s lawan 15,9 s bawaan).
Biarkan kosong, jangan diuji ulang.

### (c) Pembacaan per PITA — dibuat, diukur, dan TIDAK MEMBELI APA PUN

Idenya bagus: potong halaman jadi beberapa pita mendatar, OCR per pita. Biaya deteksi turun
sebanding luas, dan **memotong tidak menyentuh tinggi huruf** sehingga tidak memecah baris
seperti memperkecil.

Dibuat, dan diukur pada 13 dokumen:

| Jumlah pita | CER | Median |
| :--- | :--- | :--- |
| **1 (dipakai)** | **14,89%** | **8,26 s** |
| 2 | 14,88% | 8,66 s |
| 3 | 15,79% | 9,95 s |
| 4 | 15,24% | 17,16 s |

**Tidak ada perbaikan sama sekali.**

> **RALAT atas kesimpulan saya sendiri: angka prototipe (-37% total, -66% kata pertama)
> adalah ARTEFAK.** Prototipenya memakai `detect()` + `recognize()` terpisah, yang ternyata
> **1,8x lebih lambat** daripada `readtext()` (dasarnya 13,58 s lawan 8,26 s pada data yang
> sama). Memecah jalur yang lambat memang menolong; memecah `readtext` tidak.
> **`readtext` tidak superlinear terhadap luas gambar** — itu dugaan saya yang terbantah.

Satu sisi positif yang tetap sah: **memotong gambar TIDAK merusak urutan bacaan** (14,88%
lawan 14,89%). Kerusakan 3 pita pada prototipe datang dari **menyusun teks PER PITA**, bukan
dari pemotongannya.

`bands: 1` tetap bawaan. Kodenya ditahan atas keputusan pengguna sebagai **mekanisme yang
dibutuhkan pembacaan bertahap nanti**, bukan karena ia membeli sesuatu sekarang.

### (d) Yang masih masuk akal: pembacaan BERTAHAP

Terukur pada dokumen `r (11)` (303 kata):

| | Waktu |
| :--- | :--- |
| OCR seluruh halaman | 20,3 s |
| **Durasi dibacakan** (TTS sungguhan, 102 kata/menit) | **177,8 s** |

**Anggaran tambahannya +157,5 detik — 10x, bukan tipis.** Artinya sistem punya waktu
berlimpah untuk meng-OCR bagian bawah halaman **sambil** membacakan bagian atas. Tapi
mengucapkan pita 1 lebih dulu **berarti** menyusun teks per pita, dan di situlah harganya
(lihat (c)). Ini pekerjaan yang belum dilakukan, dan menyentuh `document.py`, `pipeline.py`
(posisi LANJUT), server, mungkin klien.

---

## 10. Angka

| Yang diukur | Hasil | Target |
| :--- | :--- | :--- |
| **CER** | **9,0%** | <= 15% — **tercapai dengan margin besar** |
| Median per halaman | **2,08 s** | — |
| Terburuk per halaman | **2,62 s** | — |
| Satu giliran penuh | **5,0 s** | <= 8 s — **lolos** |
| Giliran terburuk | 9,5 s | sebagian foto masih lewat |

Diukur pada **13 dokumen beracuan** (ada teks acuan yang diketik manual untuk
membandingkan).

> **Margin CER dulu hampir habis.** Pada era EasyOCR angkanya 14,94% lawan target 15% —
> **margin 0,06 poin**, artinya perubahan apa pun yang menambah 0,06 poin saja akan
> membuatnya gagal. Setelah pindah ke ONNX margin itu jadi 6 poin. Sebutkan riwayat ini
> kalau ditanya "kenapa dulu tidak diganti lebih awal".

> **Satu putaran pengukuran tidak boleh dikutip.** Putaran PERTAMA hari itu memberi dokumen
> **12,4 detik**, dan itu artefak transien; putaran kedua memberi **5,0 detik**. Yang kedua
> dipercaya **bukan karena lebih bagus**, melainkan karena cocok dengan pengukuran komponen
> terpisah (STT 1,3 + pipeline 2,6 + TTS 1,2).

### Penyimpangan NFR-01 sudah DICABUT

Dulu latensi dokumen **11,5 detik** dan kedaluwarsa 11,4 detik, melewati batas 8 detik, dan
itu dicatat sebagai **penyimpangan yang disadari**. Setelah ONNX, keempat intent lolos.
**Penyimpangan itu dicabut 24 November.**

Tiga tuas pernah dicoba sebelum ONNX dan semuanya gagal: gambar 800 px (akurasi 81% ke 56%
**dan** latensi 11,4 ke 20,2 s), matikan rotasi (akurasi -12%), matikan jalur zona (latensi
11,4 ke 27,3 s). Yang akhirnya menyelesaikannya **bukan** penyetelan parameter, melainkan
**mengganti mesinnya**.

---

## 11. Unggahan berkas: PDF dan DOCX tidak di-OCR

Kalau penggunanya mengunggah PDF atau DOCX yang **punya lapisan teks**, teksnya **diambil
langsung** — **tidak di-OCR sama sekali**. Teksnya sudah akurat; meng-OCR-nya hanya akan
menambahkan kesalahan dan waktu.

OCR hanya dipakai untuk **PDF hasil pindai** (yang isinya gambar).

Dua batasan yang disengaja:
- **Hanya halaman pertama.**
- **Tanpa dependensi baru:** `pypdfium2` sudah ikut terpasang bersama paddlex, dan DOCX
  cuma berkas zip berisi XML.

Fungsinya `result_dari_teks()`: ia melewati OCR dan pengelompokan baris, tetapi memakai
**pemotongan 40 kata yang sama** dengan jalur foto.

---

## 12. Masalah yang BELUM selesai: urutan bacaan foto buku

Kalau yang difoto adalah **halaman buku yang dipegang**, urutan bacaannya masih kacau.
Contoh kerusakannya: dua baris berbeda tersisip jadi satu kalimat —
*"cara yang dapat digunakan untuk mencegah 3b. Ada beberapa berdarah"*.

**Dua dugaan sudah DIBANTAH datanya:**

| Dugaan | Hasil pengukuran |
| :--- | :--- |
| "Dua halaman melengkung berlawanan" | Membelah halaman di selokan terlebarnya hampir tidak mengubah taksiran: **-0,0276** (sisi kiri) lawan **-0,0282** (seluruh halaman) |
| "Gugus menggumpal jadi satu" | Pengelompokan gugus sudah memisahkan halaman seberang dengan **benar**: 121 kotak lawan 18 |

**Penjelasan yang tersisa: halamannya MELENGKUNG**, bukan miring rata. Di tengah halaman
barisnya hampir datar, mendekati jilidan ia menukik sampai **-0,18**. Jadi satu angka
kemiringan **tidak akan pernah muat** — dan median justru memilih bagian yang paling datar,
karena itu bagian yang paling banyak.

`line_grouping: rantai` secara konsep menjawab ini: ia mengikuti baris apa adanya tanpa
taksiran kemiringan. **Tetapi itu masih penilaian mata, belum terbukti** — teks acuan untuk
foto buku belum dibuat, jadi tidak ada CER yang bisa dibandingkan. Penggantian ke `rantai`
**dibenarkan oleh angka kedaluwarsa, bukan oleh klaim ini.**

Akar masalah lainnya yang sudah ditemukan: **`deskew` SALAH UKUR pada foto buku.** Ia
memakai `minAreaRect` atas seluruh piksel, jadi bentuk yang dominan adalah **halaman dan
latar meja**, bukan baris teksnya. Itu persis jebakan yang sudah tertulis di docstring-nya
sendiri. Penangkalnya `line_slope_correct` — kemiringan ditaksir dari **kotak OCR sendiri**,
jadi tidak perlu menyentuh citra sama sekali. Perbaikan itu memberi CER **15,30% menjadi
14,89%**: 3 dokumen membaik, 10 tetap, **0 memburuk**.

---

## 13. Kalau ditanya — jawaban siap pakai

**"Pakai OCR apa?"**
PaddleOCR, dijalankan di atas ONNX Runtime. Model `PP-OCRv5_mobile_det` untuk mencari lokasi
tulisan dan `PP-OCRv5_mobile_rec` untuk membaca hurufnya. Sampai 24 November kami memakai
EasyOCR; pindah ke PaddleOCR+ONNX memperbaiki CER dari 14,9% ke 9,0% **sekaligus** membuatnya
4 kali lebih cepat.

**"CER 9% itu bagus atau jelek?"**
Target PRD <= 15%, jadi tercapai dengan margin 6 poin. Perlu diingat CER itu **semakin kecil
semakin bagus** — dari 100 huruf, 9 salah. Rata-ratanya diseret dua foto lama yang berupa
tangkapan layar; pada foto HP sungguhan jauh lebih baik.

**"Kenapa bukan Tesseract / Google Vision API?"**
Google Vision butuh internet dan berbayar per permintaan, dan foto pengguna akan dikirim ke
pihak ketiga — itu masalah privasi untuk aplikasi yang membaca dokumen pribadi. Tesseract
lemah pada foto (ia dirancang untuk hasil pindai bersih). PaddleOCR jalan **lokal di CPU**
dan sudah dibandingkan dengan EasyOCR secara terukur lewat `scripts/banding_ocr.py`.

**"Kenapa perlu mengelompokkan baris? OCR kan sudah mengembalikan teks."**
OCR mengembalikan **daftar kotak tanpa urutan yang bermakna**, bukan teks halaman. Kalau
digabung apa adanya, kalimatnya teracak. Jadi urutan bacaan adalah pekerjaan kode kami, bukan
pekerjaan modelnya — dan di situlah geometri (tinggi huruf, celah, kemiringan) dipakai.

**"Pra-pemrosesannya membantu?"**
Untuk modul ini dengan mesin sekarang: **ya, 3,4 poin** (9,0% dengan, 12,4% tanpa). Tapi
jawabannya **berbalik arah** tergantung mesin OCR: dengan EasyOCR ia netral cenderung
merugikan, dan di modul kedaluwarsa ia merugikan 12 poin. Jadi pertanyaan ini tidak punya
satu jawaban umum, dan **itu justru temuan ablasi paling kuat di proyek ini.**

**"Kalau fotonya terbalik?"**
Sistem memutar seluruh gambar dan memilih sudut yang menghasilkan kata terbanyak — tebakannya
benar 13/13. Memutar **tiap baris** sudah dicoba dan jauh lebih buruk: ia cuma memulihkan CER
ke 68,8% dengan biaya 5,2x, sedangkan memutar seluruh gambar memulihkan ke 15,3%. Sebabnya
yang gagal adalah tahap **deteksi**, dan deteksi butuh gambar tegak.

**"Dokumen panjang bagaimana?"**
Dibacakan 40 kata sekali jalan (PRD 8.7), lalu pengguna bilang "lanjut". Posisi bacaannya
disimpan pipeline, jadi tidak perlu memotret ulang.

**"Kalau OCR-nya ngaco, sistem tetap membacakan?"**
Tidak. Ada penjaga `unclear_score_min: 0.75` — bacaan meragukan dijawab "tulisannya kurang
jelas". Diukur pada 35 foto: 6 dari 8 bacaan buruk tertangkap, dan **0 dari 27 bacaan baik
salah ditandai**. Membacakan kata acak dengan nada seyakin jawaban benar lebih berbahaya
daripada mengaku tidak tahu.

**"Kecepatannya kenapa dulu 11,5 detik dan sekarang 5?"**
Mesin OCR-nya diganti. Tiga tuas penyetelan parameter sudah dicoba sebelumnya dan semuanya
gagal — memperkecil gambar bahkan membuatnya **lebih lambat**, karena gambar kecil memicu
percobaan rotasi yang membayar empat lintasan penuh.

---

## 14. Yang masih kurang, jujur

| Hal | Kondisi |
| :--- | :--- |
| **Urutan bacaan foto buku masih kacau** | Sebabnya sudah ketemu (halaman MELENGKUNG), perbaikannya belum terbukti karena **teks acuan foto buku belum dibuat.** |
| **Dua foto uji berupa tangkapan layar** | Pada era EasyOCR, `ketentuan_makalah` ber-CER 76,9% dan `open_recruitment` 22,0%, dan keduanya menyeret rata-rata. Keduanya **bukan foto HP**, jadi tidak mewakili kasus pengguna. |
| **13 dokumen beracuan, dan semuanya bagus** | Pra-pemrosesan dirancang menolong foto **buruk**, sedangkan foto uji kami bagus semua. Untuk mengujinya dengan jujur butuh foto dokumen yang sengaja dibuat buruk. Belum ada. |
| **Pembacaan bertahap belum dibuat** | Anggaran waktunya berlimpah (+157,5 detik pada dokumen 303 kata), mekanismenya sudah ada (`_ocr_pita`), tapi harganya adalah penyusunan teks per pita. |
| **Hanya halaman pertama PDF/DOCX** | Batasan yang disengaja. |
| **Privasi: teks yang dibacakan dikirim ke Microsoft** | Isi dokumen disintesis langsung lewat edge-tts, jadi **jangan menguji dengan dokumen pribadi asli.** Dan jangan menyalakan `tts.cache_dynamic_text` — ia menyimpan isi dokumen pengguna ke disk permanen. |

---

## 15. Dua modul lainnya

- `docs/pencerdasan-modul-uang.md`
- `docs/pencerdasan-modul-kedaluwarsa.md`
- Gambaran besar seluruh sistem: `docs/pencerdasan.md`
- Sumber kebenaran semua angka: `docs/keputusan-teknis.md`
- Rencana awal modul ini: `docs/rencana-modul-dokumen.md`
