# SayIt — Status Proyek

**Per 28 Oktober 2026.** Semua angka di sini **terukur**, bukan perkiraan. Yang belum
pernah diukur ditulis **BELUM ADA** dan tidak diisi tebakan.

Disusun menjawab daftar pertanyaan tim. Urutan bagian mengikuti urutan pertanyaannya.

---

## Ringkasan: posisi terhadap target PRD

| Metrik | Hasil | Target | Status |
| :--- | :--- | :--- | :--- |
| **Nominal uang** (total yang diucapkan) | **73 benar / 8 salah / 0 diam dari 81** = **90,1%** | >= 85% | **TERCAPAI** |
| **Tanggal kedaluwarsa** | **13 benar / 1 salah / 2 diam dari 16** = **81%** | >= 70% | **TERCAPAI** |
| **CER dokumen** | 15,3% dari 13 dokumen (9,0% pada 11 foto bagus) | <= 15% | meleset 0,3 poin |
| Latensi uang / perintah suara | 1,4 detik / 1,3 detik | <= 8 detik | **LOLOS** |
| Latensi dokumen / kedaluwarsa | 11,5 detik / 11,4 detik | <= 8 detik | **menyimpang, diterima** |
| Tes otomatis | 648 lulus | semua lulus | **LOLOS** |

**Cara membaca angka akurasi di proyek ini.** Kami **tidak pernah** melaporkan satu
persentase saja, melainkan **benar / salah / diam**. Alasannya bukan gaya penulisan:
bagi pengguna tunanetra, nominal atau tanggal yang **salah** jauh lebih berbahaya
daripada sistem yang **diam**, karena ia tidak punya cara memeriksanya. Dua kondisi
dengan persentase sama bisa sangat berbeda bahayanya. Prinsip ini sudah terbukti
tiga kali di proyek ini (rinciannya di `docs/keputusan-teknis.md`).

---

## 1. Gambaran aplikasi

**Bentuk dan platform.** Progressive Web App (PWA) yang dibuka lewat peramban HP,
bisa dipasang ke layar utama. Frontend Next.js, backend Python FastAPI.

```
web/      Next.js App Router (JavaScript, tanpa TypeScript)
server/   FastAPI yang membungkus seluruh pipeline
```

Ada juga panel uji internal berbasis Streamlit (`app.py`) untuk memeriksa modul satu
per satu tanpa suara. Itu alat pengembang, bukan keluaran untuk pengguna.

**Sasaran pengguna: tunanetra sebagai sasaran utama.** Seluruh keputusan desain
berangkat dari asumsi pengguna **tidak melihat layar sama sekali**: area sentuh adalah
seluruh layar (bukan tombol kecil), setiap jawaban diucapkan **dan** masuk wilayah
`aria-live`, dan setiap peringatan wajib **berbunyi** serta menyebut **tindakan
berikutnya**, bukan hanya kesalahannya. Pengguna low vision ikut terlayani — zoom
sengaja tidak dikunci (`maximumScale` dibuang karena mengunci zoom melanggar WCAG 1.4.4)
— tetapi bukan sasaran yang dioptimalkan.

**Ketiga fitur sudah terintegrasi dalam satu aplikasi.** Satu alur, satu foto, satu
pertanyaan. Pengguna tidak memilih menu fitur; ia memotret lalu **bertanya dengan
suara**, dan router intent yang menentukan fitur mana yang dijalankan. "Ini uang
berapa" menjalankan modul uang, "bacakan tulisannya" menjalankan modul dokumen,
"kapan kedaluwarsanya" menjalankan modul tanggal.

**Kebutuhan internet.** Sebagian besar berjalan **lokal**:

| Bagian | Lokal / Daring |
| :--- | :--- |
| Deteksi nominal uang (YOLOv8n) | lokal |
| Deteksi zona tanggal (YOLOv8n) | lokal |
| OCR dokumen (EasyOCR) | lokal |
| OCR kedaluwarsa (PaddleOCR) | lokal |
| Pengenalan suara / STT (faster-whisper small) | lokal |
| Jawaban tetap: nominal, tanggal, pesan galat | lokal (klip MP3 tersimpan, 88 klip) |
| **Pembacaan teks dokumen** | **daring (gTTS)** |

Jadi satu-satunya bagian yang wajib internet adalah **membacakan isi dokumen**, karena
teksnya tidak bisa diketahui sebelumnya sehingga tidak bisa disiapkan sebagai klip.

**Catatan privasi yang harus disebut:** teks dokumen yang dibacakan **dikirim ke server
Google** lewat gTTS. Karena itu ada aturan internal: jangan menguji dengan dokumen
pribadi asli.

Backend saat ini berjalan di laptop pengembang dan diekspos lewat ngrok. Bukan hosting
permanen — itu keterbatasan yang disadari.

---

## 2. Cara kerja setiap fitur

### 2.1 Uang

**Nominal yang didukung: tujuh kelas** — 1.000, 2.000, 5.000, 10.000, 20.000, 50.000,
100.000. **Hanya nominal, bukan tahun emisi.** Model tidak membedakan emisi 2016 dan
2022; itu bukan dimensi label dan tidak pernah ada di datanya.

**Beberapa lembar: didukung secara kode, tetapi buktinya tipis.** Pasca-pemrosesan
menghitung lembar per nominal lalu menjumlahkannya. Masalahnya **data uji banyak lembar
hampir tidak ada — hanya satu foto** (dua lembar 2.000). Foto itu dijawab benar.
Jadi penghitungan banyak lembar **belum bisa diklaim terbukti**; itu kejujuran yang
harus ditulis di laporan.

**Keluaran menyebut ketiganya: jumlah lembar, nominal per jenis, dan total.** Contoh
untuk satu lembar:

> "Uang seratus ribu rupiah."

Untuk beberapa lembar:

> "Terdeteksi tiga lembar. Dua lembar lima puluh ribu rupiah, dan satu lembar sepuluh
> ribu rupiah. Totalnya seratus sepuluh ribu rupiah."

Kalau model tidak yakin (ada kotak berbeda kelas yang bertindihan, atau tidak ada
deteksi di atas ambang), sistem **tidak menyebut angka sama sekali** dan meminta foto
ulang. Itu disengaja: diam lebih baik daripada salah.

**Pasca-pemrosesan** (ini bagian yang sering terlupa saat membandingkan angka):
1. Ambang skor `score_min = 0,30`
2. Buang kotak bersarang (>= 85% luasnya di dalam kotak lain sekelas)
3. Buang deteksi yang skornya < 0,80 x deteksi terkuat di foto yang sama
4. Periksa konflik antar-kelas yang bertindihan

Langkah 3 baru ditambahkan dan dampaknya besar — lihat Bagian 6.

### 2.2 Tanggal kedaluwarsa

**Cara menemukan area tanggal: dua jalur, dengan jalur cadangan.**

1. **Jalur zona.** Model YOLOv8n kedua (`best_zone.pt`) mencari area tanggal pada
   kemasan. Kalau skornya >= 0,40, area itu dipotong (dengan margin 10%), lalu hanya
   potongan itu yang di-OCR.
2. **Jalur cadangan.** Kalau zona tidak ketemu, **atau** potongannya ternyata tidak
   menghasilkan tanggal, sistem meng-OCR **seluruh gambar**.

Yang penting dipahami: **jalur zona adalah optimasi KECEPATAN, bukan ketepatan.** Pada
16 kemasan uji, akurasinya sama saja dengan atau tanpa jalur zona (81% keduanya), tetapi
mematikannya memperburuk latensi dari 11,4 detik menjadi 27,3 detik.

**Teknologi pengenalan teks: PaddleOCR** (model `PP-OCRv5_mobile_det`). Ini hasil ablasi
terukur pada 16 kemasan, bukan pilihan selera:

| | EasyOCR | PaddleOCR |
| :--- | :--- | :--- |
| Benar / Salah / Diam | 3 / 2 / 11 | **7 / 0 / 9** |
| Detik per foto | 3,5 | 24,9 |

PaddleOCR jauh lebih tepat walau tujuh kali lebih lambat. Setelah perbaikan lanjutan,
akurasinya naik sampai 81%.

**Rotasi.** Pengguna tunanetra tidak bisa memastikan arah kemasan. Sistem menangani ini
sebagai **percobaan ulang saat gagal**: kalau pembacaan pertama tidak menghasilkan
tanggal, gambar diputar 180°, lalu 90°, lalu 270°. Foto yang sudah tegak dijawab di
percobaan pertama dan tidak membayar biaya apa pun.

**Format tanggal yang didukung** (semuanya punya kasus ujinya sendiri):
- Lengkap berpemisah: `08/10/2026`, `08-10-2026`, `08.10.2026`
- Bulan-tahun: `10/2026`, `10-26`
- Nama bulan: `08 OKT 2026`, `OKT 2026` (Indonesia dan Inggris)
- **Rapat tanpa pemisah**: `210829`
- **Berpemisah spasi**: `EXP 08 10 26`, `10 2026`

**Cara membedakan dari tanggal produksi dan kode bets** — ini bagian yang paling rawan,
dan jawabannya berlapis:

1. **Penanda kata.** Kata seperti `EXP`, `BAIK SEBELUM`, `BEST BEFORE`, `KEDALUWARSA`
   menaikkan prioritas sebuah kandidat. Kata `MFG`, `PROD` menurunkannya.
2. **Saklar `require_marker_for_compact`.** Format rapat (`210829`) paling mudah
   tertukar dengan kode produksi. Saklar ini menentukan apakah format itu boleh diterima
   tanpa penanda. **Nilainya milik mesin OCR, bukan keputusan global** — dengan EasyOCR
   melonggarkannya menguntungkan, dengan PaddleOCR merugikan.
3. **Tahun wajib empat digit** untuk pola bulan-tahun berspasi. Aturan ini sendirian
   **menghapus dua jawaban salah** pada pengukuran 02-10.

Bahaya nyatanya sudah dibuktikan dengan kasus uji: teks `NO BETS 210829 ISI 250 G`
**lolos menjadi tanggal** kalau syarat penanda dilonggarkan. Karena itu setiap kali mesin
OCR diganti, pengukuran ini wajib diulang.

### 2.3 Dokumen

**Jenis dokumen.** Teks cetak di atas kertas — surat, pengumuman, selebaran, ketentuan.
**Bukan** tulisan tangan, dan belum diuji pada tabel atau formulir berkolom.

**Bahasa: Indonesia dan Inggris** (`languages: [id, en]` pada EasyOCR).

**Satu halaman saja.** Untuk unggahan PDF dan DOCX pun hanya halaman pertama yang
dibaca. PDF dan DOCX yang **sudah berteks tidak di-OCR sama sekali** — teksnya diambil
langsung, jadi hasilnya sempurna dan cepat. OCR hanya dipakai untuk PDF hasil pindai.

**Cara menjaga urutan bacaan.** EasyOCR mengembalikan kotak setingkat **baris**, bukan
kata. Kotak-kotak itu dikelompokkan menjadi baris lalu paragraf memakai toleransi
relatif terhadap tinggi huruf, lalu diurutkan atas-ke-bawah, kiri-ke-kanan.

**Pembacaan dipotong 40 kata per bagian.** Setelah satu bagian selesai, sistem berkata
"katakan lanjut", dan perintah LANJUT membacakan bagian berikutnya. Posisi bacaan
disimpan, jadi pengguna tidak kehilangan tempat.

**Sebelum OCR** gambar melewati koreksi perspektif dan pelurusan kemiringan (deskew),
supaya halaman yang difoto miring tetap terbaca urut.

