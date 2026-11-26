# Pencerdasan SayIt

**Untuk anggota kelompok.** Dibuat 5 November 2026, **diperbarui 26 November 2026**.
Yang berubah paling besar sejak versi pertama: mesin OCR-nya diganti, dan target
kecepatan PRD yang dulu dilanggar sekarang terpenuhi. Lihat Tahap 6 dan bagian 5.
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

Kenapa dipisah? Karena membaca seluruh permukaan kemasan itu lambat. Diukur pada 16
kemasan sungguhan: mematikan jalur zona membuat waktunya **lebih dari dua kali lipat**.

> **Jadi YOLO kedua itu demi KECEPATAN, bukan akurasi.** Akurasinya sama saja dengan atau
> tanpa dia (81% dua-duanya). Yang berubah cuma waktunya.

> Zonanya ketemu pada **9 dari 14** kemasan bertanggal. Lima sisanya jatuh ke jalur
> cadangan: baca seluruh gambar. Jadi jalur cadangan itu bukan kasus langka — ia dipakai
> sepertiga waktu, dan harus tetap benar.

Setelah dibaca, hasilnya diurai oleh **parser tanggal** kita sendiri, karena format
tanggal kemasan di Indonesia kacau: `29/08/25`, `29 AGT 2025`, `210829`, `AGT 2025`…

### Tahap 6 — Membaca dokumen: **PaddleOCR di atas ONNX Runtime**

**OCR** = *Optical Character Recognition*, mengubah gambar tulisan jadi teks yang bisa
dibaca komputer.

OCR mengembalikan kotak **per baris**, bukan per kata. Kotak-kotak itu lalu kita
kelompokkan jadi baris dan paragraf, supaya urutan bacaannya masuk akal.

> **BERUBAH 24 November, dan ini perbaikan terbesar proyek ini.** Sampai tanggal itu
> modul dokumen memakai **EasyOCR**. Sekarang **kedua modul memakai PaddleOCR**, tetapi
> dijalankan oleh mesin yang berbeda di belakangnya: **ONNX Runtime**, bukan PaddlePaddle.
>
> **ONNX Runtime** itu bukan model baru — modelnya sama persis, bobotnya sama persis.
> Yang berganti hanya *program yang menjalankan* model itu. Analoginya: lagu yang sama,
> pemutar yang berbeda.
>
> | Modul dokumen | sebelum (EasyOCR) | sesudah (ONNX) |
> | :--- | :--- | :--- |
> | Salah baca (CER) | 14,9% | **9,0%** |
> | Detik per halaman | 8,04 | **2,08** |
>
> Menang di **dua-duanya sekaligus** — lebih akurat *dan* 4 kali lebih cepat. Itu jarang
> terjadi; biasanya satu harus dikorbankan. Dan tidak ada pustaka baru yang dipasang:
> `onnxruntime` ternyata sudah ikut terpasang sejak lama.

> **Tapi modelnya tetap beda per modul, dan itu terukur.** Model pembaca yang paling
> bagus untuk dokumen (`PP-OCRv5_mobile_rec`) justru **menjatuhkan akurasi kemasan dari
> 81% ke 62%**. Sebabnya masuk akal: cetakan *dot-matrix* di kemasan jauh lebih samar
> daripada tulisan cetak di kertas A4, jadi ia butuh model pembaca yang lebih besar.
>
> Jadi: **mesin sama, pembaca beda.** Dokumen pakai yang kecil dan cepat, kemasan pakai
> yang besar dan teliti.

> ⚠️ **Catatan lama yang sudah DIRALAT:** dulu di sini tertulis "dua mesin OCR dalam satu
> proses membuat program langsung mati". Itu **salah, dan versi yang benar lebih
> berbahaya**: ia tidak mati, ia **memberi angka yang keliru tanpa tanda apa pun.**
> Sejak kedua modul memakai PaddleOCR, masalah ini hilang dengan sendirinya.

### Tahap 7 — Menjawab dengan suara: **edge-tts**

**TTS** = *Text-to-Speech*, mengubah tulisan jadi suara. Kita pakai **edge-tts** dengan
suara `id-ID-GadisNeural` (suara neural Microsoft). Sebelumnya gTTS (Google), diganti
28 Oktober karena **gTTS terdengar robotik** saat diuji dengar.

Desainnya **hibrida**, dan ini trik yang cukup penting:

- **Kalimat yang sudah bisa ditebak** — semua nominal uang, semua tanggal, semua pesan
  galat — **sudah disintesis sejak awal** dan disimpan sebagai 95 berkas MP3 di
  `assets/tts/`. Jadi saat dipakai, tinggal diputar. **Nol detik, dan tidak butuh internet.**
