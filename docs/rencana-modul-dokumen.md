# Rencana menaikkan kelayakan modul dokumen

**Disusun 31 Oktober 2026. Waktu tersedia: 2–3 hari.**

---

## Duduk perkaranya: masalahnya BUKAN akurasi

Ini perlu diluruskan lebih dulu, karena mengubah seluruh arah rencana.

Akurasi dokumen **sudah pernah tercapai**. Diukur 2 Oktober pada 13 dokumen yang sama:

| Mesin | CER | Target ≤15% | Latensi per halaman |
| :--- | ---: | :--- | ---: |
| EasyOCR (dipakai sekarang) | 15,3% | meleset 0,3 poin | **7,3 detik** |
| **PaddleOCR** | **9,4%** | **TERCAPAI** | **41,8 detik** |

PaddleOCR lebih baik di **11 dari 13** dokumen. Lompatan terbesarnya justru pada
`ketentuan_makalah`, foto yang selama ini menyeret rata-rata: **76,9% → 11,3%**.

**Jadi yang menghalangi bukan ketepatan, melainkan 41,8 detik.** Untuk pengguna tunanetra,
menunggu 42 detik sebelum kata pertama dibacakan tidak dapat diterima.

Dan latensi itu **tidak bisa ditekan lewat ukuran gambar**, karena biayanya per **baris
teks**, bukan per piksel:

| Ukuran | Latensi | CER |
| ---: | ---: | ---: |
| 800 px | 34,6 s | 15,2% (target gagal) |
| 1200 px | 38,1 s | 10,0% |
| 1600 px | 41,8 s | 9,4% |

Memperkecil gambar hanya menghemat 7 detik tetapi mengorbankan targetnya.

**Pertanyaan yang benar untuk 2–3 hari ke depan:** bagaimana mendapatkan ketepatan
PaddleOCR pada latensi yang bisa diterima — bukan bagaimana menaikkan akurasi.

---

## Tiga jalur, berurutan menurut biaya

### Jalur 1 — Ganti dua foto uji yang bukan foto kertas (Hari 1 pagi, ~20 menit waktumu)

Bahannya **sudah siap** di `data/uji_dokumen/cetak/`: dua halaman siap cetak berisi teks
yang sama dengan dokumen lama, berikut teks acuannya yang sudah dibuktikan identik.

Dua foto itu bukan foto kertas sama sekali:

| Berkas | CER | Sebenarnya apa |
| :--- | ---: | :--- |
| `ketentuan_makalah` | 76,9% | foto **layar monitor**, huruf kecil, ada pantulan |
| `open_recruitment` | 22,0% | **tangkapan layar WhatsApp**; OCR-nya bagus, tetapi ikut membaca jam, nama grup, nomor telepon |

Pada **11 foto kertas sungguhan, CER-nya 9,0%**.

**Perkiraan hasil:** rerata 13 dokumen turun ke sekitar **9–11%** dengan EasyOCR, latensi
tetap 7,3 detik. Titik impasnya longgar — kedua foto baru boleh ber-CER sampai **47,8%**
dan target tetap lolos.

**Peringatan yang wajib masuk laporan:** ini **tidak membuat modelnya lebih baik**, ini
membuat **data ujinya jujur**. Mengganti foto uji yang di luar lingkup (tangkapan layar
bukan foto dokumen) sah, tetapi penguji jurnal akan menanyakannya, jadi harus dinyatakan
terbuka beserta CER foto lamanya.

---

### Jalur 2 — Tuas PaddleOCR yang belum pernah dicoba (Hari 1 siang – Hari 2)

**Ini bagian yang paling berpeluang mengubah keadaan, dan belum pernah diuji sama sekali.**

Yang sudah diketahui: biaya PaddleOCR ada di tahap **pengenalan per baris**, bukan
deteksi. Yang sudah dilakukan tim: mengganti model **deteksi** ke `PP-OCRv5_mobile_det`.

Masalahnya, itu mempercepat tahap yang **bukan** penghambatnya.

Diperiksa hari ini di `sayit/vision/document.py`: pabrik PaddleOCR hanya meneruskan
`text_detection_model_name`. Padahal pustakanya (paddleocr 3.7.0) juga menerima:

| Parameter | Status sekarang |
| :--- | :--- |
| `text_detection_model_name` | diteruskan (sudah `mobile_det`) |
| **`text_recognition_model_name`** | **tidak diteruskan — belum pernah dicoba** |
| **`text_recognition_batch_size`** | **tidak diteruskan — belum pernah dicoba** |

Jadi model **pengenalan** masih memakai versi bawaan yang berat, dan baris-baris teks
dikenali satu per satu tanpa pengelompokan.

**Yang dikerjakan:**

1. Teruskan kedua parameter itu dari config (~6 baris di `_buat_paddle`, plus tesnya).
2. Ukur kombinasi berikut pada 13 dokumen yang sama, catat **CER dan latensi bersama-sama**:

   | Kondisi | Model pengenalan | Batch |
   | :--- | :--- | ---: |
   | dasar (pembanding) | bawaan | bawaan |
   | A | `PP-OCRv5_mobile_rec` | bawaan |
   | B | `PP-OCRv5_mobile_rec` | 8 |
   | C | `PP-OCRv5_mobile_rec` | 16 |
   | D | bawaan | 16 |

**Kalau berhasil:** misalnya 41,8 detik turun ke 10–15 detik dengan CER tetap 9–11% —
modul dokumen langsung tercapai targetnya dengan margin lebar, dan Jalur 3 tidak perlu.

**Kalau gagal:** kita tahu pasti bahwa latensi PaddleOCR memang tidak bisa ditawar, dan
itu sendiri temuan yang layak ditulis.

**Biaya:** sekitar 6 baris kode, lalu 5 kondisi × 13 dokumen. Berdasarkan 41,8 detik per
halaman, sekitar **45 menit waktu mesin per kondisi** untuk yang lambat, jauh lebih cepat
untuk yang mobile. Bisa ditinggal jalan.

**Risiko yang perlu dijaga:** jangan mengukur CER tanpa latensi, atau sebaliknya. Proyek
ini sudah tiga kali kena: akurasi dan latensi di modul ini saling terkait.

**Aman dari efek samping:** mesin dokumen (`vision.document.engine`) sudah terpisah dari
mesin kedaluwarsa (`vision.expiry.engine`) sejak 2 Oktober. Mengubah dokumen **tidak
akan** merusak kedaluwarsa yang sudah 81%.

---

### Jalur 3 — Pembacaan bertahap (Hari 2–3, hanya bila Jalur 2 gagal)

Kalau PaddleOCR tetap 35–42 detik, latensinya diubah dari **nyata** menjadi **terasa**:
OCR bagian atas halaman dulu, **mulai membacakan**, lalu lanjutkan sisanya di belakang
layar sementara pengguna masih mendengarkan bagian pertama.

Masuk akal karena jawaban dokumen memang sudah dipotong 40 kata per bagian dan sudah ada
perintah LANJUT. Pengguna tidak pernah mendengar seluruh halaman sekaligus.

**Biaya:** paling mahal dari ketiganya — mengubah pipeline, menjaga urutan bacaan, dan
menambah tes. Jangan dimulai sebelum Jalur 2 terjawab.

---

## Pertanyaan datasetmu: jawaban jujurnya

**Tidak ada dataset publik yang cocok** dengan kasus pakai kita, yaitu pengguna tunanetra
memotret dokumen A4 Bahasa Indonesia dengan kamera HP. Yang ada mengukur sebaran yang
berbeda.

Tiga pilihan, berurutan menurut nilai per menit yang kamu habiskan:

### a. Cetak lalu potret — paling murah dan paling sahih

Ini yang sudah disiapkan untuk dua foto pengganti. **20 menit** untuk dua dokumen, dan
hasilnya data sungguhan yang sebarannya cocok.

Kalau ada 20 menit lagi, cetak 4–6 halaman tambahan dari berkas teks yang sudah kamu
punya (misalnya `docs/PRD_SayIt_v2_1.md`), potret dengan variasi sudut dan cahaya, lalu
salin berkas aslinya sebagai `.txt`. **Tidak perlu mengetik acuan sama sekali.**

### b. Dokumen sintetis dari berkas sendiri — bisa tak terbatas, tanpa memotret

