# SayIt — konteks proyek untuk Claude Code

## Tentang proyek
- Tugas kelompok mata kuliah **Pengolahan Citra dan Visi Komputer**, TRPL Sekolah Vokasi IPB.
- Aplikasi asistif untuk penyandang disabilitas netra: pengguna memotret, bertanya dengan suara, dan mendengar jawaban.
- Tiga kemampuan: nominal uang Rupiah (termasuk total beberapa lembar), membacakan tulisan dokumen, dan membacakan tanggal kedaluwarsa kemasan.
- Persyaratan lengkap: `docs/PRD_SayIt_v2_1.md` (salinan; versi utama ada di Claude Docs). Keputusan dan buktinya: `docs/keputusan-teknis.md`.
- Nilai mata kuliah bergantung pada **teknik pengolahan citra klasik** (CLAHE, denoise, koreksi perspektif, threshold, morfologi), bukan hanya YOLO/OCR. Pastikan tahap ini ada dan bisa diuji ablasi.

## Cara bekerja dengan pengguna
- Balas dalam **Bahasa Indonesia**. Pengguna mahasiswa; jelaskan langkah dengan konkret dan singkat.
- Bersikap kritis: sebutkan kelemahan atau risiko lebih dulu, bedakan fakta terukur dari dugaan, jangan mengarang angka.
- Tanyakan dulu sebelum: memasang pustaka besar (torch CUDA, paddle), menghapus file, atau mengubah `config/settings.yaml` secara besar.
- Hal yang hanya bisa dilakukan pengguna: bicara ke mikrofon, menilai suara, memotret data, menjalankan Colab.

## Lingkungan
- Windows, Python **3.11** (Python Install Manager, `py -V:3.11`), venv di `.venv` (jangan dipindah).
- Laptop pengembang: i7-13650HX, 20 GB RAM, RTX 4050 6 GB. Kode tetap harus jalan di **CPU** agar anggota lain bisa demo.
- Perintah (Command Prompt di root repo):
  - `.venv\Scripts\activate`
  - `python -m pytest -q` — wajib lulus sebelum dan sesudah setiap perubahan
  - `python scripts\build_tts_cache.py` — butuh internet, membuat klip suara di `assets/tts/`
  - `python scripts\demo_voice.py [--offline]` — demo suara interaktif (butuh pengguna)
- Folder `fase0/` berisi skrip dan hasil uji STT/TTS. `fase0/fase0_hasil/rekaman/` berisi suara orang: jangan dibaca isinya, jangan di-commit.

## Keputusan yang sudah dikunci (jangan diubah tanpa diskusi)
- **STT:** faster-whisper `small`, CPU int8, `language="id"`, VAD, dengan `initial_prompt`. Tanpa prompt WER naik 7% → 27%.
- **TTS:** **edge-tts `id-ID-GadisNeural`** sejak 28-10 (suara neural, dipilih pengguna setelah uji dengar; gTTS
  terdengar robotik). Mesinnya saklar config `tts.engine`: `edge` atau `gtts`, dan `gtts_save` tetap ada, jadi
  kembali ke gTTS cukup ubah YAML lalu `build_tts_cache.py --force`. Desain hibrida tidak berubah:
  jawaban uang/tanggal/pesan tetap = klip MP3 tersimpan (offline); teks dokumen = sintesis langsung, tidak disimpan ke disk.
  Semua kalimat baru harus didaftarkan di `sayit/response/templates.py` (CLIP_TEXTS) lalu cache dibuat ulang.
  **Sintesis pertama tiap proses ~9 detik** (edge-tts membangun sesi), berikutnya ~1,0 detik lawan gTTS
  0,74 detik - karena itu `SpeechRenderer.warmup()` dipanggil saat server dan panel uji memuat model,
  bukan saat pengguna menunggu. Angka 4-8 detik dan "setara gTTS" pada catatan 28-10 **sudah dikoreksi 31-10**.
  Panjang jawaban uang **tidak berubah bermakna** (di bawah 1,5%); bacaan dokumen ~9% lebih singkat.
  **Utang:** bila `warmup()` gagal (start tanpa internet, atau server hidup ulang di tengah sesi),
  9 detik itu jatuh tepat di pembacaan dokumen pertama pengguna.
- **Angka ke kata:** `sayit/response/terbilang.py` menghasilkan token; jangan ganti dengan num2words.
- **Router intent:** aturan berbobot di `sayit/intent/`. Fuzzy hanya untuk kata kunci ≥ 6 huruf, intent kendali dicocokkan persis,
  akhiran -nya dipotong. Setiap kata kunci baru wajib disertai kasus uji di `tests/test_router.py`.
- **Model uang:** YOLOv8n, 7 kelas (`1000`…`100000`), model kerja v2.1 dilatih di Colab (`notebooks/02_money_v2_1_build_and_train.ipynb`).
  Bobot disalin ke `models/best_money.pt` (tidak di-commit). Pasca-pemrosesan wajib: buang kotak bersarang
  (≥ 85% luas di dalam kotak lain berkelas sama), lalu ambang skor **0,40** (dikalibrasi 27-09, PRD menulis 0,5).

## Jebakan yang sudah pernah terjadi
- Dataset Roboflow `deteksi-rupiah-jkkmu` punya **label tertukar** (uang 100.000 berlabel 5000, dll.), 3 salinan augmentasi per foto,
  dan kebocoran antar split. Hanya 56 gambar yang dipakai (label diambil dari nama file). Skor 0,947 darinya tidak valid.
- Split test v2.1 berasal dari sumber yang sama dengan data latih → mAP 0,966 **optimistis**. Model lemah pada emisi 2016
  dan foto berisi banyak lembar. Jangan klaim performa dunia nyata tanpa foto uji sendiri.
- Fuzzy matching longgar membuat "uang" ≈ "ulang". Kata pendek harus cocok persis.
- Whisper kadang menyisipkan kata dari prompt; ada penjaga di `sayit/audio/stt.py`.
- Hasil STT baru dari **1 penutur**; akurasi router pada kalimat baru masih optimistis.
- `soundfile` bisa membaca MP3, tetapi byte MP3 yang disambung tidak terbaca utuh: selalu decode per klip lalu gabungkan array.
- Privasi: teks dokumen yang disintesis langsung dikirim ke **Microsoft** (edge-tts sejak 28-10; Google bila `tts.engine: gtts`). Jangan menguji dengan dokumen pribadi asli.

## Aturan kode
- Semua parameter di `config/settings.yaml`, dibaca lewat `sayit/config.py`. Hindari angka ajaib di kode.
- Fungsi yang butuh perangkat (mikrofon, model, internet) harus bisa diganti tiruan di tes (lihat pola `model_factory` dan `synth`).
- Teks untuk pengguna dalam Bahasa Indonesia; nama variabel boleh Inggris atau Indonesia, konsisten per modul.
- Setelah menyelesaikan satu tahap, perbarui bagian **Status** di bawah dan tambahkan baris di `docs/keputusan-teknis.md` bila ada keputusan baru.

## Status (18 September 2026)
Selesai: config, `audio/io.py`, `audio/stt.py`, `audio/tts.py`, `intent/`, `response/`, skrip cache & demo,
`vision/quality_gate.py` (PRD 8.2), `vision/preprocess.py` (PRD 8.3), `vision/money.py` (PRD 8.6),
`vision/date_parser.py` (PRD 8.8.1), `vision/document.py` (PRD 8.7), `vision/expiry.py` (PRD 8.8), `pipeline.py` (PRD 7), `app.py` + `sayit/appkit.py` (Streamlit), `scripts/diagnosa_uang.py`, `scripts/buat_label_uang.py`, `scripts/ukur_dokumen.py`,
`scripts/ukur_kedaluwarsa.py`, `sayit/gambar.py`, `tests/test_ukur.py`, `scripts/banding_ocr.py`, `scripts/ukur_latensi.py`, 764 tes lulus.
`opencv-python`, `ultralytics`, dan `easyocr` terpasang dan masuk `requirements.txt`.

Pra-pemrosesan: tiap langkah adalah fungsi murni `(citra, params) -> citra` di `STEPS`, dirangkai lewat
`vision.preprocess.chains` di config. Rangkaian bawaan: uang = resize+clahe; dokumen = resize+perspective+deskew+clahe
(**denoise dibuang 29-09** karena menaikkan CER 2,2%); kedaluwarsa = upscale+clahe
(**binarisasi dan morfologi dibuang 30-09**: pada 9 potongan zona sungguhan memberi 0 benar).
`perspective.min_area_ratio` = **0,50** (dinaikkan dari 0,25 pada 29-09 setelah satu salah kenal terbukti merusak satu halaman). Semua punya saklar `enabled` sendiri, jadi uji ablasi Fase 4
cukup mengubah YAML. `PreprocessResult.notes` mencatat bukti (sudut kemiringan, kertas ditemukan atau tidak).

Pola yang dipakai ulang di tiga modul berat: logika murni dipisah dari perangkat, lalu kelas pembungkus menerima
pabrik model (`model_factory` / `reader_factory`) supaya tes jalan tanpa bobot. Lihat `Transcriber`, `MoneyDetector`, `DocumentReader`.

Modul uang: `postprocess()` fungsi murni atas daftar `Detection`. Panggil `load()` saat aplikasi mulai:
inferensi pertama 2,0 detik, berikutnya 40 ms.
Parser tanggal: `parse_expiry(teks, today, cfg)` -> `DateParseResult`. Semua format PRD 8.8.1 punya tesnya sendiri.
Modul dokumen: `build_result(boxes, cfg)` fungsi murni; pengelompokan baris/paragraf memakai toleransi relatif tinggi huruf.
EasyOCR mengembalikan kotak setingkat **baris**, bukan kata, karena itu tipenya bernama `TextBox` dan ambangnya `text_score_min`.
Sudah diuji sungguhan: dokumen sintetis A4 terbaca 100% benar. Bobot tersimpan di `models/easyocr/` (diabaikan Git).

Modul kedaluwarsa: `ExpiryReader.read(foto, today)` -> `ExpiryResult`. Dua jalur. Jalur zona (YOLO -> crop margin 10% ->
rangkaian `kedaluwarsa` -> OCR -> parser) dan jalur cadangan FR-12 (OCR seluruh gambar). **Bobot zona sudah ada**
(`models/best_zone.pt`, 28-09), jadi jalur zona otomatis dipakai bila skor deteksi >= 0,40; di bawah itu jatuh ke
jalur cadangan dan hasilnya dibacakan "kurang yakin". Terukur pada gambar sintetis dengan model panas:
jalur zona 0,82 detik, jalur cadangan 3,74 detik (4,6x). `ocr=` wajib dioper agar EasyOCR tidak dimuat dua kali.
Rotasi ditangani sistem sebagai **percobaan ulang saat gagal** (`expiry.rotate_retry: [180, 90, 270]`, `cv2.rotate`):
foto yang sudah tegak menjawab di percobaan pertama dan tidak membayar apa pun. Parser juga menerima
format rapat tanpa pemisah (`210829`). Syarat penanda **dimatikan 30-09** lewat
`date_parser.require_marker_for_compact: false` setelah diukur pada 21 foto (BENAR 3->8 tanpa menambah SALAH).
Jalur zona kini **mundur ke OCR seluruh gambar** bila potongannya gagal (`expiry.full_image_fallback`).

Pipeline: `Pipeline(cfg).load()` lalu `set_photo(foto)` dan `ask(teks)` / `listen(audio)` -> `Turn`.
Menyimpan foto terakhir, jawaban terakhir (ULANGI), dan posisi bacaan (LANJUT). `load()` melaporkan status per modul
dan tidak mati bila satu bobot hilang. Terukur dengan model asli: muat 8,7 detik; uang 0,17 detik; baca 5,08 detik;
kedaluwarsa 4,82 detik; intent kendali < 0,01 detik.

Aplikasi: `streamlit run app.py` (port 8501, ada `.claude/launch.json`). Foto lewat kamera atau unggahan,
pertanyaan lewat `st.audio_input` atau kotak teks. Sidebar menampilkan status modul. Halaman diuji tanpa peramban
lewat `streamlit.testing.v1.AppTest`; `st.camera_input` dan `st.audio_input` tidak bisa diisi dari AppTest.
Aksesibilitas (PRD Prinsip Desain 1): tiap jawaban diumumkan suara **dan** masuk wilayah `aria-live`;
intent lambat memutar penanda "sedang saya proses" lebih dulu lewat `on_progress`. Asumsi lama bahwa Streamlit
baru menggambar setelah proses selesai **salah** dan sudah diuji di peramban: elemen audio sampai ke DOM dan
berbunyi saat proses masih berjalan. Yang masih di luar kendali: urutan fokus keyboard dan label widget Streamlit.

