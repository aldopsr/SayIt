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
- **TTS:** gTTS (pilihan tim setelah uji dengar; MMS-TTS tidak jelas, suara Windows hanya Inggris). Desain hibrida:
  jawaban uang/tanggal/pesan tetap = klip MP3 tersimpan (offline); teks dokumen = gTTS langsung, tidak disimpan ke disk.
  Semua kalimat baru harus didaftarkan di `sayit/response/templates.py` (CLIP_TEXTS) lalu cache dibuat ulang.
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
- Privasi: teks yang dibacakan gTTS dikirim ke Google. Jangan menguji dengan dokumen pribadi asli.

## Aturan kode
- Semua parameter di `config/settings.yaml`, dibaca lewat `sayit/config.py`. Hindari angka ajaib di kode.
- Fungsi yang butuh perangkat (mikrofon, model, internet) harus bisa diganti tiruan di tes (lihat pola `model_factory` dan `synth`).
- Teks untuk pengguna dalam Bahasa Indonesia; nama variabel boleh Inggris atau Indonesia, konsisten per modul.
- Setelah menyelesaikan satu tahap, perbarui bagian **Status** di bawah dan tambahkan baris di `docs/keputusan-teknis.md` bila ada keputusan baru.

## Status (18 September 2026)
Selesai: config, `audio/io.py`, `audio/stt.py`, `audio/tts.py`, `intent/`, `response/`, skrip cache & demo,
`vision/quality_gate.py` (PRD 8.2), `vision/preprocess.py` (PRD 8.3), `vision/money.py` (PRD 8.6),
`vision/date_parser.py` (PRD 8.8.1), `vision/document.py` (PRD 8.7), `vision/expiry.py` (PRD 8.8), `pipeline.py` (PRD 7), `app.py` + `sayit/appkit.py` (Streamlit), `scripts/diagnosa_uang.py`, `scripts/buat_label_uang.py`, `scripts/ukur_dokumen.py`,
`scripts/ukur_kedaluwarsa.py`, `sayit/gambar.py`, `tests/test_ukur.py`, `scripts/banding_ocr.py`, `scripts/ukur_latensi.py`, 566 tes lulus.
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
1. **Dengan PaddleOCR, `require_marker_for_compact` harus DINYALAKAN kembali** - kebalikan dari keputusan
   30-09. Pelonggaran di PaddleOCR memberi +1 benar tetapi +1 salah (miesedap dijawab dari kode produksi
   `200122`). Saklar itu milik mesin OCR, bukan keputusan global.
2. Latensi PaddleOCR 7x EasyOCR, dan oneDNN **tidak bisa dinyalakan** di paddlepaddle 3.3.1. Belum diuji:
   model `PP-OCRv5_mobile_det` (butuh internet) - itu tuas latensi yang paling menjanjikan.
3. Menjalankan kedua mesin dalam satu proses **crash native**. Pakai `--mesin` satu per satu, dan `--sisi 800`
   karena paddle crash pada foto 3024x4032 utuh. Skripnya `python scripts\banding_ocr.py`.

Celah pemisah spasi sudah ditutup 01-10 dan 02-10 (pola `dmy_spasi` dan `my_spasi`).
Yang masih terbuka: latensi PaddleOCR - lihat **Titik sambung**.

Sudah ada: 35 foto uji uang sendiri di `data/uji_sendiri/` (1000 2, 2000 4, 5000 5, 10000 7, 20000 5, 50000 6,
100000 6). Dua latar: meja kayu dan dipegang di depan laptop. Berkas asli iPhone ada di `data/uji_sendiri/asli/`
(HEIC, sudah dikonversi; boleh dihapus).
**Label YOLO (diperbarui 22-10): 49 gambar, 48 label berisi, 0 kosong, ketujuh kelas**
(1000:4, 2000:8, 5000:7, 10000:10, 20000:7, 50000:6, 100000:6) di `data/label_sendiri/`.
Naik dari 29 label: 13 foto baru dari teman + 6 foto yang ternyata ada di
`data/uji_sendiri/` tetapi TIDAK PERNAH disalin ke folder dataset.
Empat foto dilabeli dengan memeriksa gambarnya satu per satu, karena kotak model
tidak bisa dipakai apa adanya (terlalu lebar, seluruh bingkai, atau lembar terlipat
yang dipecah jadi tiga). Rinciannya di `data/label_sendiri/BACA_DULU.txt`.
Satu foto SENGAJA tidak dilabeli: `5000_dipegang_ (3).jpeg` berisi DUA lembar
(5.000 dipegang + satu lembar lagi di meja). Menebak labelnya adalah persis
kesalahan yang dulu merusak dataset Roboflow.
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
  **diantre, bukan diparalelkan**.
- `MediaRecorder` menghasilkan webm/opus yang **tidak terbaca `soundfile`**. Didecode di
  peramban lewat `decodeAudioData` lalu dikemas ulang jadi WAV 16-bit (~25 baris, tanpa dependensi).
- Uji asap: `python server\smoke.py` (bukan pytest - memuat model sungguhan).
- Unggah berkas: gambar, PDF, DOCX. PDF/DOCX **berteks tidak di-OCR** sama sekali;
  OCR hanya untuk PDF hasil pindai. Hanya halaman pertama. Tanpa dependensi baru
  (`pypdfium2` sudah ikut paddlex, DOCX hanya zip berisi XML).

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

## Titik sambung (2 Oktober 2026)

566 tes lulus. Seluruh metrik PRD Bagian 11 kini sudah pernah diukur.

| Metrik | Hasil | Target | |
|---|---|---|---|
| Akurasi kedaluwarsa | **81%** (13 benar / 1 salah / 2 diam) | >= 70% | **TERCAPAI** |
| CER dokumen | 15,3% (9,0% pada 11 foto bagus) | <= 15% | meleset 0,3 poin |
| Akurasi uang (total diucapkan) | **68,0%** (k-fold, 50 foto, 22-10) | >= 85% | meleset 17 poin |
| Latensi uang / kendali | 1,4 s / 1,3 s | <= 8 s | **LOLOS** |
| Latensi dokumen / kedaluwarsa | 11,5 s / 11,4 s | <= 8 s | **penyimpangan diterima** |

**Konfigurasi terkunci (jangan diubah tanpa mengukur ulang):**
mesin OCR dipisah per modul - dokumen EasyOCR, kedaluwarsa PaddleOCR + `mobile_det`;
`expiry.preprocess_chain: hanya_resize` (resize WAJIB ada, ia pengendali latensi);
`resize.max_side: 1600`; `rotate_retry: [180, 90, 270]`; `zone_score_min: 0.40`.

**Kerja berikutnya, berurutan:**
1. **Modul uang 68,0% lawan target 85% (k-fold 50 foto, 22-10).** Model
   `money_kfold_v1_final` sudah dipasang. **Penghambatnya kini DIAM, bukan SALAH**:
   14 diam lawan 4 salah. Yang tersisa, berurutan dari termurah:
   a. **Sapu `money.score_min` pada model BARU** - belum pernah dilakukan. 28% foto tidak
      dijawab karena tidak ada deteksi di atas 0,40. Ini tuas termurah dan belum disentuh.
      Ukur benar/salah/diam, bukan hanya akurasi: menurunkan ambang menukar DIAM dengan
      BENAR **dan** SALAH.
   b. **Kelas terlemah: 5000 (0,29), 2000 (0,50), 100000 (0,50).** 20000 dan 50000 sempurna.
      Foto tambahan sebaiknya difokuskan ke tiga kelas lemah itu, bukan merata.
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
