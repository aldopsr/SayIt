# Rencana: membacakan tulisan apa pun dari foto

**Disusun 31 Oktober 2026. Waktu tersedia: 2–3 hari.**

> **Ralat lingkup.** Versi pertama rencana ini ditulis untuk "modul dokumen" — foto
> kertas A4. Itu **terlalu sempit**. Sasaran sebenarnya: pengguna memotret **apa saja**
> yang ada tulisannya — papan tulis, kemasan, papan nama, halaman buku, tulisan tangan —
> dan sistem membacakannya. Seluruh rencana di bawah sudah disusun ulang untuk itu.

---

## Yang saya ukur hari ini: sistem sudah separuh jalan ke sana

Modul pembaca tulisan dijalankan pada **foto kemasan sungguhan** (20 foto yang sudah kita
punya dari modul kedaluwarsa). Ini teks di dunia nyata, bukan kertas.

| Foto | Kertas ditemukan? | Kotak teks | Waktu |
| :--- | :--- | ---: | ---: |
| ajinomoto | tidak | 14 | 8,7 s |
| 20261008 | tidak | 16 | 8,7 s |
| miesedap | tidak | 14 | 7,3 s |
| mentega | tidak | 69 | 11,9 s |

**Kabar baik — tiga hal sudah benar:**

1. Koreksi perspektif **tidak merusak** foto bukan-kertas. Ia mencari lembar kertas,
   tidak menemukan, lalu mengembalikan citra apa adanya. Arsitekturnya tidak menghalangi.
2. Teks **memang terbaca**: "Petunjuk Penyimpanan", "Baik digunakan sebelum",
   "KODE PRODUKSI", "Mi Kuah Rasa Bumbu Kari Kental", "membuat kue lebih mengembang".
3. Waktunya 7–12 detik, sama seperti dokumen — tidak meledak.

**Kabar buruk — dua masalah baru yang tidak ada pada kertas A4:**

**a. Urutan bacaan jadi kacau.** Pada foto mentega keluarannya:

> "kedekatan BlueBand sebagai enak banan karena rasa bertekstur lemout Menggunakan
> membuat kue lebih mengembang kue: akan butter. kue yang wangi"

Tiap kata benar, susunannya tidak. Pengelompokan baris dan paragraf dirancang untuk
**tata letak dokumen** — teks mengalir kiri ke kanan, atas ke bawah. Pada kemasan,
papan tulis, atau papan nama, teks tersebar dan aturan itu tidak berlaku.

**b. Teks terbalik dibaca jadi sampah.** Contoh nyata: `"wejes BundoL uejues"` — itu
tulisan terbalik yang dibaca huruf demi huruf apa adanya.

Penyebabnya ketemu: **kedua saklar orientasi tidak dipakai.**

| Saklar | Tempat | Status |
| :--- | :--- | :--- |
| `rotation_info` EasyOCR | `readtext(image, detail=1)` | **tidak dioper** |
| `use_textline_orientation` PaddleOCR | `_buat_paddle()` | **dipaksa `False`** |

Untuk pengguna tunanetra, **membacakan susunan kata yang kacau dengan nada seyakin
jawaban benar lebih berbahaya daripada berkata "tulisannya kurang jelas"**. Prinsip ini
sudah dipakai di modul uang dan tanggal; modul tulisan belum punya.

---

## Satu hal yang harus saya katakan terus terang: tulisan tangan

**Tulisan tangan tidak akan selesai dalam 2–3 hari dengan model lokal.** Ini bukan soal
penyetelan, melainkan soal model yang memang tidak ada.

