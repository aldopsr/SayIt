# Laporan Progres SayIt

**Mata kuliah:** Pengolahan Citra dan Visi Komputer — TRPL, Sekolah Vokasi IPB
**Tanggal:** 28 September 2026

---

## 1. Apa yang sedang kami buat

SayIt adalah aplikasi untuk **penyandang disabilitas netra**. Cara pakainya sederhana:
pengguna memotret sesuatu, bertanya dengan suara, lalu mendengar jawabannya.

Tiga hal yang bisa ditanyakan:

1. **"Ini uang berapa?"** — menyebutkan nominal uang kertas, dan menjumlahkan bila ada
   beberapa lembar.
2. **"Tolong bacakan tulisannya"** — membacakan isi dokumen atau surat.
3. **"Kapan kedaluwarsanya?"** — membacakan tanggal kedaluwarsa pada kemasan, sekaligus
   menyebut masih berlaku berapa hari lagi.

Semua jawaban keluar sebagai suara, karena pengguna tidak melihat layar.

---

## 2. Posisi sekarang secara singkat

**Perangkat lunaknya sudah jadi dan bisa dijalankan dari ujung ke ujung.** Yang sedang
kami kerjakan sekarang adalah **mengukur seberapa bagus hasilnya** dan memperbaiki
bagian yang lemah.

| Bagian | Status |
| :--- | :--- |
| Pengenalan suara (pertanyaan pengguna) | Selesai dan terukur |
| Pengolahan citra (inti mata kuliah) | Selesai dan terukur |
| Pengenalan nominal uang | Berjalan, akurasi masih di bawah target |
| Membacakan dokumen | Berjalan, belum diukur |
| Membaca tanggal kedaluwarsa | Berjalan, model pencari tanggal baru selesai dilatih |
| Menjawab dengan suara | Selesai |
| Aplikasi antarmuka | Selesai |
| Laporan dan demo akhir | Belum mulai |

Perkiraan keseluruhan: **sekitar 70% selesai.** Sisanya sebagian besar bukan menulis
program lagi, melainkan mengumpulkan data uji, mengukur, dan menyusun dokumen.

---

## 3. Teknologi yang dipakai

| Bagian | Alat | Penjelasan singkat |
| :--- | :--- | :--- |
| Bahasa pemrograman | Python 3.11 | — |
| **Pengolahan citra** | **OpenCV** | Memperbaiki foto sebelum dikenali: memperjelas kontras, mengurangi bintik, meluruskan foto yang miring, menajamkan tulisan |
| Deteksi uang | YOLOv8 | Mencari letak uang di foto lalu menebak nominalnya |
| Pencari tanggal kedaluwarsa | YOLOv8 (model kedua) | Menemukan letak tanggal pada kemasan, agar tidak perlu membaca seluruh foto |
| Membaca tulisan | EasyOCR | Mengubah tulisan di foto menjadi teks |
| Suara ke teks | faster-whisper | Mengubah pertanyaan lisan pengguna menjadi tulisan |
| Teks ke suara | gTTS | Membacakan jawaban |
| Antarmuka | Streamlit | Halaman web sederhana untuk memotret, bertanya, dan mendengar jawaban |
| Pelatihan model | Google Colab | Melatih kedua model (uang dan pencari tanggal) memakai GPU gratis |

### Mana yang kami latih sendiri, mana yang memakai yang sudah ada

Pembedaan ini kami sampaikan terbuka supaya tidak ada salah paham tentang ruang lingkup
pekerjaan kami.

**Dilatih sendiri — dua model:**

| Model | Tugas | Catatan |
| :--- | :--- | :--- |
| Pengenal nominal uang | Menemukan uang di foto dan menebak nominalnya | Dilatih ulang tiga kali berdasarkan temuan evaluasi |
| Pencari tanggal kedaluwarsa | Menemukan letak tanggal pada kemasan | Baru selesai |

Keduanya memakai **transfer learning**: kami tidak merancang arsitektur jaringan saraf
baru, melainkan memulai dari model umum yang sudah tersedia lalu melatihnya ulang untuk
mengenali objek yang kami butuhkan. Ini cara yang lazim dan sesuai untuk lingkup
prototipe.

Bagian terberatnya justru bukan proses pelatihannya, melainkan **menyiapkan datanya**:
membuang label yang tertukar, membuang salinan foto yang berulang, memastikan foto yang
mirip tidak terpisah antara data latih dan data uji, serta memilih variasi pelatihan yang
tepat.