Notebook uang sekarang menerima **daftar `DATASETS` bebas** (tiap entri punya `mode` dan penanda `sendiri`).
Kelompok yang memuat foto `sendiri=True` menjadi split test seluruhnya; tanpa itu, notebook mencetak peringatan
bahwa mAP-nya optimistis. Logika split sudah diuji lokal dengan record buatan (0, 35, 70 foto sendiri).

Notebook uang menerima **daftar `DATASETS` bebas**: tiap entri boleh dari Roboflow
(`workspace`/`project`/`versi`) atau folder Drive (`lokal='/content/drive/MyDrive/...'`), punya `mode`
(`label_dari_nama` atau `percaya_label`) dan penanda `sendiri`. Kelompok yang memuat foto `sendiri=True`
menjadi split test seluruhnya; tanpa itu notebook mencetak peringatan bahwa mAP-nya optimistis.
Notebook sudah diperiksa AST: tidak ada nama yang dipakai sebelum didefinisikan, aman untuk Run all.
Notebook k-fold (`04_money_kfold.ipynb`, 33 sel) menjawab pertanyaan yang notebook 02 tidak bisa:
**bagaimana kalau 35 foto sendiri ikut melatih, bukan hanya menguji?** Sel 0-18 disalin dari
notebook 02 (unduh, dedupe, pengelompokan pHash) supaya tidak menyimpang; yang baru hanya
pembagian lipatan, perulangan latih-dan-uji, agregasi, dan satu latihan terakhir pada seluruh data.
Pembagian atas kelompok kemiripan, bukan berkas. Evaluasi memakai metrik TOTAL dengan ambang 0,40,
sama dengan aplikasi. `LATIH_MODEL_TERAKHIR = False` secara bawaan: lihat angka k-fold dulu, baru
latih model yang dipakai. Logika lipatan sudah diuji lokal dengan record buatan (5 kelompok
pemeriksaan), dan urutan namanya diperiksa AST - aman untuk Run all.

Berikutnya, berurutan:
1. Lihat **Titik sambung** di bawah - itu daftar kerja yang paling mutakhir.
   CATATAN: saran lama "foto kemasan ulang dari dekat" sudah **dibantah** 30-09. Foto yang dipotong tepat
   pada tanggalnya pun 0 benar dari 5; penghambatnya pengenalan cetakan, bukan pembidikan. Memotret ulang
   dari dekat adalah alat diagnosis, bukan perbaikan.
2. Ukur ulang: `python scripts\ukur_kedaluwarsa.py`
   Untuk uang: `python scripts\diagnosa_uang.py data\uji_sendiri --harapan-dari-nama`
3. Uji pengguna proksi: teman bermata tertutup mencoba 5 tugas, catat berhasil/gagal, isi kuesioner SUS.
4. Fase 5: laporan, README, video demo, slide. Bahan angkanya sudah lengkap di `docs/keputusan-teknis.md`.

**Ablasi PRD nomor 1 SUDAH SELESAI** (29-09, 13 dokumen), termasuk ablasi per langkah lewat
`python scripts\ukur_dokumen.py --per-langkah`. Hasilnya negatif dan harus dilaporkan apa adanya:
pra-pemrosesan tidak meningkatkan akurasi dokumen.

**Ablasi PRD nomor 2 JUGA SUDAH SELESAI** (01-10, 16 kemasan, 800 px, mesin OCR diisolasi dari
jalur zona dan rotasi). Hasilnya: **PaddleOCR menang jauh.**

| penanda | EasyOCR | PaddleOCR |
|---|---|---|
| nyala | BENAR 3 / SALAH 2 / DIAM 11 (19%) | **BENAR 7 / SALAH 0 / DIAM 9 (44%)** |
| dilonggarkan | BENAR 5 / SALAH 2 / DIAM 9 (31%) | BENAR 8 / SALAH 1 / DIAM 7 (50%) |
| detik/foto | 3,5 | 24,9 |

Tiga konsekuensi yang harus diingat:
1. ~~**Dengan PaddleOCR, `require_marker_for_compact` harus DINYALAKAN kembali**~~
   **DIBATALKAN 16-11 - DIUKUR DI PIPELINE PENUH DAN HASILNYA JAUH LEBIH BURUK.** Saran ini
   berdiri di atas ablasi mesin TERISOLASI (800 px, jalur zona dan rotasi dimatikan), dan di
   pipeline sungguhan ia salah: 16 kemasan, `false` 12 BENAR / 3 SALAH / 1 DIAM = **75%** lawan
   `true` 9 / 2 / 5 = **56%**. Menyalakannya menukar **3 jawaban benar** demi 1 jawaban salah
   (ajinomoto, miesedap, dan merica jadi DIAM), dan latensi median naik 10,5 -> 19,1 detik karena
   tiap DIAM memicu percobaan rotasi. `require_marker_for_compact` tetap **`false`**.
   Pelajaran lama yang terulang: temuan dari uji mesin terisolasi TIDAK berpindah ke pipeline
   penuh - sama seperti pola `dmy_spasi` yang +1 benar di mesin tetapi nol efek di pipeline.
2. Latensi PaddleOCR 7x EasyOCR, dan oneDNN **tidak bisa dinyalakan** di paddlepaddle 3.3.1. Belum diuji:
   model `PP-OCRv5_mobile_det` (butuh internet) - itu tuas latensi yang paling menjanjikan.
3. Menjalankan kedua mesin dalam satu proses **tidak aman - dan RALAT 17-11: ia tidak selalu
   crash, ia bisa GAGAL DIAM-DIAM dengan angka yang masih terlihat masuk akal.** Terukur:
   satu skrip yang memuat PaddleOCR lalu EasyOCR memberi CER dokumen **10,28%** dan median
   **77 detik**, padahal proses bersih hari yang sama memberi **14,89%** dan **8,10 detik**;
   `ketentuan_makalah` melompat 76,9% -> 11,3%. Gagal diam-diam lebih berbahaya daripada crash,
   karena angkanya ikut dipakai. **Satu proses = satu mesin, selalu.**
   Pakai `--mesin` satu per satu, dan `--sisi 800`
   karena paddle crash pada foto 3024x4032 utuh. Skripnya `python scripts\banding_ocr.py`.

Celah pemisah spasi sudah ditutup 01-10 dan 02-10 (pola `dmy_spasi` dan `my_spasi`).
Yang masih terbuka: latensi PaddleOCR - lihat **Titik sambung**.

Sudah ada: 35 foto uji uang sendiri di `data/uji_sendiri/` (1000 2, 2000 4, 5000 5, 10000 7, 20000 5, 50000 6,
100000 6). Dua latar: meja kayu dan dipegang di depan laptop. Berkas asli iPhone ada di `data/uji_sendiri/asli/`
(HEIC, sudah dikonversi; boleh dihapus).
**Label YOLO (diperbarui 09-11): 80 gambar, 80 label berisi, 0 kosong, 81 kotak, ketujuh kelas**
(1000:4, 2000:21, 5000:20, 10000:10, 20000:7, 50000:6, 100000:13) di `data/label_sendiri/`.
**`5000_dipegang_ (3)` DIKELUARKAN 09-11, gambar DAN labelnya**, ke
`data/label_sendiri/_dikeluarkan/`. Labelnya terbukti salinan identik byte-per-byte dari
`5000_dipegang_ (2).txt` (satu-satunya pasangan kembar dari 81 berkas), kotaknya 99,87%
lebar bingkai. Menghapus `.txt` saja sudah dicoba 23-10 dan GAGAL karena tersalin balik
dari Drive, jadi kali ini gambarnya ikut dipindah; `image_files()` tidak rekursif sehingga
folder itu aman diabaikan. **Wajib dihapus juga di Google Drive sebelum Colab dijalankan.**
Angka 90,1% dihitung DENGAN foto itu di dalamnya (73/8/0 dari 81); dasar sebandingnya
72/8/0 dari 80 = 90,0%. **Latih ulang k-fold v3 pada 80 foto SUDAH dijalankan 10-11
dan memberi 68/11/1 = 85,0%** (ambang 0,30) - lihat blok akurasi uang di bawah.
Tambahan 23-10 (+33 foto) sengaja **diarahkan ke tiga kelas terlemah k-fold**
(5000 0,29 / 2000 0,50 / 100000 0,50), bukan merata: 2000 8->21, 5000 7->20, 100000 6->13.
1000 (hanya 4 kotak) kini kelas terlemah berikutnya kalau hasilnya tetap buruk.
Dari 33 foto baru, 21 berlabel otomatis (deteksi tunggal) dan 12 diputuskan dengan melihat
gambarnya satu per satu. **Pola kesalahan model yang paling sering: deteksi palsu di LAYAR
LAPTOP** di bagian atas bingkai - model membaca gambar uang di layar sebagai uang sungguhan.
Rinciannya per berkas di `data/label_sendiri/BACA_DULU.txt`.
Dua foto istimewa, dan keduanya menjebak skrip ukur:
- `5000_dipegang_ (3).jpeg` SENGAJA tidak dilabeli (dua lembar, yang kedua tidak terbaca).
  Menebak labelnya adalah persis kesalahan yang dulu merusak dataset Roboflow.
- `2000_dipegang_ (10).jpeg` punya **dua kotak** (dua lembar 2.000 sungguhan, nomor seri
  berbeda) - satu-satunya foto banyak lembar yang berlabel. `scripts/diagnosa_uang.py
  --harapan-dari-nama` akan selalu menilainya SALAH karena membaca harapan dari nama berkas;
  notebook k-fold membaca labelnya, jadi di situ benar.
**JANGAN melengkapi foto tanpa label dengan berkas `.txt` kosong** - dalam YOLO
label kosong berarti "tidak ada uang di gambar ini", dan itu pernah merusak
latihan k-fold pertama (07-10).
Belum ada: foto uang dengan variasi latar/cahaya/emisi/banyak lembar, rekaman penutur lain,
lisensi dataset B belum dicatat.

Yang hanya bisa diuji pengguna sendiri: kamera dan mikrofon di peramban (panel uji memblokir akses perangkat),
kualitas suara gTTS, dan seluruh alur `scripts/demo_voice.py`.

## Aplikasi web (11 Oktober 2026)

Keluaran untuk pengguna sekarang **PWA Next.js + API FastAPI**, bukan hanya Streamlit.
Streamlit `app.py` tetap ada sebagai panel uji internal.

```
web/      Next.js App Router (JS biasa, tanpa TypeScript) -> Vercel
server/   FastAPI membungkus Pipeline                      -> Hugging Face Spaces (Docker, port 7860)
```

- `next.config.mjs` me-rewrite `/api/*` ke `API_ORIGIN`, jadi frontend dan backend
  satu origin - **CORS tidak dibutuhkan sama sekali**, dan jalurnya sama di panel uji maupun produksi.
- Satu `Pipeline` dibagi di belakang `threading.Lock`: modelnya 2,5 GB, jadi permintaan
  **diantre, bukan diparalelkan**. Antrean yang lebih lama dari `server.antre_timeout_s`
  (1,5 detik) dijawab klip **`server_sibuk`**, bukan diam - diam tidak bisa dibedakan
  dari server mati oleh pengguna tunanetra.
- **Endpoint berat WAJIB `def`, bukan `async def`.** Isinya kerja blocking, dan `async def`
  menjalankannya di event loop sehingga SELURUH server membeku: terukur 11-11, `GET /sehat`
  memakan **6,57 detik** saat satu dokumen dibaca, dan permintaan kedua bahkan belum diterima
  sehingga kuncinya tidak pernah berebut. Dengan `def`, Starlette memakai threadpool:
  `/sehat` 0,21 detik. Dikunci tes `test_endpoint_berat_sinkron_bukan_async`.
- `warmup()` TTS yang gagal **dicoba ulang di latar** (10x, jeda 30 detik) dan statusnya
  masuk `/sehat` sebagai kunci `tts`. Tanpa itu 9 detik edge-tts jatuh di pembacaan
  dokumen pertama pengguna, dan kegagalannya tidak terlihat sama sekali.
- `MediaRecorder` menghasilkan webm/opus yang **tidak terbaca `soundfile`**. Didecode di
  peramban lewat `decodeAudioData` lalu dikemas ulang jadi WAV 16-bit (~25 baris, tanpa dependensi).