---

## 3. Alur interaksi pengguna

### 3.1 Memilih fitur dan memulai

**Tidak ada menu fitur.** Alurnya: **foto → tanya dengan suara → dengar jawaban.**
Fitur mana yang jalan ditentukan dari pertanyaannya.

Saat aplikasi dibuka, klip sambutan langsung berbunyi dan menjelaskan apa yang bisa
dilakukan. Ini **satu-satunya pintu masuk** bagi pengguna yang tidak melihat layar,
jadi diperlakukan khusus: klipnya diambil saat halaman dibuka (bukan saat disentuh)
supaya tidak terblokir aturan autoplay iOS.

### 3.2 Tombol dan perintah suara

**Keduanya ada, dan semua tombol punya padanan suara.** Area sentuh utama adalah
**seluruh layar**, bukan tombol kecil — pengguna tidak perlu mencari apa pun.

Perintah suara yang dikenali: pertanyaan tugas (uang / bacakan / kedaluwarsa) dan
perintah kendali: **ULANGI, LANJUT, FOTO LAGI, BANTUAN, KELUAR, PUTAR KAMERA,
PILIH BERKAS**.

Perintah kendali dicocokkan **persis**, tanpa fuzzy matching. Ini bukan kemalasan:
fuzzy yang longgar pernah membuat "uang" cocok dengan "ulang". Kata kunci di bawah
6 huruf harus cocok persis.

Satu pengecualian yang dilonggarkan dengan sengaja: **BANTUAN**. Isinya memuat nama
aplikasi yang paling sering salah ditranskrip, dan diukur hanya 5 dari 15 ucapan wajar
yang dikenali. Setelah dilonggarkan: 13 dari 13. Risikonya kecil — salah memicu BANTUAN
hanya membacakan satu kalimat, tidak seperti KELUAR yang menutup aplikasi.

**Barge-in**: pengguna bisa memotong suara yang sedang berbicara dengan menyentuh layar.

**Hening 3 detik** mengakhiri perekaman pertanyaan. Kalau yang terekam hanya hening,
sistem **memasang mikrofon lagi** alih-alih mengirim hening ke server — dulu ini
membuat lingkaran tanpa akhir "suaramu tidak terdengar jelas".

**Idle 30 detik** menutup aplikasi dengan sendirinya.

### 3.3 Petunjuk mengarahkan kamera

**Ini kelemahan yang paling jujur harus disebut: belum ada panduan arah kamera.**

Yang ada baru **quality gate** — foto diperiksa ketajaman dan pencahayaannya, dan kalau
tidak layak pengguna diminta memotret ulang dengan pesan yang menyebut sebabnya
("fotonya terlalu gelap"). Itu umpan balik **sesudah** memotret, bukan panduan **saat**
memotret.

Untuk uang dan dokumen ini belum jadi penghambat karena objeknya besar. Untuk
kedaluwarsa masalahnya nyata: pengguna tunanetra tidak tahu tanggal tercetak di sisi
mana kemasan. Pilihan yang sudah dipetakan: panduan suara saat membidik, pemindaian
ubin pada foto resolusi penuh, atau beberapa foto sekaligus. **Belum dikerjakan**, dan
sengaja ditunda karena penghambat utamanya saat ini bukan pembidikan melainkan
pengenalan cetakan (lihat Bagian 4).

### 3.4 Contoh kalimat hasil dan kalimat gagal

