# Pencerdasan: Modul Uang

**Untuk anggota kelompok, dibuat 26 November 2026.** Tujuannya satu: kalau dosen atau
penguji bertanya **"ini jalannya gimana?"** atau **"kok angkanya segitu?"**, kamu bisa
jawab tanpa buka kode.

Anggap kamu belum pernah lihat kodenya. Istilah teknis dijelaskan di tempatnya.
Kalau ada kata yang tidak kamu kenal, itu kesalahan tulisan ini, bukan kamu.

> **Kode yang dibahas:** `sayit/vision/money.py` (343 baris) dan bagian `vision.money`
> di `config/settings.yaml`.

---

## 1. Tugas modul ini

Pengguna tunanetra memegang uang kertas dan bertanya *"ini uang berapa"*.
Modul ini menjawab **nominalnya, dan kalau ada beberapa lembar, totalnya.**

Contoh jawaban sungguhan: *"Dua belas ribu rupiah. Dua lembar."*

Kenapa ini masalah nyata: **uang kertas Rupiah tidak punya huruf Braille.** Ada tanda
timbul (*blind code*) di sebagian pecahan, tapi cepat hilang kalau uangnya lecek, dan
banyak pengguna tidak bisa membedakannya dengan yakin.

---

## 2. Alurnya, enam langkah

```
  FOTO HP
     |
     +- 1. Penjaga mutu   -> foto gelap/buram? tolak, minta foto ulang
     +- 2. Resize         -> 3024x4032 piksel dikecilkan jadi maks 1600
     +- 3. YOLOv8n        -> gambar kotak di tiap lembar + sebut nominalnya
     +- 4. Pasca-proses   -> buang kotak palsu dan kotak ganda
     +- 5. Hitung         -> jumlah per nominal, lalu totalnya
     +- 6. Suara          -> putar klip MP3 yang sudah disiapkan
```

Langkah 3 itu yang biasanya orang sebut "AI-nya". Tapi **langkah 4 yang menentukan
jawabannya benar atau salah**, dan itu kode kita sendiri, bukan modelnya. Bagian 4 di
bawah menjelaskan kenapa.

---

## 3. Langkah 3: YOLO, dan kenapa harus YOLO

**YOLO** = *You Only Look Once*, sebuah model **deteksi objek**.

Bedanya dengan "klasifikasi gambar" biasa — dan ini yang sering ditanya:

| | Klasifikasi gambar | Deteksi objek (YOLO) |
| :--- | :--- | :--- |
| Jawabannya | satu label untuk SELURUH foto | satu label untuk SETIAP objek |
| Pada foto 3 lembar uang | *"ada uang"* | *"Rp2.000 di sini, Rp10.000 di sini, Rp10.000 di sini"* |
| Bisa menghitung total? | **tidak** | **ya** |

PRD kita mewajibkan **total beberapa lembar**. Jadi klasifikasi gambar biasa tidak cukup
secara arsitektur, bukan cuma kurang bagus. Itu alasan teknis memilih deteksi objek.

**Versinya `YOLOv8n`.** Huruf `n` = *nano*, varian paling kecil dari lima varian
(n/s/m/l/x). Dipilih karena **kodenya harus jalan di CPU** — laptop anggota lain tidak
punya GPU, dan demo harus bisa jalan di mana saja.

**Modelnya kita latih sendiri**, 7 kelas: `1000`, `2000`, `5000`, `10000`, `20000`,
`50000`, `100000`. Dilatih di Google Colab (GPU gratis), bobotnya disalin ke
`models/best_money.pt`. Bobot tidak masuk Git karena ukurannya ~6,5 MB dan Git tidak
cocok untuk berkas biner yang sering berubah.

Pengaturan inferensinya: `imgsz: 640` (gambar diperkecil ke 640 px oleh YOLO sendiri),
`device: cpu`, `max_det: 50` (maksimum 50 kotak per foto).

---

## 4. Langkah 4: pasca-pemrosesan — bagian yang paling sering ditanya

Keluaran mentah YOLO **tidak bisa dipakai langsung**. Satu lembar uang sering terdeteksi
dua-tiga kali, dan kalau tiap kotak dihitung satu lembar, pengguna diberi tahu uangnya
dua kali lebih banyak daripada kenyataan.