- Uji asap: `python server\smoke.py` (bukan pytest - memuat model sungguhan).
- Unggah berkas: gambar, PDF, DOCX. PDF/DOCX **berteks tidak di-OCR** sama sekali;
  OCR hanya untuk PDF hasil pindai. Hanya halaman pertama. Tanpa dependensi baru
  (`pypdfium2` sudah ikut paddlex, DOCX hanya zip berisi XML).

**AUDIT AKSESIBILITAS 19-11 lewat pohon aksesibilitas aplikasi berjalan - tiga cacat,
satu di antaranya kritis. SEMUA SUDAH DIPERBAIKI:**
1. **KRITIS: tombol dari layar lain bisa difokus pembaca layar.** Saat aplikasi di layar
   kamera, keempat tombol ini masih terjangkau: "Ulangi pembacaan", "Foto lagi",
   "Keluar aplikasi", "Mulai lagi". Panel disembunyikan hanya dengan `opacity: 0` +
   `pointerEvents: 'none'` - hilang dari MATA dan MOUSE, **tidak** dari pohon aksesibilitas.
   `aria-hidden` saja juga tidak cukup: ia tidak mengeluarkan dari urutan fokus.
   **Pengguna tunanetra menyapu layar, menemukan "Keluar aplikasi" saat sedang memotret, lalu
   aplikasinya tertutup tanpa ia tahu kenapa.** Diperbaiki dengan **`inert`** pada keempat
   panel; `aria-hidden` ditahan sebagai lapis kedua untuk Safari lama (pengguna pakai iPhone).
2. **Pembaca layar mengucapkan "tanyakandari"** - satu kata yang tidak ada. Sebabnya
   `tanyakan<br/>dari`: `<br/>` pemisah VISUAL, dan pohon aksesibilitas menyambung tanpa spasi.
   **Setiap `<br/>` di tengah kalimat adalah calon kata gabungan.** Diperbaiki dengan `{' '}`.
3. **Heading kosong** pada kartu jawaban (`<h2>{resultText}</h2>` dirender tanpa syarat).
   Navigasi antar-heading mendarat di tempat yang tidak mengucapkan apa pun.

**Yang WAJIB diperiksa setiap kali `inert` dipakai: wilayah `aria-live` tidak boleh ikut
terkubur di dalamnya.** Sudah diverifikasi - satu-satunya `[aria-live]` berada di luar seluruh
subtree inert. Kalau ia ikut masuk, SELURUH pengumuman suara mati, yaitu memperbaiki satu cacat
dengan membuat cacat yang jauh lebih besar bagi pengguna yang sama.

**Cara mengaudit ini lagi** (tidak butuh pembaca layar): jalankan `api` + `web`, lalu di peramban
jalankan percobaan fokus pada setiap tombol dan daftar elemen yang bisa dijangkau keyboard.
Sesudah perbaikan: seluruh percobaan fokus mengembalikan `false` dan daftarnya KOSONG.
**Cacat jenis ini tidak mungkin terlihat penguji yang melihat layar** - di mata semuanya benar.

**Aksesibilitas - aturan yang tidak boleh dilanggar lagi:**
setiap peringatan wajib (a) **berbunyi**, bukan hanya tampil, dan (b) menyebut
**tindakan berikutnya**, bukan hanya kesalahannya. Galat dari server memakai klip gTTS
yang dikirim bersama responsnya; peringatan sisi klien memakai `speechSynthesis`
bawaan peramban, karena sebagian di antaranya muncul justru ketika servernya tidak
terjangkau. Tabel lengkapnya di `docs/deploy.md`.

**`Turn.diterima` wajib dipakai untuk menilai penerimaan foto, JANGAN disimpulkan dari
`intent`.** `set_photo()` mengembalikan intent `"FOTO"` untuk foto layak maupun foto
yang ditolak quality gate. Empat tempat pernah menyimpulkannya dari intent dan
keempatnya salah; akibatnya pengguna diminta bertanya tentang foto yang tidak pernah
tersimpan. Ada tesnya di `tests/test_pipeline.py`.

Sudah di-push: https://github.com/aldopsr/SayIt

**Hosting backend: laptop sendiri + `ngrok http 8000`, BUKAN Hugging Face Spaces.**
HF kini menggerbangi SDK Docker di balik PRO 9 dolar/bulan (diperiksa 11-10), dan
2 vCPU-nya akan memperburuk latensi 11,4 detik yang sudah menyimpang dari NFR-01.
ngrok 3.35.0 sudah terpasang dan authtoken-nya sudah diset - tidak ada yang perlu
dipasang. `Dockerfile` dibiarkan di repo tetapi tidak dipakai.

**Dua jebakan tunnel yang sudah menggigit dan sudah diperbaiki:**
1. URL ngrok berganti tiap restart, sedangkan `API_ORIGIN` ikut dibangun saat deploy.
   Basis API karena itu bisa diganti saat jalan lewat `?api=`, diingat di localStorage,
   dengan **daftar putih host** - foto dan rekaman suara pengguna dikirim ke host itu,
   jadi tautan sembarangan tidak boleh mengarahkannya.
2. ngrok gratis membalas `ERR_NGROK_6024` untuk GET yang tampak dari peramban, dan
   elemen `<audio>` tidak bisa mengirim header pelewatnya. Akibatnya klip `sambutan`
   bisu - pintu masuk satu-satunya pengguna tunanetra. Klip karena itu diambil lewat
   `fetch` berheader lalu diputar sebagai blob, dan **diambil saat halaman dibuka**,
   bukan saat disentuh (fetch dalam penangan gestur membuat `play()` kehilangan
   konteks gestur; iOS memblokirnya).

Langkah lengkapnya di `docs/deploy.md`.

## graphify

Proyek ini punya knowledge graph di `graphify-out/` (2.096 node, 4.127 edge, 177 komunitas,
dibangun 4 November 2026 dari 66 berkas kode + 24 dokumen).

**Perintahnya `py -V:3.11 -m graphify ...`, bukan `graphify ...`.** graphifyy sengaja dipasang
di **base Python 3.11**, BUKAN di `.venv` proyek, supaya tes dan `requirements.txt` tidak
tersentuh. Folder `Scripts` base tidak ada di PATH.

Aturan:
- Selama `graphify-out/graph.json` ada, jalankan `py -V:3.11 -m graphify query "<pertanyaan>"`
  SEBELUM grep, pencarian, atau membaca berkas sumber untuk pertanyaan soal kode. Sertakan
  aturan ini juga di setiap prompt subagent yang menjelajah kode. Baca berkas mentah hanya
  untuk baris yang sudah dilokalisasi graph.
- `py -V:3.11 -m graphify path "<A>" "<B>"` untuk relasi; `... explain "<konsep>"` untuk konsep.
- Baca `graphify-out/GRAPH_REPORT.md` hanya untuk tinjauan arsitektur luas, atau bila
  query/path/explain belum cukup.
- Setelah mengubah kode: `py -V:3.11 -m graphify update .` (AST saja, tanpa biaya).
- `graphify-out/` ada di `.gitignore` dan TIDAK di-commit.

**Notebook WAJIB diekspor dulu.** graphify tidak mengenal `.ipynb` sama sekali - ekstensi itu
tidak ada di 114 ekstensi kode maupun 10 ekstensi dokumen yang didukungnya, jadi keempat
notebook pernah sama sekali tidak terlihat oleh graph, termasuk logika k-fold penghasil
angka 90,1%. Sebelum membangun ulang graph:

    python scripts\ekspor_notebook.py

Itu menulis `notebooks/_ekspor/*.py` (berkas turunan, diabaikan Git, 74 sel kode, semuanya
dijamin lolos `ast.parse`). Hasilnya 86 node notebook masuk graph, dan fungsi seperti
`sidik_lipatan()`, `tulis_dataset()`, `evaluasi_total()`, `group_with()` jadi bisa dicari.
Catatan jujur: ke-119 edge notebook mengarah ke pustaka luar, NOL ke kode aplikasi - memang
begitu kenyataannya, notebook berjalan di Colab dan tidak mengimpor modul proyek.

**`gitignore: false` di `.graphify_build.json`, jadi daftar `excludes` adalah SATU-SATUNYA
penjaga.** Ini disengaja supaya `notebooks/_ekspor/` yang diabaikan Git tetap ikut terbaca.
Konsekuensinya setiap penambahan folder besar atau sensitif harus ditambahkan ke `excludes`
secara eksplisit. Yang sudah dikeluarkan:
`assets/tts/**` (89 klip sintesis - teksnya sudah ada di `templates.py`), `.claude/**` dan
`.agents/**` (dokumentasi skill, bukan isi proyek), seluruh gambar (foto uang dan grafik
pelatihan tidak menyumbang untuk graph arsitektur), `**/args*.yaml` dan `**/data.yaml`
(dump hiperparameter: 7 komunitas berkohesi 0,017 yang mencemari daftar saran), berkas berat
(`.venv`, `node_modules`, `web/.next`, `data/`, `models/`, `__pycache__`), dan
`fase0/fase0_hasil/**` (**rekaman suara orang - jangan pernah dimasukkan**).
Sudah diverifikasi setelah `gitignore` dimatikan: 0 berkas rekaman dan 0 berkas folder berat
ikut terdeteksi.

Catatan membaca laporan: 457 "dangling-endpoint edge" pada diagnostik BUKAN korupsi - itu
`imports` ke pustaka luar (`time`, `streamlit`, `argparse`) yang memang bukan berkas proyek.

## Titik sambung (2 Oktober 2026)

764 tes lulus.

**RALAT 20-11: klaim lama "seluruh metrik PRD Bagian 11 sudah pernah diukur" SALAH.**
PRD Bagian 11 punya delapan metrik; tabel di bawah hanya memuat empat. Yang di luar tabel:

| metrik PRD | target | keadaan |
|---|---|---|
| **Pengujian pengguna proksi + SUS** | keberhasilan >= 80% | **BELUM PERNAH DIUKUR** - hanya pengguna yang bisa |
| mAP@0.5 zona kedaluwarsa | >= 0,75 | **TIDAK DAPAT diukur dari repo** - `data/zona_sendiri/` kosong jadi tidak ada kotak acuan; angka 0,864 itu milik model 4 kelas yang DITOLAK. Pengganti yang sah: **tingkat deteksi 9/14 = 64% pada ambang 0,40, deteksi palsu 0/2** (dan 12/14 pada 0,15, palsu tetap 0/2). **Itu BATAS ATAS, bukan recall** - `chees` terdeteksi 0,72 tapi kotaknya menunjuk nomor produksi |
| STT WER | <= 25% | sudah: 7% dengan `initial_prompt` (Fase 0, 1 penutur) |
| Akurasi intent router | >= 90% | 24/27 = 89% (PRD baris 247), dan **PRD sendiri menyebutnya optimistis** karena aturannya disetel pada data yang sama |

Jangan mengutip baris lama itu di laporan - satu metrik yang PRD-nya menargetkan angka
memang belum dijalankan.

| Metrik | Hasil | Target | |
|---|---|---|---|
| Akurasi kedaluwarsa | **81%** (13 benar / 2 salah / 1 diam, 17-11 dengan `line_grouping: rantai`) | >= 70% | **TERCAPAI** |
| CER dokumen | **14,94%** (17-11, `line_grouping: rantai`; 14,89% dengan `pita`) | <= 15% | **TERCAPAI, margin 0,06 poin** |
| Akurasi uang (total diucapkan) | **85,0%** (68 benar / 11 salah / 1 diam, k-fold v3, 80 foto bersih, ambang 0,30); 86,25% pada ambang 0,25 | >= 85% | **TERCAPAI, tepat di garis** |
| Latensi uang / kendali | 1,4 s / 1,3 s | <= 8 s | **LOLOS** |
| Latensi dokumen / kedaluwarsa | 11,5 s / 11,4 s | <= 8 s | **penyimpangan diterima** |

**Modul tulisan, pembaruan 31-10 (urutan bacaan + penjaga mutu):**
- **CER 15,30% -> 14,89%, target PRD tercapai.** Dari `line_slope_correct`: kemiringan baris
  ditaksir dari kotak OCR sendiri, lalu `y` diluruskan sebelum dikelompokkan. 3 dokumen membaik,
  10 tetap, **0 memburuk**. Akarnya: `deskew` SALAH UKUR pada foto buku karena `minAreaRect`
  mengukur bentuk halaman dan meja, bukan baris teks.