| Keadaan | Yang diucapkan |
| :--- | :--- |
| Uang satu lembar | "Uang lima puluh ribu rupiah." |
| Uang beberapa lembar | "Terdeteksi tiga lembar. Dua lembar lima puluh ribu rupiah, dan satu lembar sepuluh ribu rupiah. Totalnya seratus sepuluh ribu rupiah." |
| Uang tidak yakin | "Saya kurang yakin. Coba foto ulang dengan cahaya lebih terang." |
| Kedaluwarsa terbaca | "Kedaluwarsa 8 Oktober 2026, sekitar dua bulan lagi." |
| Kedaluwarsa kurang yakin | dibacakan dengan awalan "kurang yakin" |
| Tanggal tidak ketemu | "Saya tidak menemukan tanggal kedaluwarsa. Coba dekatkan kamera ke tulisan tanggalnya." |
| Foto terlalu gelap | "Fotonya terlalu gelap. Coba foto ulang di tempat yang lebih terang." |
| Server tidak terjangkau | diucapkan oleh peramban sendiri, karena server memang tidak bisa dihubungi |

**Durasi dibacakan dalam satuan yang bisa dibayangkan**, bukan ratusan hari. Di bawah
7 hari tetap hari, 7–59 hari jadi minggu, 60–364 jadi bulan, di atas itu tahun. Angka
yang dibulatkan **wajib** didahului kata "sekitar" — sistem tidak boleh terdengar lebih
yakin daripada yang sebenarnya.

### 3.5 Mengulang dan menghentikan

- **ULANGI** — mengulang jawaban terakhir
- **LANJUT** — bagian berikutnya dari dokumen
- **FOTO LAGI** — membuang foto, kembali ke kamera
- **KELUAR** — menutup aplikasi
- **Sentuh layar** — memotong suara yang sedang berbicara (barge-in)

---

## 4. Status terbaru per fitur

| Fitur | Status | Kendala utama |
| :--- | :--- | :--- |
| **Uang** | **Sudah diuji, target tercapai** | Data uji banyak lembar hanya 1 foto |
| **Kedaluwarsa** | **Sudah diuji, target tercapai** | Pengenalan cetakan kemasan; latensi 11,4 detik |
| **Dokumen** | **Sudah berjalan, diuji sebagian** | CER meleset 0,3 poin; latensi 11,5 detik |
| **Aplikasi web (PWA)** | **Sudah berjalan** | Backend masih di laptop + ngrok, bukan hosting tetap |
| **Suara (STT + TTS)** | **Sudah berjalan** | Data uji STT dari 1 penutur saja |
| **Uji pengguna** | **BELUM ADA** | Belum dijadwalkan |

### Yang belum terintegrasi

**Semua fitur sudah terintegrasi.** Yang belum selesai bukan integrasi, melainkan:

1. **Hosting backend permanen.** Sekarang laptop + ngrok. URL ngrok berganti tiap
   restart. Sudah ada jalan keluarnya (basis API bisa diganti lewat `?api=` dengan
   daftar putih host), tetapi itu penambal, bukan solusi.
2. **Uji pengguna proksi + kuesioner SUS.** Belum dilakukan sama sekali.
3. **Satu keputusan konfigurasi masih terbuka** — lihat Bagian 6.

### Kendala utama per fitur

**Uang.** Delapan jawaban salah yang tersisa semuanya **salah kenal kelas pada satu
lembar tunggal** (bukan salah hitung lembar). Kelas terlemah sekarang: 1.000 (3 dari 4),
10.000 (8 dari 10), 50.000 (5 dari 6), 2.000 (16 dari 19). Kelas 100.000 dan 20.000
sudah sempurna. Tidak ada parameter lagi yang bisa disetel — yang tersisa hanya foto
latih baru untuk kelas lemah.

**Kedaluwarsa.** Penghambatnya **pengenalan cetakan, bukan pembidikan**, dan ini sudah
dibuktikan: foto yang dipotong **tepat pada tanggalnya** pun 0 benar dari 5 pada
pengukuran lama. Cetakan dot-matrix dan inkjet pada kemasan memang sulit. Lompatan ke
81% datang dari mengganti mesin OCR, bukan dari membidik lebih baik.

**Dokumen.** CER 15,3% meleset 0,3 poin dari target, dan penyebabnya sempit: dua foto
lama yang sebenarnya **tangkapan layar**, bukan foto kertas (CER 76,9% dan 22,0%).
**Pada 11 foto sesi yang bagus CER-nya 9,0%**, jauh di bawah target. Mengganti dua foto
itu dengan foto asli kemungkinan besar menuntaskannya — perkiraan kerja 20 menit.