| Mesin | Dilatih untuk | Tulisan tangan? |
| :--- | :--- | :--- |
| EasyOCR | teks cetak dan teks pemandangan | **tidak ada model tulisan tangan** |
| PaddleOCR | teks cetak dan teks pemandangan | **tidak ada model tulisan tangan** |
| TrOCR (Microsoft) | tulisan tangan **Bahasa Inggris** | ada, tetapi ~1,3 GB, per baris, dan lambat di CPU |
| Google Vision / Azure Read | cetak + tulisan tangan, banyak bahasa | **bisa**, tetapi berbayar, butuh internet, dan **fotonya dikirim ke pihak ketiga** |

Catatan penting soal pilihan terakhir: selama ini yang dikirim keluar hanya **teks** (ke
Google lewat gTTS, kini ke Microsoft lewat edge-tts). Mengirim **fotonya** adalah langkah
privasi yang jauh lebih besar — foto bisa memuat wajah, alamat, dokumen pribadi. Dataset
kita sendiri sudah terbukti memuat wajah orang dan layar berisi data pihak lain.

Jadi ada **persimpangan yang harus kamu putuskan**, bukan saya:

| Pilihan | Tulisan tangan | Biaya | Privasi | Muat 2–3 hari? |
| :--- | :--- | :--- | :--- | :--- |
| **A. Teks cetak di mana saja** (papan tulis spidol, kemasan, papan nama, buku, label) | tidak | nol | foto tetap di laptop | **ya** |
| **B. A + tulisan tangan lewat API awan** | ya | berbayar | **foto keluar** | ya, tetapi butuh akun dan kartu |
| **C. A + TrOCR lokal** | sebagian, Inggris | nol | aman | **tidak realistis** |

**Saran saya: ambil A sekarang**, dan tulis tulisan tangan sebagai keterbatasan yang
disadari. A sudah mencakup papan tulis (asal pakai spidol, bukan tulisan tangan sambung),
kemasan, papan nama, buku, dan label — yaitu sebagian besar yang ditemui pengguna.

---

## Rencana untuk pilihan A

### Hari 1 — orientasi dan urutan bacaan (dampak terbesar)

**1a. Nyalakan deteksi orientasi baris.** Oper `rotation_info=[90, 180, 270]` ke EasyOCR,
dan `use_textline_orientation=True` untuk PaddleOCR, keduanya lewat config supaya bisa
diablasi. Ini langsung menyerang `"wejes BundoL uejues"`.

**1b. Pisahkan aturan urutan bacaan.** Tambah mode tata letak di config:

| Mode | Untuk | Aturan |
| :--- | :--- | :--- |
| `dokumen` | kertas, halaman buku | seperti sekarang: baris dan paragraf rapat |
| `tersebar` | kemasan, papan tulis, papan nama | kelompokkan menurut gugus spasial, urutkan atas→bawah, dan **beri jeda antar-gugus saat dibacakan** |

Pemilihan modenya otomatis dari petunjuk yang sudah ada: `document_found` dari koreksi
perspektif, ditambah sebaran kotak teks. Kalau kertas ketemu → `dokumen`; kalau tidak →
`tersebar`.

**1c. Ukur.** Jalankan pada 20 foto kemasan + 13 dokumen, bandingkan sebelum–sesudah.

### Hari 2 — penjaga mutu bacaan

**2a. Ambang keyakinan untuk teks.** Kalau rata-rata skor kotak di bawah ambang, atau
kotak yang lolos terlalu sedikit, sistem berkata **"tulisannya kurang jelas, coba foto
lebih dekat"** alih-alih membacakan kata acak. Konsisten dengan modul uang dan tanggal.

**2b. Ablasi pra-pemrosesan untuk foto bukan-kertas.** Rangkaian `dokumen` memuat koreksi
perspektif dan deskew yang dirancang untuk kertas. Pada foto tersebar, keduanya mungkin
tidak berguna atau merugikan. **Belum pernah diukur.** Ini juga menjawab pertanyaan
ablasi mata kuliah dengan data baru.