- **Isi dokumen** tidak bisa ditebak (tulisannya apa saja), jadi **disintesis saat itu juga**
  dan butuh internet.

> Sintesis langsung itu normalnya **0,77 detik**. Tetapi sekitar **2 dari 20 panggilan
> melonjak ke 5–7 detik**, acak, dan **sebabnya belum ketemu** — empat dugaan sudah diuji
> dan semuanya meleset. Kemungkinan terbesar variasi di sisi layanan Microsoft, di luar
> kendali kita. Disebut di sini supaya kalau kamu merasa "kok kadang lama", itu bukan
> perasaanmu saja.

---

## 5. Sekarang sudah sampai mana

**Semua target akurasi DAN kecepatan di PRD sudah tercapai** — yang terakhir baru
24 November.

| Yang diukur | Hasil | Target | |
| :--- | :--- | :--- | :--- |
| Nominal uang | **85–90%** | ≥ 85% | tercapai, tepat di garis |
| Tanggal kedaluwarsa | **81%** | ≥ 70% | tercapai |
| Ketepatan baca dokumen (CER) | **9,0%** salah | ≤ 15% | tercapai |
| Kecepatan uang / perintah | 1,4 s / 1,3 s | ≤ 8 s | lolos |
| Kecepatan dokumen / kedaluwarsa | **5,0 s / 3,0 s** | ≤ 8 s | **lolos** |
| Tes otomatis | **769 lulus** | semua lulus | lolos |

**CER** artinya *Character Error Rate* — dari 100 huruf, berapa yang salah. Jadi
**semakin kecil semakin bagus**, kebalikan dari persentase lainnya di tabel itu.

> **Kenapa uang ditulis sebagai rentang 85–90%, bukan satu angka?** Karena dua pengukuran
> yang sah memberi 90,0% dan 85,0%, dan selisihnya bukan karena modelnya memburuk —
> melainkan karena satu foto cacat dikeluarkan, dan itu mengubah pembagian data ujinya
> sepenuhnya. Dengan 80 foto dan sekitar 10 kesalahan, selisih 5 poin masih di dalam
> variasi wajar. **Menulis satu angka presisi di situ akan menyesatkan.**

> **Kecepatan dokumen dan kedaluwarsa dulu 11,5 dan 11,4 detik — melewati batas 8 detik,
> dan itu sempat dicatat sebagai penyimpangan yang disadari.** Pindah ke ONNX Runtime
> (lihat Tahap 6) menghapusnya. **Penyimpangan itu sudah dicabut.**
>
> Tapi sebutkan juga ekornya kalau ditanya: yang lolos itu nilai **tengah**. Foto
> terburuk masih 9,5 detik (dokumen) dan 11,9 detik (kedaluwarsa).

> ⚠️ **Satu keterbatasan yang wajib disebut di laporan, jangan dilewat.** Semua angka
> akurasi di atas adalah **estimasi resubstitusi** — artinya data yang dipakai mengukur
> adalah data yang juga dipakai *menyetel* sistemnya. Untuk kedaluwarsa, 16 foto yang
> sama dipakai memilih tujuh keputusan konfigurasi. Angka pada data yang benar-benar baru
> kemungkinan **lebih rendah**, dan seberapa rendah belum diketahui karena belum diukur.

### Cara kita melaporkan akurasi — tolong ikuti ini di laporan

Kita **tidak pernah** menulis satu persentase saja. Selalu **benar / salah / diam**.

