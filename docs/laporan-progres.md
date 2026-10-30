# Laporan Progres SayIt

**Mata kuliah:** Pengolahan Citra dan Visi Komputer — TRPL, Sekolah Vokasi IPB
**Tanggal:** 30 Oktober 2026
**Laporan sebelumnya:** 28 September 2026

---

## 1. Apa yang sedang kami buat

SayIt adalah aplikasi untuk **penyandang disabilitas netra**. Cara pakainya sederhana:
pengguna memotret sesuatu, bertanya dengan suara, lalu mendengar jawabannya.

Tiga hal yang bisa ditanyakan:

1. **"Ini uang berapa?"** — menyebutkan nominal uang kertas, dan menjumlahkan bila ada
   beberapa lembar.
2. **"Tolong bacakan tulisannya"** — membacakan isi dokumen atau surat.
3. **"Kapan kedaluwarsanya?"** — membacakan tanggal kedaluwarsa pada kemasan, sekaligus
   menyebut masih berapa lama lagi.

Semua jawaban keluar sebagai suara, karena pengguna tidak melihat layar.

---

## 2. Ringkasan perubahan sejak laporan 28 September

Satu bulan terakhir hampir seluruhnya berisi **pengukuran dan perbaikan**, bukan menulis
fitur baru. Perubahan terbesarnya:

| Hal | 28 September | 30 Oktober |
| :--- | :--- | :--- |
| Akurasi nominal uang | 71% (35 foto) | **90,1%** (81 foto, validasi silang) — **target tercapai** |
| Akurasi tanggal kedaluwarsa | belum diukur | **81%** (16 kemasan) — **target tercapai** |
| Akurasi membaca dokumen | belum diukur | **galat 15,3%** (13 dokumen) — meleset 0,3 poin |
| Antarmuka | Streamlit (halaman uji) | **Aplikasi web PWA** yang bisa dipasang di HP |
| Pembaca tulisan | EasyOCR untuk semua | dipisah per modul setelah uji banding |
| Pengujian otomatis | 481 | **648** |
| Keputusan teknis tercatat | 102 | **319** |
| Foto uang sendiri untuk uji | 35 | **81** |

**Dua dari tiga target akurasi PRD kini tercapai.** Yang ketiga meleset tipis dan
penyebabnya sudah diketahui persis (Bagian 5.4).

---

## 3. Posisi sekarang

**Perangkat lunaknya selesai dan sudah berjalan sebagai aplikasi web yang bisa dipakai
dari HP.** Yang tersisa sebagian besar bukan menulis program lagi, melainkan pengujian
dengan pengguna dan penyusunan dokumen akhir.

| Bagian | Status |
| :--- | :--- |
| Pengenalan suara (pertanyaan pengguna) | Selesai dan terukur |
| Pengolahan citra (inti mata kuliah) | Selesai, dan **sudah diuji ablasi** |
| Pengenalan nominal uang | Selesai, **target tercapai** |
| Membacakan dokumen | Selesai, meleset tipis dari target |
| Membaca tanggal kedaluwarsa | Selesai, **target tercapai** |
| Menjawab dengan suara | Selesai |
| Aplikasi web (PWA) | Selesai dan berjalan |
| Uji coba oleh pengguna | **Belum dilakukan** |
| Laporan, video demo, slide | Baru mulai (jurnal sudah disusun) |

Perkiraan keseluruhan: **sekitar 85% selesai.**

---

## 4. Hasil pengukuran

Seluruh angka di bawah **diukur dengan foto yang kami potret sendiri**, bukan dengan data
bawaan dari internet. Alasannya ada di Bagian 5.1.

| Yang diukur | Target | Hasil | Keterangan |
| :--- | :---: | :---: | :--- |
| **Menebak nominal uang** | ≥ 85% | **90,1%** | **Tercapai** |
| **Membaca tanggal kedaluwarsa** | ≥ 70% | **81%** | **Tercapai** |
| Membacakan isi dokumen | galat ≤ 15% | galat 15,3% | Meleset 0,3 poin |
| Mengenali pertanyaan lisan | salah ≤ 25% | salah 7–8% | Tercapai |
| Waktu menjawab pertanyaan uang | ≤ 8 detik | 1,4 detik | Tercapai |
| Waktu menjawab perintah suara | ≤ 8 detik | 1,3 detik | Tercapai |
| Waktu membacakan dokumen | ≤ 8 detik | 11,5 detik | **Menyimpang, disengaja** |
| Waktu menjawab tanggal kedaluwarsa | ≤ 8 detik | 11,4 detik | **Menyimpang, disengaja** |
| Uji coba oleh pengguna | ≥ 80% | belum dilakukan | Direncanakan |

