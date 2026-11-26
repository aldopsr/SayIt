# Pencerdasan: Modul Kedaluwarsa

**Untuk anggota kelompok, dibuat 26 November 2026.** Ini modul yang **paling banyak
percobaan gagalnya** di proyek ini, dan justru itu yang membuatnya paling bagus untuk
menjawab pertanyaan penguji — hampir setiap keputusannya punya angka pembandingnya.

Anggap kamu belum pernah lihat kodenya. Istilah teknis dijelaskan di tempatnya.

> **Kode yang dibahas:** `sayit/vision/expiry.py` (431 baris),
> `sayit/vision/date_parser.py` (468 baris), dan `vision.expiry` + `vision.date_parser`
> di `config/settings.yaml`.

---

## 1. Tugas modul ini

Pengguna memotret kemasan makanan dan bertanya *"kapan kedaluwarsanya"*.
Modul ini menjawab **tanggalnya**, atau mengatakan ia tidak menemukannya.

Contoh jawaban: *"Kedaluwarsa dua puluh sembilan Agustus dua ribu dua puluh lima."*

**Ini modul tersulit dari ketiganya.** Sebabnya bukan tanggalnya, tapi **cetakannya**:
tanggal kedaluwarsa dicetak *inkjet* atau *dot-matrix* langsung ke plastik mengkilap —
titik-titik terpisah, tipis, sering kena refleksi cahaya. Itu jenis tulisan tersulit untuk
OCR mana pun.

---

## 2. Alurnya: dua jalur, bukan satu

```
  FOTO KEMASAN
      |
      +- YOLO zona (best_zone.pt)  -> DI MANA tanggalnya?
      |
      +- ketemu (skor >= 0,40) ---> JALUR ZONA
      |                              1. potong + margin 10%
      |                              2. resize
      |                              3. PaddleOCR baca potongannya
      |                              4. parser tanggal
      |
      +- tidak ketemu -------------> JALUR CADANGAN
                                     OCR SELURUH gambar
                                     (jawabannya dibacakan "kurang yakin")
```

**Dua model, dan jangan tertukar:**

| Model | Tugas | Yang dia TIDAK lakukan |
| :--- | :--- | :--- |
| YOLO zona | menunjuk **lokasi** tanggal di kemasan | **tidak membaca apa pun** |
| PaddleOCR | **membaca** tulisan di lokasi itu | tidak tahu mana yang tanggal |

> **Pertanyaan yang hampir pasti ditanya: kenapa pakai dua model, tidak langsung OCR
> seluruh kemasan saja?**
>
> **Karena kecepatan, bukan akurasi.** Dan ini terukur: mematikan jalur zona membuat
> latensi median **lebih dari dua kali lipat** (11,4 menjadi 27,3 detik pada pengukuran
> 2 Oktober), sementara **akurasinya sama saja: 81% dengan maupun tanpa jalur zona.**
>
> Jadi kalau ditanya "jalur zona menaikkan akurasi berapa?", jawaban jujurnya **nol**.
> Yang dia beli adalah waktu.

**Cakupan zonanya: 9 dari 14 kemasan bertanggal** (7 dari 16 berkas uji secara keseluruhan).
Artinya **jalur cadangan dipakai hampir separuh waktu** — itu bukan kasus langka, dan harus
tetap benar.

---

## 3. Urutan eskalasi — bagian yang paling banyak diukur

Kalau potongan zona gagal dibaca, sistem tidak langsung menyerah. Urutannya:

| # | Langkah | Biaya | Seberapa sering menolong |
| :-- | :--- | :--- | :--- |
| 1 | potongan zona **tegak** | paling murah | paling sering berhasil |
| 2 | OCR **seluruh gambar** | murah | terbukti menyelamatkan |
| 3 | rotasi **potongan** | paling mahal | paling jarang (`rotate_crop: false`) |

Dan di luar ketiganya: kalau zona **tidak ketemu sama sekali**, `read()` mengulangi
seluruh alur pada **gambar penuh yang diputar** `[180, 90, 270]` derajat.

Tiga temuan di balik urutan ini, semuanya layak dikutip:

