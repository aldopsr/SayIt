# Pencerdasan SayIt

**Untuk anggota kelompok.** Dibuat 5 November 2026.
Tujuannya satu: setelah baca ini kamu paham **kita bikin apa, pakai apa, dan sekarang sudah sampai mana** —
tanpa perlu buka kode.

Istilah teknis dijelaskan di tempatnya. Kalau ada kata yang tidak kamu kenal, itu bug tulisan ini, bukan kamu.

---

## 1. Masalah yang kita selesaikan

Bayangkan kamu tidak bisa melihat. Lalu:

- Kamu pegang selembar uang. **Berapa nilainya?** Uang kertas Rupiah tidak punya huruf Braille.
- Kamu dapat selembar surat. **Isinya apa?**
- Kamu beli susu kemasan. **Masih layak diminum atau sudah kedaluwarsa?**

Ketiganya butuh mata. Dan ketiganya adalah hal yang dilakukan orang **setiap hari**.

**SayIt menjawab ketiganya dengan telinga, bukan mata.**

---

## 2. Cara pakainya (alurnya cuma tiga langkah)

```
     FOTO              TANYA                 DENGAR
  ketuk layar   →   tahan tombol,      →   jawaban dibacakan
  untuk jepret      ucapkan pertanyaan      dengan suara
```

Contoh nyata:

| Pengguna memotret | Pengguna bilang | SayIt menjawab |
| :--- | :--- | :--- |
| Dua lembar uang | *"ini uang berapa"* | "Dua puluh lima ribu rupiah. Dua lembar." |
| Selembar surat | *"bacakan tulisannya"* | (membacakan isi suratnya) |
| Kemasan susu | *"kapan kedaluwarsanya"* | "Kedaluwarsa dua puluh sembilan Agustus dua ribu dua puluh lima." |

**Yang penting dipahami: tidak ada menu.** Pengguna tidak memilih "mode uang" atau
"mode dokumen". Ia cuma memotret lalu **bertanya**, dan sistem yang menebak maksudnya
dari pertanyaannya. Alasannya sederhana: pengguna tunanetra tidak bisa mencari menu.

Satu foto bisa ditanyai berkali-kali. Bisa juga bilang "ulangi" atau "lanjut" (untuk
dokumen panjang) tanpa memotret lagi.

---

## 3. Bentuknya apa? (bukan aplikasi Play Store)

**PWA** — *Progressive Web App*. Artinya: **website yang bisa dipasang ke layar utama HP**
dan setelah itu terasa seperti aplikasi biasa.

Kita pilih ini, bukan aplikasi Android, karena:

- Tidak perlu upload ke Play Store (butuh biaya dan review berhari-hari)
- Satu kode jalan di Android maupun iPhone
- Update cukup deploy, pengguna tidak perlu update manual

Ada juga **panel uji Streamlit** (`app.py`). Itu **alat kita sendiri** untuk mengetes
modul satu-satu tanpa suara. Bukan untuk pengguna. Jangan tertukar.

---

## 4. Pakai teknologi apa saja

Ini bagian yang paling sering ditanya. Saya urutkan **sesuai alur kerjanya**, dari
suara masuk sampai suara keluar.

### Tahap 1 — Mendengar pertanyaan: **faster-whisper**

Ini **STT** (*Speech-to-Text*) — mengubah suara jadi tulisan.

Modelnya `small`, buatan OpenAI, versi yang dioptimasi supaya **jalan di CPU** (tidak
butuh kartu grafis). Jadi laptop anggota mana pun bisa demo.

> **Trik yang berpengaruh besar:** kita beri Whisper daftar kata yang mungkin diucapkan
> (`initial_prompt`) — "uang", "tanggal", "bacakan", "sayit", "bantuan". Hasilnya
> **tingkat kesalahan turun dari 27,5% ke 7,2%.** Tanpa daftar itu, Whisper sering salah
> dengar kata-kata khas aplikasi kita.

### Tahap 2 — Memahami maksud: **router aturan**, bukan AI

Setelah jadi tulisan, kita harus tahu: pengguna mau fitur yang mana?

Di sini kita **sengaja tidak pakai AI**. Cuma pencocokan kata kunci berbobot. Kalau ada
kata "uang"/"nilai"/"nominal" → modul uang. Kalau "baca"/"tulisan" → modul dokumen.
Kalau "kedaluwarsa"/"expired"/"basi" → modul tanggal.

Alasannya: lebih cepat (di bawah 0,01 detik), bisa diperiksa, dan tidak pernah
berhalusinasi. Pakai AI di sini cuma bikin lambat tanpa manfaat.