### Cara kami melaporkan akurasi

Kami **tidak pernah** melaporkan akurasi sebagai satu persentase saja, melainkan selalu
dipisah menjadi **benar / salah / tidak menjawab**.

Alasannya bukan gaya penulisan. Bagi pengguna tunanetra, nominal atau tanggal yang
**salah** jauh lebih berbahaya daripada sistem yang **diam**, karena ia tidak punya cara
memeriksanya. Dua kondisi dengan persentase sama bisa sangat berbeda bahayanya.

| Modul | Benar | Salah | Tidak menjawab | Jumlah |
| :--- | ---: | ---: | ---: | ---: |
| Uang | **73** | 8 | 0 | 81 foto |
| Tanggal kedaluwarsa | **13** | 1 | 2 | 16 kemasan |

### Rincian pengenalan uang per nominal

| Nominal | Benar dari | Catatan |
| ---: | :---: | :--- |
| 100.000 | **13 / 13** | Sempurna |
| 20.000 | **7 / 7** | Sempurna |
| 5.000 | 20 / 21 | Naik tajam; dulu kelas terlemah |
| 2.000 | 16 / 19 | |
| 50.000 | 5 / 6 | |
| 10.000 | 8 / 10 | Kini salah satu yang terlemah |
| 1.000 | 3 / 4 | Data latihnya paling sedikit (4 foto) |

Delapan kesalahan yang tersisa **semuanya** berupa satu lembar yang nominalnya tertukar,
bukan kesalahan menghitung jumlah lembar.

### Bagaimana akurasi uang diukur

Memakai **validasi silang lima lipatan**: foto dibagi lima kelompok, model dilatih lima
kali, dan setiap foto diuji **tepat sekali oleh model yang belum pernah melihatnya**.

Pembagian kelompoknya berdasarkan **kemiripan visual**, bukan nama berkas, supaya dua
foto yang hampir sama tidak terpisah antara data latih dan data uji. Tanpa penjagaan
ini, angkanya akan terlihat jauh lebih bagus daripada kenyataannya.

---

## 5. Temuan penting

Bagian ini menurut kami yang paling bernilai, karena menunjukkan proses kerja.

### 5.1 Angka bagus dari data internet ternyata menyesatkan

Model pertama kami mendapat **96,7%** dengan data dari internet, tetapi hanya **20%**
dengan foto yang kami potret sendiri. Penyebabnya data uji dari internet berasal dari
sumber yang sama dengan data latihnya.

Sejak itu semua angka yang kami laporkan berasal dari foto sendiri. Temuan ini berulang
sepanjang proyek dan menjadi prinsip kerja kami.

### 5.2 Kenaikan terbesar bulan ini datang dari memperbaiki ALAT UKURNYA

Ini temuan paling penting bulan Oktober, dan layak disampaikan apa adanya.

Pada 26 Oktober hasil pengukuran menunjukkan **84,0%**. Setelah ditelusuri, ternyata
**program pengukurannya tidak menjalankan seluruh langkah yang dijalankan aplikasi**:
satu aturan penyaring yang ada di aplikasi tidak ikut dipakai saat mengukur.

Petunjuknya terlihat dari pola kesalahannya — lima dari tiga belas kesalahan berbentuk
"satu lembar dijawab dua lembar", misalnya Rp100.000 dijawab Rp102.000. Itu persis pola
yang dirancang dibuang oleh aturan tersebut.

Setelah alat ukurnya disamakan dengan aplikasi, kelima kesalahan itu **hilang seluruhnya**
dan angkanya menjadi **90,1%**.

**Modelnya sama persis.** Kenaikan 84,0% → 90,1% **bukan** karena model membaik,
melainkan karena pengukurannya sebelumnya salah. Ini kami catat eksplisit supaya tidak
diklaim sebagai keberhasilan pelatihan.

### 5.3 Perbaikan citra yang justru merugikan