**(a) Zona adalah PETUNJUK letak, bukan komitmen.**
Terbukti 30 September pada kemasan `ajinomoto`: zona terdeteksi dengan skor 0,76,
potongannya **gagal** dibaca, padahal **OCR seluruh gambar membaca `110426` dengan benar.**
Sebelum perbaikan ini sistem terkunci di jalur zona dan membuang jawaban yang sudah ada di
tangannya. Saklarnya `full_image_fallback: true`.

**(b) Urutan 1-2-3 ini sudah pernah DITERBALIK, dan hasilnya lebih buruk.**
Diukur 16 November pada 16 kemasan: memindahkan rotasi potongan ke depan membuat median
**6,54 menjadi 9,33 detik**, total 234 menjadi 344 detik, dan melambat di **13 dari 16
berkas** — **tanpa menambah satu jawaban benar pun**. Sebabnya: langkah yang murah dan
sering berhasil justru ditunda di belakang tiga rotasi yang jarang menolong.

**(c) NOL dari 16 kemasan pernah menyentuh langkah 3.**
Jejak per berkas: 7 berhenti di potongan tegak, 2 di seluruh gambar, 7 tidak punya zona,
**0 sampai ke rotasi potongan**. Jadi `rotate_crop` tetap `false` **bukan karena terbantah,
tetapi karena tidak terukur** — kasus yang ia sasar (zona ketemu, potongan gagal, gambar
penuh juga gagal) tidak ada di data uji kami.

> **Kenapa memutar POTONGAN lebih murah daripada memutar gambar penuh?** Karena satu
> lintasan gambar penuh berarti: deteksi zona YOLO pada gambar 3000x4000 lagi, potong lagi,
> OCR lagi. Memutar potongan hanya membayar OCR potongan kecil. Dan zona yang sudah ketemu
> tidak akan hilang karena gambarnya diputar, jadi mendeteksinya ulang tidak membeli
> apa pun.

---

## 4. Rotasi ditangani SISTEM, bukan diminta ke pengguna

Pengguna tunanetra **tidak bisa memastikan kemasannya terpegang tegak.** Jadi kalau
tanggalnya tidak ketemu, sistem memutar fotonya sendiri dan mencoba lagi:
`rotate_retry: [180, 90, 270]`.

Dirancang sebagai **percobaan ulang saat gagal**, bukan selalu dijalankan. Konsekuensinya:
foto yang sudah tegak menjawab di percobaan pertama dan **tidak membayar apa pun**,
sementara foto terbalik membayar waktu tambahan hanya ketika memang perlu.

Urutannya `180` dulu, baru `90` dan `270`: kemasan yang terpegang balik jauh lebih umum
daripada yang miring tepat seperempat putaran.

---

## 5. Anggaran waktu 90 detik — penjaga, bukan optimasi

`expiry.budget_s: 90.0`. Sebelum tiap percobaan rotasi gambar penuh, sistem memeriksa:
*"kalau satu lintasan lagi dimulai sekarang, apakah akan melewati anggaran?"*

**Alasannya arsitektur, bukan selera.** Proksi Vercel memutus permintaan pada **120 detik**
untuk semua paket, dan 23 November batas itu benar-benar terlanggar: kemasan `tolakangin2`
memakan **120,2 detik** pada **tiga dari tiga** pengulangan, dan dibalas **502**.

Lebih buruk lagi: **servernya tidak ikut berhenti.** Ia terus bekerja sambil memegang kunci
antrean, sehingga **dua giliran BERIKUTNYA ikut gagal.** Satu foto lambat merusak tiga
giliran.

Dua detail desain yang layak disebut:

1. **Biaya satu lintasan DIUKUR, tidak ditebak.** Lintasan pertama dicatat waktunya, dan itu
   jadi penaksir untuk lintasan berikutnya. Memeriksa "sudah lewat belum" saja tidak cukup:
   tanpa taksiran, satu lintasan 40 detik tetap boleh dimulai tepat sebelum batas lalu
   berjalan jauh melewatinya.
2. **Lintasan pertama TIDAK PERNAH dipotong**, berapa pun ketat anggarannya. Ada tes khusus
   untuk itu.

**Hasilnya diukur lewat deploy, 48 percobaan:**