Contoh: akurasi uang 90,0% itu = **72 benar, 8 salah, 0 diam** dari 80 foto.

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
| `tests/` | 769 tes otomatis. |
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
terhubung ke SayIt. Periksa koneksi internetmu"* — **itu normal.** Tata letak, warna, animasi, ukuran sentuh
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
| **Semua angka akurasi adalah estimasi resubstitusi** | Data yang dipakai mengukur juga dipakai menyetel sistem. **Ini keterbatasan paling serius di daftar ini**, dan paling mudah dilewatkan karena angkanya terlihat bagus. Butuh 20–30 kemasan baru yang belum pernah menyentuh penyetelan apa pun. |
| **Belum pernah diuji pengguna sungguhan** | Rencananya: teman bermata tertutup, 5 tugas, lalu kuesioner SUS. Ini **satu-satunya target PRD bernomor yang belum pernah dijalankan sama sekali.** |
| **Tangkapan layar & video demo** | **Belum ada.** Dibutuhkan untuk laporan. |
| **Lisensi dataset detektor zona tidak tercantum** | Di Roboflow tertulis `license: null`. Untuk publikasi jurnal ini **risiko nyata**, bukan urusan administratif. |
| **Suara pengguna baru 1 penutur** | Akurasi pengenalan suara diukur dari satu orang saja, jadi angkanya optimistis. |
| **Dua tanggal masih salah dibaca** | `chees` membaca nomor produksi sebagai tanggal; `ovaltine` meleset tiga hari. Keduanya belum terpecahkan. |
| **Urutan bacaan foto buku masih kacau** | Penyebabnya sudah ketemu: halaman buku **melengkung**, jadi satu angka kemiringan tidak cukup. |
| **Lewat deploy sungguhan akurasinya 75%, bukan 81%** | Selisihnya satu berkas yang ditolak penjaga mutu. Angka 81% diukur dengan memanggil modulnya langsung, jadi ia **melewatkan penjaga mutu dan seluruh lapisan jaringan.** Dua angka itu mengukur cakupan yang berbeda, bukan saling bertentangan. |
| **Hosting masih laptop sendiri** | Backend jalan di laptop + tunnel ngrok. Bukan hosting permanen — modelnya 2,5 GB, tidak muat di hosting gratis. **Kalau laptopnya mati, aplikasinya mati.** |

---

## 10. Tiga hal yang JANGAN ditulis di laporan

**1. Jangan tulis "pra-pemrosesan tidak berguna" — itu sudah tidak benar lagi sejak
24 November.**

Versi lama halaman ini bilang pra-pemrosesan **netral**, dan waktu itu memang begitu.
Setelah mesin OCR-nya diganti, ia **membantu 3,4 poin** pada modul dokumen (9,0% dengan,
12,4% tanpa). Jadi Ablasi PRD nomor 1 yang dulu hasilnya negatif, sekarang **positif untuk
mesin yang sekarang dipakai** — dan ini kabar bagus untuk nilai mata kuliah, karena yang
dinilai justru teknik pengolahan citra klasiknya.

Yang tetap benar, dan justru temuan paling menarik di proyek ini: **nilai pra-pemrosesan
berbalik arah tergantung mesin OCR-nya.** Pernah membantu, pernah netral, pernah merugikan
12% — semuanya terukur, pada sistem yang sama, hanya beda mesin pembacanya. Jadi pertanyaan
"apakah pra-pemrosesan membantu" **tidak punya satu jawaban yang berlaku umum**, dan itulah
yang layak ditulis.

Kalau mengutip angkanya, **sebutkan mesin OCR-nya sekalian.** Angka tanpa mesin tidak
bermakna apa-apa.

**2. Jangan pakai angka-angka usang ini:**
65,7% · 68,8% · 84,0% · 87,5% (akurasi uang) · 15,3% · 15,2% · **14,89%** (CER) ·
648 · 566 · **685** (jumlah tes) · **11,4 / 11,5 detik** (kecepatan — sudah jadi 3,0 / 5,0) ·
0,947 (dari dataset Roboflow yang labelnya tertukar — **angka ini tidak valid**).

Dan jangan tulis **"modul dokumen memakai EasyOCR"** — itu benar sampai 24 November, tidak
lagi sesudahnya.

**3. Jangan klaim performa dunia nyata dari angka mAP notebook.** Data uji kami berasal
dari sumber yang sama dengan data latih, jadi angka itu optimistis. Yang sah dikutip
adalah hasil **validasi silang**, dan ditulis sebagai **rentang 85–90%** — bukan satu
angka presisi. Alasannya ada di bagian 5.

---

## Mau baca lebih dalam?

| Berkas | Isinya |
| :--- | :--- |
| `README.md` | Cara menjalankan sistem |
| `docs/status-proyek.md` | Laporan status untuk tim — **per 28 Oktober, angkanya sudah usang.** Pakai halaman ini atau `keputusan-teknis.md`. |
| `docs/keputusan-teknis.md` | **Setiap keputusan beserta angka buktinya.** Ini sumber kebenaran angka. |
| `docs/lampiran-radit/` | Bahan jurnal modul kedaluwarsa. Mulai dari `11_PERUBAHAN_KEDALUWARSA_24NOV.md`. |
| `docs/isi-ppt-progres.md` | Konten siap pakai untuk slide presentasi progres |
| `docs/PRD_SayIt_v2_1.md` | Dokumen persyaratan — apa yang dijanjikan |
| `docs/deploy.md` | Cara mengunggah aplikasinya |