Urutan aturannya **tidak boleh ditukar**, dan tiap aturan punya kasus nyatanya:

| # | Aturan | Nilai | Apa yang dia buang |
| :-- | :--- | :--- | :--- |
| 1 | Ambang skor | `score_min: 0.30` | kotak yang modelnya sendiri tidak yakin |
| 2 | Buang kotak bersarang | `nested_area_ratio: 0.85` | kotak kecil di dalam kotak besar sekelas — biasanya **potret pahlawan** di dalam lembarnya |
| 3 | Ambang relatif | `relative_score_min: 0.80` | kotak yang skornya jauh di bawah kotak TERKUAT di foto yang sama |
| 4 | Gabung sekelas bertindihan | `same_class_iou: 0.0` (**mati**) | kotak sekelas yang bertindih tapi tidak bersarang |
| 5 | Deteksi konflik | `conflict_iou: 0.5` | kalau dua **kelas berbeda** bertindih, jawabannya **tidak diucapkan sama sekali** |

Tiga hal yang layak kamu hafal karena kemungkinan besar ditanya:

**(a) Kenapa aturan 3 ada, padahal sudah ada aturan 1?**
Karena pola kesalahannya bukan "skornya rendah", melainkan "skornya jauh di bawah yang
lain". Terukur 22 Oktober pada 35 foto: deteksi palsu lolos dengan skor **0,59-0,68**
sementara lembar aslinya **0,90-0,94** **di foto yang sama**. Ambang mutlak tidak bisa
memisahkan keduanya — kalau ambangnya dinaikkan ke 0,7, lembar asli di foto lain ikut
terbuang. Yang membedakan bukan nilainya, melainkan **jaraknya**.

**(b) Kenapa aturan 3 harus SESUDAH aturan 2, bukan sebelum?**
Karena lembar utuh bisa berskor **lebih rendah** daripada potret di dalamnya. Kalau
ambang relatif jalan dulu, justru lembar aslinya yang terbuang dan potretnya yang
bertahan. Ada tes yang mengunci urutan ini:
`test_lembar_utuh_dipertahankan_walau_skornya_lebih_rendah`.

**(c) Kenapa konflik kelas bikin sistem DIAM, bukan memilih yang skornya tertinggi?**
Karena satu lembar uang tidak mungkin punya dua nominal. Kalau model melihat satu
gumpalan dan menebak "ini 10.000 atau 50.000", **jawaban mana pun berpeluang salah**, dan
bagi pengguna tunanetra jawaban salah jauh lebih berbahaya daripada diam — kalau diam ia
foto ulang, kalau salah ia tidak punya cara tahu.

> **Arah kesalahan itu penting, dan terukur.** Diukur 22 Oktober pada 35 foto: **semua**
> kesalahan menggelembungkan jumlah (Rp5.000 diucapkan Rp25.000), tidak pernah
> mengecilkan. Arah itu yang paling berbahaya — pengguna menyerahkan uang **lebih banyak**
> daripada yang dikiranya.

---

## 5. Bonus: memberi tahu kalau uangnya terpotong

Kalau jawabannya tidak yakin, sistem **tidak cukup** bilang *"tidak yakin, foto ulang"* —
itu tidak memberi tahu APA yang harus diubah, dan pengguna tunanetra tidak bisa melihat
bahwa uangnya terpotong bingkai.

Jadi ada penanda `terpotong_tepi()`: kalau ada kotak yang menempel tepi bingkai (margin
2%, `edge_margin_ratio: 0.02`), klipnya diganti **`uang_terpotong`** yang berbunyi
*"mundurkan kamera sedikit"*.

> **Detail yang penting:** penanda ini dihitung dari deteksi **MENTAH**, bukan yang lolos
> ambang. Justru saat jawabannya tidak yakin, kotak mentah itulah satu-satunya petunjuk
> letak yang kita punya.

---

## 6. Pra-pemrosesan: cuma `resize`, dan itu keputusan yang diukur

Rangkaian pra-pemrosesan modul ini **`[resize]` saja** — tidak ada CLAHE, tidak ada
denoise.

**CLAHE dibuang 28 Oktober.** Ini salah satu temuan terbaik proyek ini, dan sebabnya
bukan "CLAHE jelek":