**Memakai yang sudah tersedia — tidak kami latih:**

| Komponen | Keterangan |
| :--- | :--- |
| Pengenalan suara (faster-whisper) | Model siap pakai, kami hanya menyetel parameternya |
| Pembacaan tulisan (EasyOCR) | Model siap pakai |
| Pengucapan jawaban (gTTS) | Layanan dari Google |

**Bukan machine learning sama sekali — kami tulis sendiri sebagai program biasa:**

Seluruh tahap pengolahan citra (perbaikan kontras, reduksi derau, koreksi perspektif dan
kemiringan, binarisasi, morfologi), pemeriksaan kualitas foto, pembacaan format tanggal,
pengenalan maksud pertanyaan, penjumlahan beberapa lembar uang, dan pengubahan angka
menjadi kata.

Bagian inilah yang paling erat dengan mata kuliah, dan seluruhnya dapat dinyalakan atau
dimatikan satu per satu untuk keperluan uji ablasi.

### Bagian pengolahan citra klasik

Ini bagian yang paling ditekankan mata kuliah, dan seluruhnya sudah selesai serta
bisa dinyalakan atau dimatikan satu per satu untuk keperluan uji ablasi:

| Teknik | Gunanya | Bukti sudah berfungsi |
| :--- | :--- | :--- |
| Penyeragaman ukuran | Menyamakan skala foto dari kamera berbeda | Ambang deteksi buram jadi tidak bergantung resolusi |
| CLAHE (perbaikan kontras) | Menolong foto yang kurang cahaya | Foto redup: sebaran kecerahan naik dari 4,9 menjadi 12,9 |
| Reduksi derau | Menghilangkan bintik-bintik | Galat turun dari 19,8 menjadi 5,2 |
| Koreksi perspektif | Meluruskan kertas yang difoto miring | Keempat sudut kertas ditemukan dengan meleset kurang dari 1 piksel |
| Koreksi kemiringan | Memutar tulisan agar mendatar | Diuji pada −12° sampai +12°, sisa kemiringan 0,00° |
| Binarisasi adaptif | Memisahkan tulisan dari latar walau cahaya tidak rata | Tulisan tetap terbaca di sisi gelap maupun terang |
| Operasi morfologi | Menyambung cetakan titik-titik pada kemasan | Dari 138 titik terpisah menjadi 3 baris utuh |

### Pemeriksaan kualitas foto

Sebelum diproses, foto diperiksa dulu: terlalu buram, terlalu gelap, terlalu silau, atau
resolusinya terlalu kecil. Kalau tidak layak, pengguna langsung diberi tahu lewat suara
supaya bisa memotret ulang — bukan dibiarkan menunggu lalu mendapat jawaban yang salah.

---

## 4. Hasil pengukuran sejauh ini

Angka di bawah ini **diukur dengan foto yang kami potret sendiri**, bukan dengan data
bawaan dari internet. Alasannya dijelaskan di Bagian 5.

| Yang diukur | Target | Hasil | Keterangan |
| :--- | :---: | :---: | :--- |
| Mengenali pertanyaan lisan | salah ≤ 25% | **salah 7–8%** | Tercapai |
| Waktu menjawab pertanyaan uang | — | **0,2 detik** | Cepat |
| Waktu membacakan dokumen | ≤ 8 detik | **5,1 detik** | Tercapai |
| Waktu menjawab tanggal kedaluwarsa | ≤ 8 detik | **0,8 detik** | Tercapai, tetapi baru diukur pada gambar buatan |
| **Menebak nominal uang** | **≥ 85%** | **71%** | **Belum tercapai** |
| Membacakan isi dokumen | salah ≤ 15% | belum diukur | Menunggu foto uji |
| Membaca tanggal kedaluwarsa | ≥ 70% | belum diukur | Menunggu foto uji |
| Uji coba oleh pengguna | ≥ 80% | belum dilakukan | Direncanakan |

### Rincian pengenalan uang (35 foto)

