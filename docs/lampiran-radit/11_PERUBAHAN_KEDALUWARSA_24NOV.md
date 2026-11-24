# Perubahan modul kedaluwarsa — 24 November 2026

Untuk Radit, dan untuk Claude yang membantunya menulis jurnal.

Berkas ini **menambah**, tidak menggantikan, lampiran 23 November. Angka
**akurasi** di lampiran lama masih berlaku seluruhnya. Angka **latensi** di
lampiran lama sudah usang — bagian 6 di bawah mendaftar persisnya baris mana.

Repo pada commit `715134d`. Semua angka di sini diukur pada 24 November 2026
di laptop pengembang (i7-13650HX, 20 CPU logis, **CPU saja, tanpa GPU**).

---

## 0. Ringkasan satu paragraf

Modul kedaluwarsa **tidak berubah akurasinya sama sekali** hari ini: tetap
81%, dan jawabannya **identik berkas per berkas**. Yang berubah adalah
kecepatannya, karena mesin OCR-nya kini berjalan di atas ONNX Runtime alih-alih
PaddlePaddle. Median 7,40 → 2,39 detik, dan kasus terburuknya 90,50 → 9,74
detik. Akibat terpentingnya bukan angka median itu, melainkan hilangnya ekor
90 detik, yang menghapus satu risiko arsitektur. Dan karena itu, **target
latensi PRD NFR-01 terpenuhi untuk pertama kalinya**.

---

## 1. Apa yang diubah, persisnya

Satu baris config, ditambah satu mekanisme pendukung.

```yaml
vision:
  document:
    engine: paddleocr              # sebelumnya easyocr
    paddle:
      engine: onnxruntime          # <-- INI perubahannya
      text_detection_model_name: PP-OCRv5_mobile_det
      text_recognition_model_name: PP-OCRv5_mobile_rec
  expiry:
    engine: paddleocr              # tidak berubah
    paddle:                        # <-- timpaan BARU, khusus modul ini
      text_recognition_model_name:   # kosong = PP-OCRv6_medium_rec
```

`engine: onnxruntime` memakai **model yang sama persis**, hanya dijalankan
oleh runtime yang berbeda. paddlex mengunduh sendiri varian ONNX-nya
(`PP-OCRv5_mobile_det_onnx`, `PP-OCRv6_medium_rec_onnx`); tidak ada konversi
manual, tidak ada `paddle2onnx`, dan **tidak ada pustaka baru yang dipasang** —
`onnxruntime` sudah ikut terpasang sejak lama sebagai dependensi tidak langsung.

Versi yang dipakai saat pengukuran, **wajib ditulis di jurnal**:

```
paddleocr==3.7.0   paddlepaddle==3.3.1   paddlex==3.7.2   onnxruntime==1.30.0
deteksi : PP-OCRv5_mobile_det  (varian ONNX)
pengenal: PP-OCRv6_medium_rec  (varian ONNX)   <- modul kedaluwarsa
bobot zona: models/best_zone.pt (1 kelas)
```

---

## 2. Hasilnya pada 16 kemasan uji

Diukur dalam **satu sesi**, dua kondisi berurutan, dengan
`python scripts\ukur_kedaluwarsa.py`. Data per berkas:
`10_latensi_kedaluwarsa_sebelum_sesudah.csv`.

| | BENAR | SALAH | DIAM | akurasi | median | **terburuk** | total |
|---|---|---|---|---|---|---|---|
| PaddlePaddle (sebelum) | 13 | 2 | 1 | **81%** | 7,40 s | **90,50 s** | 268,3 s |
| ONNX Runtime (sesudah) | 13 | 2 | 1 | **81%** | **2,39 s** | **9,74 s** | **42,7 s** |

Percepatan: **median 3,1x, ekor 9,3x, total 6,3x.**

**Jawabannya identik pada keenam belas berkas.** Dua yang salah tetap sama
(`chees` menjawab 2026-05-21 padahal 2027-03-21; `ovaltine` 2027-09-30 padahal
2027-09-27) dan satu yang diam tetap sama (`tolakangin2`). Tidak ada satu pun
berkas yang nilainya berubah.

Kalimat yang akurat untuk jurnal: *perubahan ini murni optimasi latensi;
akurasi tidak ikut berubah, dan itu diverifikasi per berkas, bukan hanya
lewat rerata.*

### Kenapa dasar pembandingnya dapat dipercaya