> **Ketidakcocokan latih-pakai (*train/serve mismatch*).** Notebook melatih model pada
> gambar **ASLI**, tetapi aplikasi dulu menerapkan CLAHE **saat inferensi**. Jadi model
> dites pada jenis gambar yang tidak pernah ia lihat saat belajar. Akibatnya tolok ukur
> 90,1% selalu diukur **tanpa** CLAHE sementara aplikasi sungguhan berjalan **dengan**
> CLAHE — dua hal yang berbeda, dan tidak ada yang menyadarinya berbulan-bulan.
>
> Setelah dibuang, diukur ulang pada 81 foto dengan config sungguhan:
> **96,3% menjadi 97,5%**, dan **latensi modul turun 36%** (88,4 ms menjadi 56,4 ms).
>
> Angka 97,5% itu **tercemar** (semua fotonya ikut melatih model), jadi jangan dikutip
> sebagai akurasi. Yang sah dikutip adalah **rasio latensinya** dan arah perbaikannya.

`resize` **wajib tetap ada**: ia pengendali kecepatan untuk foto HP 3024x4032 piksel.
Langkah `clahe` sendiri tidak dihapus dari kode — masih dipakai rangkaian `dokumen`.

---

## 7. Angka: akurasi

**85,0%** — 68 benar / 11 salah / 1 diam, dari 80 foto, validasi silang k-fold v3.

**Tapi di laporan tulis rentang 85-90%, bukan satu angka.** Alasannya penting:

| Versi | Akurasi | Data |
| :--- | :--- | :--- |
| v2 | 90,1% | 81 foto (termasuk 1 label cacat) |
| v3 | 85,0% | 80 foto bersih |

Penurunan 5 poin itu **bukan** modelnya memburuk. Mengeluarkan satu foto cacat mengubah
pembagian kelima lipatan k-fold **sepenuhnya**, jadi kedua angka diukur pada partisi yang
berbeda. Dengan 80 foto dan sekitar 10 kesalahan, selisih 5 poin ada **di dalam variasi
antar-run**. Artinya 90,1% mungkin ujung atas yang beruntung, bukan titik tengah.

**Riwayatnya:** 65,7% -> 68,8% -> 84,0% -> 90,1% -> 85,0%.

### Apa itu k-fold, dalam satu paragraf

**Validasi silang k-fold**: data dibagi 5 kelompok. Model dilatih pada 4 kelompok dan
diuji pada kelompok ke-5, lalu diulang 5 kali sampai setiap foto pernah jadi data uji.
Gunanya: **tidak ada foto yang dinilai oleh model yang pernah melihatnya.** Kalau model
diuji pada foto yang ikut melatihnya, itu namanya **resubstitusi** dan angkanya selalu
terlalu bagus.

Di proyek ini pembagiannya **atas kelompok kemiripan foto (pHash)**, bukan per berkas —
supaya dua foto lembar yang sama dari sudut berbeda tidak terpisah ke latih dan uji.

### Kelas terlemah

| Kelas | Benar | Kotak latih |
| :--- | :--- | :--- |
| Rp1.000 | 3/4 | **hanya 4** |
| Rp10.000 | 7/10 | 10 |
| Rp2.000 | 16/20 | 21 |
| Rp100.000 | **13/13** | 13 |

Polanya jelas: **makin sedikit contoh latih, makin lemah kelasnya.** Rp1.000 cuma punya
4 kotak, dan itu kelas terlemah berikutnya kalau mau diperbaiki.

Kesebelas kesalahan v3: **9 salah kenal kelas** (satu lembar, nominal keliru) dan
**2 salah hitung lembar** (Rp2.000 jadi Rp4.000; Rp10.000 jadi Rp30.000). Dua yang
terakhir **baru di v3** — v2 tidak punya satu pun.

---

## 8. Angka: kecepatan

| Yang diukur | Hasil |
| :--- | :--- |
| Inferensi **pertama** | 2,0 detik |
| Inferensi berikutnya | **40 ms** |
| Modul uang di dalam pipeline | 0,17 detik |
| Satu giliran penuh (suara masuk sampai suara keluar) | **1,4 detik** (target PRD <= 8 s) |