CLAHE adalah teknik perbaikan kontras, dan secara teori seharusnya menolong.

Ternyata tidak. Model dilatih memakai **gambar asli**, sedangkan aplikasi menerapkan
CLAHE sebelum mengenali. Akibatnya gambar yang dilihat model saat dipakai berbeda dari
yang dilihat saat belajar.

| Kondisi | Akurasi | Waktu |
| :--- | ---: | ---: |
| Dengan CLAHE | 65,6% | 88,4 ms |
| Tanpa CLAHE | **87,5%** | **56,4 ms** |

*(diukur pada 32 foto yang belum pernah dilihat model)*

CLAHE dibuang dari jalur uang pada 28 Oktober — akurasi naik dan waktunya **36% lebih
cepat**.

Yang perlu ditegaskan untuk mata kuliah: **tekniknya tidak dihapus dari proyek.** Ia
tetap ada, tetap dipakai untuk jalur dokumen, dan sekarang justru punya **bukti ablasi
terukur**. Hasil ablasi yang negatif tetap hasil ablasi, dan menurut kami lebih berbobot
daripada klaim tanpa pengukuran.

### 5.4 Dua foto uji dokumen ternyata bukan foto kertas

Akurasi dokumen meleset 0,3 poin dari target. Setelah ditelusuri, penyebabnya sempit:
**dua dari 13 foto uji bukan foto kertas**, dan penyebabnya pun berbeda.

| Berkas | Galat | Sebab |
| :--- | ---: | :--- |
| `ketentuan_makalah` | 76,9% | **Foto layar monitor.** Huruf kecil, ada pantulan. Pembacaan benar-benar gagal |
| `open_recruitment` | 22,0% | **Tangkapan layar WhatsApp.** Pembacaannya justru bagus, tetapi ikut membaca jam, nama grup, dan nomor telepon |

Pada **11 foto kertas sungguhan, galatnya hanya 9,0%** — jauh di bawah target.

Penggantinya sudah disiapkan: halaman siap cetak dengan isi yang sama persis, berikut
teks acuannya. Tinggal dicetak dan dipotret. Hitungan kami menunjukkan kedua foto baru
boleh ber-galat sampai 47,8% dan target tetap lolos, jadi hampir foto kertas apa pun
sudah cukup.

### 5.5 Dua kesalahan program yang hanya ketahuan lewat alat bantu

Pada notebook pelatihan ditemukan dua masalah yang **tidak menghasilkan pesan error sama
sekali** — keduanya hanya membuat angkanya salah diam-diam:

1. Foto yang belum dilabeli ikut masuk sebagai contoh **"tidak ada uang di gambar ini"**,
   sehingga model diajari kebalikan dari yang benar.
2. Bila pelatihan diulang tanpa mengganti nama percobaan, program **melewati pelatihan**
   dan diam-diam menilai model lama memakai data baru.

Keduanya diperbaiki. Untuk masalah kedua ditambahkan penjaga: setiap putaran kini
menyimpan sidik jari dari daftar datanya, dan program **berhenti keras** bila sidiknya
tidak cocok.

Penjaga itu kemudian berguna di luar tujuan aslinya — ia menjadi satu-satunya bukti
yang bisa diperiksa bahwa kelima putaran memakai pembagian yang benar-benar berbeda dan
setiap foto diuji tepat sekali.

### 5.6 Memilih antara "salah menjawab" dan "tidak menjawab"

Sistem menolak menjawab bila keyakinannya di bawah ambang tertentu. Kami menyapu delapan
nilai ambang:

| Ambang | Benar | Salah | Tidak menjawab |
| ---: | ---: | ---: | ---: |
| 0,15 – **0,30** | **73** | 8 | 0 |
| 0,35 | 72 | 7 | 2 |
| 0,40 | 71 | 7 | 3 |
| 0,50 | 70 | 7 | 4 |
| 0,60 | 63 | 6 | 12 |

Kami memilih **0,30**. Menaikkannya ke 0,35 menukar satu jawaban benar dengan dua kali
diam, hanya untuk mengurangi satu jawaban salah.

### 5.7 Membaca seluruh foto ternyata boros

Untuk tanggal kedaluwarsa, model kedua mencari **letak tanggal** lebih dulu, lalu hanya
bagian itu yang dibaca. Mematikannya memperburuk waktu dari 11,4 detik menjadi 27,3
detik.