Kondisi "sebelum" **diukur ulang hari itu juga**, tidak disalin dari catatan
lama. Hasilnya mereproduksi catatan 20 November hampir persis (81%, median
7,82 s, terburuk 90,0 s, total 262,1 s lawan 81%, 7,40 s, 90,50 s, 268,3 s),
jadi instrumennya terbukti sehat sebelum dipakai menilai kondisi baru.

Ini penting karena latensi di modul ini **berderau besar antar-sesi**:
kondisi yang sama persis pernah memberi median 6,54 detik di satu proses dan
10,46 detik di proses lain pada hari yang sama. Karena itu aturannya,
dan jurnal sebaiknya menyebutnya: **hanya perbandingan di DALAM satu sesi yang
sah dikutip**, bukan angka detik mutlaknya.

---

## 3. Kenapa pengenalnya harus berbeda dari modul dokumen

Ini temuan yang layak masuk jurnal, karena ia **temuan negatif yang mahal**
dan menunjukkan prosedur yang benar.

Mesin dokumen ikut dipindah ke PaddleOCR+ONNX hari itu, dan pengenal yang
memenangkan dokumen adalah `PP-OCRv5_mobile_rec`. Godaannya jelas: pakai satu
pengenal untuk kedua modul, lebih sederhana dan lebih hemat memori. Diukur
dulu sebelum ditukar, dan hasilnya:

| pengenal | BENAR | SALAH | DIAM | akurasi |
|---|---|---|---|---|
| `PP-OCRv6_medium_rec` (dipakai) | 13 | 2 | 1 | **81%** |
| `PP-OCRv5_mobile_rec` | 10 | 2 | 4 | **62%** |

Tiga kemasan yang tadinya BENAR menjadi DIAM: `tolakangin1`, `kecapasin`,
`merica`. Penjelasannya masuk akal dan konsisten dengan temuan lama proyek
ini: **cetakan dot-matrix pada kemasan menuntut pengenal yang lebih besar,
sedangkan teks cetak pada kertas A4 tidak.** Penghambat modul kedaluwarsa
sejak awal memang pengenalan cetakan, bukan pembidikan.

Karena itu `vision.expiry.paddle` kini boleh menimpa setelan modul dokumen,
dan timpaan apa pun **memaksa dua pembaca terpisah** walau mesinnya sama.

### Dan ini hampir lolos tanpa ketahuan

Verifikasi pertama melaporkan **62%, bukan 81%**, karena
`scripts/ukur_kedaluwarsa.py` menyusun sendiri config pembacanya dan
melewatkan timpaan itu — jadi skrip mengukur `mobile_rec` sementara aplikasi
akan menjalankan `medium_rec`. Angka 62% itu **terlihat masuk akal
sepenuhnya**. Satu-satunya yang membocorkannya adalah baris diagnostik
`[saklar]` yang mencetak nilai setiap saklar di tiap kondisi.

Aturannya sekarang hanya ditulis di satu tempat,
`pipeline.cfg_ocr_kedaluwarsa()`, dan dipakai baik oleh aplikasi maupun oleh
skrip pengukuran. **Logika config yang diduplikasi adalah cara bug ini lahir.**

Untuk jurnal, ini contoh konkret dari praktik yang bisa disebut sebagai
bagian metodologi: *setiap skrip pengukuran mencetak nilai seluruh parameter
yang sedang diuji, supaya kondisi yang tertukar tidak lolos sebagai angka
yang kebetulan masuk akal.*

---

## 4. Target latensi PRD NFR-01 sekarang terpenuhi

PRD NFR-01 menargetkan latensi ujung ke ujung ≤ 8 detik, diukur dari pengguna
selesai bicara sampai suara jawaban mulai (STT + pipeline + render TTS;
pemuatan model tidak dihitung). Sejak 2 Oktober modul kedaluwarsa dan dokumen
**melanggarnya**, dan penyimpangan itu diterima secara sengaja dan tercatat.

Diukur ulang dengan `python scripts\ukur_latensi.py` sesudah perubahan:

| intent | 2 Okt | 24 Nov | p90 | maks | status |
|---|---|---|---|---|---|
| uang | 1,4 s | 1,4 s | 1,5 s | 1,5 s | LOLOS |
| kendali | 1,3 s | 1,3 s | 1,7 s | 1,7 s | LOLOS |
| **kedaluwarsa** | **11,4 s** | **3,0 s** | 6,1 s | 11,9 s | **LOLOS** |
| **dokumen** | **11,5 s** | **5,0 s** | 7,6 s | 9,5 s | **LOLOS** |

PRD Bagian 11 menilai dari **median**, dan keempat median lolos.
**Penyimpangan NFR-01 dapat dicabut dari laporan.**