### Penyimpangan dari PRD yang diterima dengan sengaja

Tiga, dan semuanya harus disebut di laporan akhir:

1. **Latensi NFR-01.** Dokumen dan kedaluwarsa 11,4–11,5 detik, target <= 8 detik.
   Tiga cara menurunkannya sudah dicoba dan **semuanya gagal** tanpa mengorbankan
   akurasi: perkecil gambar ke 800 px (akurasi 81% → 56% **dan** latensi malah naik ke
   20,2 detik), matikan rotasi (akurasi −12%), matikan jalur zona (latensi → 27,3 detik).
2. **`money.score_min` 0,30, PRD menulis 0,50.** Hasil sapuan ambang terukur.
3. **`bright.min_mean` 245, PRD menulis 220.** Ambang PRD menolak foto dokumen yang sah
   karena kertas putih memang terang.

---

## 5. Bukti yang bisa dilampirkan

| Bukti | Ada? | Letak |
| :--- | :--- | :--- |
| Hasil uji uang per foto | **ADA** | `money_kfold_v2_kfold_totals.csv` (81 baris) |
| Sapuan ambang skor uang | **ADA** | `money_kfold_v2_sapuan_ambang.csv` |
| Confusion matrix + kurva PR/F1 | **ADA** | `docs/jurnal_bahan/val_sendiri/` |
| Grafik training (loss, mAP, 100 epoch) | **ADA** | `docs/jurnal_bahan/grafik_training.png` |
| Hyperparameter lengkap (113 kunci) | **ADA** | `docs/jurnal_bahan/args.yaml` |
| Contoh prediksi benar / salah / diam | **ADA** | `docs/jurnal_bahan/contoh_prediksi/` |
| Waktu inferensi per foto | **ADA** | `docs/jurnal_bahan/waktu_inferensi.csv` |
| Ablasi pra-pemrosesan | **ADA** | `docs/jurnal_bahan/ablasi_clahe_v2.csv` |
| Riwayat tiap keputusan + angkanya | **ADA** | `docs/keputusan-teknis.md` |
| **Tangkapan layar / video demo** | **BELUM ADA** | perlu dibuat |
| **Contoh gambar masukan + keluaran kedaluwarsa** | **BELUM ADA** sebagai berkas rapi | foto mentahnya ada |
| **Hasil uji pengguna** | **BELUM ADA** | belum dilakukan |

### Cara menilai (supaya angkanya bisa diperiksa)

**Uang — metrik TOTAL.** Yang dinilai adalah **apakah jumlah rupiah yang diucapkan ke
pengguna benar**, bukan apakah kotaknya pas. Ini sengaja: satu lembar 100.000 yang
terdeteksi dua kali tetap "benar" menurut metrik kelas, tetapi diucapkan "dua ratus ribu
rupiah" — dan itulah yang dialami pengguna.

**Jumlah sampel: 81 foto sendiri**, dinilai dengan **validasi silang 5-lipatan**. Tiap
foto diuji **tepat sekali** oleh model yang belum pernah melihatnya. Pembagian lipatan
dilakukan atas **kelompok kemiripan** (perceptual hash), bukan atas berkas, supaya dua
foto nyaris identik tidak terpisah antara data latih dan data uji.

**Kedaluwarsa: 16 kemasan**, dinilai dengan membandingkan tanggal yang diucapkan dengan
tanggal yang tercetak.

**Dokumen: 13 dokumen**, dinilai dengan Character Error Rate terhadap transkrip manual.

### Contoh kesalahan uang yang tersisa (8 dari 81)