- **Penjaga mutu `unclear_score_min: 0.75`**: bacaan meragukan dijawab "tulisannya kurang jelas"
  alih-alih dibacakan. Pada 35 foto: 6/8 bacaan buruk tertangkap, **0/27 bacaan baik salah ditandai**.
  Foto mentega (OCR rusak) kini tidak dibacakan. Penanda kedua (rasio) TIDAK TERBUKTI, dimatikan.
- **`layout_mode: tersebar`** sebagai bawaan. `auto` dari `document_found` DITOLAK - memilih persis
  terbalik (tersebar untuk seluruh 13 dokumen A4, dokumen untuk 2 papan nama).
- **BELUM SELESAI: urutan bacaan foto buku masih kacau.** Dua dugaan sudah DIBANTAH datanya:
  bukan "dua halaman melengkung berlawanan" (membelah halaman memberi -0,0276 lawan -0,0282,
  nyaris sama), dan bukan "gugus menggumpal" (gugus sudah terpisah benar, 121 kotak lawan 18).
  Penjelasan yang tersisa: halamannya **MELENGKUNG** - datar di tengah, menukik sampai -0,18
  dekat jilidan - jadi satu angka kemiringan tidak akan pernah muat.
- **`line_grouping: rantai` SEKARANG BAWAAN (diganti 17-11).** Menyambung kotak ke tetangga
  terdekat tanpa taksiran kemiringan sama sekali. Buktinya datang dari modul **KEDALUWARSA**,
  bukan dari foto buku yang sejak 31-10 ditunggu teks acuannya - lihat blok "rantai jadi bawaan"
  di bawah. Harganya di dokumen +0,05 poin CER, di dalam derau.
  **Teks acuan foto buku TETAP perlu**: keunggulan `rantai` pada halaman MELENGKUNG masih
  penilaian mata, belum terbukti. Penggantian ini dibenarkan angka kedaluwarsa, bukan klaim itu.

**OCR dokumen, ablasi 11-11 (tuas latensi PaddleOCR):**
- `text_recognition_batch_size` **TERBANTAH**: 8 memberi nol perbaikan, 32 justru lebih lambat
  (22,3 s lawan 15,9 s bawaan). Biarkan kosong, jangan diuji ulang.
- **`PP-OCRv5_mobile_rec` adalah titik terbaik di sisi PaddleOCR: CER 10,1%, median 21,6 detik**
  (13 dokumen). Lawan `medium_rec` 9,4% pada ~42 detik: bayar 0,7 poin CER untuk separuh latensi.
  `PP-OCRv6_mobile_rec` tidak terdaftar di paddleocr 3.3.1.
- Perbandingan satu sesi: **EasyOCR 14,89% / 8,8 detik lawan mobile_rec 10,1% / 21,6 detik.**
  **Pindah mesin SEKARANG adalah kemunduran bagi pengguna** - CER membaik 4,8 poin tetapi kata
  pertama terdengar 12,8 detik lebih lambat. `document.engine` SENGAJA masih `easyocr`.
- **Yang membuka kuncinya: pembacaan bertahap (OCR per pita).** Terukur pada `r (11)` (303 kata):
  OCR seluruh halaman 20,3 detik, durasi dibacakan **177,8 detik** (TTS sungguhan, 102 kata/menit).
  Anggaran **+157,5 detik** - 10x, bukan tipis. Kalau OCR dipecah per pita, kata pertama keluar
  ~4-5 detik (TAKSIRAN, belum diukur; lihat ralat 16-11 di bawah - hanya berlaku bila
  GAMBARNYA ikut dipotong) sambil CER turun ke 10,1%. Menyentuh `document.py`,
  `pipeline.py` (posisi LANJUT), server, mungkin klien. Flag `--rec-model` dan `--rec-batch`
  sudah ada di `scripts/ukur_dokumen.py` untuk mengulang ablasinya.

**OCR dokumen, sapuan `resize.max_side` 16-11 - TUASNYA MATI, dan sebabnya sekarang jelas:**
- **Biaya EasyOCR terbagi hampir rata, dan separuhnya dibayar PER PIKSEL.** Terukur pada
  tiga dokumen: deteksi 4,42-7,32 detik (sebanding luas gambar, tidak peduli jumlah baris),
  pengenalan 2,60-6,47 detik (51-100 ms per kotak). Deteksi 46-53% biaya.
- **Sapuan `max_side` pada 13 dokumen beracuan: tidak ada titik yang menang di dua sisi.**

  | sisi | CER | median | total |
  |---|---|---|---|
  | **1600 (dipakai)** | **14,89%** | 7,85 s | 109,8 s |
  | 1200 | 15,42% | 6,28 s | 81,1 s |
  | 1000 | 20,17% | 5,76 s | **117,0 s** |
  | 800 | 39,54% | **24,12 s** | 316,9 s |

  Hanya 1200 memberi perbaikan nyata (median -20%) dan harganya target PRD <= 15% hilang.
  Nilai tetap **1600**. Flag `--sisi` ada di `scripts/ukur_dokumen.py` untuk mengulang satu titik.
- **KOPLING AKURASI-LATENSI LEWAT ROTASI KINI TERBUKTI DI MODUL DOKUMEN JUGA.** Itu sebab
  total 1000 px lebih lambat daripada 1600 px: gambar kecil menjatuhkan skor baris di bawah
  `rotate_trigger_score` 0,75, lalu `rotate_retry` membayar empat lintasan penuh. Per berkas:
  `r (10)` 8,4 -> 33,7 s, `r (4)` 7,5 -> 47,8 s, `r (7)` 5,9 -> 23,5 s.
- **Yang rusak saat diperkecil adalah deteksi yang MEMECAH baris, bukan yang melewatkannya.**
  Jumlah kotak NAIK: `r (4)` 76 -> 99 -> 104 -> **156**; `r (11)` 72 -> 97 -> 100 -> 133.
  Deteksi turun 7,93 -> 1,49 s tetapi pengenalan tidak ikut turun (12,98 -> 15,83 s).
  Ini **membantah** gagasan "deteksi resolusi rendah + pengenalan resolusi penuh": kotaknya
  sudah pecah sebelum sampai ke pengenalan.
- **MEMOTONG bukan MEMPERKECIL - itu sebabnya pita masih hidup sebagai satu-satunya tuas.**
  Memotong pita dari gambar penuh tidak menyentuh tinggi huruf, jadi tidak memecah baris,
  sementara biaya deteksi tetap turun sebanding luas. Proyeksi `r (11)` 3 pita: kata pertama
  ~4,6 s lawan 14,15 s sekarang. **Proyeksi dari angka terukur, belum diukur.**

**Pembacaan per PITA 16-11 - DIBUAT, DIUKUR, DAN TIDAK MEMBELI APA PUN:**
- Jalur produksi (`read()`, `readtext` per potongan, penyusunan global, 13 dokumen):

  | pita | CER | median | total |
  |---|---|---|---|
  | **1 (dipakai)** | **14,89%** | **8,26 s** | 120,2 s |
  | 2 | 14,88% | 8,66 s | 112,0 s |
  | 3 | 15,79% | 9,95 s | 133,8 s |
  | 4 | 15,24% | 17,16 s | 208,4 s |

- **RALAT: angka prototipe (-37% total, -66% kata pertama) ARTEFAK.** Prototipe memakai
  `detect()`+`recognize()` terpisah yang **1,8x lebih lambat** dari `readtext()` (dasarnya
  13,58 s lawan 8,26 s pada data yang sama). Memecah jalur lambat menolong; memecah
  `readtext` tidak. **`readtext` tidak superlinear terhadap luas gambar** - itu dugaan saya
  yang terbantah.
- **Sisi positif: memotong gambar TIDAK merusak urutan bacaan** (14,88% lawan 14,89%).
  Kerusakan 3 pita pada prototipe datang dari penyusunan teks PER PITA, bukan dari
  pemotongannya. Untuk streaming nanti: mengucapkan pita 1 lebih dulu BERARTI menyusun
  per pita, dan di situlah harganya.
- `bands: 1` tetap bawaan. Kode `_ocr_pita` ditahan atas keputusan pengguna sebagai
  mekanisme yang dibutuhkan streaming, **bukan** karena ia membeli sesuatu sekarang.
  Pita MEMILIKI kotak yang pusatnya di wilayahnya, potongan dilebihkan `band_pad_ratio`
  4% - penyaring pusat itu yang mencegah baris batas terbaca dua kali, tanpa dedupe.
  `build_result` tetap dipanggil SEKALI atas gabungan kotak. Flag `--pita` di
  `scripts/ukur_dokumen.py`. Dikunci 5 tes.

**Uji lapangan pertama oleh pengguna di HP lewat ngrok (12-11) - tiga temuan:**
1. **Kemasan Indomie: tanggal TIDAK terbaca, 44,9 detik.** Zona ketemu dengan skor **0,755**
   (pembidikan benar), potongan benar, tetapi OCR membaca sampah di KEEMPAT rotasi:
   `'CBI.'` / `'2 57 8 90 88.'` / `'5 4.'` / `'O6 8 4 5.'`. Menegaskan ulang: penghambatnya
   **pengenalan cetakan**, bukan pembidikan. 45 detik itu habis di `rotate_retry` yang mengulang
   SELURUH pipeline (deteksi zona + potong + OCR) pada gambar 3000x4000 empat kali, padahal
   zonanya sudah ketemu di lintasan pertama. **Tuas yang belum dikerjakan: putar POTONGANNYA
   (OCR 4,4 s) bukan gambar penuh (~10 s)** - perkiraan 45 s -> 20 s. Wajib ukur akurasi
   16 kemasan bersamaan, jangan latensi saja.
2. **Dua lembar uang dijawab satu nominal, dan BUKAN karena penjumlahan.** Deteksi mentah pada
   foto 2.000 + 10.000: tiga kotak yang SAMA (seluruh bingkai) dengan kelas berbeda -
   10000 skor 0,641, 50000 skor 0,301, 2000 skor 0,296. Model melihat satu gumpalan lalu menebak
   tiga kelas; pasca-pemrosesan membuang dua. Penjumlahannya tidak pernah dapat kesempatan.
   Sebabnya data latih: dari 80 foto hanya **1** yang berlabel banyak lembar.
3. **Ambang buram memang terlalu ketat.** Foto kemasan asli pengguna `blur_variance` **137,2**
   lawan ambang **100** - lolos, tetapi margin 37%. Foto malam dalam ruangan duduk di tepi ambang.
   Butuh 2-3 foto ASLI yang DITOLAK untuk mengkalibrasinya; tangkapan layar TIDAK BISA dipakai
   (latar putih aplikasi membuat `saturated_ratio` 0,44 dan hasilnya tidak sah).

**DATASET PUBLIK UNTUK MODUL KEDALUWARSA KETEMU (19-11): ExpDate, Seker & Ahn 2022, KIST.**
Unduhan: https://github.com/felizang/expdate (tombol Dataset -> Google Drive), **CC BY 4.0**,
tanpa pendaftaran. Wajib mengutip paper dan menyebut KIST.
- Enam subset: **Products-Real 1.767 gambar NYATA** (1.102 latih / 665 uji), Products-Synth
  ~12.000, Date-Synth 128.000, Components-Synth 450.000, plus Date-Real dan Components-Real.
- **Anotasinya memuat `transcription`**, bukan hanya bbox - jadi ia bisa dipakai untuk
  **fine-tune PENGENAL**, yang memang penghambat kami, bukan cuma detektor.
- Kelas deteksinya **`date`, `due mark`, `production mark`, `code mark`**. Model zona kami
  sekarang hanya SATU kelas (`expired_date_zone`). Dengan empat kelas, wilayah kode produksi
  bisa **ditolak sebelum OCR** - itu perbaikan di SUMBER untuk kegagalan `chees`, jauh lebih
  kuat daripada heuristik penanda negatif di parser.
- Halaman dataset menyebut **"dot-matrix fonts"** eksplisit, plus refleksi, pencahayaan tidak
  rata, dan beberapa tanggal pada satu produk. 13 format tanggal, bulan singkatan Inggris (OCT).
- **DUGAAN KUAT: Roboflow `expdate-pj47a/expiery_date` (12.960 gambar) adalah unggahan ulang
  Products-Synth, yaitu data SINTETIS.** Petunjuknya: kelas `date, code, due, prod` identik,
  jumlah ~12.000, dan nama workspace-nya literal "EXPDATE". **Ambil dari sumber, bukan cermin
  Roboflow** - format Roboflow membuang `transcription`, dan sintetis bukan yang kami kurang.