Yang penting dicatat: cara ini **tidak menaikkan akurasi sama sekali** (81% dengan
maupun tanpa). Ia murni penghemat waktu, dan kami melaporkannya begitu.

### 5.8 Penghambat tanggal kedaluwarsa bukan pembidikan, melainkan jenis cetakannya

Dugaan awal kami: pengguna tunanetra tidak bisa membidik, jadi tanggalnya tidak terfoto
dengan baik. **Dugaan ini terbantah.** Foto yang dipotong tepat pada tanggalnya pun
nol benar dari lima.

Penyebab sebenarnya adalah cetakan titik-titik (dot-matrix) pada kemasan yang memang
sulit dibaca. Akurasi naik dari 19% menjadi 81% setelah **mengganti mesin pembaca
tulisan**, bukan setelah memperbaiki pembidikan.

---

## 6. Mutu pengerjaan

- **648 pengujian otomatis**, seluruhnya lulus. Dijalankan ulang setiap ada perubahan.
- **319 keputusan teknis tercatat** di `docs/keputusan-teknis.md`, masing-masing disertai
  angka dan batasannya — termasuk keputusan yang kemudian terbukti salah dan dibatalkan.
- Semua angka pengaturan berada di satu berkas konfigurasi, sehingga uji ablasi cukup
  dilakukan dengan mengubah satu baris.
- Pengujian dapat berjalan **tanpa model dan tanpa internet**, sehingga anggota tim lain
  bisa ikut mengembangkan tanpa mengunduh berkas besar.

---

## 7. Keterbatasan yang kami sadari

Kami sampaikan terbuka karena menurut kami ini bagian dari kejujuran laporan.

| Keterbatasan | Penjelasan |
| :--- | :--- |
| **Penghitungan banyak lembar belum terbukti** | Programnya ada dan berjalan, tetapi data ujinya **hanya satu foto**. Belum bisa diklaim |
| **Satu anotasi cacat ikut terpakai** | Satu foto berisi dua lembar tetapi labelnya hanya satu, dan kotaknya menutupi hampir seluruh bingkai. Ia ikut melatih dan menguji model. Bila dikeluarkan, akurasinya 90,0% atau 91,25% |
| **Waktu menjawab melampaui target** | Dokumen dan kedaluwarsa 11,4–11,5 detik lawan target 8 detik. Tiga cara mempercepatnya sudah dicoba dan semuanya mengorbankan akurasi |
| **Tidak ada panduan arah kamera** | Foto diperiksa **setelah** dipotret, belum ada tuntunan suara **saat** membidik |
| **Belum ada uji pengguna** | Belum dilakukan sama sekali |
| **Pengujian suara satu penutur** | Angkanya optimistis untuk pengguna lain |
| **Server masih di laptop** | Dijalankan dari laptop pengembang lewat ngrok, belum hosting tetap |
| **Tahun emisi tidak dibedakan** | Model mengenali tujuh nominal, bukan emisi 2016 dan 2022 secara terpisah |
| Tidak memeriksa keaslian uang | Disampaikan kepada pengguna |

---

## 8. Rencana terdekat

1. **Uji coba pengguna** dengan mata tertutup, lima tugas, disertai kuesioner SUS.
   Ini satu-satunya target PRD yang belum tersentuh sama sekali.
2. **Mencetak dan memotret dua dokumen pengganti**, lalu mengukur ulang. Bahannya sudah
   siap; perkiraan kerja 20 menit.
3. **Menambah foto uang** untuk nominal 1.000 dan 10.000 yang kini paling lemah.
4. Menyusun **laporan akhir, video demo, dan slide**. Jurnal sudah disusun dan seluruh
   angkanya sudah dilampirkan beserta data mentahnya.

---

## Lampiran — berkas rujukan

| Berkas | Isi |
| :--- | :--- |
| `docs/status-proyek.md` | Status rinci per fitur, lengkap dengan daftar angka yang sudah usang |
| `docs/keputusan-teknis.md` | Riwayat 319 keputusan beserta angkanya |
| `docs/PRD_SayIt_v2_1.md` | Persyaratan lengkap |
| `Jurnal SayIt/` | Naskah jurnal beserta lampiran data mentah |
| `docs/jurnal_bahan/` | Keluaran mentah eksperimen model uang |