**Tetapi sebutkan ekornya.** Kedaluwarsa maks 11,9 detik dan dokumen maks
9,5 detik — sebagian foto masih melewati 8 detik walau mediannya lolos.
Jurnal yang menulis "8 detik tercapai" tanpa menyebut ini tidak jujur.
Pemuatan model 11,3 detik, sekali saat aplikasi mulai, di luar NFR-01.

### Peringatan metodologis yang sebaiknya ikut ditulis

Putaran NFR-01 **pertama** hari itu memberi dokumen **12,4 detik**; putaran
kedua pada konfigurasi yang sama persis memberi **5,0 detik**. Yang dipercaya
adalah putaran kedua, dan alasannya **bukan** karena angkanya lebih bagus,
melainkan karena ia cocok dengan pengukuran komponen yang terpisah
(STT 1,3 + pipeline 2,6 + TTS 1,2 ≈ 5,1 detik, dan sintesis 40 kata terukur
0,77 detik median pada 40 panggilan). Putaran pertama tidak cocok dengan
apa pun; penyebabnya transien di layanan TTS pihak ketiga.

Pelajarannya, dan ini layak disebut: **satu putaran tidak cukup untuk
mengutip latensi**, dan cara memutuskan putaran mana yang benar adalah
memeriksa apakah ia konsisten dengan pengukuran komponennya.

---

## 4b. Hasil lewat deploy sungguhan, bukan hanya pemanggilan modul

Angka 81% di atas diukur dengan memanggil `ExpiryReader.read()` langsung di
laptop, jadi ia **melewatkan quality gate dan seluruh lapisan jaringan**.
Pengukuran lewat deploy (klien → Vercel → ngrok → FastAPI) menangkap keduanya.
48 percobaan, 16 gambar × 3 pengulangan. Data: `09_waktu_respons_deploy_onnx.csv`,
penilaian: `12_penilaian_deploy_onnx.txt`.

| | sebelum ONNX (24 Nov pagi) | sesudah ONNX |
|---|---|---|
| akurasi lewat deploy | 75% (12/2/2) | **75% (12/2/2)** |
| percobaan berhasil | 48 / 48 | **48 / 48** |
| median total per giliran | 12,20 s | **4,73 s** |
| maksimum | 80,17 s | **38,32 s** |
| tahap A `/foto` median | — | 1,11 s |
| tahap B `/tanya` median | — | 3,39 s |
| kegagalan infrastruktur | nol | **nol** |

Akurasi deploy **tidak berubah**, konsisten dengan akurasi lokal yang juga
tidak berubah. Yang membaik latensinya: median 2,6x lebih cepat.

**Selisih 81% lokal lawan 75% deploy seluruhnya dari satu berkas**,
`20290821_tisu1.PNG`, yang ditolak quality gate ("foto terlalu gelap")
sebelum OCR. Penyebabnya sudah ditelusuri dan dicatat 24 November: berkas itu
**tangkapan layar dengan 38% bingkainya berupa bilah hitam**, sehingga rata-rata
intensitasnya 51,4 (di bawah ambang 60); tanpa bilah hitam nilainya 83,5 dan
lolos nyaman. Ini cacat **data uji**, bukan cacat sistem, dan ambangnya
sengaja **tidak** diturunkan karena itu berarti mengkalibrasi pada data tidak sah.

Catat juga bahwa maksimum deploy (38,32 s pada `tolakangin2`) jauh di atas
maksimum lokal (9,74 s) untuk berkas yang sama. Selisih itu **belum
ditelusuri**; kandidatnya jaringan, antrean, dan ukuran unggahan. Jangan
jelaskan sebabnya di jurnal tanpa mengukurnya dulu.

---

## 5. Anggaran waktu `budget_s` — statusnya berubah makna

Pagi 24 November, sebelum ONNX, dipasang `vision.expiry.budget_s: 90.0`:
sebelum tiap percobaan rotasi gambar penuh, `read()` memeriksa
`waktu_terpakai + biaya_lintasan > anggaran`, dengan `biaya_lintasan`
**diukur dari lintasan pertama**, bukan ditebak. Lintasan pertama tidak
pernah dipotong, berapa pun ketat anggarannya.

Alasannya batas proksi Vercel **120 detik** untuk semua paket, dan kasus
terburuk saat itu 121,63 detik — benar-benar melanggarnya, 3 dari 3
pengulangan. Hasil waktu itu: maksimum 121,63 → 80,17 detik, balasan 502
dari 3 menjadi nol, akurasi lewat deploy 62% → 75%.