> **Kenapa inferensi pertama 50x lebih lambat?** Pemanggilan pertama mengalokasikan memori
> dan membangun grafik komputasinya. Karena itu `load()` dipanggil **saat aplikasi mulai**
> dengan gambar kosong (*warmup*), bukan saat pengguna sedang menunggu. Trik yang sama
> dipakai untuk TTS dan OCR.

**Modul uang punya anggaran latensi paling longgar di seluruh sistem** — 1,4 dari 8 detik.
Secara teori itu ruang untuk membeli akurasi dengan waktu. **Sudah dicoba, dan gagal:**

| Kondisi | Akurasi (35 foto) |
| :--- | :--- |
| `imgsz 640`, tanpa TTA | **65,7%** (terbaik) |
| `imgsz 640` + TTA | 62,9% |
| `imgsz 960`, tanpa TTA | 62,9% |
| `imgsz 1280`, tanpa TTA | **48,6%** |

**TTA** = *test-time augmentation*, inferensi dijalankan pada beberapa skala dan cerminan
lalu digabung. Lebih lambat, dan di sini **lebih buruk**. Menaikkan `imgsz` di atas ukuran
latih (640) justru merusak. Jadi anggaran latensi itu **tidak bisa ditukar dengan akurasi**
— opsi `money.augment` tetap ada di config tapi `false`.

---

## 9. Dua jebakan yang sudah menggigit kami

### (a) Dataset Roboflow yang labelnya tertukar

Dataset publik `deteksi-rupiah-jkkmu` punya **label tertukar** (uang Rp100.000 berlabel
5000, dan seterusnya), 3 salinan augmentasi per foto, dan **kebocoran antar-split** (foto
yang sama muncul di data latih dan data uji). Akhirnya hanya **56 gambar** yang dipakai,
labelnya diambil dari nama berkas.

**Skor 0,947 dari dataset itu TIDAK VALID. Jangan dikutip.**

Pelajarannya: **jangan pernah menilai model dari data uji yang buruk.** Kesalahan yang
sama persis hampir terulang di modul kedaluwarsa, saat model zona dinyatakan "tidak
bekerja" padahal yang buruk adalah foto ujinya.

### (b) Dua lembar dijawab satu nominal

Uji lapangan 12 November, foto Rp2.000 + Rp10.000. Deteksi mentahnya:

| Kotak | Kelas | Skor |
| :--- | :--- | :--- |
| seluruh bingkai | 10000 | 0,641 |
| seluruh bingkai | 50000 | 0,301 |
| seluruh bingkai | 2000 | 0,296 |

Model melihat **satu gumpalan** lalu menebak tiga kelas. Pasca-pemrosesan membuang dua,
dan **penjumlahannya tidak pernah dapat kesempatan**.

Sebabnya **data latih**: dari 80 foto, hanya **1** yang berlabel banyak lembar. Jadi
kemampuan "menghitung beberapa lembar" — yang justru dijanjikan PRD — **paling lemah
buktinya**, dan itu harus disebut jujur di laporan.

---

## 10. Dataset kita sendiri, apa adanya

- **80 gambar, 80 label, 81 kotak**, ketujuh kelas ada.
  Sebaran: 1000:4 - 2000:21 - 5000:20 - 10000:10 - 20000:7 - 50000:6 - 100000:13.
- Dua latar: meja kayu, dan dipegang di depan laptop.
- Penambahan 23 Oktober (+33 foto) **sengaja diarahkan ke tiga kelas terlemah** hasil
  k-fold, bukan dibagi merata: 2000 naik 8 ke 21, 5000 naik 7 ke 20, 100000 naik 6 ke 13.

Tiga catatan yang menyelamatkan dataset ini dari rusak:

1. **Satu foto dikeluarkan 9 November** (`5000_dipegang_ (3)`), **gambar DAN labelnya**.
   Labelnya terbukti salinan identik byte-per-byte dari foto lain, dan kotaknya 99,87%
   lebar bingkai. Menghapus `.txt`-nya saja sudah dicoba dan **gagal** karena tersalin
   balik dari Google Drive, jadi gambarnya ikut dipindah.
2. **Satu foto SENGAJA tidak dilabeli** (dua lembar, yang kedua tidak terbaca).
   **Menebak labelnya adalah persis kesalahan yang merusak dataset Roboflow.**