- **Batasnya: ia TIDAK menggantikan foto kemasan Indonesia.** Yang ia beri: bahan fine-tune
  dan **tolok ukur PUBLIK** (jawaban langsung untuk kelemahan n=13). Yang tidak: pembenaran
  mengklaim performa pada kemasan Indonesia. Itu tetap butuh +30 kemasan sendiri.

**`build_tts_cache.py --kunci <nama>` (19-11):** `assets/tts/*.mp3` SENGAJA di-commit, jadi
`--force` mengubah 91 berkas biner walau yang berubah cuma satu kalimat. Pakai `--kunci` untuk
klip yang teksnya memang berubah. Klip sekarang **91**, `uang_terpotong` baru dan `foto_gelap`
dibuat ulang karena teksnya berubah.

**UJI LAPANGAN 19-11 - dua temuan dan satu ralat atas kesimpulan saya sendiri:**
1. **AMBANG BURAM 100 TERBUKTI SALAH, DITURUNKAN KE 15.** Aplikasi mengirim POTONGAN
   ketat sebatas kurung jingga (sisi pendek **841** px, dari log `[quality]`), sedangkan
   ambang 100 dikalibrasi pada foto UTUH. Diuji pada 15 kemasan yang TERBUKTI TERBACA,
   dipotong seperti aplikasi memotong: **4 jatuh di bawah 100** - `20270906` 48,4,
   `merica` 87,9, `permen1` 23,4, `permen2` 19,3. Foto lapangan pengguna: 16,3 / 21,9 /
   22,5 / 31,4 / 38,0 / 38,2 / 40,2 - tujuh percobaan, nol lolos.
   Sebabnya **variance of Laplacian mengukur KEKAYAAN TEPI, bukan ketajaman**: latar
   bertekstur menaikkannya, plastik mengkilap yang memenuhi bingkai menurunkannya - jadi
   **makin benar pembingkaiannya, makin rendah skornya**. 15 dipilih karena di bawah 19,3,
   skor terendah di antara foto yang terbaca benar. **Harganya: foto buram kini sampai ke
   OCR** (latensi terbuang, bukan jawaban salah - penjaga hilir sudah ada).
   **BELUM DIUKUR: pada nilai blur berapa OCR mulai gagal.** 15 adalah batas yang sah dari
   data, bukan nilai optimal.
1b. **Autofokus mengunci ke latar juga nyata**, terukur pada dua tangkapan layar (bagian
   tengah 21,6 lawan 72,5 seluruh bingkai). `aturFokus()` dipasang dan dipertahankan, tetapi
   **ia bukan yang membuka blokade** - foto yang fokusnya baik pun ditolak oleh ambang.
   Pelajaran: dua tangkapan layar cukup untuk HIPOTESIS, tidak cukup untuk memilih perbaikan.
   Diukur pada dua tangkapan layar pengguna, ambang 100: foto 1 seluruh bingkai **176,8** /
   dalam kurung jingga 108,9 / sepertiga tengah 98,6; foto 2 **72,5** / **21,6** / **13,2**.
   Bagian TENGAH justru jauh lebih buram - latar (keyboard laptop) tajam, objek di tangan tidak.
   **Dugaan saya bahwa mengukur di dalam kurung akan menolong TERBANTAH**: di dalam kurung
   justru lebih buruk. Kalimat `foto_buram` karena itu memberi **saran yang salah**
   ("pegang kamera lebih diam") - kameranya tidak goyang. Diperbaiki dengan `aturFokus()`:
   `focusMode: continuous` + `pointsOfInterest` tengah, gagal dalam diam.
   **Menurunkan `blur.min_variance` DITOLAK** - itu hanya meloloskan foto yang tidak terbaca OCR.
2. **RALAT: perintah suara senter TIDAK bekerja; yang bekerja TOMBOLNYA.** Saya sempat
   menyimpulkan dari log bahwa rantai suara utuh karena `senter_nyala.mp3` terambil - padahal
   `GET /klip/...` tidak bisa membedakan pemanggil, sebab `setSenter()` dipanggil kedua jalur.
   **Log permintaan HTTP tidak membuktikan jalur mana yang memanggilnya.**
3. **`transcript` tidak ikut dikirim justru pada `PUTAR_KAMERA` dan `SENTER_*`**, sehingga
   `console.info('didengar: ...')` tidak pernah menyala untuk intent yang paling perlu
   didiagnosis. Diperbaiki, dan server kini mencetak **`[dengar] '<teks>' -> <INTENT>`** untuk
   setiap `/tanya` plus **`[quality] DITOLAK ... blur=`** untuk setiap foto yang ditolak.
   Di ponsel `console.info` tidak terjangkau, jadi jejaknya harus di sisi server.
4. **TERBUKTI: Whisper menulis "senter" dengan ejaan Inggris `center`**, sesekali `sender`,
   dan merusak "nyalakan" jadi "Yalahkan"/"Alakan". Log: `'Yalahkan Center Yalahkan Center'`,
   `'nyalakan center'`, `'Nyalakan center'`, `'Alakan sender'` - **keempatnya TIDAK_DIKENALI**.
   `center` dan `sender` ditambahkan; sisi MATI pada bobot 3 agar tetap menang. Keempat
   transcript itu dipakai langsung sebagai kasus uji. `senternya`/`centernya` TIDAK
   didaftarkan - router sudah memotong akhiran -nya, dan mendaftarkannya merusak kemenangan
   SENTER_MATI pada "tolong matikan senternya".

**SENTER (torch) 19-11 - jalan di Android, kemungkinan TIDAK di iPhone:**
`SENTER_NYALA` / `SENTER_MATI` (dua intent, bukan toggle) + tombol `.btn-cam` 56 px di
**kanan atas**. Klien memakai `track.applyConstraints({advanced:[{torch}]})`.
- **Torch web hanya ada di kamera BELAKANG, sedangkan bawaan aplikasi kamera DEPAN** -
  jadi jalur gagal adalah jalur BAWAAN, bukan kasus pinggiran. Tiga cabang gagal punya
  klipnya sendiri: `senter_butuh_kamera_belakang`, `senter_tidak_ada` (dua kali: `caps.torch`
  kosong, dan `applyConstraints` dilempar). **Tidak ada bukti Safari iOS mendukung `torch`** -
  di sana `getCapabilities` tidak ada, jadi `caps` jatuh ke `{}`. **Uji di Android dulu.**
- **BUG yang hampir lolos:** `matikan senter` terbaca `SENTER_NYALA`, karena frasa itu memuat
  kata "senter" milik SENTER_NYALA dan pada bobot sama skornya SERI. Pengguna minta dimatikan,
  sistem menyalakan - dan pengguna tunanetra tidak bisa melihatnya. Dijaga dua lapis: bobot
  **3** pada frasa "matikan", dan `SENTER_MATI` sebelum `SENTER_NYALA` di `CONTROL_INTENTS`.
  Itu juga sebabnya BUKAN satu intent toggle.
- Torch milik **TRACK**: penandanya direset tiap `startStream`, kalau tidak tombolnya akan
  berkata "matikan senter" untuk senter yang sudah padam.
- Letaknya kanan atas, **bukan baris bawah**: baris bawah adalah peta tiga posisi (kiri
  unggah, TENGAH rana, kanan balik kamera) dan tombol keempat akan menggeser rana keluar dari
  titik tengah - satu-satunya penanda yang bisa ditemukan tanpa melihat.
- 95 klip sekarang. `menu_bantuan` dibuat ulang karena ikut menyebut perintah senter.

**Quality gate bicara SOLUSI (19-11):** `terpotong_tepi()` di `quality_gate.py` adalah penanda
murni atas koordinat kotak - ada kotak menempel tepi bingkai (margin 2%) berarti objeknya
terpotong. Modul uang menghitungnya dari deteksi MENTAH dan `money_utterance` menukar
`tidak_yakin_uang` dengan klip baru **`uang_terpotong`** ("mundurkan kamera sedikit").
Itu menangkap persis kasus lapangan 12-11: dua lembar jadi tiga kotak SEUKURAN BINGKAI.
`foto_gelap` juga diubah menyebut **"nyalakan senter di ponselmu"** - pengguna tunanetra bisa
menyalakan senter sendiri, belum tentu bisa mencari lampu.
**ARAH (kiri/kanan) SENGAJA TIDAK diberikan.** `web/app/page.js:465` menyetel `facingMode`
bawaan `'user'` (kamera DEPAN) dan pratinjaunya dicerminkan CSS, sedangkan gambar ke server
tidak - jadi kanan GAMBAR adalah kiri PENGGUNA. Arah yang salah lebih berbahaya daripada tanpa
arah. Prasyarat untuk arah: klien mengirim `facingMode`, dan sisi cermin dipastikan dengan foto uji.
**Klip `uang_terpotong` belum punya berkas suara** sampai `python scriptsuild_tts_cache.py`
dijalankan (butuh internet).

**DITOLAK pengguna 12-11: menampilkan transcript ("didengar: <teks> -> <intent>") di bawah
kartu jawaban.** Sudah dibuat lalu di-revert atas permintaan pengguna. Jangan ditawarkan lagi.
Transcript tetap dikirim server dan tetap masuk `console.info`.

**`rantai` JADI BAWAAN 17-11, DAN ITU MENGEMBALIKAN AKURASI KEDALUWARSA KE 81%:**
- `pita` 12 BENAR / 3 SALAH / 1 DIAM = 75% lawan **`rantai` 13 / 2 / 1 = 81%** pada 16 kemasan.
  Yang berubah **hanya satu berkas**: `mentega` SALAH -> BENAR. **Nol regresi** pada 15 lainnya.
- Sebabnya: tanggal mentega tercetak **DIAGONAL** - `02:31`(x995,cy261) `NS`(831,362)
  `27`(680,428) `MAR`(418,523) `11`(238,614), jadi x TURUN saat y naik. Kemiringan sejatinya
  **-0,418**, di atas `line_slope_max` 0,35 sehingga dibuang jadi 0; taksiran median seluruh
  potongan hanya **-0,196** karena blok tabel gizi di atasnya hampir datar. **Satu angka
  kemiringan tidak muat untuk dua blok berorientasi berbeda** - masalah yang SAMA dengan
  halaman buku melengkung, muncul di modul yang berbeda.
- Harga di modul dokumen: CER **14,89% -> 14,94%** (1 membaik `r (10)`, 1 memburuk `r (4)`,
  11 tetap), direproduksi persis dari pengukuran 31-10. **PERINGATAN: margin target PRD
  <= 15% menyusut dari 0,11 ke 0,06 poin.** Perubahan berikutnya yang menambah 0,06 poin saja
  akan membuatnya gagal.
- Saklar `line_grouping` hidup di `vision.document` tetapi modul kedaluwarsa memakai
  `compose_text` yang sama, jadi **mengubahnya SELALU menyentuh kedua modul** dan keduanya
  wajib diukur bersamaan.
- `line_slope_correct` kini hanya berlaku untuk `pita`. Tesnya memakai mode yang dipatok.

**MODUL ZONA SADAR KELAS (20-11), siap menerima bobot 4 kelas:**
`Zone.cls` + `expiry.zone_classes_date: [date]` / `zone_classes_reject: [code, prod]`.
`pick_zone` membuang kelas yang ditolak lalu mengutamakan `date`. **Mundur aman dan itu
DIUJI**: zona tanpa nama kelas tidak pernah dibuang, dan tanpa kelas `date` pilihannya
kembali ke skor tertinggi - jadi config ini **tidak mengubah apa pun** selama `best_zone.pt`
(1 kelas) yang dipakai. 7 tes baru.
- Menyerang `chees` dari sisi yang benar: menolak wilayah kode produksi **sebelum OCR**,
  jadi label "Kode Produksi" tidak perlu terbaca - dan memang tidak pernah terbaca.
- **Tahan harapan: batas atas ~+6 poin** (1 berkas dari 16). Jalur zona adalah optimasi
  LATENSI bukan akurasi (81% dengan maupun tanpa, 02-10).
- `notebooks/05_zone_4kelas.ipynb` (11 sel, lolos `ast.parse`) melatihnya dari
  **`esigelec-rniez/expiry`** - 700 gambar, 4 kelas, satu-satunya dari lima kandidat yang
  punya split train/valid/test lengkap. Notebook memuat penjaga GPU, pemeriksaan dataset
  sebelum melatih (nama kelas + gambar tanpa label per split), dan penjaga timpa.