> **Satu jebakan yang pernah kena kami:** pencocokan "mirip-mirip" (*fuzzy*) membuat
> **"uang" dianggap sama dengan "ulang"**. Sekarang kata pendek wajib cocok persis;
> kemiripan hanya untuk kata 6 huruf ke atas.

### Tahap 3 — Memperbaiki foto: **pengolahan citra klasik**

Sebelum foto masuk ke model, fotonya dirapikan dulu. Ini bagian yang **dinilai mata
kuliah kita**, jadi penting:

| Teknik | Gunanya, bahasa manusia |
| :--- | :--- |
| **Resize** | Perkecil foto HP yang 3024×4032 piksel. Ini pengendali kecepatan paling besar. |
| **CLAHE** | Perataan kontras. Bagian gelap dibuat lebih terang **tanpa** membuat bagian terang jadi putih polos. |
| **Koreksi perspektif** | Foto kertas yang diambil miring diluruskan jadi seperti dilihat dari atas. |
| **Deskew** | Memutar foto yang sedikit miring supaya tulisannya lurus. |
| **Koreksi kemiringan baris** | Meluruskan tiap baris teks, bukan seluruh halaman. Ini yang menyelamatkan target CER kita. |
| **Quality gate** | Menolak foto yang terlalu gelap, terlalu buram, atau kena silau — **sebelum** diproses, supaya pengguna langsung diminta foto ulang. |

### Tahap 4 — Mengenali uang: **YOLOv8n**

**YOLO** = model *deteksi objek*. Bedanya dengan "mengenali gambar" biasa: YOLO tidak
cuma bilang "ini ada uang", tapi **menggambar kotak di tiap lembar uang dan menyebut
nominalnya masing-masing.** Itulah kenapa kita bisa menghitung total beberapa lembar.

`n` di `YOLOv8n` artinya *nano* — versi paling kecil dan paling cepat. Sengaja, karena
harus jalan di CPU.

Modelnya **kita latih sendiri** dengan 7 kelas: Rp1.000, 2.000, 5.000, 10.000, 20.000,
50.000, 100.000. Dilatih di Google Colab (gratis, pakai GPU-nya).

> Setelah YOLO selesai, ada **pasca-pemrosesan**: kotak yang bersarang di dalam kotak lain
> (satu lembar terdeteksi dua kali) dibuang. Tanpa ini, satu lembar Rp100.000 bisa
> diucapkan jadi "dua ratus ribu".

### Tahap 5 — Tanggal kedaluwarsa: **YOLOv8n lagi + PaddleOCR**

Ini dua langkah, dan **penting untuk tidak tertukar**:

1. **YOLO kedua** (`best_zone.pt`) mencari **DI MANA** tanggal tercetak di kemasan.
   Ia **tidak membaca apa pun** — cuma menunjuk lokasinya.
2. **PaddleOCR** lalu **MEMBACA** angka di lokasi itu.

Kenapa dipisah? Karena membaca seluruh permukaan kemasan itu lambat. Dengan ditunjuk
dulu: **0,82 detik**. Tanpa ditunjuk, harus baca semuanya: **3,74 detik** — 4,6 kali lebih lambat.

> **Jadi YOLO kedua itu demi KECEPATAN, bukan akurasi.** Akurasinya sama saja dengan atau
> tanpa dia (81% dua-duanya). Yang berubah cuma waktunya.

Setelah dibaca, hasilnya diurai oleh **parser tanggal** kita sendiri, karena format
tanggal kemasan di Indonesia kacau: `29/08/25`, `29 AGT 2025`, `210829`, `AGT 2025`…

### Tahap 6 — Membaca dokumen: **EasyOCR**

**OCR** = *Optical Character Recognition*, mengubah gambar tulisan jadi teks yang bisa
dibaca komputer.

EasyOCR mengembalikan kotak **per baris**, bukan per kata. Kotak-kotak itu lalu kita
kelompokkan jadi baris dan paragraf, supaya urutan bacaannya masuk akal.

> **Kenapa OCR-nya DUA, beda per modul?** Ini keputusan dari pengukuran, bukan selera:
>
> | | EasyOCR | PaddleOCR |
> | :--- | :--- | :--- |
> | Cetakan kemasan (dot-matrix) | 19% benar | **44% benar** |
> | Detik per foto | **3,5** | 24,9 |
>
> PaddleOCR jauh lebih jago baca cetakan kemasan yang samar, tapi **7 kali lebih lambat.**
> Jadi: PaddleOCR untuk kemasan (yang susah), EasyOCR untuk dokumen (yang sudah cukup).
>
> ⚠️ **Keduanya tidak boleh jalan di satu proses — programnya langsung mati (*crash*).**

