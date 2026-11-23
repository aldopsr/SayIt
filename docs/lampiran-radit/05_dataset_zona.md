# 3. Dokumentasi detektor zona kedaluwarsa

Bobot yang dipakai produksi: **`models/best_zone.pt`**, 6.256.362 bita,
bertanggal 28 September 2026 08:18.

---

## 3.1 Dataset dan lisensinya

**[Diperiksa ulang lewat API Roboflow Universe, 22 November 2026]**

| hal | nilai |
|---|---|
| Dataset | `coolstuff-rfnc5/expiry-date-detection-i3bav` |
| Nama tampilan | "Expiry Date Detection" |
| Workspace | CoolSTuff |
| Versi | **1** |
| Tautan | https://universe.roboflow.com/coolstuff-rfnc5/expiry-date-detection-i3bav |
| Jumlah citra | **998** |
| Kelas | **1** — bernama `Label` |
| Terakhir diperbarui | 20 Oktober 2024 |
| **Lisensi** | **TIDAK TERCANTUM** (`license: null`) |

### Lisensi: ini risiko nyata, bukan detail administratif

API Roboflow mengembalikan `license: null` untuk proyek ini. Artinya **bukan**
"belum sempat dicek" — halaman datasetnya memang tidak menyatakan lisensi apa
pun. Tanpa pernyataan lisensi, tidak ada izin eksplisit untuk memakai ulang,
mendistribusikan, maupun menerbitkan hasil turunannya.

**Alternatif berlisensi jelas dengan ukuran hampir sama**, kalau perlu melatih
ulang sebelum submit:

| dataset | citra | kelas | lisensi |
|---|---|---|---|
| `expiry-label-detection/expiry-date-detection-egbf3` | 1.014 | 1 (`Label`) | **CC BY 4.0** |
| `abhilashasacademicworkspace-8igt2/expiry-date-detection-ssxnm` | 5.229 | — | **MIT** |

Dataset empat kelas yang dipakai percobaan (bukan produksi):
`esigelec-rniez/expiry` versi 1, 700 citra, kelas `date` / `code` / `due` /
`prod`.

---

## 3.2 Konfigurasi pelatihan

Dari `notebooks/03_zone_build_and_train.ipynb`:

| parameter | nilai |
|---|---|
| Arsitektur | YOLOv8n (`yolov8n.pt` sebagai bobot awal) |
| Epoch | **100** (setelan), `patience=20` |
| Ukuran masukan | **640 px** |
| Batch | 16 |
| Seed | 42 |
| Nama run | `zone_v1` |
| Pembagian data | `SPLIT_RATIO = (0.7, 0.2, 0.1)` |
| Augmentasi | `degrees=180`, `perspective=0.0005`, `scale=0.6`, `translate=0.2`, `hsv_v=0.5`, `hsv_s=0.8`, `fliplr=0.5` |

Dua catatan supaya tidak salah kutip:

1. **"100 epoch" adalah SETELAN, belum tentu yang berjalan.** `patience=20`
   menghentikan latihan lebih awal bila validasi berhenti membaik. Berapa epoch
   yang sungguh berjalan hanya ada di keluaran Colab.
2. **`degrees=180` dan `fliplr=0.5` disengaja**, dan berbeda dari model uang.
   Alasannya ada di komentar notebook: kemasan bisa dipegang pada sudut apa pun,
   dan model ini hanya mencari **letak** tanggal, bukan bacaannya — jadi tanggal
   yang tercermin tetap contoh latih yang sah.

Konfigurasi runtime (yang dipakai aplikasi saat menjalankan model ini) ada di
`04_konfigurasi_kedaluwarsa.yaml`, diekstrak dari config yang benar-benar dimuat
aplikasi, bukan disalin tangan.

---

## 3.3 Catatan pelatihan dan daftar pembagian data

**TIDAK TERCATAT**, dan ini jujur harus ditulis begitu:

- **`notebooks/03_zone_build_and_train.ipynb` tersimpan tanpa keluaran sama
  sekali** — 0 dari 25 sel punya `outputs`. Jadi tidak ada `results.csv`, tidak
  ada kurva pelatihan, dan **tidak ada mAP50 validasi** untuk `best_zone.pt` di
  dalam repo.
- **Daftar pembagian train/val/test tidak tersimpan sebagai berkas.** Notebook
  tidak memakai split bawaan Roboflow: ia mengunduh seluruh citra, membuang
  duplikat dengan pHash, lalu membagi ulang **per kelompok kemiripan** dengan
  `SPLIT_RATIO` dan `SEED` di atas. Jumlah akhir tiap split hanya tercetak saat
  notebook dijalankan.

**Kalau folder `runs/zone_v1` masih ada di Google Drive**, `results.csv` di
dalamnya memuat catatan pelatihan per epoch dan mAP validasinya. Itu satu-satunya
tempat angka ini mungkin masih ada.

Sebagai pembanding, dua model empat kelas yang dilatih belakangan **memang**
menyimpan ringkasan metrik ke Drive secara otomatis
(`MyDrive/sayit/hasil/<run>_metrik.json`), karena kebiasaan itu baru dipakai
sejak notebook 05:

| | `zone_4kelas_v1` | `zone_gabungan_v1` |
|---|---|---|
| Waktu latih | 19-11-2026 18:37 | 20-11-2026 03:25 |
| Epoch | 80 | 100 |
| mAP50 | 0,8643 | 0,7813 |
| mAP50-95 | 0,6766 | 0,5310 |
| AP50 `date` | 0,9384 | 0,6305 |

---

## 3.4 Kinerja detektor zona pada kemasan sendiri

mAP50 untuk `best_zone.pt` tidak ada (lihat 3.3), dan **tidak dapat dihitung
dari repo**: menghitung mAP butuh kotak acuan, sedangkan 16 foto uji hanya punya
tanggal acuan di nama berkasnya, bukan koordinat kotak. Folder
`data/zona_sendiri/` yang disiapkan untuk itu masih kosong.

**Pengganti yang terukur** — tingkat deteksi pada 16 kemasan sendiri, diukur
dengan ambang dipaksa 0,01 agar seluruh deteksi terlihat:

| ambang skor | zona ketemu / 14 kemasan bertanggal | laju | deteksi palsu / 2 kemasan tanpa tanggal |
|---|---|---|---|
| 0,15 | 12 / 14 | 86% | **0 / 2** |
| 0,25 | 11 / 14 | 79% | **0 / 2** |
| **0,40 (dipakai)** | **9 / 14** | **64%** | **0 / 2** |
| 0,50 | 8 / 14 | 57% | **0 / 2** |
| 0,60 | 7 / 14 | 50% | **0 / 2** |

Dua hal yang layak disebut:

- **Nol deteksi palsu di seluruh ambang**, bahkan 0,15. Model tidak mengarang
  zona pada kemasan yang tidak punya tanggal.
- Angka ini **mereproduksi persis** catatan 30 September ("9 dari 14, skor
  0,43–0,77") setelah hampir dua bulan.

**Tetapi 64% itu BATAS ATAS, bukan recall.** Tanpa kotak acuan, "ketemu" tidak
berarti kotaknya di tempat yang benar. Buktinya ada di data yang sama:

- `chees` terdeteksi dengan skor **0,72** — tertinggi ketiga — dan kotaknya
  menunjuk **nomor produksi**, bukan tanggalnya. Itulah sebab jawabannya salah.
- Pada `20290821_tisu2.PNG`, deteksi terbaik (skor 0,20) mendarat di **jam
  aplikasi Foto iOS** di dalam tangkapan layarnya, bukan di kemasannya.

Dalam perhitungan mAP sungguhan, keduanya dihitung sebagai *false positive*.
