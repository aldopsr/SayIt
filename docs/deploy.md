# Deploy SayIt — langkah dan posisi sekarang

Arsitektur: **frontend di Vercel, backend di Hugging Face Spaces.**
Vercel tidak bisa memuat backend-nya — torch 531 MB + paddle 400 MB + cv2 158 MB,
sedangkan batas serverless function Vercel 250 MB, dan timeout-nya 10 detik
sementara pipeline kedaluwarsa median 11,4 detik.

```
web/        Next.js PWA   -> Vercel
server/     FastAPI        -> Hugging Face Spaces (Dockerfile di root)
sayit/      Pipeline yang dibungkus server
```

---

## Posisi sekarang (11 Oktober 2026)

- [x] `server/app.py` — diuji end-to-end lewat `python server\smoke.py`
- [x] `web/` — Next.js, build lolos, jalur teks terverifikasi di peramban
- [x] `Dockerfile` untuk HF Spaces
- [x] `.gitignore` — 98 berkas / 1,1 MB; `.venv`, `data/`, `models/*.pt`,
      dan `fase0/fase0_hasil/` (suara orang) tidak ikut
- [ ] **push ke GitHub** — lihat Langkah 1
- [ ] deploy backend ke HF Spaces — Langkah 2
- [ ] deploy frontend ke Vercel — Langkah 3

Jalankan lokal: `.claude/launch.json` punya `api` (port 8000) dan `web` (port 3000).

---

## Langkah 1 — GitHub

Git repo sudah di-`init` di root `sayit/`. **Yang di-push seluruh folder `sayit`**,
bukan `web/` saja: `web/` butuh `server/` dan `sayit/`, dan notebook serta laporan
ikut dinilai.

`user.name` belum diset, jadi author-nya akan jadi `unknown`. Set sekali:

```bash
git config --global user.name "aldopsr"
git config --global user.email "mochammadalthofsr@gmail.com"
```

Lalu dari root `sayit/`:

```bash
git add -A
git commit -m "SayIt: pipeline visi-suara, API FastAPI, dan PWA Next.js"
gh repo create sayit --private --source=. --remote=origin --push
```

Periksa author-nya benar sebelum lanjut:

```bash
git log -1 --format='%an <%ae>'
```

---

## Langkah 2 — Backend di Hugging Face Spaces

1. Buat Space baru: SDK **Docker**, visibility bebas.
2. Push isi repo ini ke Space (atau hubungkan dari GitHub).
3. **Bobot model tidak ikut Git** (`models/*.pt`, 130 MB). Unggah manual ke repo
   Space lewat antarmuka web atau `git lfs`:
   - `models/best_money.pt`
   - `models/best_zone.pt`
4. Space akan jalan di port 7860. Catat URL-nya, misalnya
   `https://aldopsr-sayit.hf.space`.

Pemuatan model ~10 detik saat Space pertama bangun. Free tier tidur setelah tidak
dipakai, jadi permintaan pertama setelah tidur akan lambat.

---

## Langkah 3 — Frontend di Vercel

```bash
cd web
npx vercel --prod
```

Set satu environment variable di Vercel:

| Nama | Nilai |
|---|---|
| `API_ORIGIN` | URL Space dari Langkah 2 |

`next.config.mjs` me-rewrite `/api/*` ke `API_ORIGIN`, jadi frontend dan backend
satu origin — tidak perlu CORS sama sekali.

---

## Uji setelah deploy

Kamera dan mikrofon **hanya jalan di HTTPS**, dan panel uji memblokir akses
perangkat — jadi ini hanya bisa kamu lakukan sendiri di HP:

1. Buka URL Vercel di HP, izinkan kamera dan mikrofon.
2. Arahkan ke uang, **tahan** tombol, ucapkan "berapa nilai uang ini", lepas.
3. Jawaban harus terdengar, bukan hanya tampil.
4. Ulangi untuk dokumen dan kemasan.
5. Nyalakan TalkBack (Android) atau VoiceOver (iOS) dan ulangi tanpa melihat layar —
   ini yang sebenarnya diuji, karena penggunanya tunanetra.

Catatan: jawaban dokumen memakai gTTS langsung, jadi butuh internet di sisi server.

---

## Alur aplikasi (web)

State machine di `web/app/page.js`, klip suaranya di `sayit/response/templates.py`.

| Fase | Yang terjadi | Klip |
|---|---|---|
| `mulai` | Sentuh layar di mana saja. Browser memblokir autoplay sampai ada gestur, jadi sambutan menunggu sentuhan pertama. | `sambutan` |
| `foto` | Sentuh layar **di mana saja** untuk memotret. `POST /foto` memeriksa mutunya. | `foto_diambil`, atau `foto_buram` / `foto_gelap` / `foto_terang` / `foto_kecil` bila ditolak |
| `proses` | Menunggu. Lewat 2 detik, penanda suara diputar. | `sedang_memproses` |
| `tanya` | Tahan tombol lalu bicara, lepas untuk mengirim. Ada juga kotak teks. | — |
| jawaban | `POST /tanya` menjawab, dan tawaran langkah berikutnya **disambung ke audio yang sama** supaya tidak ada jeda. | jawaban + `tindak_lanjut` |
| tindak lanjut | Router mengenali `ULANGI`, `FOTO_BARU`, `KELUAR`. Klien pindah fase sesuai intent. | `sampai_jumpa` untuk KELUAR |

Foto yang ditolak quality gate **tidak** memindahkan fase: pengguna tetap di `foto`
dan mendengar alasannya.

`KELUAR` mengembalikan tampilan ke `mulai` — web tidak bisa menutup tabnya sendiri.

## Jebakan saat mengembangkan

- **Jangan jalankan `npm run build` selagi `next dev` hidup.** Keduanya memakai `.next/`,
  dan build menimpa manifes chunk milik dev server. Gejalanya halus: halaman tetap
  tampil tetapi React tidak pernah hydrate, jadi tidak ada tombol yang bereaksi dan
  konsol hanya menunjukkan 404. Perbaikannya `rm -rf .next` lalu jalankan ulang.
- Uji asap API: `python server\smoke.py` — menjalankan alur lengkap dengan model sungguhan.
