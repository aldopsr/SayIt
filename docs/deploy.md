# Deploy SayIt — langkah dan posisi sekarang

Arsitektur: **frontend di Vercel, backend di laptop sendiri lewat tunnel ngrok.**

Vercel tidak bisa memuat backend-nya — torch 531 MB + paddle 400 MB + cv2 158 MB,
sedangkan batas serverless function Vercel 250 MB, dan timeout-nya jauh di bawah
median pipeline kedaluwarsa 11,4 detik.

```
web/        Next.js PWA    -> Vercel (gratis, Hobby, non-komersial)
server/     FastAPI         -> laptop sendiri, dibuka lewat `ngrok http 8000`
sayit/      Pipeline yang dibungkus server
```

**Hugging Face Spaces DICORET (diperiksa 11-10).** Halaman harga resmi HF kini
mencantumkan "Host ZeroGPU, Gradio & Docker Spaces" sebagai keuntungan **PRO
9 dolar/bulan**. Perangkat kerasnya masih gratis (`CPU Basic — 2 vCPU, 16 GB,
FREE`) tetapi SDK Docker-nya digerbangi langganan. Alasan kedua yang berdiri
sendiri: 2 vCPU lawan i7-13650HX 14 inti akan **memperburuk** latensi 11,4 detik
yang sudah kita catat menyimpang dari NFR-01. `Dockerfile` dibiarkan di repo
untuk kalau nanti pindah host, tetapi tidak dipakai.

---

## Posisi sekarang (11 Oktober 2026)

- [x] `server/app.py` — diuji end-to-end lewat `python server\smoke.py`
- [x] `web/` — Next.js, build lolos, jalur teks terverifikasi di peramban
- [x] `Dockerfile` — ADA tetapi TIDAK DIPAKAI (lihat catatan HF di atas)
- [x] `.gitignore` — 98 berkas / 1,1 MB; `.venv`, `data/`, `models/*.pt`,
      dan `fase0/fase0_hasil/` (suara orang) tidak ikut
- [x] **push ke GitHub** — https://github.com/aldopsr/SayIt
- [x] basis API bisa diganti saat jalan lewat `?api=` (diuji lewat tunnel sungguhan)
- [x] **alur pasang ke layar utama** — `?install=1`, tiga cabang (prompt / iOS / manual),
      seluruhnya diucapkan; diverifikasi di aplikasi berjalan
- [ ] deploy frontend ke Vercel sebagai `sayit-app` — Langkah 3 (butuh akun kamu)
- [ ] domain statis ngrok + `start_url` manifest — Langkah 3.3 (butuh dashboard ngrok kamu)
- [ ] `NEXT_PUBLIC_PWA_URL` di proyek landing page — Langkah 3.4
- [ ] uji dari HP sendiri — hanya kamu yang bisa

Jalankan lokal: `.claude/launch.json` punya `api` (port 8000) dan `web` (port 3000).

---

## Langkah 1 — GitHub

Git repo sudah di-`init` di root `sayit/`. **Yang di-push seluruh folder `sayit`**,
bukan `web/` saja: `web/` butuh `server/` dan `sayit/`, dan notebook serta laporan
ikut dinilai.

`user.name` belum diset, jadi author-nya akan jadi `unknown`. Set sekali:

```bash
git config --global user.name "aldopsr"
git config --global user.email "email-kamu@contoh.com"   # ganti dengan email akun GitHub-mu
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

## Langkah 2 — Backend: laptop sendiri + tunnel

`ngrok` **sudah terpasang** (3.35.0) dan authtoken-nya sudah diset, jadi tidak ada
yang perlu dipasang atau didaftarkan.

Tiga perintah, tiga jendela:

PowerShell tidak mengenal `&&`, dan venv tidak perlu diaktifkan sama sekali:

```powershell
.venv\Scripts\uvicorn.exe server.app:app --port 8000
```

```powershell
cd web; npm run dev
```

```powershell
ngrok http 3000
```

**Satu tunnel ke port 3000, bukan 8000.** Rewrite Next berjalan di laptop dan
meneruskan `/api` ke port 8000 secara lokal, jadi backend ikut lewat tunnel yang
sama dan `?api=` tidak diperlukan untuk uji lokal.

ngrok mencetak URL seperti `https://expansive-surely-iodine.ngrok-free.dev`.
**URL itu berganti setiap kali ngrok dijalankan ulang.**