| Nominal | Jumlah foto | Benar | Salah | Tidak dijawab |
| ---: | ---: | ---: | ---: | ---: |
| 100.000 | 6 | **6** | 0 | 0 |
| 20.000 | 5 | **5** | 0 | 0 |
| 10.000 | 7 | 6 | 1 | 0 |
| 5.000 | 5 | 3 | 0 | 2 |
| 2.000 | 4 | 2 | 2 | 0 |
| 1.000 | 2 | 1 | 0 | 1 |
| **50.000** | 6 | **2** | 1 | 3 |
| **Total** | **35** | **25 (71%)** | 4 | 6 |

Catatan penting: bila sistem tidak yakin, ia **menolak menjawab** dan meminta pengguna
memotret ulang, bukan menebak asal. Untuk pengguna tunanetra ini disengaja — jawaban
yang salah lebih berbahaya daripada tidak menjawab, karena pengguna tidak punya cara
memeriksa kebenarannya.

Kelemahan terbesar saat ini ada pada uang **50.000**. Penyebabnya sedang ditelusuri.

---

## 5. Temuan penting selama pengerjaan

Bagian ini menurut kami yang paling bernilai, karena menunjukkan proses kerja, bukan
sekadar hasil akhir.

### 5.1 Angka bagus dari data internet ternyata menyesatkan

Model pengenalan uang pertama kami mendapat nilai **96,7%** saat diuji dengan data dari
internet. Terdengar sangat bagus. Namun ketika diuji dengan **foto yang kami potret
sendiri**, hasilnya hanya **20%**.

Penyebabnya: data uji dari internet berasal dari sumber yang sama dengan data latihnya,
sehingga model hanya "mengenali kembali" foto yang mirip. Foto kami dengan kamera HP,
di atas meja kayu, dengan cahaya ruangan, adalah dunia yang sama sekali berbeda.

**Pelajaran:** angka evaluasi hanya berarti bila data ujinya mewakili pemakaian
sebenarnya. Sejak itu, semua angka yang kami laporkan berasal dari foto sendiri.

### 5.2 Model tidak pernah diajari melihat objek miring

Saat ditelusuri, ternyata proses pelatihan berjalan **tanpa variasi rotasi** — pengaturan
bawaannya memang begitu, dan kami tidak menyadarinya. Akibatnya model hanya mengenali
uang yang terpotret tegak.

Ini fatal untuk aplikasi kami: **pengguna tunanetra tidak bisa membidik kamera.** Sudut
acak bukan kasus tepi, melainkan keadaan normal.

Setelah pelatihan diulang dengan variasi rotasi, akurasi naik dari **20% menjadi 50%**,
dan yang lebih penting, jawabannya menjadi stabil — foto yang sama diputar ke 13 sudut
berbeda kini memberi jawaban yang sama, padahal sebelumnya berubah-ubah.

Setelah data latih ditambah lagi, akurasinya naik menjadi **71%**.

### 5.3 Kesimpulan dari sampel kecil bisa menyesatkan

Ketika kami baru punya 5 foto uji, hasil percobaan sempat menyimpulkan hal yang kemudian
**terbukti terbalik** setelah fotonya bertambah menjadi 20, lalu berubah lagi di 35 foto.

Karena itu semua kesimpulan sekarang kami sertai jumlah sampelnya, dan kesimpulan dari
data yang terlalu sedikit kami tandai sebagai belum bisa dipercaya.

### 5.4 Memilih antara "salah menjawab" dan "tidak menjawab"

Sistem memberi nilai keyakinan pada setiap tebakan. Bila nilainya di bawah ambang
tertentu, sistem menolak menjawab dan meminta pengguna memotret ulang.

Kami menguji tujuh nilai ambang yang berbeda pada 35 foto:

| Ambang | Benar | Salah | Tidak menjawab |
| ---: | ---: | ---: | ---: |
| 0,20–0,30 | 25 | **5** | 5 |
| **0,35–0,45** | **25** | **4** | 6 |
| 0,50 (rencana awal) | 24 | 4 | 7 |
| 0,60 | 19 | 3 | 13 |

Kami memilih **0,40**. Alasannya bukan karena akurasinya paling tinggi — selisihnya
hanya satu foto dari 35 dan itu terlalu kecil untuk disimpulkan. Alasannya karena pada
rentang itu **jumlah jawaban yang salah paling sedikit**.

Pertimbangannya khusus untuk pengguna tunanetra: mereka tidak punya cara memeriksa
apakah jawaban sistem benar. Sistem yang berkata "saya tidak yakin, coba foto ulang"
jauh lebih aman daripada sistem yang menyebut nominal yang keliru dengan percaya diri.