### Tahap 7 — Menjawab dengan suara: **edge-tts**

**TTS** = *Text-to-Speech*, mengubah tulisan jadi suara. Kita pakai **edge-tts** dengan
suara `id-ID-GadisNeural` (suara neural Microsoft). Sebelumnya gTTS (Google), diganti
28 Oktober karena **gTTS terdengar robotik** saat diuji dengar.

Desainnya **hibrida**, dan ini trik yang cukup penting:

- **Kalimat yang sudah bisa ditebak** — semua nominal uang, semua tanggal, semua pesan
  galat — **sudah disintesis sejak awal** dan disimpan sebagai 89 berkas MP3 di
  `assets/tts/`. Jadi saat dipakai, tinggal diputar. **Nol detik, dan tidak butuh internet.**
- **Isi dokumen** tidak bisa ditebak (tulisannya apa saja), jadi **disintesis saat itu juga**
  dan butuh internet.

---

## 5. Sekarang sudah sampai mana

**Keempat target akurasi di PRD sudah tercapai.**

| Yang diukur | Hasil | Target | |
| :--- | :--- | :--- | :--- |
| Nominal uang | **90,1%** | ≥ 85% | tercapai |
| Tanggal kedaluwarsa | **81%** | ≥ 70% | tercapai |
| Ketepatan baca dokumen (CER) | **14,89%** salah | ≤ 15% | tercapai |
| Kecepatan uang / perintah | 1,4 s / 1,3 s | ≤ 8 s | lolos |
| Kecepatan dokumen / kedaluwarsa | 11,5 s / 11,4 s | ≤ 8 s | **melewati batas** |
| Tes otomatis | **685 lulus** | semua lulus | lolos |

**CER** artinya *Character Error Rate* — dari 100 huruf, berapa yang salah. Jadi
**semakin kecil semakin bagus**, kebalikan dari persentase lainnya di tabel itu.

### Cara kita melaporkan akurasi — tolong ikuti ini di laporan

Kita **tidak pernah** menulis satu persentase saja. Selalu **benar / salah / diam**.

Contoh: akurasi uang 90,1% itu = **73 benar, 8 salah, 0 diam** dari 81 foto.

Kenapa penting? Karena bagi pengguna tunanetra, jawaban yang **salah** jauh lebih
berbahaya daripada sistem yang **diam**. Kalau diam, ia foto ulang. Kalau salah, ia
tidak punya cara tahu — dan bisa kehilangan uang atau makan yang sudah kedaluwarsa.

Dua kondisi dengan persentase sama bisa sangat berbeda bahayanya. Di proyek ini itu
sudah terbukti tiga kali.

---

## 6. Isi folder repo, satu baris per folder

| Folder | Isinya |
| :--- | :--- |
| `sayit/` | **Otak aplikasi.** Semua logika: suara, intent, visi, pipeline. |
| `server/` | API FastAPI — pembungkus `sayit/` supaya bisa dipanggil dari web. |
| `web/` | Tampilan PWA (Next.js). **Kalau kamu pegang UI, cuma folder ini yang kamu sentuh.** |
| `config/settings.yaml` | **Semua angka pengaturan ada di sini**, bukan di kode. |
| `tests/` | 685 tes otomatis. |
| `notebooks/` | Notebook Colab untuk melatih model. |
| `docs/` | Dokumentasi, keputusan, dan angka-angkanya. |
| `models/` | Bobot model hasil latih. **Tidak masuk Git** (file besar) — minta ke anggota. |
| `data/` | Foto uji. **Tidak masuk Git.** |

---

## 7. Mau ikut ngerjain? Mulai dari sini

**Kalau kamu pegang tampilan/UI — tidak perlu Python sama sekali.** Cukup Node.js:

```bash
cd web
npm ci
npm run dev
```

Buka `http://localhost:3000`. Tanpa backend, tombolnya akan menjawab *"Tidak bisa
menghubungi server SayIt"* — **itu normal.** Tata letak, warna, animasi, ukuran sentuh
semuanya tetap bisa dikerjakan. Hampir semua yang perlu diubah ada di dua berkas:
`web/app/page.js` dan `web/app/globals.css`.

**Kalau kamu pegang backend/Python:** lihat `README.md` bagian "Menjalankan seluruh sistem".
Butuh Python 3.11 dan sekitar 2,5 GB dependensi.