**Sesudah ONNX, kasus terburuk 9,74 detik, jadi anggaran 90 detik tidak akan
pernah tersentuh.** Ia berubah dari penambal aktif menjadi jaring pengaman
pasif. Keduanya layak ditulis di jurnal sebagai urutan kejadian: masalah
nyata, ditambal dengan benar, lalu hilang di akarnya.

Angka 90 diambil dari **batas arsitektur** (120 detik dikurangi ruang untuk
unggah foto, render suara, dan jaringan), **bukan** dari 16 kemasan uji —
set itu sudah dipakai memilih tujuh keputusan lain, jadi menyetelnya di situ
akan menjadi resubstitusi.

---

## 6. Baris mana di lampiran lama yang sudah USANG

Jangan dikutip lagi:

| angka lama | berkas | ganti dengan |
|---|---|---|
| kedaluwarsa median 9,96 s / 7,82 s | `BACA_DULU.md`, `02_banding_model_zona.csv` | **2,39 s** |
| kedaluwarsa terburuk 90,0 s | `BACA_DULU.md` | **9,74 s** |
| kedaluwarsa total 262,1 s | `BACA_DULU.md` | **42,7 s** |
| "latensi 11,4 s, NFR-01 dilanggar" | `BACA_DULU.md` | **3,0 s, NFR-01 LOLOS** |
| waktu respons deploy (48 percobaan) | `06_waktu_respons_deploy.csv` | `09_waktu_respons_deploy_onnx.csv` |

Yang **masih berlaku sepenuhnya**:

- akurasi 81% (13 BENAR / 2 SALAH / 1 DIAM) — tidak berubah
- `01_hasil_per_gambar.csv` — nilai per berkas tidak berubah
- `03_tanggal_acuan.csv` — tanggal acuan tidak berubah
- `05_dataset_zona.md` — dataset dan lisensinya tidak berubah
- `08_subset_foto_kamera.txt` — subset foto kamera 85%, tidak berubah
- seluruh temuan model zona 4 kelas (temuan negatif, tetap berlaku)

`04_konfigurasi_kedaluwarsa.yaml` **sudah diekstrak ulang** dari config sekarang,
jadi ia mutakhir dan boleh dilampirkan apa adanya.

---

## 7. Yang TIDAK boleh diklaim di jurnal

Daftar ini sama pentingnya dengan angkanya.

1. **Jangan tulis "akurasi meningkat".** Akurasi kedaluwarsa **tidak berubah**:
   81% sebelum dan sesudah, identik per berkas. Yang membaik hanya kecepatan.
   (Untuk modul dokumen, CER memang membaik 14,9% → 9,0% — tetapi itu modul
   yang berbeda dan jangan dicampur.)

2. **Jangan tulis "ONNX Runtime 1,4–1,5x lebih cepat".** Angka itu dari blog
   pihak ketiga yang menginspirasi percobaan ini. Yang terukur di sini
   **3,1x median dan 9,3x pada ekor**. Kutip pengukuran sendiri.

3. **Jangan klaim performa pada kemasan Indonesia secara umum.** 16 kemasan,
   14 produk unik, 3 di antaranya tangkapan layar. Set ini juga **dipakai
   untuk MENYETEL** tujuh keputusan lain, jadi 81% adalah **estimasi
   resubstitusi**, bukan hasil pada data tertahan. Ini wajib disebut.

4. **Jangan kutip satu angka latensi tanpa konteks.** Sebutkan median **dan**
   terburuk, dan sebutkan bahwa ia dari satu sesi. Modul ini pernah memberi
   6,54 dan 10,46 detik untuk kondisi identik pada hari yang sama.

5. **Jangan sebut "pembidikan sudah terpecahkan".** Cakupan zona tetap 9 dari
   14 kemasan bertanggal; 7 berkas jatuh ke jalur cadangan OCR seluruh gambar.
   Tidak ada yang berubah di situ hari ini.

6. **Jangan sebut ONNX memperbaiki `chees` atau `ovaltine`.** Keduanya masih
   salah, persis seperti sebelumnya.

---

## 8. Cara mereproduksi setiap angka