- **Bobot baru disimpan sebagai `models/best_zone_4kelas.pt`, JANGAN menimpa `best_zone.pt`** -
  itu bukti angka 81% sekarang. Ukur dengan `scripts/ukur_kedaluwarsa.py`, bandingkan
  benar/salah/diam terhadap dasar **13 / 2 / 1**.

**BOBOT 4 KELAS SUDAH DIUKUR 20-11, DAN JAWABANNYA: TETAP PAKAI `best_zone.pt`.**
Tiga bobot, 16 kemasan, nilai saklar dicetak tiap kondisi:

| bobot | BENAR | SALAH | DIAM | median | zona ketemu |
|---|---|---|---|---|---|
| **`best_zone.pt` (1 kelas) - DIPAKAI** | **13** | 2 | 1 | **9,96 s** | **7/16** |
| 4 kelas satu dataset | 13 | **0** | 3 | 20,23 s | 2/16 |
| gabungan (notebook 06) | 13 | **0** | 3 | 20,18 s | 3/16 |

- **Menggabungkan dataset TIDAK membeli apa pun.** Cakupan zona 2/16 -> 3/16, satu berkas;
  akurasi dan latensi identik. Dugaan bahwa cakupan runtuh karena datasetnya kurang
  mewakili kemasan Indonesia **terbantah**.
- **20 detik itu BUKAN harga model 4 kelasnya.** Deteksi zona sendiri 6,6 ms. Yang mahal
  adalah akibatnya: cakupan zona runtuh, jadi 13 berkas jatuh ke OCR seluruh gambar +
  rotasi. Latensi di modul ini **gejala cakupan**, bukan biaya inferensi.
- **Kesadaran kelas MEMANG bekerja** - dan itu dipisahkan dengan deteksi mentah pada
  `conf=0,01` (tanpa OCR, hitungan detik). `chees` memberi `code:0.75` `date:0.54`
  `date:0.47`: `code` ditolak, `date:0.54` dipakai, hasilnya DIAM bukan SALAH. `ovaltine`
  memakai `date:0.69`. Kedua jawaban salah hilang karena mekanisme yang dirancang, bukan
  kebetulan. **Tetapi** cakupan runtuh pada berkas LAIN, karena sebab yang berbeda:
  `ajinomoto` `code:0.65` lolos ambang lalu ditolak, sementara `date:0.26` ada di bawahnya,
  jadi `lolos` kosong dan zona dianggap tidak ada.
- **TUAS AMBANG MATI.** `zone_score_min` 0,40 -> 0,25 pada bobot gabungan: 12/1/3 = 75%,
  cakupan 3/16 -> 4/16 saja, dan `ajinomoto` BENAR -> SALAH. Kotak `date` berskor rendah
  itu **berskor rendah karena wilayahnya memang salah**; menurunkan ambang memasukkan zona
  buruk, bukan memulihkan zona yang terbuang. Dugaan 20-11 soal ambang **terbantah**.
- Satu temuan yang sah: **menolak `due` adalah kemenangan latensi murni** (akurasi identik
  per berkas, median 14,97 -> 11,12 s). `due` penanda "EXP", bukan tanggalnya - `20270906`
  memilih `due:0.45` padahal `date:0.34` ada. Berlaku hanya bila bobot 4 kelas dipakai.
- **`Zone.cls` TIDAK kosong pada model 1 kelas** - isinya `expired_date_zone`. Mundur aman
  tetap bekerja tetapi lewat cabang lain: nama itu tidak ada di daftar tolak sehingga lolos,
  lalu `bertanggal` kosong sehingga pilihan kembali ke skor tertinggi. Baca catatan
  "zona tanpa nama kelas" di atas sebagai "zona yang kelasnya tidak dikenali config".
- **Mengutip latensi modul ini: median SAJA menyesatkan.** Pada 1 kelas `tolakangin2`
  **90-149 detik**, `tolakangin1` 41-62 s, `tisu2` 23-42 s. Sebutkan median DAN terburuknya,
  atau pembaca akan menyangka pengguna menunggu 8 detik.

**Perbandingan PENUTUP, satu proses (wajib - lihat derau di bawah), dua finalis:**

| kondisi | BENAR | SALAH | DIAM | akurasi | median | terburuk | total | zona |
|---|---|---|---|---|---|---|---|---|
| **1 kelas @0,40 - DIPAKAI** | **13** | 2 | 1 | **81%** | **7,82 s** | 90,0 s | **262,1 s** | **7/16** |
| gabungan @0,25 tolak cpd | 12 | **1** | 3 | 75% | 10,43 s | 86,1 s | 380,4 s | 4/16 |

**1 kelas menang di KEDUA sisi, jadi ini bukan pertukaran.** Akurasi 81% lawan 75%,
median -33%, total -45%. Dugaan saya bahwa latensinya setara (sehingga pilihannya jadi
"1 salah lawan 2 salah pada kecepatan sama") **terbantah**. Penyumbang terbesar satu
berkas: `mentega` 6,1 -> 85,4 detik.

**Dan ini pembenaran aturan "bandingkan DI DALAM satu sesi", dengan angkanya sendiri:**
kondisi yang sama persis (1 kelas @0,40) memberi median **9,96 s** di satu proses dan
**7,82 s** di proses lain pada hari yang sama. Membandingkan 9,96 (sesi A) lawan 11,12
(sesi B) terbaca "nyaris seri" dan **hampir mengubah keputusan ini**.

**Ringkasnya: percobaan 4 kelas adalah temuan NEGATIF, dan itu dilaporkan apa adanya** -
sejajar dengan ablasi pra-pemrosesan PRD nomor 1. Yang dibelinya bukan model melainkan
pengetahuan: kesadaran kelas terbukti bekerja, `due` terbukti layak ditolak, dan
`Zone.cls` ternyata tidak kosong pada model 1 kelas. Kodenya tetap di tempatnya,
berteskan, dan tidak mengubah apa pun selama bobot 1 kelas dipakai.
**Jangan ulangi tiga sapuan ini** (gabung dataset, turunkan ambang, banding latensi) -
ketiganya sudah dijalankan dan hasilnya di atas.

**Penanda NEGATIF (`date_parser.negative_markers`, 20-11) - NETRAL, dipasang demi bahaya:**
A/B 16 kemasan: `[]` 13/2/1 = 81% lawan daftar terisi **13/2/1 = 81%, identik per berkas**.
Dibiarkan menyala karena bahaya yang ia tutup berjenis JAWABAN SALAH (`"NO BETS 210829"`
terbaca sebagai tanggal - ada tesnya), bukan karena ia memperbaiki sesuatu yang terukur.
**Pembenarannya tes bahaya, bukan perbaikan terukur.** Kosongkan daftarnya bila merugikan.
- **TIDAK memperbaiki `chees`, dan rencana saya terbantah.** Teks yang benar-benar diurai
  pipeline: `'man.yeg Bes 0re Cae 0 T7 回 回 WOR SUCALNED 210526/ en im ua.'` - **tanpa
  "Kode Produksi" sama sekali**. Kata itu muncul di diagnosis 19-11 karena OCR dijalankan
  lewat jalur terpisah. **Diagnosis WAJIB lewat `ExpiryReader.read()`**, bukan memanggil OCR
  sendiri - teks kedua jalur itu berbeda.
- **Aturan baru untuk SETIAP sapuan: skrip wajib mencetak NILAI saklar tiap kondisi.**
  Sapuan pertama penanda negatif memakai `sed` yang polanya tidak cocok, jadi yang tertukar
  cuma judul kolom dan yang terukur tetap saklar lama. Hasilnya terlihat masuk akal sepenuhnya.

**Dua jawaban salah yang MASIH tersisa di kedaluwarsa (bukan soal urutan bacaan):**
- `chees` 2026-05-21 (harap 2027-03-21): parser menjawab dari **nomor produksi** `210526`,
  padahal `MAR` ada di sebelahnya. `rantai` tidak mengubahnya. Penjaganya BUKAN
  `require_marker_for_compact` - menyalakan itu memberi 56%.
- `ovaltine` 2027-09-30 (harap 2027-09-27): meleset tiga hari, tercatat sejak 02-10.

**RIWAYAT: akurasi sempat terbaca TURUN 81% -> 75% pada 16-11, dan sebabnya ternyata `pita`,
bukan regresi misterius.** Yang tetap tidak dapat ditelusuri: mengapa 02-10 memberi 13/1/2
sementara 17-11 memberi 13/2/1 - komposisi berbeda pada akurasi yang sama. **Riwayat Git mulai
11 Oktober sedangkan 81% diukur 2 Oktober**, jadi sembilan hari itu tidak ada di versi kontrol.
**Yang masuk jurnal adalah angka 17-11 dengan tanggal, versi paddleocr, dan nama model.**

**Catatan diagnosis 16-11 (ditahan sebagai jejak):**
- **12 BENAR / 3 SALAH / 1 DIAM** pada 16 kemasan, disepakati DUA instrumen (skrip ad-hoc dan
  `scripts/ukur_kedaluwarsa.py` resmi). Catatan 02-10: 13 / 1 / 2 = 81%.
- **Arahnya buruk: jawaban SALAH naik 1 -> 3, DIAM turun 2 -> 1.** Itu melanggar prioritas yang
  sudah dikunci modul ini - tanggal keliru lebih berbahaya daripada diam. Dua salah baru:
  `mentega` 2027-03-31 (harap 03-11), `chees` 2026-05-21 (harap 2027-03-21). `ovaltine`
  2027-09-30 tetap salah seperti 02-10.
- **DIDIAGNOSIS SEBAGIAN 16-11. Ketiga jawaban salah adalah kegagalan PARSER, bukan OCR** -
  OCR membaca tanggalnya dengan benar di ketiganya, penafsirannya yang keliru:
  - `chees`: teks `'... 210526 MAR ... /Production Code BestBefore Kode Produksi/'`. Parser
    menjawab dari **nomor produksi** `210526`, padahal tanggalnya `MAR` tepat di sebelahnya.
  - `mentega`: teks `'... MAR 27 NS 02:31 11.'`. Cetakan aslinya "02:31 11 MAR 27", tetapi
    **urutan kotak OCR mengacaukannya** sehingga `11` terlempar ke belakang `MAR 27`, lalu
    pola bulan-saja menang. Ini masalah URUTAN BACAAN, sama akar dengan foto buku.
  - `ovaltine`: `'LOT:2 09.27/L3A'` -> 2027-09-30, meleset tiga hari. Bukan temuan baru.
- **Sebab turunnya 81% -> 75% TETAP TIDAK DAPAT DITELUSURI, dan sekarang kita tahu kenapa:
  riwayat Git mulai 11 Oktober, sedangkan 81% diukur 2 Oktober.** Sembilan hari itu tidak ada
  di Git, jadi bisect tidak mungkin dan 81% tidak bisa direproduksi. **Yang masuk jurnal
  adalah 75% dengan tanggal pengukurannya**, bukan 81%.
- Kandidat yang SUDAH DIELIMINASI: `require_marker_for_compact` (dinyalakan justru memberi 56%,
  lihat ralat di atas) dan kode parser (tidak tersentuh sejak commit pertama).
- **Angka 81% mungkin tidak dapat direproduksi dari repo saja**: pengenal `PP-OCRv6_medium_rec`
  tersimpan di `~/.paddlex/official_models/`, bukan di Git. Terpasang sekarang **paddleocr 3.7.0,
  paddlepaddle 3.3.1** (catatan lama menulis "paddleocr 3.3.1" - yang 3.3.1 itu paddlepaddle).
  Jurnal WAJIB menulis versi paddleocr, nama model pengenal, dan tanggal pengukuran.
- Petunjuk arah: `mentega` dan `ovaltine` sama-sama jatuh di hari TERAKHIR bulan, yaitu bentuk
  jawaban bulan-saja - wilayah `require_marker_for_compact` dan pola `my_spasi`. Tanpa
  pra-pemrosesan `chees` justru BENAR dan komposisinya 12/2/2 (satu salah lebih sedikit),
  walau ablasi resmi melaporkan "tidak berpengaruh +0%" karena akurasinya sama-sama 75%.

**Urutan eskalasi kedaluwarsa disusun ulang 17-11, dan temuannya bukan soal latensi:**
- Urutannya sekarang **`potongan tegak -> seluruh gambar -> rotasi potongan`**. `_read_zone`
  hanya potongan tegak; rotasinya di `_putar_potongan` sebagai langkah terakhir. Rotasi gambar
  PENUH tidak masuk daftar ini - ia tetap di `read()` dan hanya dipakai bila zona tidak ketemu.