### Kenapa URL-nya tidak lagi menjadi masalah

`API_ORIGIN` ikut dibangun saat deploy Vercel, jadi dulu setiap URL baru berarti
deploy ulang. Sekarang basis API bisa diganti **saat jalan**:

```
https://sayit.vercel.app/?api=https://expansive-surely-iodine.ngrok-free.dev
```

Basis itu diingat di `localStorage`, jadi cukup sekali per perangkat.
`?api=` kosong mengembalikannya ke bawaan.

**Hanya host tunnel yang diterima** (`ngrok-free.dev`, `ngrok-free.app`,
`ngrok.app`, `trycloudflare.com`). Ini daftar putih, bukan kenyamanan: tautan
berisi `?api=` bisa dikirim siapa saja, dan foto serta rekaman suara pengguna
akan dikirim ke host itu. Sudah diuji — `?api=https://jahat.example.com`
diabaikan dan tidak disimpan.

### Jebakan ngrok gratis yang sudah menggigit

ngrok gratis membalas **halaman peringatan `ERR_NGROK_6024`** untuk GET yang
tampak datang dari peramban. Terbukti saat diuji:

| Permintaan | Hasil |
|---|---|
| UA peramban, tanpa header (persis elemen `<audio>`) | `ERR_NGROK_6024`, 236 bita teks |
| dengan `ngrok-skip-browser-warning` lewat `fetch` | MP3 asli, 165.696 bita |
| POST (semua endpoint) | lolos, tidak kena |

Elemen `<audio>` **tidak bisa** mengirim header, hanya `fetch` yang bisa. Jadi
klip `sambutan` dan `sedang_memproses` diambil lewat `fetch` berheader lalu
diputar sebagai blob URL. Diambil saat halaman dibuka, **bukan** saat disentuh:
memanggil `fetch` di dalam penangan gestur membuat `play()` kehilangan konteks
gestur, dan iOS memblokirnya.

Kalau ini tidak diperbaiki, gejalanya tepat yang paling buruk: **klip sambutan
bisu**, yaitu satu-satunya pintu masuk pengguna tunanetra.

---

## Langkah 3 - Frontend ke Vercel sebagai `sayit-app`

Keputusan 20-11 (**pilihan A**): landing page dan PWA ini menjadi **dua proyek
Vercel dari dua repo**. Alasannya bukan selera - peramban hanya mengizinkan
sebuah situs memasang DIRINYA SENDIRI, jadi landing page tidak akan pernah bisa
memasang PWA ini walau digabung dalam satu proyek. Yang bisa ia lakukan hanya
mengalihkan ke sini.

### 3.1 Buat proyeknya

1. vercel.com -> **Add New -> Project** -> impor `aldopsr/SayIt`.
2. **Project Name: `sayit-app`** (menghasilkan `https://sayit-app.vercel.app`).
3. **Root Directory: `web`** - ini yang paling sering salah. Repo ini bukan
   repo Next.js; `web/` hanya salah satu foldernya.
4. Framework Preset: Next.js (terdeteksi sendiri setelah Root Directory benar).
5. Deploy.

### 3.2 Basis API: pilih jalur LANGSUNG, bukan rewrite

Ada dua jalur ke backend, dan di Vercel keduanya TIDAK setara:

| jalur | lewat mana | batas waktu |
|---|---|---|
| `API_ORIGIN` (rewrite `/api/*`) | peramban -> **proksi Vercel** -> ngrok -> laptop | **120 detik**, batas Vercel |
| `?api=<host ngrok>` | peramban -> ngrok -> laptop | tidak ada batas proksi |