### 5.5 Membaca seluruh foto ternyata boros

Awalnya, untuk mencari tanggal kedaluwarsa, sistem membaca **seluruh tulisan** di foto
kemasan lalu mencari mana yang berbentuk tanggal. Cara ini berhasil, tetapi lambat:
sekitar 3,7 detik.

Kami melatih model kedua yang tugasnya hanya **menemukan letak tanggal**, lalu memotong
bagian itu saja untuk dibaca. Hasilnya **0,8 detik** — sekitar 4,6 kali lebih cepat
untuk jawaban yang sama.

Model ini baru selesai dilatih dan belum diuji dengan foto kemasan sungguhan.

### 5.6 Pemeriksaan kualitas foto sempat menolak dokumen yang sah

Ambang "foto terlalu terang" yang kami rencanakan ternyata menolak foto dokumen biasa,
karena kertas putih memang punya tingkat kecerahan tinggi. Padahal fotonya jelas dan
tulisannya terbaca.

Ambangnya kami koreksi, dan penjaga utamanya diganti menjadi proporsi piksel yang
benar-benar "terbakar" cahaya. Perubahan ini beserta alasannya dicatat.

### 5.7 Kesalahan program yang ditemukan lewat pengukuran

Saat menyiapkan alat ukur, ditemukan bahwa penulisan `BB 12/2027` — bentuk yang sangat
umum pada kemasan — gagal dibaca sama sekali, padahal `12/2027` berhasil. Penyebabnya
huruf **B** termasuk huruf yang sering tertukar dengan angka pada hasil OCR, sehingga
program salah mengenali batas tanggalnya.

Kesalahan ini ditemukan sebelum pengujian dengan foto asli, sehingga tidak sempat
merusak hasil pengukuran.

---

## 6. Mutu pengerjaan

- **481 pengujian otomatis**, seluruhnya lulus. Setiap kali ada perubahan, semuanya
  dijalankan ulang untuk memastikan tidak ada yang rusak.
- **102 keputusan teknis tercatat** di `docs/keputusan-teknis.md`, masing-masing disertai
  bukti angka dan batasannya.
- Semua angka pengaturan berada di satu berkas konfigurasi, bukan tersebar di kode,
  sehingga uji ablasi cukup dilakukan dengan mengubah satu baris.
- Pengujian dapat berjalan **tanpa model dan tanpa internet**, sehingga anggota tim lain
  bisa ikut mengembangkan tanpa mengunduh berkas besar.

---

## 7. Yang belum selesai

| Pekerjaan | Keterangan |
| :--- | :--- |
| Foto uji dokumen dan kemasan | Dibutuhkan untuk dua pengukuran yang belum ada, sekaligus untuk menyetel model pencari tanggal |
| Menguji model pencari tanggal dengan foto asli | Modelnya sudah jadi, tetapi baru diuji dengan gambar buatan |
| Memperbaiki pengenalan uang 50.000 | Kelemahan terbesar saat ini |
| Uji coba oleh pengguna | Dilakukan dengan mata tertutup sebagai pengganti |
| Laporan akhir, video demo, slide | Tahap terakhir |

### Keterbatasan yang kami sadari

- Antarmuka web yang kami pakai **belum sepenuhnya ramah pembaca layar**. Jawaban dan
  status sudah diumumkan dengan suara, tetapi urutan navigasi keyboard masih mengikuti
  bawaan alatnya. Hal ini sudah dinyatakan sejak awal sebagai batasan prototipe.
- Pengujian pengenalan suara baru melibatkan **satu penutur**, sehingga angkanya
  optimistis untuk pengguna lain.
- Aplikasi ini **tidak memeriksa keaslian uang**, dan hal itu disampaikan kepada pengguna.

---

## 8. Rencana terdekat

1. Memotret foto uji dokumen dan kemasan, lalu menjalankan dua pengukuran yang belum ada.
2. Menguji model pencari tanggal dengan foto kemasan sungguhan, lalu menyetel
   ambang keyakinannya. Percepatan dari 3,7 detik menjadi 0,8 detik sudah terukur,
   tetapi baru pada gambar buatan.
3. Menambah data latih untuk nominal yang masih lemah.
4. Uji coba pengguna dengan mata tertutup.
5. Menyusun laporan akhir, video demo, dan slide.