---

## 8. Aturan yang tidak boleh dilanggar

**Aksesibilitas** — penggunanya tunanetra, jadi ini bukan selera desain:

1. Setiap peringatan wajib **berbunyi**, bukan cuma tampil di layar. Dan wajib menyebut
   **tindakan berikutnya** ("coba foto ulang lebih dekat"), bukan cuma kesalahannya
   ("foto terlalu gelap").
2. Setiap jawaban masuk wilayah `aria-live` supaya pembaca layar ikut membacanya.
3. Area sentuh utama adalah **seluruh layar**, bukan tombol kecil.
4. **Zoom tidak boleh dikunci** — mengunci zoom melanggar WCAG 1.4.4.

**Privasi:**

1. Teks dokumen yang dibacakan **dikirim ke server Microsoft** (lewat edge-tts).
   Jadi **jangan mengetes dengan dokumen pribadi asli.**
2. Rekaman suara anggota di `fase0/fase0_hasil/rekaman/` **tidak boleh di-commit**
   maupun diunggah ke mana pun. Itu suara orang.

**Kode:**

1. `python -m pytest -q` wajib lulus **sebelum dan sesudah** setiap perubahan.
2. Semua angka pengaturan masuk `config/settings.yaml`, jangan ditulis langsung di kode.
3. Kalimat suara baru wajib didaftarkan di `sayit/response/templates.py` lalu klipnya dibuat ulang.

---

## 9. Yang masih kurang (jujur, supaya tidak salah klaim)

| Hal | Kondisi |
| :--- | :--- |
| **Kecepatan dokumen & kedaluwarsa** | 11,4–11,5 detik, target 8 detik. Tiga cara mempercepat sudah dicoba, semuanya malah menurunkan akurasi. Dicatat sebagai penyimpangan yang disadari. |
| **Belum pernah diuji pengguna sungguhan** | Rencananya: teman bermata tertutup, 5 tugas, lalu kuesioner SUS. |
| **Tangkapan layar & video demo** | **Belum ada.** Dibutuhkan untuk laporan. |
| **Suara pengguna baru 1 penutur** | Akurasi pengenalan suara diukur dari satu orang saja, jadi angkanya optimistis. |
| **Urutan bacaan foto buku masih kacau** | Penyebabnya sudah ketemu: halaman buku **melengkung**, jadi satu angka kemiringan tidak cukup. |
| **Hosting masih laptop sendiri** | Backend jalan di laptop + tunnel ngrok. Bukan hosting permanen — modelnya 2,5 GB, tidak muat di hosting gratis. |

---

## 10. Tiga hal yang JANGAN ditulis di laporan

**1. Jangan tulis "pra-pemrosesan meningkatkan akurasi".** Datanya tidak mendukung.
Pada 13 dokumen hasilnya **netral**. Pada modul kedaluwarsa dengan PaddleOCR ia malah
**merugikan 12%**.

Yang benar dan justru lebih menarik: **nilai pra-pemrosesan berbalik arah tergantung
mesin OCR-nya** — EasyOCR dibantu +6%, PaddleOCR dirugikan −12%. Jadi pertanyaan
"apakah pra-pemrosesan membantu" **tidak punya satu jawaban**. Itu temuan ablasi yang
layak dibanggakan, bukan kegagalan.

**2. Jangan pakai angka-angka usang ini:**
65,7% · 68,8% · 84,0% · 87,5% (akurasi uang) · 15,3% · 15,2% (CER) · 648 tes · 566 tes ·
0,947 (dari dataset Roboflow yang labelnya tertukar — **angka ini tidak valid**).

**3. Jangan klaim performa dunia nyata dari angka mAP notebook.** Data uji kami berasal
dari sumber yang sama dengan data latih, jadi angka itu optimistis. Yang sah dikutip
adalah **90,1% hasil validasi silang.**

---

## Mau baca lebih dalam?

| Berkas | Isinya |
| :--- | :--- |
| `README.md` | Cara menjalankan sistem |
| `docs/status-proyek.md` | Laporan status lengkap untuk tim (per 28 Oktober) |
| `docs/keputusan-teknis.md` | **Setiap keputusan beserta angka buktinya.** Ini sumber kebenaran angka. |
| `docs/isi-ppt-progres.md` | Konten siap pakai untuk slide presentasi progres |
| `docs/PRD_SayIt_v2_1.md` | Dokumen persyaratan — apa yang dijanjikan |
| `docs/deploy.md` | Cara mengunggah aplikasinya |