- Ini **memperbaiki kerugian 16-11**: dua kemasan yang menjawab dari seluruh gambar dulu dihukum
  urutan lama (`20261008` 15,1 -> 22,5 s, `20270906` 4,3 -> 13,0 s) dan kini kembali normal.
- **TEMUAN UTAMA: NOL dari 16 kemasan menyentuh langkah 3.** Jejak per berkas: 7 berhenti di
  potongan tegak, 2 di seluruh gambar, **7 tanpa zona**, 0 sampai rotasi potongan. Jadi kedua
  kondisi `rotate_crop` menjalankan kode IDENTIK pada ke-16 berkas: akurasi 13/2/1 = 81% memang
  harus sama, dan selisih median 9,35 lawan 7,35 detik **murni derau** - `tidakada_permen1`
  10,5 -> 7,2 detik padahal saklar itu tidak menyentuh jalurnya. **Jangan kutip -21% itu.**
- **`rotate_crop` tetap `false`.** Bukan karena terbantah, tetapi karena **tidak terukur**:
  kasus yang ia sasar (zona ketemu, potongan gagal, gambar penuh gagal) tidak ada di data uji.
- **Foto Indomie dari uji lapangan 12-11 TIDAK DISIMPAN** (`find` seluruh repo: tidak ada).
  Satu-satunya contoh nyata kasus itu hilang. **Aturan proses baru: setiap foto lapangan yang
  gagal WAJIB langsung disimpan ke `data/uji_kedaluwarsa/` dengan nama bertanggal.**
- Cakupan zona: **9 dari 14 kemasan bertanggal**, sama persis dengan catatan 30-09. Tetapi itu
  juga berarti 7 berkas jatuh ke jalur cadangan, dan di situ `rotate_crop`, `crop_margin_ratio`,
  dan `zone_score_min` tidak berpengaruh sama sekali.

**Catatan 16-11 soal urutan lama (ditahan sebagai jejak):**
16 kemasan, dua kondisi: akurasi **identik per berkas** (12/3/1 keduanya), latensi JAUH lebih
buruk - median 6,54 s -> 9,33 s, total 234,4 s -> 344,4 s, terburuk `tolakangin2` 91,7 s ->
**147,3 s**, melambat di 13 dari 16 berkas. Taksiran 45 s -> 20 s **terbantah, arahnya terbalik**.
Sebab yang paling mungkin: jalur lama yang gagal membaca potongan langsung mundur ke OCR seluruh
gambar, dan itu sering BERHASIL dan murah (ajinomoto 30-09); jalur baru membakar tiga rotasi
potongan lebih dulu. **Tuas yang masih masuk akal dan BELUM diuji: URUTAN eskalasinya** -
`potongan tegak -> seluruh gambar -> rotasi potongan`.

**PERINGATAN soal mengutip LATENSI kedaluwarsa:** kondisi yang sama persis
(`rotate_crop=false`) memberi median **6,54 detik** di satu sesi dan **10,46 detik** di sesi
lain pada hari yang sama - simpangan 60% dari beban laptop. Yang sah dikutip adalah
perbandingan DI DALAM satu sesi, bukan angka detiknya. Kalau jurnal menulis satu angka latensi,
sebutkan ia median satu sesi dan berderau besar.

**Konfigurasi terkunci (jangan diubah tanpa mengukur ulang):**
mesin OCR dipisah per modul - dokumen EasyOCR, kedaluwarsa PaddleOCR + `mobile_det`;
`expiry.preprocess_chain: hanya_resize` (resize WAJIB ada, ia pengendali latensi);
`resize.max_side: 1600`; `rotate_retry: [180, 90, 270]`; `zone_score_min: 0.40`.

**AKURASI UANG: 85,0% pada k-fold v3, dataset bersih 80 foto** (68 benar / 11 salah /
1 diam, ambang 0,30). Target PRD >= 85% tercapai, tetapi **tepat di garisnya**.
Sapuan ambang v3: 0,15 / 0,20 / 0,25 seluruhnya **69/11/0 = 86,25%**; 0,30 dan 0,35
68/11/1; 0,40 67/11/2; 0,50 64/9/7. Lampiran di `docs/jurnal_bahan/v3/`.
Riwayat: 65,7% -> 68,8% -> 84,0% -> 90,1% (v2, 81 foto) -> **85,0% (v3, 80 foto bersih)**.

**Penurunan 90,0% -> 85,0% itu TIDAK boleh dibaca sebagai kemunduran model.** Mengeluarkan
satu foto cacat mengubah pembagian kelima lipatan sepenuhnya, jadi kedua angka diukur pada
partisi berbeda. Dengan n=80 dan ~10 kesalahan, selisih 5 poin ada di dalam variasi
antar-run - artinya 90,1% mungkin ujung atas yang beruntung, bukan titik tengah.
**Laporkan akurasi uang sebagai rentang 85-90%, bukan satu angka presisi.** Itu temuan,
bukan kegagalan, dan sekaligus jawaban terhadap kritik "angkanya berdiri di atas anotasi lama".

Kesebelas kesalahan v3: **sembilan salah kenal kelas satu lembar** dan **dua salah hitung
lembar** (01241 2000->4000, 01210 10000->30000). Dua yang terakhir BARU - v2 tidak punya
satu pun. Kalau bertambah, kesimpulan 28-10 bahwa "tuas pasca-pemrosesan sudah habis"
perlu ditinjau ulang. Terlemah per proporsi: **1000 (3/4, hanya 4 kotak latih),
10000 (7/10), 2000 (16/20)**; **100000 sempurna 13/13**.

Bobot yang DIPASANG di `models/best_money.pt` masih **v2** (MD5
`bc09a6fc2c9fedbb38c39aa8aba44672`; model lama di `models/best_money_SEBELUM_v2.pt`).
`money_kfold_v3_final/weights/best.pt` sudah ada di Drive (6.515.946 bita, optimizer
dibuang = latihan selesai normal) tetapi **belum diunduh dan belum dipasang** - keputusan
pengguna. Angka laporan dan model yang dipakai sebaiknya dari dataset yang sama;
ketidakcocokan latih-pakai adalah persis jebakan CLAHE 28-10.
`score_min` tetap **0,30** sampai diputuskan lain; sapuan v3 menunjukkan **0,25 lebih baik
di dua sisi sekaligus** (+1 benar, diam 1 -> 0, salah tetap 11).

**CLAHE SUDAH DIBUANG dari rangkaian `uang` (28-10): `[resize, clahe]` -> `[resize]`.**
Sebabnya ketidakcocokan latih-pakai - notebook melatih pada gambar ASLI, aplikasi dulu
menerapkan CLAHE saat inferensi, sehingga tolok ukur 90,1% selalu diukur TANPA CLAHE
sementara aplikasi berjalan DENGAN CLAHE. Diukur ulang dengan config sungguhan pada
81 foto: **79 benar / 2 salah / 0 diam = 97,5%** (dari 96,3%), dan **latensi modul turun
36%**: 88,4 ms -> 56,4 ms. Angka 97,5% itu TERCEMAR (semua foto ikut melatih v2) -
yang sah untuk laporan tetap k-fold **90,1%**. Bukti terkuat tetap v1 pada 32 foto
bersih: 65,6% lawan 87,5%. Rasio latensi (34-36%) lebih layak dikutip daripada
milidetiknya, yang bergerak antar-sesi tergantung beban laptop.
Langkah `clahe` **tidak dihapus**: tetap di `STEPS`, tetap dipakai rangkaian `dokumen`,
dan uji ablasi per langkah dipindah ke rangkaian itu (`tests/test_preprocess.py`).

Rangkaian `uang` sekarang **`[resize]` saja**. `resize` WAJIB tetap ada: ia pengendali
latensi untuk foto HP 3024x4032.

Laporan status untuk tim: `docs/status-proyek.md` (28-10), memuat daftar angka USANG
(65,7% / 68,8% / 87,5% / 84,0%) supaya tidak beredar lagi di draf laporan.

**Kerja berikutnya, berurutan:**
1. **Modul uang 68,8% lawan target 85%** (k-fold bersih, 48 foto, ambang 0,30).
   Model `money_kfold_v1_final` dipasang, `score_min` sudah disapu dan disetel 0,30.
   **Penghambatnya DIAM, bukan SALAH**: 11 diam lawan 4 salah.
   **Tuas ambang SUDAH HABIS** - dari 12 DIAM di 0,40 hanya 5 yang bisa diselamatkan
   dengan menurunkan ambang; sisanya tidak punya deteksi sama sekali bahkan di 0,15.
   Itu batas model, bukan batas ambang. Yang tersisa:
   b. **Kelas terlemah: 5000 (0,29), 2000 (0,50), 100000 (0,50).** 20000 dan 50000 sempurna.
      **SUDAH DIKERJAKAN 23-10**: +33 foto diarahkan tepat ke tiga kelas itu
      (2000 8->21 kotak, 5000 7->20, 100000 6->13), dataset kini 81 foto / 80 label.
      **Belum diukur** - unggah `data/label_sendiri/` ke Drive dan jalankan ulang
      `notebooks/04_money_kfold.ipynb` (`percaya_label`, `sendiri=True`,
      `LATIH_MODEL_TERAKHIR = False`). Itu langkah berikutnya yang paling berbobot.
   c. Augmentasi lebih agresif (blur, derau, cutout) untuk mensimulasikan variasi yang tidak difoto.
   d. YOLOv8n -> YOLOv8s, lebih banyak epoch.
   e. Foto baru dengan variasi latar, cahaya, dan emisi - ini yang tidak bisa digantikan apa pun.
2. CER dokumen meleset 0,3 poin, disebabkan dua foto lama berupa tangkapan layar
   (`ketentuan_makalah` 76,9%, `open_recruitment` 22,0%). Ganti keduanya dengan foto asli.
3. Opsional: pembacaan dokumen bertahap (OCR bagian atas dulu, bacakan, lanjutkan) bila ingin
   memperbaiki latensi dokumen sungguhan alih-alih mencatatnya sebagai penyimpangan.

**Yang hanya bisa dikerjakan pengguna:** uji pengguna proksi + kuesioner SUS, lalu Fase 5
(laporan, README, video demo, slide). `assets/tts/` sudah lengkap 69 klip.

Utang yang sudah diketahui:
- **PENYIMPANGAN PRD NFR-01 diterima dengan sengaja (02-10): latensi end-to-end 11,4-11,5 detik untuk
  intent dokumen dan kedaluwarsa, sedangkan NFR-01 menulis <= 8 detik.** Diukur pada 64 foto dengan
  STT + pipeline + TTS render, pemuatan model tidak dihitung. Yang lolos: uang 1,4 s dan kendali 1,3 s.
  Tiga tuas dicoba dan semuanya gagal menurunkan latensi tanpa mengorbankan akurasi:
  ukuran gambar 800 px (akurasi 81% -> 56% DAN latensi 11,4 -> 20,2 s), matikan rotasi (akurasi -12%),
  matikan jalur zona (latensi 11,4 -> 27,3 s). Dasar penyimpangan: PRD baris 154 (target latensi bersifat
  awal, boleh direvisi setelah pengukuran) dan FR-14 (pengumuman "sedang memproses" sudah ada).
  **Sebutkan di laporan**, sejajar dengan `money.score_min` dan `bright.min_mean`.
- **Akurasi dan latensi TERKAIT lewat mekanisme percobaan ulang.** Gambar lebih kecil lebih cepat per
  panggilan, tetapi menurunkan akurasi, dan tiap kegagalan memicu empat rotasi - sehingga totalnya
  justru lebih lambat. Jangan mengoptimasi latensi tanpa mengukur akurasi di saat yang sama.
- **Jalur zona adalah optimasi LATENSI, bukan akurasi.** Pada 16 kemasan ia tidak menyumbang akurasi
  sama sekali (81% dengan maupun tanpa), tetapi mematikannya memperburuk latensi median 11,4 -> 27,3 s.
- **Model uang v2.3 pada 35 foto sendiri, DUA metrik (diukur ulang 06-10):**
  metrik TOTAL (yang diucapkan ke pengguna) **23 benar / 6 salah / 6 diam = 65,7%**;
  metrik KELAS (apakah model mengenali nominalnya) 25 / 4 / 6 = 71,4%.
  **Yang masuk laporan sebagai akurasi sistem adalah metrik TOTAL.** Target PRD >= 85% belum tercapai.
  Angka lama "24/35 (68,6%)" sudah BASI: itu dari ambang skor 0,50 sebelum diturunkan ke 0,40 pada 27-09.
  Dari 6 kesalahan metrik total, 2 adalah salah hitung lembar (pasca-pemrosesan) dan 4 salah kenal kelas.