| Foto | Seharusnya | Dijawab |
| :--- | ---: | ---: |
| SENDIRI_01208 | 10.000 | 2.000 |
| SENDIRI_01237 | 2.000 | 1.000 |
| SENDIRI_01253 | 50.000 | 10.000 |
| SENDIRI_01216 | 10.000 | 2.000 |
| SENDIRI_01217 | 1.000 | 2.000 |
| SENDIRI_01247 | 2.000 | 50.000 |
| SENDIRI_01235 | 2.000 | 20.000 |
| SENDIRI_01274 | 5.000 | 2.000 |

Semuanya **satu lembar dijawab satu lembar** — murni salah kenal nominal, tidak ada lagi
kesalahan menghitung jumlah lembar.

### Keterbatasan data uji yang wajib disebut

- **81 foto dari sedikit latar dan sedikit kamera.** Validasi silang tidak bisa mengarang
  variasi yang tidak ada di datanya.
- **Sebaran kelas sengaja tidak seimbang**: 1.000 hanya 4 foto, 5.000 ada 21.
- **Foto banyak lembar hanya satu.**
- **Data uji STT dari satu penutur**, jadi akurasi router pada kalimat orang lain masih
  optimistis.
- **Angka k-fold mengukur PROSEDURNYA**, bukan bobot akhir. Model akhir dilatih pada
  semua foto, jadi tidak ada data tersisa untuk mengujinya. Pengujian sebenarnya hanya
  bisa dengan foto yang benar-benar baru.

---

## 6. Konfirmasi hasil uang

### a. Apakah pelatihan ulang 23 Oktober sudah selesai?

**Sudah.** Selesai **26 Oktober 2026**.

| | Nilai |
| :--- | :--- |
| Nama run | `money_kfold_v2_final` |
| Arsitektur | YOLOv8n, 7 kelas |
| Epoch | 100 (penuh) |
| Data latih | 81 foto sendiri + dataset publik |
| Bobot | `models/best_money.pt`, MD5 `bc09a6fc2c9fedbb38c39aa8aba44672` |

**Bobotnya sudah dipasang ke aplikasi pada 28 Oktober 2026.** Model lama disimpan
sebagai `models/best_money_SEBELUM_v2.pt`.

### b. Apakah CLAHE masih digunakan dalam aplikasi?

**Ya, masih.** Rangkaian pra-pemrosesan uang masih `[resize, clahe]`.
**Dan ini keputusan yang masih terbuka**, bukan keputusan yang sudah diambil.

Duduk perkaranya: **notebook melatih model pada gambar ASLI** — tidak ada CLAHE di jalur
latihnya sama sekali — sedangkan **aplikasi menerapkan CLAHE saat inferensi**. Jadi
distribusi gambar saat dipakai berbeda dari saat dilatih.

Akibatnya **angka 90,1% itu diukur TANPA CLAHE**, sementara aplikasi berjalan DENGAN
CLAHE. Selama ini keduanya tidak pernah diukur berdampingan, jadi selisihnya tidak
terlihat.

Yang sudah terukur:

| Kondisi | Model | Data | Hasil |
| :--- | :--- | :--- | :--- |
| `resize + clahe` | v1 | 32 foto bersih | **65,6%** |
| `resize` saja | v1 | 32 foto bersih | **87,5%** |
| `resize + clahe` | v2 | 81 foto (tercemar) | 96,3%, 46,9 ms |
| `resize` saja | v2 | 81 foto (tercemar) | 97,5%, **30,8 ms** |

**Kejujuran yang penting:** pada model v2 selisihnya kecil (1,2 poin), tetapi angka itu
diukur pada foto yang **semuanya ikut melatih model**, jadi hafalan menutupi efeknya.
**Untuk v2 belum ada pengukuran CLAHE yang bersih.** Yang kuat tetap bukti v1
(+21,9 poin) ditambah mekanisme yang masuk akal dan latensi yang 34% lebih cepat.

