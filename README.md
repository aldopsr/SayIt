# SayIt

Teknologi asistif berbasis Computer Vision dan suara untuk penyandang disabilitas netra.
Pengguna memotret, bertanya dengan suara, lalu mendengar jawabannya.

Tiga kemampuan: **nominal uang Rupiah** (termasuk total beberapa lembar),
**membacakan tulisan dokumen**, dan **membacakan tanggal kedaluwarsa kemasan**.

- Persyaratan: `docs/PRD_SayIt_v2_1.md`
- **Baru di proyek ini? Mulai dari `docs/pencerdasan.md`**
- Status proyek terkini: `docs/status-proyek.md`
- Catatan keputusan beserta angkanya: `docs/keputusan-teknis.md`
- Langkah deploy: `docs/deploy.md`
- Perubahan UI web terakhir beserta angkanya: `docs/perubahan-ui-web.md`
- Konteks untuk Claude Code: `CLAUDE.md`

---

## Mau ubah UI saja? Tidak perlu Python.

Ini jalur untuk anggota tim yang mengerjakan tampilan. Cuma butuh **Node.js**.

```bash
cd web
npm ci
npm run dev
```

Buka `http://localhost:3000`. Halaman langsung tampil dan bisa diubah-ubah
(simpan berkas, halaman menyegarkan sendiri).

Yang diubah hampir semuanya ada di dua berkas:

| Berkas | Isi |
| :--- | :--- |
| `web/app/page.js` | seluruh tampilan dan alurnya, satu komponen |
| `web/app/globals.css` | warna merek (`--jingga`, `--hitam`), kelas `.sr`, mode gerak-dikurangi |

**Tanpa backend, buka `http://localhost:3000/?demo=1`.** Seluruh alur berjalan
sampai layar selesai, memakai suara edge-tts yang sama dengan aplikasi penuh dan
tanpa memanggil `/api` sama sekali. Jawabannya karangan dan latensinya
dibuat-buat, jadi jangan dipakai menilai akurasi atau kecepatan; ada penanda
merah di layar supaya tidak tertukar dengan hasil sungguhan. Berkas suaranya
dibuat ulang dengan `python scripts/buat_demo_suara.py`.

Tanpa `?demo=1` dan tanpa backend, tombol-tombolnya akan menjawab "Tidak bisa
terhubung ke SayIt". Itu normal. Untuk melihat jawaban sungguhan, ada dua
pilihan:

**Pilihan A — pakai backend orang lain (paling cepat).** Minta URL ngrok dari
anggota tim yang sedang menjalankan servernya, lalu buka:

```
http://localhost:3000/?api=https://xxxx.ngrok-free.dev
```

URL itu diingat di `localStorage`, jadi cukup sekali. `?api=` kosong
mengembalikannya ke bawaan. Hanya host tunnel yang diterima — lihat
`docs/deploy.md` untuk alasannya.

**Pilihan B — jalankan backend sendiri.** Lihat bagian berikutnya. Butuh
Python 3.11, ~2,5 GB dependensi, dan bobot model yang tidak ikut Git.

### Aturan tampilan yang tidak boleh dilanggar

Penggunanya tunanetra, jadi ini bukan selera:

1. **Setiap peringatan wajib berbunyi**, bukan hanya tampil, dan wajib menyebut
   **tindakan berikutnya** — bukan hanya kesalahannya. Pakai `peringatkan()`,
   jangan `setGalat()` langsung.
2. Setiap jawaban masuk wilayah `aria-live` (elemen `<p className="sr">`).
   Jangan hapus elemen itu walau tidak terlihat.
3. Area sentuh utama adalah **seluruh layar**, bukan tombol kecil. Satu
   pengecualian: ketukan selagi sistem bicara hanya **menyela**, tidak memotret —
   kalau digabung, menyela sambutan di layar kamera selalu berarti ikut memotret
   sebelum penggunanya sempat membidik. Memotret tetap bisa lewat tombol rana
   yang berlabel "Ambil foto".
4. Hormati `prefers-reduced-motion` (sudah ada di `globals.css`).
5. Setiap teks yang tampil wajib sama dengan yang diucapkan. Kalau mengubah
   kalimat, ubah keduanya.

---

## Menjalankan seluruh sistem

### Backend (Python)

Windows, Python **3.11**, Command Prompt di folder `sayit`:

```bat
py -V:3.11 -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python -m pytest -q
```

Yang **tidak ikut Git** dan harus diminta ke anggota tim:

| Berkas | Isi |
| :--- | :--- |
| `models/best_money.pt` | bobot YOLO nominal uang |
| `models/best_zone.pt` | bobot YOLO zona tanggal |
| `data/` | foto uji |

Bobot EasyOCR dan PaddleOCR terunduh sendiri saat pertama dipakai (butuh internet).
Klip suara `assets/tts/` **sudah ikut Git**, jadi tidak perlu dibuat ulang —
kecuali kalau kamu menambah kalimat baru di `sayit/response/templates.py`,
lalu jalankan `python scripts\build_tts_cache.py`.

### Tiga jendela untuk alur lengkap