```powershell
# akurasi + latensi kedaluwarsa, config apa adanya
python scripts\ukur_kedaluwarsa.py

# kondisi pembanding: paksa backend lama, SATU SESI dengan di atas
python scripts\ukur_kedaluwarsa.py --engine ""

# membuktikan pengenal mobile_rec merusak modul ini
python scripts\ukur_kedaluwarsa.py --rec-model PP-OCRv5_mobile_rec

# NFR-01 ujung ke ujung (STT + pipeline + TTS)
python scripts\ukur_latensi.py

# akurasi lewat deploy sungguhan (butuh backend + ngrok hidup)
python scripts\ukur_respons_deploy.py --ulang 3 --keluar hasil.csv
python scripts\nilai_respons_deploy.py hasil.csv
```

Setiap skrip mencetak baris `[saklar]` berisi nilai mesin, backend, model
deteksi, dan model pengenal yang benar-benar dipakai. **Salin baris itu ke
catatan tiap kali mengukur** — ia yang membedakan angka sah dari angka yang
kebetulan masuk akal.

Catatan teknis: **satu proses hanya boleh memuat satu mesin OCR.** Menjalankan
PaddleOCR dan EasyOCR dalam satu proses pernah memberi angka yang salah tanpa
crash. Karena kedua modul kini memakai PaddleOCR, masalah itu hilang dengan
sendirinya — tetapi aturannya tetap berlaku bila kelak EasyOCR dipakai lagi.

---

## 9. Kalimat siap pakai

Boleh disalin dan disunting.

> Optimasi runtime pada modul pembacaan tanggal kedaluwarsa dilakukan dengan
> mengganti backend inferensi PaddleOCR dari PaddlePaddle ke ONNX Runtime,
> tanpa mengubah arsitektur model, bobot, maupun parameter pasca-pemrosesan.
> Pada 16 citra kemasan uji, akurasi sistem tidak berubah (13 benar, 2 salah,
> 1 tanpa jawaban; 81%) dan identik pada setiap citra, sementara waktu
> pemrosesan median turun dari 7,40 detik menjadi 2,39 detik (3,1x) dan kasus
> terburuk dari 90,50 detik menjadi 9,74 detik (9,3x). Karena akurasi tidak
> terpengaruh, perubahan ini dilaporkan sebagai optimasi latensi murni.

> Penurunan kasus terburuk tersebut menghapus satu kendala arsitektur: batas
> waktu proksi 120 detik pada layanan hosting frontend, yang sebelumnya
> terlampaui secara deterministik pada satu citra uji dan harus ditangani
> dengan mekanisme anggaran waktu.

> Setelah optimasi ini, target NFR-01 (latensi ujung ke ujung ≤ 8 detik)
> terpenuhi pada keempat jenis permintaan berdasarkan nilai median: nominal
> uang 1,4 detik, perintah kendali 1,3 detik, tanggal kedaluwarsa 3,0 detik,
> dan pembacaan dokumen 5,0 detik. Nilai maksimum masih melampaui target pada
> sebagian citra (kedaluwarsa 11,9 detik; dokumen 9,5 detik).

> Percobaan menyatukan model pengenalan teks untuk modul dokumen dan modul
> kedaluwarsa ditolak berdasarkan pengukuran: model `PP-OCRv5_mobile_rec` yang
> optimal untuk dokumen menurunkan akurasi modul kedaluwarsa dari 81% menjadi
> 62%, karena cetakan dot-matrix pada kemasan memerlukan model pengenalan
> dengan kapasitas lebih besar dibanding teks cetak pada kertas.

> Seluruh angka akurasi pada modul ini merupakan estimasi resubstitusi: 16
> citra uji yang sama digunakan untuk memilih tujuh keputusan konfigurasi,
> sehingga belum tersedia pengujian pada data tertahan.

---

## 10. Yang masih terbuka di modul ini

Tidak berubah hari ini, dan sebaiknya tetap disebut di jurnal sebagai
keterbatasan:

1. **Dua jawaban salah.** `chees` membaca nomor produksi `210526` sebagai
   tanggal padahal `MAR` tercetak di sebelahnya. `ovaltine` meleset tiga hari.
2. **Cakupan zona 9 dari 14** kemasan bertanggal; sisanya jalur cadangan.
3. **Belum ada pengujian pada data tertahan.** Butuh 20–30 kemasan baru yang
   belum dipakai menyetel apa pun.
4. **Lisensi dataset detektor zona tidak tercantum** (`license: null` di
   Roboflow, diperiksa 22 November). Ini risiko nyata untuk publikasi.
   Alternatif berlisensi jelas ada di `05_dataset_zona.md`.
5. **Pengujian pengguna proksi dan kuesioner SUS belum pernah dijalankan.**
   Itu satu-satunya metrik PRD Bagian 11 bertarget angka yang belum diukur.
