# Isi Konten PPT Progres — SayIt

**Dibuat 5 November 2026.** Semua angka di sini terukur, bukan perkiraan.
Satu bagian = satu slide. Tinggal salin ke slide; teks sudah dipadatkan untuk dibaca dari jauh.

Sumber angka: `docs/status-proyek.md`, `docs/keputusan-teknis.md`, `CLAUDE.md`.

---

## Slide 1 — Judul

**SayIt**
Teknologi asistif berbasis Computer Vision dan suara untuk penyandang disabilitas netra

Progres Proyek · Pengolahan Citra dan Visi Komputer
TRPL — Sekolah Vokasi IPB · November 2026

*Nama anggota kelompok*

---

## Slide 2 — Apa itu SayIt (satu slide, jangan lebih)

> Pengguna **memotret**, **bertanya dengan suara**, lalu **mendengar jawabannya.**

Tiga kemampuan dalam satu alur — pengguna tidak memilih menu:

| Pertanyaan pengguna | Yang dijalankan |
| :--- | :--- |
| "ini uang berapa" | Nominal uang Rupiah, termasuk total beberapa lembar |
| "bacakan tulisannya" | Membacakan tulisan dokumen |
| "kapan kedaluwarsanya" | Membacakan tanggal kedaluwarsa kemasan |

Bentuknya **PWA** (web app yang bisa dipasang ke layar utama HP).
Frontend Next.js, backend Python FastAPI.

> **Poin bicara:** yang memilih fitur adalah *router intent* dari hasil suara —
> bukan tombol menu. Pengguna tunanetra tidak perlu mencari apa pun di layar.

---

## Slide 3 — Model apa dipakai di mana ⭐ (slide inti permintaan)

Alurnya berurutan dari suara masuk sampai suara keluar:

| # | Tahap | Model / Teknik | Tugasnya |
| :-- | :--- | :--- | :--- |
| 1 | Suara masuk | **faster-whisper `small`** (STT) | Ucapan → teks, Bahasa Indonesia |
| 2 | Memahami niat | Router aturan berbobot (**bukan** ML) | Menentukan fitur mana yang jalan |
| 3 | Pra-pemrosesan citra | **CLAHE, resize, koreksi perspektif, deskew** | Memperbaiki foto sebelum masuk model |
| 4 | **Uang** | **YOLOv8n** — `best_money.pt`, 7 kelas | Mendeteksi tiap lembar + mengenali nominalnya |
| 5 | **Kedaluwarsa, langkah 1** | **YOLOv8n** — `best_zone.pt` | Mencari **LETAK** tanggal di kemasan |
| 6 | **Kedaluwarsa, langkah 2** | **PaddleOCR** | **MEMBACA** angka tanggal di zona itu |
| 7 | **Dokumen** | **EasyOCR** | Membaca seluruh tulisan satu halaman |
| 8 | Suara keluar | **edge-tts** `id-ID-GadisNeural` | Membacakan jawaban |

**Dua hal yang wajib disebut, karena ini keputusan teknis kami sendiri:**

1. **Ada DUA model YOLO berbeda, bukan satu.** Satu mengenali *nominal uang*,
   satu lagi hanya mencari *di mana letak tanggal* pada kemasan — ia tidak membaca
   apa pun, hanya menunjuk tempat.
2. **Ada DUA mesin OCR berbeda, dipilih per modul karena terukur berbeda.**
   PaddleOCR menang jauh untuk cetakan kemasan (44% vs 19%), tetapi 7x lebih lambat;
   EasyOCR cukup dan jauh lebih cepat untuk dokumen biasa.

---

## Slide 4 — Hasil latih model uang (persentase) ⭐

**Riwayat akurasi: 65,7% → 68,8% → 84,0% → 90,1%**

| | Angka |
| :--- | :--- |
| Akurasi akhir | **90,1%** — 73 benar / 8 salah / 0 diam dari 81 foto |
| Target PRD | ≥ 85% → **TERCAPAI** |
| mAP@50 | 0,928 |
| Cara uji | Validasi silang **5-lipatan**, tiap foto diuji tepat sekali oleh model yang belum pernah melihatnya |
| Dataset | 81 foto hasil fotret sendiri, 7 kelas (Rp1.000 – Rp100.000) |
| Arsitektur | YOLOv8n, 100 epoch, dilatih di Google Colab |