**Pakai jalur langsung untuk aplikasi ini.** Sebabnya terukur: foto kedaluwarsa
terburuk memakan **99,2 detik** (p90 72,9 detik) karena percobaan rotasi. Itu
muat di dalam 120 detik, tetapi marginnya hanya 20% pada laptop pengembang -
satu foto yang lebih berat akan menembusnya, dan gejalanya persis yang paling
menyesatkan: server menjawab 200 dengan benar sementara proksi sudah menyerah
(`ROUTER_EXTERNAL_TARGET_ERROR`), lalu klien mengumumkan "tidak bisa menghubungi
server" padahal servernya baik-baik saja.

Catatan: `proxyTimeout: 180_000` di `web/next.config.mjs` **tidak menolong di
Vercel** - batas 120 detik milik Vercel lebih ketat dan dialah yang menang. Nilai
itu tetap berguna saat dijalankan sendiri (`npm run dev` / `next start`).

CORS tidak jadi masalah di jalur langsung: `server/app.py` sudah memasang
`CORSMiddleware` dengan `allow_origins=["*"]`. (Catatan lama "CORS tidak
dibutuhkan sama sekali" hanya benar untuk jalur rewrite.)

### 3.3 Domain ngrok TERNYATA SUDAH STATIS - catatan lama di berkas ini keliru

Bagian "Jebakan tunnel" di atas menulis URL ngrok berganti tiap restart. **Itu
terbantah buktinya sendiri**: hostname `expansive-surely-iodine.ngrok-free.dev`
tercatat di berkas ini pada **11 Oktober** dan masih dipakai pada **20 November**
- enam minggu, tanpa berubah. Paket gratis ngrok memang memberi satu domain yang
ditetapkan otomatis dan tetap; yang tidak tetap adalah URL yang didapat kalau
`--url` tidak diberikan.

Jalankan backend begini supaya domainnya selalu yang itu:

```powershell
ngrok http 8000 --url=expansive-surely-iodine.ngrok-free.dev
```

Karena domainnya tetap, `web/public/manifest.json` sekarang memuatnya di
`start_url`:

```json
"start_url": "/?api=https://expansive-surely-iodine.ngrok-free.dev",
```

Alasannya: **PWA terpasang diluncurkan di `start_url`**, dan tanpa parameter itu
ia bergantung sepenuhnya pada localStorage - yang pada pemasangan baru masih
KOSONG, karena pengguna datang lewat `?install=1` tanpa `?api=`. Dengan parameter
di manifest, aplikasi terpasang selalu membawa basis API-nya sendiri sejak
peluncuran pertama, dan permintaannya langsung ke ngrok tanpa melewati batas 120
detik milik proksi Vercel.

**Harga yang harus diketahui:** tiap peluncuran dari ikon menulis ulang nilai ini
ke localStorage. Kalau suatu saat domain ngrok benar-benar berganti, `?api=` yang
ditempel manual hanya bertahan sampai peluncuran berikutnya dari ikon - nilai
manifest akan menimpanya lagi. Yang benar saat itu: ubah manifest lalu deploy
ulang. Host-nya tetap diperiksa daftar putih `API_DIIZINKAN` di `web/app/page.js`.

### 3.4 Variabel yang harus diisi di kedua proyek

Deploy sungguhan 20-11 menghasilkan nama dengan akhiran, bukan nama polos:

| proyek | URL | variabel | nilai |
|---|---|---|---|
| PWA (repo ini, root `web`) | `https://sayit-app-phi.vercel.app` | `API_ORIGIN` | `https://expansive-surely-iodine.ngrok-free.dev` |
| Landing page (repo rekan tim) | `https://sayit-web-three.vercel.app` | `NEXT_PUBLIC_PWA_URL` | `https://sayit-app-phi.vercel.app` |

- `API_ORIGIN` **tanpa** awalan `NEXT_PUBLIC_`: dibaca di sisi server oleh
  `next.config.mjs`. Ia adalah **jaring pengaman** untuk kunjungan polos
  (`https://sayit-app-phi.vercel.app/` tanpa `?api=` dan tanpa localStorage);
  tanpa itu rewrite jatuh ke `http://127.0.0.1:8000`, yang di server Vercel
  berarti localhost milik Vercel dan selalu gagal.
- `NEXT_PUBLIC_PWA_URL` **wajib** berawalan `NEXT_PUBLIC_`: `install-pwa.tsx`
  komponen klien, dan tanpa awalan itu nilainya tidak sampai ke peramban
  sehingga tombol Install mengarah ke bawaan `https://app.sayit.id` yang tidak
  dimiliki siapa pun di tim.
- **Keduanya butuh deploy ulang setelah disimpan.** `rewrites()` dievaluasi saat
  build, dan `NEXT_PUBLIC_*` dipanggang ke dalam bundel klien saat build.

Jadi ada DUA jalur ke backend, dan itu disengaja: aplikasi terpasang memakai
`?api=` langsung (cepat, tanpa batas 120 detik), kunjungan polos memakai rewrite
lewat `API_ORIGIN` (lebih lambat batasnya, tetapi jauh lebih baik daripada gagal).

### 3.5 Alur yang dihasilkan

1. Pengguna menekan **Install SayIt** di landing page.
2. Modal menjelaskan izin yang akan diminta, lalu mengalihkan ke
   `https://sayit-app.vercel.app/?install=1`.
3. Aplikasi ini menangkap `?install=1` dan menampilkan panel pasang, **sambil
   mengucapkannya** lewat `peringatkan()` - bukan hanya menampilkan.
4. Android/Chrome: tombol **Pasang SayIt** memicu dialog pasang asli.
   iPhone: tidak ada dialog apa pun (Safari tidak mendukung
   `beforeinstallprompt`, WebKit bug 255716), jadi yang diucapkan adalah langkah
   Bagikan -> Tambah ke Layar Utama.
   Peramban lain yang tidak mengirim eventnya: petunjuk menu peramban.
5. Selalu ada **Lanjut tanpa memasang** supaya pengguna tidak terkunci.

**Di iPhone alurnya TIDAK pernah otomatis**, dan itu batas Safari, bukan sesuatu
yang bisa diperbaiki dari sisi kita. Uji di Android dulu.

Saat panel pasang tampil, seluruh layar lain dibuat `inert` - termasuk tombol
rana, senter, unggah, dan balik kamera. Sudah diverifikasi pada aplikasi berjalan
dengan kamera palsu: 9 tombol terlihat, **1 yang bisa difokus**, dan wilayah
`aria-live` berada di luar seluruh subtree `inert`.

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

- **Endpoint baru butuh server API dijalankan ulang.** Uji asap `TestClient` membuat
  app baru di dalam proses, jadi ia LULUS sementara proses uvicorn yang hidup masih
  404 untuk rute baru. Gejalanya di klien dulu muncul sebagai "gagal menghubungi
  server" - pesan yang salah, karena servernya terjangkau dan hanya rutenya belum ada.
- **Jangan jalankan `npm run build` selagi `next dev` hidup.** Keduanya memakai `.next/`,
  dan build menimpa manifes chunk milik dev server. Gejalanya halus: halaman tetap
  tampil tetapi React tidak pernah hydrate, jadi tidak ada tombol yang bereaksi dan
  konsol hanya menunjukkan 404. Perbaikannya `rm -rf .next` lalu jalankan ulang.
- Uji asap API: `python server\smoke.py` — menjalankan alur lengkap dengan model sungguhan.

## Unggah berkas

Selain kamera, pengguna bisa memilih berkas dari penyimpanan (`POST /berkas`).

| Jenis | Perlakuan |
|---|---|
| Gambar (jpg, png, heic, webp, bmp) | Sama persis dengan foto kamera: quality gate lalu jalur visi |
| PDF **berteks** | Teks diambil langsung dari lapisan teksnya, **tanpa OCR** |
| PDF **hasil pindai** | Halaman pertama dirender (skala 2x, ~144 dpi) lalu di-OCR |
| DOCX | Teks diambil dari `word/document.xml`, **tanpa OCR** |

Alasan PDF dan DOCX berteks tidak di-OCR: teksnya sudah akurat, dan meng-OCR hasil
render justru lebih lambat sekaligus lebih banyak salah baca. OCR dipakai hanya
ketika memang tidak ada pilihan lain.

Hanya **halaman pertama** yang dibaca. Modul dokumen sudah membacakan per potongan
40 kata; membaca seluruh PDF sekaligus membuat pengguna menunggu tanpa guna.

Tidak ada dependensi baru: `pypdfium2` sudah ikut terpasang bersama paddlex, dan
DOCX hanya zip berisi XML sehingga cukup ditangani pustaka standar.

Berkas rusak, `.doc` lama, dan jenis yang tidak didukung dijawab dengan pesan dalam
bahasa pengguna, bukan galat 500 — pesannya langsung bisa dibacakan.

Berkas gambar yang sah tetapi mutunya ditolak quality gate **tidak** memindahkan
pengguna ke tahap bertanya, dan klip mutunya disambung `berkas_lain` karena
"coba foto ulang" adalah saran yang salah bagi orang yang baru memilih berkas.

## Peringatan: semuanya diucapkan, semuanya menyebut jalan keluar

Penggunanya tunanetra, jadi peringatan yang hanya tampil di layar sama saja dengan
tidak terkirim. Dua mekanisme, dipilih berdasarkan **siapa yang tahu masalahnya**:

| Sumber | Mekanisme | Alasan |
|---|---|---|
| Server (berkas tak didukung, berkas rusak, mutu foto) | klip gTTS, dikirim sebagai `audio` di badan respons yang sama | kualitas suaranya sudah dipilih tim, dan tidak ada perjalanan jaringan tambahan |
| Klien (kamera/mikrofon ditolak, server tak terjangkau, rekaman terlalu pendek) | `speechSynthesis` bawaan peramban, `lang="id-ID"` | sebagian peringatan ini muncul **justru ketika servernya tidak terjangkau**, jadi klip tidak bisa diandalkan |

Klip dipakai bila ada; `speechSynthesis` hanya cadangan, jadi satu peringatan tidak
pernah berbunyi dua kali. Teks yang sama tetap masuk wilayah `aria-live` untuk
pembaca layar.

Tiap kalimat wajib menyebut **tindakan berikutnya**, bukan hanya kesalahannya:

| Keadaan | Jalan keluar yang diucapkan |
|---|---|
| Kamera ditolak | buka pengaturan izin, muat ulang — **dan** sementara itu pakai tombol pilih berkas |
| Mikrofon ditolak | buka pengaturan izin — **atau** ketik pertanyaan di kotak teks |
| Kamera belum siap | tunggu lalu sentuh lagi; kalau tetap gagal, pilih berkas |
| Server tak terjangkau | periksa koneksi, lalu coba lagi |
| Server menjawab galat | coba sekali lagi, atau pilih berkas lain (**bukan** disuruh periksa internet) |
| Rekaman terlalu pendek | tahan tombolnya sampai selesai bicara, baru lepas |
| Suara tak terbaca | bicara lebih dekat ke mikrofon, atau ketik pertanyaan |

Kamera gagal sebelum ada gestur pengguna, dan iOS memblokir `speechSynthesis`
sebelum gestur — jadi peringatan kamera **menunggu sentuhan pertama**, lalu
diucapkan menggantikan sambutan (sambutan akan menyesatkan karena menyuruh memotret).