Render berkas `.md` proyek sendiri menjadi halaman A4, lalu berikan kerusakan terkendali:
buram, miring, perspektif, cahaya tidak rata, derau JPEG. Acuannya sempurna karena
teksnya kita yang tulis.

**Gunanya: uji ablasi dan uji regresi, BUKAN angka utama.** Proyek ini sudah pernah
tertipu gambar sintetis — model zona dinilai "tidak bekerja" padahal datanya yang buruk,
dan ambang skornya sempat dikalibrasi dari artefak gambar uji. Jangan diulang.

Kelebihannya nyata: ini satu-satunya cara menjawab pertanyaan yang **belum pernah bisa
dijawab** — "apakah pra-pemrosesan menolong foto BURUK?" Selama ini foto uji kita bagus
semua, sehingga pra-pemrosesan tercatat netral. Dengan foto yang sengaja dibuat buruk,
pertanyaan itu akhirnya bisa diuji.

### c. Dataset publik — hanya sebagai pemeriksaan luar

| Dataset | Isi | Cocoknya |
| :--- | :--- | :--- |
| **CORD** | struk belanja **Indonesia**, ada acuan teks | Bahasa paling dekat, tetapi jenis dokumennya salah |
| **FUNSD** | 199 formulir pindaian Inggris, berderau, acuan per kata | Bagus untuk uji ketahanan pada pindaian rusak |
| **SROIE** | struk Inggris, acuan teks | Mirip CORD, bahasa Inggris |

Ketiganya **bukan pengganti**. Kalau dipakai, laporkan sebagai **bukti sekunder** dengan
sebarannya disebut terbuka, dan jangan campur ke rerata 13 dokumen.

**Saran saya:** pilihan (a) untuk angka utama, (b) untuk ablasi, dan (c) hanya kalau
penguji jurnal memintanya.

---

## Jadwal

| Hari | Kerja | Siapa |
| :--- | :--- | :--- |
| 1 pagi | Cetak dan potret 2 dokumen pengganti, lalu ukur ulang | **kamu** (20 menit) |
| 1 pagi | Sementara itu: teruskan `text_recognition_model_name` dan `text_recognition_batch_size` dari config, tambah tes | saya |
| 1 siang | Jalankan 5 kondisi Jalur 2 pada 13 dokumen, catat CER + latensi | saya |
| 1 sore | Putuskan: cukup dengan EasyOCR, atau pindah ke PaddleOCR mobile_rec | bersama |
| 2 | Bila Jalur 2 berhasil: kunci config, ukur ulang penuh, perbarui dokumen. Bila gagal: mulai Jalur 3 | saya |
| 2–3 | Bangun dokumen sintetis berkerusakan terkendali, jalankan ablasi pra-pemrosesan yang selama ini tidak terjawab | saya |
| 3 | Ukur akhir, perbarui `keputusan-teknis.md`, `status-proyek.md`, dan laporan progres | saya |

---

## Yang akan saya laporkan apa adanya

- Bila targetnya tercapai hanya karena dua foto uji diganti, itu **ditulis sebagai begitu**,
  bukan sebagai peningkatan model.
- CER dilaporkan **per dokumen**, bukan hanya reratanya. Rerata di sini dikuasai satu-dua
  berkas terburuk, dan itu menyesatkan.
- Setiap angka disertai jumlah sampel dan mesin yang dipakai.
- Bila Jalur 2 gagal, kegagalannya ditulis — itu menutup satu kemungkinan dan punya nilai
  sendiri.

---

## Keputusan yang saya butuhkan darimu

1. **Setuju Jalur 2 dikerjakan lebih dulu?** Itu satu-satunya tuas yang benar-benar belum
   dicoba, dan paling berpeluang mengubah keadaan.
2. **Apakah kamu sempat mencetak dan memotret** dua dokumen pengganti besok pagi?
   Tanpa itu, CER 15,3% akan tetap jadi angka laporan walaupun modelnya membaik.
3. **Berapa halaman tambahan yang sanggup kamu potret?** Kalau bisa 4–6, data ujinya
   menjadi jauh lebih meyakinkan. Kalau tidak sama sekali, kita jalan dengan 13 dokumen
   dan menyatakan keterbatasannya.