**PowerShell (bawaan Windows) tidak mengenal `&&`** - seluruh baris gagal di-parse
dan tidak ada yang dijalankan. Perintah di bawah sengaja satu baris tanpa `&&`,
dan **tanpa mengaktifkan venv sama sekali**: memanggil berkasnya langsung
menghilangkan sekaligus masalah `&&`, aktivasi, dan izin skrip.

Tiga jendela PowerShell, masing-masing dibiarkan terbuka:

```powershell
.venv\Scripts\uvicorn.exe server.app:app --port 8000
```

```powershell
cd web; npm run dev
```

```powershell
ngrok http 3000
```

ngrok mencetak alamatnya sendiri; yang dibuka di HP adalah yang di sebelah
`Forwarding`, dan **berganti setiap ngrok dijalankan ulang**:

```
Forwarding   https://xxxx.ngrok-free.dev -> http://localhost:3000
```

Satu tunnel ke port 3000 sudah cukup - backend ikut lewat situ, karena rewrite
Next berjalan di laptop dan meneruskan `/api` ke port 8000 secara lokal.

Menghentikannya: Ctrl+C di tiap jendela, atau `taskkill /F /IM ngrok.exe`.

Kamera dan mikrofon **hanya jalan di HTTPS**, jadi untuk mengujinya dari HP
pakai URL ngrok, bukan `localhost` maupun IP laptop.

### Panel uji Streamlit (internal)

```bat
streamlit run app.py
```

Berguna untuk memeriksa modul satu per satu tanpa peramban dan tanpa suara.

---

## Status

| Modul | Berkas | Status |
| :--- | :--- | :--- |
| Konfigurasi | `config/settings.yaml`, `sayit/config.py` | Siap |
| Rekam/putar audio | `sayit/audio/io.py` | Siap |
| Speech-to-Text | `sayit/audio/stt.py` | Siap (faster-whisper small + prompt) |
| Text-to-Speech | `sayit/audio/tts.py` | Siap (edge-tts hibrida, 89 klip offline) |
| Intent router | `sayit/intent/` | Siap |
| Templat respons & angka ke kata | `sayit/response/` | Siap |
| Quality gate, pra-pemrosesan, uang, dokumen, kedaluwarsa | `sayit/vision/` | Siap |
| Pipeline | `sayit/pipeline.py` | Siap |
| Panel uji Streamlit | `app.py` | Siap |
| API web | `server/app.py` | Siap |
| PWA | `web/` | Siap |

Hasil ukur terakhir terhadap target PRD Bagian 11:

| Metrik | Hasil | Target | |
| :--- | :--- | :--- | :--- |
| Akurasi kedaluwarsa | 81% (13 benar / 1 salah / 2 diam dari 16) | >= 70% | tercapai |
| Akurasi uang (total diucapkan) | **90,1%** (73 benar / 8 salah / 0 diam dari 81 foto) | >= 85% | **tercapai** |
| CER dokumen | **14,89%** | <= 15% | **tercapai** |
| Latensi uang / kendali | 1,4 s / 1,3 s | <= 8 s | lolos |
| Latensi dokumen / kedaluwarsa | 11,5 s / 11,4 s | <= 8 s | penyimpangan diterima |

Angka akurasi **wajib dilaporkan terpisah** sebagai benar / salah / diam, bukan
satu persentase. Bagi pengguna tunanetra, tanggal atau nominal yang **salah**
jauh lebih berbahaya daripada sistem yang diam. Alasan lengkap dan riwayat tiap
angka ada di `docs/keputusan-teknis.md`.

---

## Aturan kerja

- `python -m pytest -q` harus lulus **sebelum dan sesudah** setiap perubahan.
  Saat ini 685 tes.
- Uji asap API: `python server\smoke.py` — memuat model sungguhan, jadi bukan
  bagian dari pytest.
- Semua parameter di `config/settings.yaml`, dibaca lewat `sayit/config.py`.
  Hindari angka ajaib di kode.
- Kalimat suara baru wajib didaftarkan di `sayit/response/templates.py` lalu
  cache dibuat ulang.
- Kata kunci intent baru wajib disertai kasus uji di `tests/test_router.py`.

### Jebakan yang sudah pernah menggigit

- **Jangan jalankan `npm run build` selagi `npm run dev` hidup.** Keduanya memakai
  `.next/`, dan build menimpa manifes chunk milik dev server. Gejalanya halus:
  halaman tetap tampil tetapi React tidak pernah hydrate, jadi tidak ada tombol
  yang bereaksi. Perbaikannya hapus `.next/` lalu jalankan ulang.
- **Endpoint API baru butuh uvicorn dijalankan ulang.** `server\smoke.py` memakai
  app baru di dalam proses, jadi ia lulus sementara server yang hidup masih 404.

---

## Aturan privasi

- Teks dokumen yang dibacakan **dikirim ke server Microsoft** (edge-tts sejak 28-10;
  dulu Google lewat gTTS). Jangan memakai dokumen pribadi asli saat pengujian.
- Audio teks dinamis tidak disimpan ke disk (`tts.cache_dynamic_text: false`).
- Rekaman suara anggota tim di `fase0/fase0_hasil/rekaman/` **tidak boleh**
  di-commit maupun diunggah. Sudah dijaga `.gitignore`.
- `?api=` hanya menerima host tunnel. Ini daftar putih, bukan kenyamanan: foto
  dan rekaman suara pengguna dikirim ke host itu.
