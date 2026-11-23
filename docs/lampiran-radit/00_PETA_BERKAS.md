# Peta berkas — buka yang mana untuk apa

Sembilan berkas. **Mulai dari `BACA_DULU.md`** — di situ seluruh penjelasannya;
berkas lain adalah datanya.

---

## Jawaban untuk kelima permintaanmu

| # | permintaanmu | buka berkas ini | bagian |
|---|---|---|---|
| **1** | Pengujian pada data baru | `BACA_DULU.md` | bagian 1 |
| | data per gambar | `01_hasil_per_gambar.csv` | — |
| **2** | Model satu atau empat kelas | `BACA_DULU.md` | bagian 2 |
| | CSV perbandingannya | `02_banding_model_zona.csv` | — |
| **3** | Dokumentasi detektor zona | `05_dataset_zona.md` | seluruhnya |
| | konfigurasi YAML | `04_konfigurasi_kedaluwarsa.yaml` | — |
| **4** | Kebenaran tanggal acuan | `03_tanggal_acuan.csv` | — |
| | foto aslinya | `data/uji_kedaluwarsa/` di repo | — |
| **5** | Pengukuran waktu respons | `BACA_DULU.md` | bagian 5 |
| | CSV per percobaan | `06_waktu_respons_deploy.csv` | — |

---

## Tiap berkas, isinya apa

### `BACA_DULU.md` — mulai di sini
Seluruh penjelasan naratif. Lima bagian menjawab lima permintaanmu, lalu tiga
blok temuan yang **tidak kamu tanyakan tetapi memengaruhi naskah**:

- **Blok A** — tiga dari 16 berkas adalah tangkapan layar, bukan foto kamera.
- **Blok B** — "dengan/tanpa pra-pemrosesan" pada catatan 2 Oktober dan hari ini
  mengukur hal **berbeda**. Jangan disatukan dalam satu tabel.
- **Blok C** — dua jawaban salah berbeda **arah**, dan bahayanya tidak sama.

Lalu di bagian bawah, tiga hal yang terjadi sesudahnya: akurasi lewat deploy,
perbaikan batas 120 detik, dan **cara melaporkannya dari data yang ada**.

### `01_hasil_per_gambar.csv` — 16 baris
Hasil tiap foto pada konfigurasi akhir: tanggal acuan, tanggal yang dijawab,
nilai benar/salah/kosong, **arah kesalahan**, jalur yang dipakai, skor zona, dan
jenis berkasnya (foto kamera atau tangkapan layar).

### `02_banding_model_zona.csv` — 7 baris
Perbandingan bobot zona 1 kelas lawan 4 kelas: benar/salah/kosong, latensi,
cakupan zona, mAP50, dan AP50 per kelas. Dua baris terakhir adalah pembanding
**dalam satu sesi**, yang paling sah dikutip untuk latensi.

### `03_tanggal_acuan.csv` — 16 baris
Tanggal acuan tiap foto, **apa yang benar-benar tercetak di kemasan**, apakah
terbaca jelas, dan cara memverifikasinya. Dua berkas bertanda `TIDAK` terbaca —
acuannya diwarisi dari produk kembarnya, bukan dibaca langsung.

### `04_konfigurasi_kedaluwarsa.yaml`
Konfigurasi runtime, diekstrak dari config yang **dimuat aplikasi**, bukan
disalin tangan. Memuat `expiry`, `date_parser`, bagian `document` yang relevan,
`quality_gate`, dan rangkaian pra-pemrosesan.

### `05_dataset_zona.md` — permintaan 3
Dataset pelatihan detektor zona, **lisensinya**, konfigurasi pelatihan, apa yang
tidak tercatat dan kenapa, serta kinerja detektor pada kemasan sendiri.

### `06_waktu_respons_deploy.csv` — 48 baris
Satu baris per percobaan: 16 gambar × 3 pengulangan. Kolom `foto_s` dan
`tanya_s` adalah dua tahap terpisah, `total_s` jumlahnya. Diukur lewat deploy
sungguhan, jadi memuat jaringan dan antrean.

### `07_penilaian_lewat_deploy.txt`
Keluaran penilai: benar/salah/kosong per gambar **berdasarkan jawaban yang
benar-benar diucapkan sistem**, bukan pemanggilan fungsi lokal.

### `08_subset_foto_kamera.txt`
Akurasi pada seluruh 16 berkas lawan subset 13 foto kamera, untuk lokal dan
deploy. Empat baris, dan di situlah penjelasan terpenting berada.

---

## Kalau waktumu sempit, tiga hal ini yang paling memengaruhi naskah

**1. Angka mana yang kamu kutip, dan jalurnya apa.**

| | BENAR | SALAH | KOSONG | n | akurasi |
|---|---|---|---|---|---|
| Lokal — seluruh berkas | 13 | 2 | 1 | 16 | 81% |
| Lokal — foto kamera saja | 11 | 2 | 0 | 13 | **85%** |
| Deploy — seluruh berkas | 12 | 2 | 2 | 16 | 75% |
| Deploy — foto kamera saja | 11 | 2 | 0 | 13 | **85%** |

Angka 81% yang ada di naskahmu sekarang diukur dengan memanggil modul langsung
di laptop — tanpa quality gate dan tanpa jaringan. **Pada foto kamera, lokal dan
deploy sama persis.** Kalimat siap pakai ada di bagian terakhir `BACA_DULU.md`.

**2. Set ujinya dipakai untuk MENYETEL sistem**, jadi angka berapa pun di atas
adalah estimasi resubstitusi, bukan hasil pada data tertahan. Tujuh keputusan
dipilih dengan mengukur pada 16 foto yang sama — daftarnya di bagian 1.

**3. Lisensi dataset detektor zona TIDAK TERCANTUM** (`license: null` di
Roboflow, diperiksa 22 November). Itu risiko nyata untuk publikasi, bukan detail
administratif. Alternatif berlisensi jelas ada di `05_dataset_zona.md`.