**Catatan untuk nilai mata kuliah:** membuang CLAHE dari rangkaian `uang` **tidak
menghapus teknik pengolahan citra klasik dari proyek**. Langkahnya tetap ada,
tetap dipakai rangkaian dokumen, dan sekarang justru punya **ablasi terukur** — bentuk
bukti yang memang diminta. Hasil ablasi yang negatif tetap hasil ablasi.

### c. Apakah 28/32 atau 87,5% masih hasil terbaru?

**Bukan. Angka itu sudah usang.** 87,5% adalah **model v1** pada 32 foto bersih tanpa
CLAHE, diukur 23 Oktober.

Yang berlaku sekarang: **73 benar / 8 salah / 0 diam dari 81 foto = 90,1%**, dari
validasi silang 5-lipatan model v2, 26 Oktober.

### d. Angka baru yang menggantikan angka lama

| Angka lama | Status | Pengganti |
| :--- | :--- | :--- |
| 65,7% (35 foto, 06-10) | usang | 90,1% |
| 68,8% (48 foto, 22-10) | usang | 90,1% |
| 87,5% (32 foto bersih v1, 23-10) | usang | 90,1% |
| 84,0% (81 foto, 26-10) | **usang — salah hitung** | 90,1% |
| mAP50 0,957 / 0,977 | **jangan dipakai** | bukan metrik sistem |

**Soal 84,0%.** Angka itu sempat dilaporkan pada 26 Oktober dan **terlalu rendah karena
bug alat ukur**: evaluasi notebook tidak menerapkan penyaring skor relatif yang dipakai
aplikasi. Terlihat dari polanya — **5 dari 13 jawaban salah berbentuk "1 lembar dijawab
2 lembar"**, misalnya 100.000 dijawab 102.000. Setelah penyaring itu diterapkan, kelima
kesalahan tersebut hilang seluruhnya dan angkanya menjadi 90,1%.

**Soal mAP.** Nilai mAP50 0,957 dan 0,977 pernah muncul di berkas bahan jurnal.
**Keduanya tidak boleh dipakai sebagai akurasi sistem**: yang pertama dihitung pada foto
yang ikut melatih model, yang kedua pada split validasi dataset publik yang labelnya
diketahui bermasalah. mAP menilai kotak dan kelas per deteksi; yang dialami pengguna
adalah total yang diucapkan.

### Sapuan ambang skor (bukti `score_min` 0,30)

| Ambang | Benar | Salah | Diam | Akurasi |
| ---: | ---: | ---: | ---: | ---: |
| 0,15 | 73 | 8 | 0 | 90,1% |
| 0,20 | 73 | 8 | 0 | 90,1% |
| 0,25 | 73 | 8 | 0 | 90,1% |
| **0,30** | **73** | **8** | **0** | **90,1%** |
| 0,35 | 72 | 7 | 2 | 88,9% |
| 0,40 | 71 | 7 | 3 | 87,7% |
| 0,50 | 70 | 7 | 4 | 86,4% |
| 0,60 | 63 | 6 | 12 | 77,8% |

Nilai 0,30 dipertahankan. Menurunkannya tidak menambah apa pun; menaikkannya ke 0,35
menukar satu jawaban benar dengan dua kali diam, hanya untuk mengurangi satu jawaban
salah.

---

## 7. Berkas rujukan

| Berkas | Isi |
| :--- | :--- |
| `docs/PRD_SayIt_v2_1.md` | persyaratan lengkap |
| `docs/keputusan-teknis.md` | riwayat tiap keputusan beserta angkanya |
| `docs/jurnal_bahan/` | keluaran mentah eksperimen model uang |
| `docs/deploy.md` | langkah menjalankan dan menyebarkan |
| `config/settings.yaml` | seluruh parameter, berkomentar lengkap |
| `notebooks/04_money_kfold.ipynb` | notebook validasi silang |
| `README.md` | cara menjalankan |

**Catatan cara kerja tim:** `python -m pytest -q` wajib lulus sebelum dan sesudah setiap
perubahan. Saat ini **648 tes lulus**.