| | sebelum | sesudah |
| :--- | :--- | :--- |
| Waktu maksimum | 121,63 s | **80,17 s** |
| Balasan 502 | 3 dari 3 | **nol** |
| Kegagalan infrastruktur | 3 gambar | **nol** |
| Median praktis | 12,38 s | 12,20 s (**tidak berubah**) |
| Akurasi lewat deploy | 62% | **75%** |

> **Angka 90 tidak diambil dari 16 kemasan uji**, melainkan dari batas arsitektur: 120 detik
> dikurangi waktu unggah foto, render suara, dan jaringan. Menyetelnya dari 16 kemasan itu
> akan jadi resubstitusi — set itu sudah dipakai memilih tujuh keputusan lain.

---

## 6. Parser tanggal: kode kita sendiri, bukan pustaka

OCR memberi **teks**, bukan tanggal. Mengubah teks jadi tanggal adalah
`sayit/vision/date_parser.py`, dan itu **tulisan kami sendiri**.

Kenapa tidak pakai pustaka tanggal biasa? Karena format tanggal kemasan di Indonesia kacau,
dan teks OCR-nya **jauh lebih berantakan** daripada yang dibayangkan orang. Contoh keluaran
OCR sungguhan:

```
'E03*51 {19425 1104 JADAN.'
'man.yeg Bes 0re Cae 0 T7 WOR SUCALNED 210526/ en im ua.'
```

Pustaka mana pun akan gagal di situ. Parser kami mencari **kandidat** tanggal di dalam
kekacauan itu, lalu memilih yang terbaik.

### Aturan-aturan pentingnya

| Pengaturan | Nilai | Gunanya |
| :--- | :--- | :--- |
| `day_first` | `true` | urutan Indonesia: hari sebelum bulan |
| `years_back` | 5 | tanggal lebih tua dari 5 tahun lalu **ditolak** sebagai salah baca |
| `years_forward` | 10 | begitu juga yang lebih dari 10 tahun ke depan |
| `two_digit_year_base` | 2000 | `27` dibaca 2027 |
| `marker_window` | 24 | jarak maksimum (karakter) antara penanda dan tanggalnya |
| `markers` | `exp`, `best before`, `kedaluwarsa`, ... | penanda yang **menaikkan prioritas** sebuah tanggal |
| `negative_markers` | `kode produksi`, `batch`, `no bets`, ... | penanda yang **menurunkan** prioritas |
| `require_marker_for_compact` | **`false`** | lihat bagian 7 |
| `require_marker_for_spaced` | `true` | format berspasi wajib punya penanda |

Ada juga perbaikan salah baca digit (`fix_ocr_digits`), karena OCR rutin menukar
`O`/`0`, `I`/`1`, `S`/`5`, `B`/`8`.

### Jebakan yang terbukti: "klaim rentang" itu PENJAGA, bukan bug

Di `find_candidates`, kandidat yang punya penanda **mengklaim rentang karakternya** walau
nanti dibuang. Kelihatan seperti bug, dan 2 Oktober perilaku ini sempat "diperbaiki".
Hasilnya **dua jawaban salah baru**:

```
'NETTO 12 29 2028 G'  ->  2029-12-31   (salah)
'LOT 11 27 2028 XY'   ->  2027-11-30   (salah)
```

Perbaikannya dibatalkan, dan sekarang dikunci **tiga tes**. **Jangan dilepas tanpa mengukur
benar/salah/diam lagi.**

---

## 7. Satu saran yang DIBATALKAN, dan ini pelajaran paling berharga

Ablasi mesin OCR 1 Oktober (terisolasi, 800 px, jalur zona dan rotasi **dimatikan**)
menyimpulkan: *"dengan PaddleOCR, `require_marker_for_compact` harus DINYALAKAN kembali."*

**Saran itu SALAH, dan dibuktikan salah 16 November di pipeline penuh:**

| `require_marker_for_compact` | Benar / Salah / Diam | Akurasi | Median |
| :--- | :--- | :--- | :--- |
| **`false` (dipakai)** | 12 / 3 / 1 | **75%** | 10,5 s |
| `true` | 9 / 2 / 5 | 56% | 19,1 s |