**Gambar untuk slide ini sudah tersedia:**
- Grafik training (loss & mAP, 100 epoch) → `docs/jurnal_bahan/grafik_training.png`
- Confusion matrix → `docs/jurnal_bahan/val_sendiri/conf030/confusion_matrix.png`
- Kurva PR → `docs/jurnal_bahan/val_sendiri/conf030/BoxPR_curve.png`
- Contoh prediksi benar/salah/diam → `docs/jurnal_bahan/contoh_prediksi/`

> **Poin bicara yang bagus (dan jujur):** lompatan terakhir 84,0% → 90,1%
> **bukan** karena modelnya diperbaiki, melainkan karena **alat ukurnya** yang salah
> diperbaiki. Evaluasi lama belum menerapkan aturan pembuangan kotak bersarang,
> sehingga lima kesalahan "1 lembar dihitung 2 lembar" hilang seluruhnya.

---

## Slide 5 — Hasil ketiga fitur vs target PRD

| Metrik | Hasil | Target | Status |
| :--- | :--- | :--- | :--- |
| Akurasi nominal uang | **90,1%** (73 / 8 salah / 0 diam dari 81) | ≥ 85% | **TERCAPAI** |
| Akurasi tanggal kedaluwarsa | **81%** (13 / 1 salah / 2 diam dari 16) | ≥ 70% | **TERCAPAI** |
| CER dokumen | **14,89%** | ≤ 15% | **TERCAPAI** |
| Latensi uang / perintah suara | 1,4 s / 1,3 s | ≤ 8 s | **LOLOS** |
| Latensi dokumen / kedaluwarsa | 11,5 s / 11,4 s | ≤ 8 s | menyimpang, dicatat |
| Tes otomatis | **685 lulus** | semua lulus | **LOLOS** |

**Keempat metrik akurasi utama sudah tercapai.**

> **Jangan dilewatkan — ini nilai tambah di mata penguji:** kami tidak pernah
> melaporkan satu persentase saja, selalu **benar / salah / diam**. Bagi pengguna
> tunanetra, jawaban yang **salah** jauh lebih berbahaya daripada sistem yang **diam**,
> karena ia tidak punya cara memeriksanya.

---

## Slide 6 — Tampilan: alur lima layar

Satu alur lurus, tanpa menu:

```
[1] Kamera  →  [2] Memproses  →  [3] Pertanyaan  →  [4] Memproses  →  [5] Hasil
   ketuk           "sedang           tahan tombol        jawaban
   layar            saya              lalu bicara        dibacakan
   memotret         proses"
```

Yang terlihat di layar:

- **Orb** — satu bola bercahaya dari partikel, hadir di **semua** layar. Ia berdenyut
  saat mendengarkan dan saat berbicara, jadi pengguna low vision tahu sistem hidup.
- **Seluruh layar adalah tombol** — bukan tombol kecil. Pengguna tidak perlu membidik.
- Layar hasil: foto di atas → orb → kotak jawaban → tiga tombol (Ulangi, Lanjut, Foto Lagi).

Aturan aksesibilitas yang dikunci di kode:

1. Setiap jawaban **diucapkan** *dan* masuk wilayah `aria-live` (untuk pembaca layar).
2. Setiap peringatan wajib **berbunyi**, dan wajib menyebut **tindakan berikutnya** —
   bukan hanya kesalahannya.
3. **Barge-in**: sentuh layar untuk memotong suara yang sedang berbicara.
4. Zoom **tidak** dikunci (mengunci zoom melanggar WCAG 1.4.4).

> ⚠️ **Tangkapan layar aplikasi BELUM ADA sebagai berkas.** Perlu difoto/di-screenshot
> dari HP sendiri sebelum slide ini bisa diisi gambar. Lihat catatan di bawah.

---

## Slide 7 — Yang masih dikembangkan: SUARA