**2c. Tuas PaddleOCR yang belum dicoba.** `text_recognition_model_name` tidak diteruskan
dari config — hanya model deteksi yang diteruskan, padahal penghambatnya tahap
pengenalan per baris. PaddleOCR lebih tepat (CER 9,4% lawan 15,3%) tetapi 41,8 detik.
Kalau `PP-OCRv5_mobile_rec` menurunkannya ke 10–15 detik, modul ini naik kelas seluruhnya.

### Hari 3 — ukur, kunci, catat

Ukur akhir pada kedua jenis foto, kunci config, perbarui `keputusan-teknis.md`,
`status-proyek.md`, dan laporan progres.

---

## Masalah yang belum punya jawaban: bagaimana mengukurnya

Metrik sekarang adalah **CER pada 13 dokumen A4**. Metrik itu **tidak mengukur sama
sekali** apa yang kamu mau. Tidak ada gunanya CER turun ke 9% kalau foto papan tulis
tetap dibacakan terbalik.

Yang dibutuhkan: **data uji kecil tapi beragam**. Pilihan, urut biaya:

**a. Pakai yang sudah ada — gratis, hari ini juga.** 20 foto kemasan sudah ada, tinggal
ditulis teks acuannya. Itu teks dunia nyata yang sah: cetak kecil, melengkung, cahaya
tidak rata, sebagian terbalik.

**b. Potret ~10 foto baru — sekitar 15 menit.** Jauh lebih murah daripada sesi foto
dokumen, dan inilah yang paling menentukan. Saran isinya:

| Jenis | Jumlah | Catatan |
| :--- | ---: | :--- |
| Papan tulis bertulisan spidol | 3 | satu lurus, satu menyudut, satu agak jauh |
| Papan nama / petunjuk arah | 2 | |
| Halaman buku atau majalah | 2 | |
| Label atau struk | 2 | |
| **Tulisan tangan** | **1** | hanya untuk membuktikan batasnya, bukan untuk dikejar |

Acuannya tinggal diketik — kalimat di papan tulis biasanya pendek.

**c. Dataset publik** — tetap tidak ada yang cocok. CORD (struk Indonesia), FUNSD
(formulir Inggris), SROIE (struk Inggris). Dipakai sebagai bukti sekunder saja.

**Tanpa (b), seluruh pekerjaan ini tidak bisa dibuktikan membaik.** Kita bisa memperbaiki
orientasi dan urutan bacaan, tetapi tidak punya angka yang menunjukkannya.

---

## Akibatnya pada PRD dan jurnal

PRD menulis kemampuan kedua sebagai **"membacakan tulisan dokumen"**. Memperluasnya
menjadi "membacakan tulisan apa pun" adalah **perubahan lingkup**, bukan perbaikan.

Dua konsekuensi yang harus disadari:

1. Metrik PRD Bagian 11 (CER ≤15% pada dokumen) **tidak otomatis gugur** — ia tetap
   diukur dan dilaporkan. Yang bertambah adalah metrik kedua untuk teks tersebar.
2. Di jurnal, ini ditulis sebagai **perluasan yang disengaja beserta batasnya**, dengan
   tulisan tangan dinyatakan terus terang sebagai di luar jangkauan.

---

## Keputusan yang saya butuhkan darimu

1. **Pilihan A, B, atau C?** Kalau tulisan tangan wajib ada, jawabannya API awan — dan
   itu berarti foto pengguna keluar dari laptop. Keputusan itu milikmu, bukan saya.
2. **Sanggup memotret ~10 foto beragam?** Sekitar 15 menit. Tanpa itu kita bisa
   memperbaiki tetapi tidak bisa membuktikan.
3. **Mulai dari mana?** Saran saya 1a (orientasi) — paling murah, dampaknya paling
   terlihat, dan hasilnya langsung terdengar pada foto kemasan yang sudah ada.

Sambil menunggu jawabanmu, saya bisa langsung mengerjakan 1a dan menulis teks acuan untuk
20 foto kemasan, karena keduanya berguna pada pilihan mana pun.