Menyalakannya **menukar 3 jawaban benar demi 1 jawaban salah** (`ajinomoto`, `miesedap`,
`merica` jadi DIAM), dan latensi median hampir **dua kali lipat** karena tiap DIAM memicu
percobaan rotasi.

> **Pelajarannya, dan ini terulang dua kali di proyek ini: temuan dari uji mesin
> TERISOLASI tidak berpindah ke pipeline penuh.** Pola `dmy_spasi` mengalami hal yang sama
> — +1 benar di uji mesin, **nol efek** di pipeline.
>
> Kalau kamu menyetel parameter apa pun, ukur **di pipeline yang sungguhan dipakai**.

---

## 8. Pra-pemrosesan DIBUANG dari modul ini — dan itu disengaja

`expiry.preprocess_chain: hanya_resize`. Jadi cuma `resize`, tidak ada CLAHE, tidak ada
binarisasi, tidak ada morfologi.

Padahal PRD 8.8 **menuliskan** binarisasi dan morfologi sebagai langkah wajib. Dua ablasi
membantahnya:

**(a) Binarisasi dan morfologi dibuang 30 September.**
Diuji pada **9 potongan zona sungguhan**: binarisasi memberi **0 benar**, dan hampir selalu
menghasilkan teks kosong. Penjelasannya: binarisasi **menghapus** cetakan tipis alih-alih
menyambungkannya. Dugaan PRD bahwa morfologi akan menyambung titik dot-matrix **terbantah**.

**(b) Seluruh pra-pemrosesan dibuang 2 Oktober, setelah pindah ke PaddleOCR.**

| Mesin OCR | Pra-pemrosesan | Akurasi |
| :--- | :--- | :--- |
| EasyOCR | dengan | 44% |
| EasyOCR | tanpa | 38% |
| PaddleOCR | dengan | 69% |
| PaddleOCR | **tanpa** | **81%** |

**Arahnya berbalik.** Dengan EasyOCR pra-pemrosesan **membantu +6%**; dengan PaddleOCR
ia **merugikan -12%**. Sebabnya: PaddleOCR punya normalisasi internalnya sendiri, dan
rangkaian kami yang meng-*upscale* 2x menambah kerusakan di atasnya.

> **Ini temuan ablasi terkuat di seluruh proyek**, dan layak jadi paragraf sendiri di
> laporan: **pertanyaan "apakah pra-pemrosesan membantu" tidak punya satu jawaban.** Ia
> bergantung pada mesin OCR DAN pada modulnya. Pada modul dokumen dengan mesin yang sekarang,
> jawabannya justru **membantu +3,4 poin**.
>
> Kalau mengutip angka pra-pemrosesan, **sebutkan mesin OCR-nya sekalian.** Angka tanpa
> mesin tidak bermakna.

`resize` tetap wajib ada — ia pengendali latensi untuk foto HP 3000x4000.

---

## 9. Angka: akurasi

**81%** — **13 benar / 2 salah / 1 diam** dari 16 kemasan (diukur 17 November,
`line_grouping: rantai`). Target PRD >= 70%, jadi **tercapai**.

**Riwayatnya:** 19% -> 31% -> 44% -> **81%**. Lompatan terakhir seluruhnya dari **pindah ke
PaddleOCR** untuk modul ini.

### Dua jawaban salah yang masih tersisa

| Berkas | Dijawab | Seharusnya | Sebabnya |
| :--- | :--- | :--- | :--- |
| `chees` | 2026-05-21 | 2027-03-21 | parser menjawab dari **nomor produksi** `210526`, padahal `MAR` ada di sebelahnya |
| `ovaltine` | 2027-09-30 | 2027-09-27 | meleset **tiga hari**, tercatat sejak 2 Oktober |

Keduanya **kegagalan parser, bukan OCR** — OCR membaca tanggalnya dengan benar,
penafsirannya yang keliru.

### Akurasi LOKAL 81% lawan akurasi DEPLOY 75%

Dua angka ini **bukan saling bertentangan** — mereka mengukur cakupan yang berbeda:

- **81%** dari `scripts/ukur_kedaluwarsa.py`, yang memanggil `ExpiryReader.read()`
  **langsung**. Jadi ia **melewatkan penjaga mutu** dan **seluruh lapisan jaringan**.
- **75%** dari deploy sungguhan. Selisih satu berkas (`tisu1`) seluruhnya dari penjaga
  mutu, yang menolaknya dengan alasan *"foto terlalu gelap"*.

Di laporan, sebut keduanya dan jelaskan sebabnya. Menyebut 81% saja berarti mengklaim
sesuatu yang pengguna sungguhan tidak dapatkan.

---

## 10. Angka: kecepatan, dan PERINGATAN cara mengutipnya

Sesudah pindah ke backend ONNX Runtime (24 November):

| | sebelum | sesudah |
| :--- | :--- | :--- |
| Median | 7,40 s | **2,39 s** |
| Terburuk | **90,50 s** | **9,74 s** |
| Satu giliran penuh | — | **3,0 s** (target <= 8 s) |

Ekor 90,50 menjadi 9,74 detik itu penting secara arsitektur: artinya `budget_s: 90` kini
**tidak akan pernah tersentuh**, dan batas 120 detik Vercel berhenti jadi risiko.

> **PERINGATAN, dan ini wajib disebut kalau mengutip latensi modul ini.**
>
> **(a) Median saja menyesatkan.** Pada pengukuran lama, `tolakangin2` memakan **90-149
> detik** sementara mediannya 7,8 detik. Sebutkan **median DAN terburuknya**, atau pembaca
> akan menyangka pengguna selalu menunggu 8 detik.
>
> **(b) Latensi modul ini berderau besar.** Kondisi yang **sama persis** memberi median
> **6,54 detik** di satu sesi dan **10,46 detik** di sesi lain **pada hari yang sama** —
> simpangan 60%, murni dari beban laptop. Yang sah dikutip adalah **perbandingan DI DALAM
> satu sesi**, bukan angka detiknya sendirian.
>
> Ini bukan teori: pernah hampir mengubah keputusan. Kondisi yang sama memberi 9,96 s di
> satu proses dan 7,82 s di proses lain, dan membandingkan antar-sesi membuat dua kondisi
> terbaca "nyaris seri" padahal selisihnya jelas.

---

## 11. Penghambat sejatinya: PENGENALAN CETAKAN, bukan pembidikan

Ini kesimpulan yang paling sering disalahpahami, dan sudah dibuktikan tiga kali.

**Dugaan yang wajar:** *"pengguna tunanetra tidak tahu tanggalnya di mana, jadi fotonya
salah bidik."*

**Terbantah 30 September.** Foto yang **dipotong tepat pada tanggalnya** pun memberi
**0 benar dari 5**. Contoh keluaran OCR dari potongan yang pembidikannya sempurna:

```
ovaltine   ->  "8 2 7 ' 58."
kecapasin  ->  (kosong sama sekali)
```

**Ditegaskan ulang di uji lapangan 12 November** pada kemasan Indomie: zona ketemu dengan
skor **0,755** (pembidikan benar), potongannya benar, tetapi OCR membaca sampah di
**keempat** rotasi: `'CBI.'` / `'2 57 8 90 88.'` / `'5 4.'` / `'O6 8 4 5.'`.

Yang **sudah diuji dan BUKAN** penyebabnya:

| Dugaan | Hasil |
| :--- | :--- |
| Rotasi | sudah ditangani sistem, bukan ini |
| Resolusi | sapuan `max_side` 1600 / 2600 / 4032 **tidak mengubah hasil**, hanya menaikkan waktu 39 ke 75 detik |
| Rangkaian pra-pemrosesan | empat rangkaian diuji; threshold+morfologi justru merusak |
| Pembidikan | 0 benar dari 5 pada potongan yang tepat |

> Jadi **memotret ulang dari dekat adalah alat diagnosis, bukan perbaikan.** Kalimat
> "foto ulang lebih dekat" di catatan lama sudah **dibantah** dan tidak boleh diulang.