3. **JANGAN melengkapi foto tanpa label dengan berkas `.txt` kosong.** Dalam format YOLO,
   label kosong berarti *"tidak ada uang di gambar ini"* — bukan *"belum dilabeli"*. Itu
   pernah merusak latihan k-fold pertama (7 Oktober).

> **Pola kesalahan model yang paling sering saat melabeli: deteksi palsu di LAYAR LAPTOP**
> di bagian atas bingkai. Model membaca gambar uang di layar sebagai uang sungguhan.

---

## 11. Kenapa bobot v3 TIDAK dipasang, padahal lebih baru

Yang terpasang di `models/best_money.pt` adalah **v2**. Keputusan 24 November: **tetap v2.**
Bukan karena belum sempat, tetapi karena **diukur**.

Perbandingan **berpasangan** pada 78 berkas yang ada di kedua k-fold, tiap prediksi
diambil dari lipatan tempat foto itu jadi data uji:

| Bobot | Benar | Salah | Diam | Akurasi |
| :--- | :--- | :--- | :--- | :--- |
| **v2 (dipakai)** | **71** | 7 | 0 | **91,0%** |
| v3 | 67 | 10 | 1 | 85,9% |

Ketidaksepakatannya **5 lawan 1** (5 berkas benar di v2 dan salah di v3; cuma 1 sebaliknya).
**Uji McNemar tepat: p = 0,219.**

> **Apa artinya p = 0,219?** Artinya **belum signifikan secara statistik** — dengan n=78
> dan selisih sekecil itu, perbedaannya masih bisa kebetulan. Jadi **jangan mengklaim v2
> terbukti lebih baik.** Yang terbukti hanya: **tidak ada satu pun bukti yang mendukung
> menukar ke v3.**

Dan tidak ada pertukaran cepat-lawan-akurat untuk dipertimbangkan: keduanya `yolov8n.pt`,
`imgsz 640`, 100 epoch, batch 16 — **yang berbeda hanya data latihnya**, jadi
kecepatannya identik. Satu-satunya sumbu adalah akurasi.

> Mengeluarkan satu label cacat memperbaiki **kebersihan dataset**, bukan modelnya.
> Itu dua hal berbeda, dan mudah tertukar.

**Jangan mengulangi sapuan ini dengan menjalankan kedua bobot pada `data/uji_sendiri/`:**
seluruh 80 foto ikut melatih KEDUA model, jadi itu resubstitusi untuk dua-duanya dan hanya
bisa mendeteksi kerusakan total.

---

## 12. Penyimpangan dari PRD yang WAJIB disebut di laporan

**`money.score_min` = 0,30, sedangkan PRD menulis 0,50.**

Ini penyimpangan yang disadari dan ada datanya. Sapuan ambang pada k-fold v3:

| Ambang | Benar / Salah / Diam | Akurasi |
| :--- | :--- | :--- |
| 0,15 - 0,20 - 0,25 | 69 / 11 / 0 | 86,25% |
| **0,30 (dipakai)** - 0,35 | 68 / 11 / 1 | **85,0%** |
| 0,40 | 67 / 11 / 2 | 83,75% |
| 0,50 (nilai PRD) | 64 / 9 / 7 | 80,0% |

Perhatikan kolom DIAM: ambang 0,50 membuat **7 foto** tidak dijawab sama sekali.

> **Kenapa tetap 0,30 padahal 0,25 terlihat lebih bagus?** Karena sapuan itu dijalankan
> pada bobot **v3**, dan v3 tidak dipakai. Menyetel ambang dari model yang berbeda dengan
> yang terpasang adalah kesalahan yang mudah lolos tanpa terlihat.

Dasar penyimpangan: PRD baris 154 menyatakan target awal boleh direvisi setelah pengukuran.
Sebutkan ini sejajar dengan penyimpangan `bright.min_mean` (245, bukan 220).

---

## 13. Kalau ditanya — jawaban siap pakai

**"Kenapa YOLO, bukan CNN klasifikasi biasa?"**
Karena PRD mewajibkan total beberapa lembar. Klasifikasi memberi satu label untuk seluruh
foto, jadi secara arsitektur tidak bisa menghitung. Deteksi objek memberi satu kotak dan
satu label per lembar.