| Hal | Kondisi sekarang | Rencana |
| :--- | :--- | :--- |
| **Latensi dokumen & kedaluwarsa** | 11,4–11,5 detik, target PRD ≤ 8 detik | Pembacaan bertahap: OCR bagian atas dulu, bacakan, lanjutkan |
| **Jeda pertama TTS** | Sintesis pertama tiap proses ~9 detik (edge-tts membangun sesi) | Sudah ditangani `warmup()` saat server mulai — tetapi kalau start tanpa internet, 9 detik itu jatuh di pembacaan pertama pengguna |
| **Suara masuk baru 1 penutur** | Akurasi STT diukur dari satu orang saja | Rekam penutur lain; akurasi router pada kalimat baru masih optimistis |
| **Urutan bacaan foto buku** | Masih kacau — halaman buku **melengkung**, satu angka kemiringan tidak cukup | Butuh teks acuan 4–5 foto buku untuk menguncinya dengan angka |

**Tiga tuas percepatan sudah dicoba dan semuanya GAGAL** (ini temuan, bukan kemalasan):
perkecil gambar ke 800 px → akurasi 81% jatuh ke 56% **dan** latensi malah naik;
matikan rotasi → akurasi −12%; matikan jalur zona → latensi 11,4 s jadi 27,3 s.

---

## Slide 8 — Yang masih dikembangkan: UI / Antarmuka

| Hal | Kondisi sekarang | Rencana |
| :--- | :--- | :--- |
| **Tangkapan layar & video demo** | **BELUM ADA** | Rekam dari HP sendiri |
| **Uji pengguna sungguhan** | **BELUM ADA** | Uji pengguna proksi: teman bermata tertutup, 5 tugas + kuesioner SUS |
| **Deploy frontend ke Vercel** | Belum | Frontend ke Vercel; backend tetap di laptop lewat tunnel ngrok |
| **Urutan fokus keyboard & label widget** | Di luar kendali kami (komponen Streamlit pada panel uji) | Hanya memengaruhi panel uji internal, bukan aplikasi pengguna |

**Arsitektur deploy** (penting disebut, karena sering ditanya):

```
web/      Next.js PWA   →  Vercel (gratis)
server/   FastAPI       →  laptop sendiri + ngrok
```

Backend **tidak bisa** masuk Vercel: torch 531 MB + paddle 400 MB + cv2 158 MB,
sedangkan batas serverless function Vercel 250 MB.

---

## Slide 9 — Rencana ke depan (urutan kerja)

1. **Uji pengguna proksi + kuesioner SUS** — 5 tugas, teman bermata tertutup
2. **Tangkapan layar + video demo** untuk laporan dan presentasi akhir
3. **Teks acuan foto buku** → mengunci perbaikan urutan bacaan
4. **Deploy frontend ke Vercel** + uji dari HP sendiri
5. **Fase 5:** laporan akhir, README, video demo, slide final

---

## Slide 10 — Penutup (opsional, kalau butuh satu kalimat)

> Keempat metrik akurasi PRD sudah tercapai. 685 tes otomatis lulus.
> Yang tersisa adalah **pengujian oleh manusia** dan **pelaporan** — bukan lagi akurasi model.

---

# Catatan untuk kamu (jangan masuk slide)

**1. Satu angka yang WAJIB tidak salah tulis di slide.**
Jangan tulis bahwa **pra-pemrosesan meningkatkan akurasi** — datanya tidak mendukung.
Pada 13 dokumen hasilnya **netral** (15,2% dengan, 14,5% tanpa), dan pada modul
kedaluwarsa dengan PaddleOCR ia malah **merugikan −12%**. Yang benar-benar menaikkan
angka adalah perbaikan pengelompokan baris dan perbaikan alat ukur.

Temuan yang justru paling menarik untuk mata kuliah ini, dan layak jadi satu baris di slide:
**"nilai pra-pemrosesan berbalik arah tergantung mesin OCR"** — EasyOCR dibantu +6%,
PaddleOCR dirugikan −12%. Jadi "apakah pra-pemrosesan membantu" tidak punya satu jawaban.

**2. Angka yang sudah USANG — jangan dipakai lagi kalau ketemu di draf lama:**
65,7% · 68,8% · 87,5% · 84,0% (akurasi uang) · 15,3% (CER) · 648 tes · 566 tes.

**3. Gambar yang sudah siap pakai** ada di `docs/jurnal_bahan/`:
grafik training, confusion matrix, kurva PR/F1, contoh prediksi benar/salah/diam.

**4. Yang belum ada dan hanya kamu bisa buat:** tangkapan layar aplikasi.
Slide 6 butuh ini. Caranya: jalankan `cd web; npm run dev`, buka dari HP lewat ngrok,
lalu screenshot kelima layar.