- **Tuas inferensi modul uang sudah habis diuji (06-10) dan semuanya gagal.** Sapuan `imgsz` x
  test-time augmentation pada 35 foto: 640 tanpa TTA 65,7% (terbaik, 0,11 s); 640+TTA 62,9%;
  960 tanpa TTA 62,9%; **1280 tanpa TTA jatuh ke 48,6%**. Menaikkan `imgsz` di atas ukuran latih
  justru merusak. Jadi anggaran latensi uang (1,4 dari 8 detik) **tidak bisa ditukar dengan akurasi**.
  Opsi `money.augment` tetap ada di config tetapi `false`.
- **Ablasi pra-pemrosesan pada 20 foto: tidak ada beda** (13/3/4 dengan maupun tanpa CLAHE).
  Ini membatalkan dua kesimpulan lama yang saling berlawanan dari n=5. Jangan ubah rangkaian `uang` tanpa data lebih banyak.
- **`money.score_min` sengaja menyimpang dari PRD: 0,40, bukan 0,50.** Sapuan pada 35 foto:
  0,35-0,45 memberi 25 benar / 4 salah / 6 diam; 0,50 memberi 24 / 4 / 7; di bawah 0,35 jawaban salah naik ke 5.
  Alasan utamanya bukan selisih satu foto itu, melainkan bahwa pada rentang tersebut jumlah jawaban SALAH
  paling sedikit. Sebutkan penyimpangan ini di laporan, seperti `bright.min_mean`.
- **`bright.min_mean` sengaja menyimpang dari PRD: 245, bukan 220.** Ambang PRD menolak foto dokumen yang sah karena
  kertas putih memang punya rata-rata intensitas tinggi. Penjaga silau yang utama sekarang proporsi piksel jenuh.
  Sebutkan penyimpangan ini di laporan. Angka 245 belum dikalibrasi dengan foto HP asli.
- **`zone_score_min` masih 0,40 dan belum pernah diuji di batasnya.** Pada foto kemasan sungguhan model
  zona mendeteksi 9 dari 14 dengan skor 0,43-0,77, jadi ambang itu kebetulan meloloskan semuanya.
  **Jangan kalibrasi dari gambar sintetis** (di situ skornya 0,35-0,49, artefak gambar ujinya).
- **Modul dokumen lambat: 4,6-5,4 detik per halaman di CPU**, dan pemotongan 40 kata tidak menguranginya karena
  OCR berjalan atas seluruh halaman lebih dulu. Tuas terbesar adalah ukuran gambar (800 px = 1,54 detik), tetapi
  menurunkannya perlu kalibrasi dengan foto asli lebih dulu.
- **CER dokumen 15,2% pada 13 dokumen** (target PRD <= 15%, jadi meleset 0,2 poin). Rata-ratanya diseret
  dua foto lama yang berupa tangkapan layar: `ketentuan_makalah` 76,9% dan `open_recruitment` 22,0%.
  **Pada 11 foto sesi 29-09 saja CER-nya 9,0%**, jauh di bawah target. Foto terbaik `r (1).JPG` = 1,9%.
  Pelajarannya konsisten: mutu foto jauh lebih menentukan daripada parameter apa pun.
- **Pra-pemrosesan dokumen kini NETRAL, bukan membantu: 15,2% dengan, 14,5% tanpa.** Sebelum dikalibrasi
  ia merugikan (20,2%). **Jangan tulis di laporan bahwa pra-pemrosesan meningkatkan akurasi** - datanya
  tidak mendukung. Dugaan yang belum diuji: pra-pemrosesan dirancang menolong foto BURUK, sedangkan
  foto uji sesi ini bagus semua. Perlu foto dokumen yang sengaja dibuat buruk untuk mengujinya.
- **Akurasi tanggal kedaluwarsa 81% - TARGET PRD TERCAPAI** (BENAR 13 / SALAH 1 / DIAM 2 dari 16
  kemasan, target >= 70%). Riwayatnya: 19% -> 31% -> 44% -> **81%**. Lompatan terakhir dari pindah ke
  PaddleOCR untuk modul ini. Satu jawaban salah tersisa: ovaltine meleset tiga hari.
- **Angka akurasi tunggal menyesatkan untuk kedaluwarsa - prinsip yang sudah tiga kali terbukti.**
  Pernah terjadi: kondisi tanpa pra-pemrosesan berskor lebih tinggi tetapi mengarang tiga tanggal salah
  (30-09); pelonggaran penanda di PaddleOCR menambah satu benar dan satu salah (01-10); perbaikan parser
  yang keliru menambah dua salah tanpa mengubah jumlah benar (02-10). Di laporan **wajib** pisahkan
  benar / salah / diam, dan sebutkan arah kesalahannya.
- **RALAT (30-09): model zona TERNYATA BEKERJA.** Mendeteksi **9 dari 14** kemasan bertanggal, skor
  0,43-0,77. Kesimpulan lama ("tidak berpindah ke kemasan Indonesia, 0 deteksi") diambil dari foto lama
  yang berupa tangkapan layar dan bidikan jauh. Jangan menilai sebuah model dari data uji yang buruk -
  ini kesalahan yang sama persis dengan menilai model uang dari dataset Roboflow yang labelnya tertukar.
- **Dua bug diperbaiki 30-09, akurasi 31% -> 44%:** (a) binarisasi dibuang dari rangkaian `kedaluwarsa`
  (`[upscale, clahe]`), karena pada 9 potongan zona sungguhan binarisasi memberi **0 benar** dan hampir
  selalu menghasilkan teks kosong - kebalikan dari dugaan PRD 8.8 langkah 3; (b) `full_image_fallback`:
  jalur zona kini mundur ke OCR seluruh gambar bila potongannya tidak menghasilkan tanggal, sebab zona
  adalah **petunjuk letak, bukan komitmen**.
- **Riwayat rincian 44%:** 30-09 masih BENAR 7 / SALAH 2 / DIAM 7 (dua jawaban benar ditukar dua jawaban
  salah, keduanya ke arah aman), lalu 02-10 menjadi **BENAR 7 / SALAH 0 / DIAM 9** setelah syarat tahun
  empat digit. Jadi akurasinya tidak naik, tetapi tanggal karangannya habis.
  **Arah kesalahan wajib dipantau ulang setiap kalibrasi**, bukan hanya jumlahnya.
- **Nilai pra-pemrosesan BERBALIK ARAH tergantung mesin OCR - temuan ablasi terkuat di proyek ini.**
  Modul kedaluwarsa: dengan EasyOCR pra-pemrosesan MEMBANTU +6% (44% lawan 38%), dengan PaddleOCR
  MERUGIKAN -12% (69% lawan 81%). Modul dokumen dengan PaddleOCR justru DIBANTU +2,9% (9,4% lawan 12,3%).
  Jadi "apakah pra-pemrosesan membantu" **tidak punya satu jawaban**: bergantung pada mesin OCR dan
  pada modul. PaddleOCR punya normalisasi internalnya sendiri, dan rangkaian `kedaluwarsa` yang
  meng-upscale 2x menambah kerusakan di atasnya.
- **Ambang quality gate belum dikalibrasi** (masih nilai awal PRD). Dataset Roboflow tidak bisa dipakai karena hanya berisi foto layak.
  Perlu ~20 foto HP sendiri (10 layak, 5 buram, 5 gelap) sebelum Fase 4.
- **Parameter pra-pemrosesan juga belum dikalibrasi pada foto asli.** Perbandingan bilateral vs NLM diukur pada derau Gaussian buatan.
- **Pasca-pemrosesan uang belum pernah diuji pada foto uang sungguhan.** Penghitungan banyak lembar tetap klaim yang belum terbukti.
- **Parser tanggal sudah kena teks OCR sungguhan** (30-09 dan 01-10), dan tiga lubang ketemu karenanya:
  format rapat tanpa pemisah, pemisah spasi, dan bacaan terpotong (`27` menjadi `2`). Dua sudah ditutup.
  Salah baca OCR asli memang jauh lebih berantakan daripada O/I/S/B: contohnya `'E03*51 {19425 1104 JADAN.'`.
- **Penghambat utama kedaluwarsa adalah PENGENALAN CETAKAN, bukan pembidikan.** Terbukti 30-09: foto yang
  dipotong tepat pada tanggalnya pun **0 benar dari 5**. Contoh keluaran OCR: ovaltine `"8 2 7 ' 58."`,
  kecapasin kosong sama sekali. Cetakan dot-matrix/inkjet kemasan di luar kemampuan EasyOCR.
  Yang sudah diuji dan **bukan** penyebabnya: rotasi, resolusi (sapuan `max_side` 1600/2600/4032 tidak
  mengubah hasil, hanya menaikkan waktu 39 -> 75 detik), dan rangkaian pra-pemrosesan (lihat di bawah).
- **Hipotesis "rangkaian `kedaluwarsa` akan menyelamatkan cetakan dot-matrix" TERBANTAH.** Diuji empat
  rangkaian: threshold+morfologi justru merusak (`r 1.`, `1 8 1 4.`, kosong). Binarisasi menghapus cetakan
  tipis alih-alih menyambungnya. Rangkaian `dokumen` yang tanpa binarisasi justru paling banyak berhasil.
- **`require_marker_for_compact` dimatikan 30-09.** Diukur pada 21 foto dengan OCR dijalankan sekali lalu
  diurai dua kali: foto utuh BENAR 3 -> 7, SALAH 0 -> 0, DIAM 13 -> 9. Akurasi foto utuh 19% -> 44%.
  **PERINGATAN: nol tambahan jawaban salah itu mungkin artefak** karena EasyOCR nyaris tidak membaca teks
  pada kemasan ini, jadi tidak ada kode bets untuk disalahbaca. `NO BETS 210829` memang lolos jadi tanggal
  saat dilonggarkan (ada tesnya). **Ulangi pengukuran ini setiap kali mesin OCR diganti.**
- **Celah pemisah spasi ditutup dua tahap, dan tahap keduanya yang berdampak.**
  01-10 pola `dmy_spasi` (hari-bulan-tahun berspasi, penanda wajib, hari/bulan dua digit): +1 benar /
  +0 salah pada uji mesin terisolasi, tetapi **nol perubahan** di pipeline penuh.
  02-10 pola `my_spasi` (bulan-tahun berspasi, tahun wajib empat digit sesuai daftar format PRD 8.8.1):
  **menghapus kedua jawaban salah di pipeline**, karena keduanya ternyata jawaban bulan-saja bertahun
  dua digit. Spasi **tidak** dimasukkan ke `SEP`; itu akan mengembalikan bug
  `"01/01/2026 12/12/2027"` (ada tes regresinya).
- **Klaim rentang di `find_candidates` adalah PENJAGA, bukan bug.** Kandidat berpenjaga mengklaim
  rentangnya walau nanti dibuang, sehingga tafsiran yang lebih lemah atas angka yang sama ikut ditekan.
  02-10 perilaku ini sempat "diperbaiki" dan hasilnya dua jawaban salah baru
  (`'NETTO 12 29 2028 G'` -> 2029-12-31, `'LOT 11 27 2028 XY'` -> 2027-11-30). Dibatalkan, dan sekarang
  dikunci tiga tes. **Jangan dilepas tanpa mengukur benar/salah/diam lagi.**
- **Pembidikan tetap masalah nyata yang BELUM dipecahkan**, hanya belum jadi penghambat. Pengguna tunanetra
  tidak tahu tanggal tercetak di sebelah mana. Pilihan yang sudah dipetakan: latih ulang model zona dengan
  foto sendiri (butuh ~100+ kotak berlabel), pemindaian ubin pada foto resolusi penuh (tanpa latihan, biaya
  latensi N x OCR), panduan suara saat memotret, atau beberapa foto sekaligus. Semuanya sia-sia sebelum
  pengenalan cetakan diperbaiki.
- Penamaan data uji: 9 berkas kemasan sempat hanya 7 digit (nol bulan hilang) dan 11 dari 13 dokumen sempat
  terlewat diam-diam karena `r (1).JPG` lawan `r(1).txt`. Keduanya sudah dibereskan, dan `tests/test_ukur.py`
  menjaganya. Pelajaran: kegagalan diam-diam pada skrip pengukuran lebih berbahaya daripada kegagalan keras.