**Pembidikan tetap masalah nyata yang belum dipecahkan** — ia cuma belum jadi penghambat.
Pilihan yang sudah dipetakan: latih ulang model zona dengan foto sendiri, pemindaian ubin
pada resolusi penuh, panduan suara saat memotret, atau beberapa foto sekaligus. **Semuanya
sia-sia sebelum pengenalan cetakan diperbaiki.**

---

## 12. Percobaan model zona 4 kelas: temuan NEGATIF, dilaporkan apa adanya

Ide yang masuk akal: model zona sekarang punya **1 kelas** (`expired_date_zone`). Kalau ia
punya **4 kelas** (`date`, `code`, `due`, `prod`), wilayah **kode produksi bisa ditolak
SEBELUM OCR** — itu akar jawaban salah `chees`, diserang dari sumbernya.

Kodenya dibuat (`Zone.cls`, `zone_classes_date`, `zone_classes_reject`), bobotnya dilatih,
dan diukur 20 November pada 16 kemasan:

| Bobot | Benar | Salah | Diam | Median | Zona ketemu |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **1 kelas (dipakai)** | **13** | 2 | 1 | **7,82 s** | **7/16** |
| 4 kelas, satu dataset | 13 | **0** | 3 | 20,23 s | 2/16 |
| 4 kelas, gabungan dataset | 13 | **0** | 3 | 20,18 s | 3/16 |

**Keputusan: tetap `best_zone.pt` 1 kelas.** Menang di **kedua** sisi — akurasi 81% lawan
75%, median -33%, total -45%. Jadi ini **bukan pertukaran**, dan dugaan saya bahwa
latensinya setara **terbantah**.

Empat hal yang dibeli percobaan ini — bukan model, melainkan **pengetahuan**:

1. **Kesadaran kelas MEMANG bekerja**, dan itu dibuktikan terpisah dengan deteksi mentah
   pada `conf=0,01`. `chees` memberi `code:0.75` `date:0.54` `date:0.47` — `code` ditolak,
   `date:0.54` dipakai, hasilnya **DIAM bukan SALAH**. Kedua jawaban salah hilang karena
   mekanisme yang dirancang, bukan kebetulan.
2. **Tetapi cakupan zona RUNTUH** karena sebab berbeda: pada `ajinomoto`, `code:0.65` lolos
   ambang lalu ditolak, sementara `date:0.26` ada di bawah ambang — jadi daftar lolosnya
   kosong dan zona dianggap tidak ada.
3. **20 detik itu BUKAN harga model 4 kelasnya.** Deteksi zona sendiri cuma **6,6 ms**. Yang
   mahal adalah akibatnya: cakupan runtuh, jadi 13 berkas jatuh ke OCR seluruh gambar +
   rotasi. **Latensi di modul ini adalah gejala cakupan, bukan biaya inferensi.**
4. **Menolak kelas `due` adalah kemenangan latensi murni** (akurasi identik per berkas,
   median 14,97 menjadi 11,12 s). `due` itu penanda "EXP", bukan tanggalnya.

**Tuas ambang juga MATI.** Menurunkan `zone_score_min` 0,40 ke 0,25 pada bobot gabungan
memberi 75%, cakupan naik cuma 3/16 ke 4/16, dan `ajinomoto` berubah BENAR menjadi SALAH.
Sebabnya: kotak `date` berskor rendah itu **berskor rendah karena wilayahnya memang salah**;
menurunkan ambang memasukkan zona buruk, bukan memulihkan zona yang terbuang.

> **Jangan ulangi tiga sapuan ini** (gabung dataset, turunkan ambang, banding latensi) —
> ketiganya sudah dijalankan dan hasilnya di atas. Kodenya tetap di tempatnya, berteskan,
> dan **tidak mengubah apa pun** selama bobot 1 kelas yang dipakai.

---

## 13. Pengenal OCR WAJIB berbeda dari modul dokumen

Kedua modul memakai **PaddleOCR di atas ONNX Runtime**, tetapi **model pengenalnya
berbeda**, dan itu terukur:

| Modul | Model pengenal | Kalau ditukar |
| :--- | :--- | :--- |
| Dokumen | `PP-OCRv5_mobile_rec` (kecil, cepat) | — |
| **Kedaluwarsa** | **`PP-OCRv6_medium_rec`** (besar, teliti) | pakai `mobile_rec`: **81% jatuh ke 62%** |