**"Akurasinya berapa?"**
85-90%, dari validasi silang k-fold pada 80 foto. Dua pengukuran sah memberi 85,0% dan
90,0% pada partisi berbeda, dan dengan n=80 selisih itu di dalam variasi antar-run — jadi
satu angka presisi akan menyesatkan. Rinciannya 68 benar / 11 salah / 1 diam.

**"Kok tidak 100%? Uang kan bentuknya baku."**
Tiga sebab terukur: (1) data latih cuma 80 foto dengan 2 latar, jadi variasi cahaya dan
emisi tahun lain belum terwakili; (2) kelas dengan sedikit contoh paling lemah — Rp1.000
cuma punya 4 kotak latih; (3) foto banyak lembar hampir tidak ada di data latih, cuma 1
dari 80.

**"Kenapa pakai teknik klasik kalau sudah ada deep learning?"**
Justru ada tiga lapis non-deep-learning yang menentukan jawabannya: penjaga mutu foto,
`resize` sebagai pengendali latensi, dan **pasca-pemrosesan geometris** (IoU, luas kotak,
kotak bersarang). Tanpa lapis ketiga, satu lembar Rp100.000 diucapkan "dua ratus ribu" —
dan itu murni perhitungan geometri, bukan model.

**"Pra-pemrosesannya membantu?"**
Untuk modul uang: **tidak**, dan itu diukur. Ablasi pada 20 foto memberi hasil identik
(13/3/4) dengan maupun tanpa CLAHE, lalu CLAHE dibuang 28 Oktober karena ketidakcocokan
latih-pakai. Jawaban berbeda untuk modul dokumen — di sana pra-pemrosesan membantu 3,4
poin. **Jadi pertanyaan ini tidak punya satu jawaban yang berlaku umum**, dan itu justru
temuan ablasi paling menarik di proyek ini.

**"Kenapa ambangnya 0,30, bukan 0,50 seperti di PRD?"**
Penyimpangan yang disadari, dengan sapuan ambang sebagai buktinya. Pada 0,50 ada 7 foto
yang tidak dijawab sama sekali; pada 0,30 tinggal 1. Jumlah jawaban SALAH tidak bertambah.

**"Kalau modelnya salah, bahaya tidak?"**
Ya, dan itu sebabnya ada tiga penjaga: konflik kelas membuat sistem diam alih-alih
menebak, ambang relatif membuang deteksi palsu, dan penanda terpotong memberi saran
konkret. Semua kesalahan terukur mengarah ke **menggelembungkan** jumlah — arah yang
paling berbahaya — jadi penjaganya memang diarahkan ke situ.

**"Datanya dari mana?"**
80 foto kami sendiri, dilabeli manual. Dataset Roboflow publik **ditolak** karena
labelnya tertukar, ada 3 salinan augmentasi per foto, dan ada kebocoran antar-split.
Skor 0,947 dari dataset itu tidak valid dan tidak kami pakai.

---

## 14. Yang masih kurang, jujur

| Hal | Kondisi |
| :--- | :--- |
| **Banyak lembar hampir tak teruji** | Cuma 1 dari 80 foto latih berlabel banyak lembar. Fitur penjumlahan yang dijanjikan PRD paling lemah buktinya. |
| **Kelas Rp1.000 cuma 4 kotak latih** | Kelas terlemah berikutnya. |
| **Belum ada variasi latar / cahaya / emisi** | Dua latar saja. Foto malam, uang lecek, emisi 2016 belum terwakili. |
| **Penyetelan parameter masih resubstitusi** | Ambang dan rangkaian pra-pemrosesan disetel pada 80 foto yang sama. k-fold menjawab ini untuk modelnya, bukan untuk pemilihan parameternya. |
| **Ambang penjaga mutu belum dikalibrasi untuk uang** | `blur.min_variance` diturunkan ke 15 berdasarkan foto KEMASAN, bukan foto uang. |

---

## 15. Dua modul lainnya

- `docs/pencerdasan-modul-kedaluwarsa.md`
- `docs/pencerdasan-modul-dokumen.md`
- Gambaran besar seluruh sistem: `docs/pencerdasan.md`
- Sumber kebenaran semua angka: `docs/keputusan-teknis.md`