Tiga kemasan (`tolakangin1`, `kecapasin`, `merica`) jadi DIAM kalau pengenal kecil dipakai.
Sebabnya masuk akal: **cetakan dot-matrix kemasan jauh lebih samar daripada tulisan cetak
di kertas A4**, jadi ia butuh model pengenal yang lebih besar.

Karena itu `vision.expiry.paddle` boleh **menimpa** `vision.document.paddle`, dan timpaan
apa pun **memaksa pembaca terpisah** walau mesinnya sama.

> **Aturan itu punya SATU rumah: `pipeline.cfg_ocr_kedaluwarsa()`. Skrip ukur WAJIB
> memakainya.**
>
> Versi pertama perubahan ini membiarkan `scripts/ukur_kedaluwarsa.py` menyusun confignya
> sendiri. Skrip itu melewatkan timpaannya, dan **melaporkan 62% untuk config yang
> sebenarnya 81%** — angkanya masuk akal sepenuhnya, dan satu-satunya petunjuk adalah baris
> `[saklar]` di keluarannya. Itu jenis kegagalan yang paling berbahaya: **gagal diam-diam.**

---

## 14. Satu aturan proses yang lahir dari kesalahan

**Setiap foto lapangan yang GAGAL wajib langsung disimpan** ke `data/uji_kedaluwarsa/`
dengan nama bertanggal.

Sebabnya: **foto Indomie dari uji lapangan 12 November TIDAK DISIMPAN.** Dicari di seluruh
repo, tidak ada. Itu satu-satunya contoh nyata dari kasus "zona ketemu tapi cetakannya tidak
terbaca", dan sekarang hilang.

Dan aturan kedua, dari kesalahan lain:
**setiap sapuan parameter WAJIB mencetak NILAI saklarnya di tiap kondisi.** Sapuan pertama
penanda negatif memakai `sed` yang polanya tidak cocok, jadi yang tertukar cuma judul
kolomnya dan yang terukur tetap saklar lama. **Hasilnya terlihat masuk akal sepenuhnya.**

---

## 15. Kalau ditanya — jawaban siap pakai

**"Kenapa pakai dua model, YOLO dan OCR?"**
YOLO menunjuk lokasi, OCR membaca. Dipisah demi kecepatan: mematikan jalur zona membuat
latensi median lebih dari dua kali lipat. Akurasinya sendiri sama, 81% dengan maupun tanpa.

**"Akurasinya berapa?"**
81% diukur langsung ke modulnya — 13 benar, 2 salah, 1 diam dari 16 kemasan. Lewat deploy
sungguhan 75%, dan selisih satu berkas itu dari penjaga mutu yang menolak foto gelap. Target
PRD 70%, jadi tercapai. Tapi n=16 itu kecil, dan 16 foto yang sama juga dipakai menyetel
tujuh keputusan lain — jadi angkanya optimistis.

**"Kenapa tidak 100%? Tanggal kan tulisannya jelas."**
Justru tidak. Tanggal kedaluwarsa dicetak inkjet atau dot-matrix ke plastik mengkilap —
titik-titik terpisah, tipis, kena refleksi. Terbukti: foto yang dipotong **tepat** pada
tanggalnya pun 0 benar dari 5. Penghambatnya **pengenalan cetakan**, bukan pembidikan, dan
itu di luar kemampuan OCR yang tersedia sekarang.

**"Pra-pemrosesannya mana? Kan ini mata kuliah pengolahan citra."**
Ada, dan **justru ablasinya yang jadi temuan.** PRD mewajibkan binarisasi dan morfologi;
kami **mengukurnya** dan ia memberi **0 benar** dari 9 potongan sungguhan, jadi dibuang.
Lalu pra-pemrosesan selengkapnya juga dibuang karena dengan PaddleOCR ia **merugikan 12
poin** (69% lawan 81%) — padahal dengan EasyOCR ia **membantu 6 poin**. Jadi hasil ablasinya
**berbalik arah tergantung mesin OCR**, dan itu temuan yang lebih berharga daripada sekadar
"pra-pemrosesan membantu".

**"Kalau fotonya terbalik bagaimana?"**
Ditangani sistem, bukan diminta ke pengguna — ia memutar 180, 90, 270 derajat dan mencoba
lagi. Dirancang sebagai percobaan ulang saat gagal, jadi foto yang sudah tegak tidak
membayar apa pun.

**"Kenapa ada batas 90 detik?"**
Karena proksi Vercel memutus pada 120 detik, dan batas itu pernah benar-benar terlanggar —
satu kemasan memakan 120,2 detik, dibalas 502, dan servernya terus bekerja sambil memegang
kunci antrean sehingga dua giliran berikutnya ikut gagal. Setelah dipasang: maksimum 121,6
menjadi 80,2 detik, 502 dari 3 jadi nol, dan **mediannya tidak berubah**.

**"Jawaban salah bahaya tidak?"**
Sangat, dan di modul ini lebih berbahaya daripada modul uang — makan sesuatu yang sudah
kedaluwarsa. Karena itu kami **selalu** melaporkan benar/salah/diam terpisah, tidak pernah
satu persentase. Di proyek ini sudah **tiga kali** terbukti bahwa persentase yang naik bisa
menyembunyikan jawaban salah yang bertambah.

**"Kenapa model zona cuma 1 kelas, padahal 4 kelas lebih pintar?"**
Sudah dicoba dan diukur. Model 4 kelas memang menghapus kedua jawaban salah — mekanisme
penolakan kelasnya terbukti bekerja — **tetapi cakupan zonanya runtuh** dari 7/16 ke 2-3/16,
jadi akurasinya turun ke 75% dan mediannya naik dua setengah kali. Menang di nol sisi, jadi
tetap 1 kelas. Temuan negatif, dan dilaporkan apa adanya.

---

## 16. Yang masih kurang, jujur

| Hal | Kondisi |
| :--- | :--- |
| **n = 16 kemasan** | Kecil, dan 16 foto yang sama dipakai menyetel tujuh keputusan. **Semua angka di sini adalah estimasi resubstitusi.** Butuh 20-30 kemasan baru yang belum menyentuh penyetelan apa pun. |
| **Dua jawaban salah tersisa** | `chees` (nomor produksi dibaca sebagai tanggal) dan `ovaltine` (meleset 3 hari). |
| **mAP zona tidak dapat diukur** | `data/zona_sendiri/` kosong, jadi tidak ada kotak acuan. Angka 0,864 yang beredar milik model 4 kelas yang **ditolak**. Pengganti yang sah: **tingkat deteksi 9/14 = 64%** pada ambang 0,40, deteksi palsu 0/2 — dan itu **BATAS ATAS, bukan recall**, karena `chees` terdeteksi 0,72 tapi kotaknya menunjuk nomor produksi. |
| **Pembidikan belum dipecahkan** | Pengguna tidak tahu tanggalnya di sebelah mana. Pilihannya sudah dipetakan, semuanya sia-sia sebelum pengenalan cetakan diperbaiki. |
| **Lisensi dataset zona tidak tercantum** | Di Roboflow tertulis `license: null`. Untuk publikasi jurnal ini **risiko nyata**. |
| **`rotate_crop` tidak terukur** | Kasus yang ia sasar tidak ada di 16 kemasan uji. Tetap `false`. |
| **Bahan perbaikan sudah ketemu, belum dipakai** | Dataset publik **ExpDate** (Seker & Ahn 2022, KIST, CC BY 4.0): 1.767 gambar NYATA, anotasinya memuat `transcription` sehingga bisa dipakai **fine-tune PENGENAL** — yang memang penghambat kami. Tapi ia **tidak** menggantikan foto kemasan Indonesia. |

---

## 17. Dua modul lainnya

- `docs/pencerdasan-modul-uang.md`
- `docs/pencerdasan-modul-dokumen.md`
- Gambaran besar seluruh sistem: `docs/pencerdasan.md`
- Bahan jurnal modul ini: `docs/lampiran-radit/`, mulai dari
  `11_PERUBAHAN_KEDALUWARSA_24NOV.md`
- Sumber kebenaran semua angka: `docs/keputusan-teknis.md`
