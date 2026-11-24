# Lampiran jurnal kedaluwarsa — lima permintaan Radit

> # ⚠ SEBAGIAN BERKAS INI SUDAH USANG (per 24 November 2026)
>
> Modul kedaluwarsa dipindah ke backend **ONNX Runtime** pada 24 November.
> **Baca `11_PERUBAHAN_KEDALUWARSA_24NOV.md` sebelum mengutip apa pun dari
> berkas ini.**
>
> **Yang MASIH BERLAKU di berkas ini: seluruh angka AKURASI.** Akurasi tidak
> berubah sama sekali — 81% (13 BENAR / 2 SALAH / 1 KOSONG), dan jawabannya
> identik pada keenam belas berkas. Begitu pula seluruh pembahasan model zona
> 4 kelas, tanggal acuan, komposisi set uji, dan resubstitusi.
>
> **Yang SUDAH TIDAK BERLAKU: seluruh angka LATENSI, dan seluruh pembahasan
> batas 120 detik.**
>
> | di berkas ini | ganti dengan |
> |---|---|
> | median modul **7,82 s** (bagian 2, 3) | **2,39 s** |
> | terburuk **90,0 s** (bagian 3, "Rerata atau median?") | **9,74 s** |
> | total **262,1 s** (bagian 3) | **42,7 s** |
> | median lewat deploy **12,38 s** (bagian 5) | **4,73 s** |
> | "4 kelas median 20,2 s" (bagian 2) | diukur pada backend lama; rasionya masih sah, angka detiknya tidak |
> | **seluruh** pembahasan proksi Vercel 502 dan batas 120 detik | sudah tidak terjadi: 48 dari 48 percobaan berhasil, maksimum 38,32 s |
> | "modul ini menyimpang dari NFR-01" (bagian 2) | **NFR-01 TERPENUHI**, median 3,0 s |
>
> Alasan membaginya begini: perubahan 24 November **murni optimasi runtime** —
> model, bobot, dan parameter pasca-pemrosesan tidak disentuh. Jadi semua yang
> berbicara tentang *apa yang dikenali* tetap sah, dan hanya yang berbicara
> tentang *berapa lama* yang perlu diganti.


Disusun 23 November 2026, repo pada commit `b988ada`.

**Bingung buka yang mana? Lihat `00_PETA_BERKAS.md`.**

| berkas | untuk permintaan |
|---|---|
| `01_hasil_per_gambar.csv` | 1, 4 |
| `02_banding_model_zona.csv` | 2 |
| `03_tanggal_acuan.csv` | 4 |
| `04_konfigurasi_kedaluwarsa.yaml` | 3 |
| `05_dataset_zona.md` | 3 |
| `06_waktu_respons_deploy.csv` | 5 |
| `08_subset_foto_kamera.txt` | 1 |
| `07_penilaian_lewat_deploy.txt` | 1, 5 |
| berkas ini | penjelasan 1, 2, 5 |

Foto asli JPG/PNG/HEIC ada di `data/uji_kedaluwarsa/` di repo.
(Folder `data/` diabaikan Git, jadi fotonya hanya ada di laptop pengembang -
minta salinannya langsung bila dibutuhkan sebagai lampiran jurnal.)

---

# 1. Pengujian pada data baru

## Jawaban singkat: BELUM ADA, dan ini perlu ditulis terus terang di jurnal.

**Ke-16 foto di `data/uji_kedaluwarsa/` dipakai untuk MENYETEL sistem, bukan
hanya mengujinya.** Jadi angka 81% adalah akurasi pada data yang sama dengan
data penyetelan — dalam istilah statistik, **estimasi resubstitusi**, bukan
estimasi pada data tertahan (*held-out*).

Ini daftar keputusan yang dipilih dengan cara mengukur pada 16 foto itu:

| yang disetel | nilai yang dipilih | dasar pemilihan |
|---|---|---|
| Mesin OCR | PaddleOCR, bukan EasyOCR | ablasi pada 16 foto ini (01-10) |
| `require_marker_for_compact` | `false` | diukur pada foto ini; `true` memberi 56% lawan 75% (16-11) |
| `line_grouping` | `rantai`, bukan `pita` | dipilih karena `mentega` di set ini berubah benar (17-11) |
| `expiry.preprocess_chain` | `hanya_resize` | ablasi pada set ini; `[upscale, clahe]` memberi 69% lawan 81% |
| `date_parser.negative_markers` | daftar terisi | A/B pada set ini (20-11) |
| `expiry.rotate_crop` | `false` | diputuskan dari jejak per berkas set ini (17-11) |
| Bobot zona 1 kelas vs 4 kelas | 1 kelas | dibandingkan pada set ini (20-11) |

Tujuh keputusan, satu set uji. Tidak ada satu pun yang diambil dari data lain.

## Kenapa ini harus disebut, bukan didiamkan

Akurasi pada data penyetelan hampir selalu lebih tinggi daripada akurasi pada
data baru. Besar selisihnya tidak diketahui karena belum pernah diukur — tetapi
arah biasnya satu arah, dan pembaca jurnal yang teliti akan menanyakannya persis
seperti Radit menanyakannya sekarang.

Kalimat yang jujur dan masih bisa dipakai, misalnya:

> Pengujian dilakukan pada 16 foto kemasan yang dikumpulkan sendiri. Himpunan
> yang sama juga dipakai untuk memilih mesin OCR dan menyetel parameter parser,
> sehingga angka 81% merupakan akurasi pada data penyetelan dan cenderung
> optimistis terhadap kemasan yang belum pernah dilihat sistem.

## Apa yang dibutuhkan untuk pengujian baru

Hanya pemilik datanya yang bisa menyediakan ini:

1. **Kemasan BARU yang belum pernah dipakai menyetel apa pun.** Supaya hasilnya
   bermakna, jumlahnya sebaiknya **minimal 20–30 kemasan**; dengan n=16 saja,
   satu foto bernilai 6 poin persentase.
2. **Diarahkan ke mode kegagalan yang sudah diketahui**, bukan merata: cetakan
   dot-matrix, cetakan terang di atas latar gelap, permukaan melengkung, dan
   beberapa kemasan yang memang tidak punya tanggal.
3. **Tanggal acuan diverifikasi ke cetakan fisiknya** sebelum diukur — lihat
   bagian 4 berkas ini untuk caranya.
4. **Diukur SATU KALI saja**, lalu angkanya dilaporkan apa adanya. Begitu
   parameter disetel ulang berdasarkan hasilnya, set itu berhenti menjadi data
   baru dan masalahnya berulang.

## Catatan tambahan tentang komposisi set uji sekarang

Diperiksa 22–23 November, dan dua hal ini sebaiknya ikut disebut di subbab data:

- **Tiga dari 16 berkas adalah TANGKAPAN LAYAR, bukan foto kamera**:
  `202804_tolakangin2.PNG`, `20290821_tisu1.PNG`, `20290821_tisu2.PNG`. Semuanya
  828×1792 — resolusi layar iPhone 11/XR tepat — tanpa EXIF kamera. Pada
  `tisu2` antarmuka aplikasi Foto iOS terlihat di dalam gambarnya (jam, label
  "Today", tombol bagikan/hapus).
- **16 foto memuat 14 produk berbeda.** Tolak Angin muncul dua kali
  (`tolakangin1`, `tolakangin2`) dan tisu basah dua kali (`tisu1`, `tisu2`).
  Keduanya **foto yang berbeda**, bukan salinan — jarak pHash 25, sama dengan
  pasangan yang tidak berhubungan — tetapi produknya sama. Jadi jumlah produk
  unik yang diuji adalah 14, bukan 16.

---

# 2. Alasan memilih model satu kelas meskipun model empat kelas mengurangi jawaban salah

Angka lengkapnya ada di `02_banding_model_zona.csv`. Ringkasnya:

| bobot | BENAR | SALAH | KOSONG | akurasi | median | zona ketemu |
|---|---|---|---|---|---|---|
| **1 kelas (dipakai)** | **13** | **2** | 1 | **81%** | **7,82 s** | **7/16** |
| 4 kelas, satu dataset | 13 | **0** | 3 | 81% | 20,23 s | 2/16 |
| 4 kelas, dua dataset digabung | 13 | **0** | 3 | 81% | 20,18 s | 3/16 |

## Alasan 1 — "nol salah" itu tidak dibeli oleh kepintaran, melainkan oleh diam

Akurasi keduanya **sama**, 81%. Yang berubah hanya komposisinya: dua jawaban
SALAH berubah menjadi dua jawaban KOSONG. Model empat kelas tidak menjawab lebih
benar; ia lebih sering **tidak menjawab**.

Itu terlihat jelas dari kolom terakhir: cakupan zona runtuh dari **7/16 menjadi
2–3/16**. Nol jawaban salah selalu bisa dicapai dengan tidak menjawab apa pun,
dan di sinilah sebagian besar perbaikannya berasal.

## Alasan 2 — harganya latensi, pada modul yang sudah menyimpang dari target

Median **7,82 → 20,2 detik**, hampir tiga kali lipat. Dan sebabnya bukan model
empat kelasnya mahal — inferensi zona sendiri hanya **6,6 ms**. Yang mahal adalah
akibatnya: karena zona jarang ditemukan, 13 dari 16 berkas jatuh ke jalur
cadangan OCR seluruh gambar yang memang jauh lebih lambat.

Target PRD NFR-01 adalah ≤ 8 detik dan modul ini sudah tercatat menyimpang;
menambah penyimpangannya tiga kali lipat demi nol perbaikan akurasi tidak bisa
dipertahankan.

## Alasan 3 — perbandingan dalam satu sesi tetap memenangkan model satu kelas

Karena latensi modul ini berderau besar antar-sesi (lihat bagian 5), kedua
finalis diukur ulang **dalam satu proses yang sama**:

| kondisi | BENAR | SALAH | KOSONG | akurasi | median | terburuk | total |
|---|---|---|---|---|---|---|---|
| **1 kelas @0,40** | **13** | 2 | 1 | **81%** | **7,82 s** | 90,0 s | **262,1 s** |
| gabungan @0,25 tolak `due` | 12 | **1** | 3 | 75% | 10,43 s | 86,1 s | 380,4 s |

Model satu kelas menang di **kedua** sisi — akurasi 81% lawan 75%, dan total
45% lebih cepat. Jadi pada konfigurasi terbaik yang bisa ditemukan untuk model
empat kelas sekalipun, ini **bukan pertukaran**: tidak ada sisi di mana model
empat kelas lebih baik.

## Alasan 4 — kenapa model gabungan justru lebih buruk, dan ini terukur

Metrik pelatihan kedua model (dari Google Drive, ditulis otomatis notebooknya):

| | 4 kelas satu dataset | 4 kelas gabungan |
|---|---|---|
| mAP50 | 0,8643 | 0,7813 |
| **AP50 kelas `date`** | **0,9384** | **0,6305** |
| AP50 `code` | 0,8120 | 0,7883 |
| AP50 `due` | 0,8532 | 0,8574 |
| AP50 `prod` | 0,8488 | 0,8488 |

Menggabungkan dataset satu kelas menjatuhkan AP50 kelas `date` dari 0,94 ke
0,63, sementara tiga kelas lain nyaris tidak bergerak. Sebabnya: seluruh kotak
dataset satu kelas dipetakan menjadi `date`, padahal sebagiannya sebenarnya kode
produksi atau penanda — jadi definisi `date` menjadi kabur.

Rantai sebabnya utuh sampai ke tingkat model: dataset digabung → `date` kabur →
cakupan zona runtuh → berkas jatuh ke jalur cadangan → latensi naik.

## Yang HARUS ikut ditulis supaya tidak berlebihan

- **Model empat kelas tidak gagal; ia tidak memberi keuntungan bersih.**
  Mekanisme yang dirancang terbukti bekerja: pada `chees`, kelas `code` memang
  ditolak dan kelas `date` dipilih. Yang tidak terjadi adalah perbaikan akurasi.
- **Kedua mAP50 di atas diukur pada split test yang sesumber dengan data
  latihnya**, jadi optimistis untuk kemasan Indonesia.
- Keputusan ini diambil pada **n=16 dengan dua jawaban salah**. Selisih satu
  berkas bernilai 6 poin. Dengan set uji baru yang lebih besar, kesimpulannya
  bisa berubah.

---

# 5. Pengukuran waktu respons

Angka per percobaan ada di `waktu_respons_deploy.csv`.

## Perangkat dan jalur yang diukur

| hal | nilai |
|---|---|
| Server | laptop pengembang — Intel i7-13650HX, RAM 20 GB, **inferensi di CPU** |
| Frontend | PWA Next.js di Vercel, `https://sayit-app-phi.vercel.app` |
| Tunnel | ngrok domain statis, ke FastAPI port 8000 di laptop |
| Klien saat mengukur | skrip Python di laptop yang sama, menembak URL Vercel publik |
| Mesin OCR | PaddleOCR — `PP-OCRv5_mobile_det` + `PP-OCRv6_medium_rec` |
| Versi | paddleocr 3.7.0, paddlepaddle 3.3.1 |

Jalur tiap permintaan: **klien → Vercel → ngrok → FastAPI → balik**. Jadi
angkanya memuat jaringan, proksi, antrean kunci server, inferensi, dan render
suara — bukan hanya pemanggilan fungsi lokal.

## Tahapan yang diukur

Dua tahap, terpisah karena pengguna memang mengalaminya terpisah:

| tahap | endpoint | isinya |
|---|---|---|
| **A** | `POST /api/foto` | quality gate + render suara "silakan bertanya" |
| **B** | `POST /api/tanya` | deteksi zona + OCR + parser + render suara jawaban |
| **TOTAL** | A + B | jeda sejak rana ditekan sampai jawaban mulai terdengar |

## Yang TIDAK terukur — wajib disebut saat mengutip

1. **Pengenalan suara (STT) tidak ikut.** Pertanyaan dikirim sebagai teks, bukan
   rekaman. Di pemakaian nyata masih ada perekaman (jeda hening 1,5–3 detik
   sebelum rekaman ditutup) dan transkripsi Whisper di atas angka ini.
2. **Klien berada di laptop yang sama dengan server.** Lalu lintasnya tetap
   keluar ke tepi ngrok dan kembali, jadi bukan localhost — tetapi **ponsel di
   jaringan seluler akan menambah latensi lagi di atas angka ini.**
3. **Durasi audio jawaban dibacakan tidak ikut.** Untuk jawaban tanggal ini
   pendek, tetapi untuk modul dokumen durasinya bisa jauh melebihi waktu proses.

## Jumlah gambar unik dan pengulangan

- **16 gambar unik** (14 produk berbeda — lihat bagian 1).
- **3 pengulangan** tiap gambar, berurutan.
- **48 giliran**, masing-masing 2 permintaan HTTP = **96 permintaan**.

## Rerata atau median?

**Pakai median, dan sebutkan maksimumnya.** Dua alasan, keduanya terukur:

1. **Sebarannya sangat miring.** Satu berkas (`tolakangin2`) memakan 90 detik
   sementara median seluruh set 7,82 detik pada pengukuran modul. Rerata akan
   ditarik satu pencilan.
2. **Latensi modul ini berderau besar antar-sesi.** Kondisi yang sama persis
   memberi median 6,54 detik di satu sesi dan 10,46 detik di sesi lain pada hari
   yang sama — simpangan sampai 60% dari beban laptop. Karena itu **perbandingan
   di dalam satu sesi** sah, sedangkan angka detik sebagai nilai mutlak harus
   disertai tanggal dan catatan sebarannya.

Ringkasan median, rerata, minimum, dan maksimum dicetak di akhir
`waktu_respons_deploy.csv` dan di keluaran skripnya
(`scripts/ukur_respons_deploy.py`).

---

# TEMUAN BARU 23-11: angka 81% diukur di laptop, BUKAN lewat sistem yang dipakai pengguna

Permintaan nomor 5 meminta pengukuran waktu respons. Karena pengukurannya
dijalankan lewat **deploy sungguhan** (`https://sayit-app-phi.vercel.app`),
jawaban yang diucapkan sistem ikut terekam — dan itu memungkinkan sesuatu yang
belum pernah dilakukan: **menilai akurasi pada jalur yang benar-benar dipakai
pengguna.**

| cara mengukur | BENAR | SALAH | KOSONG | akurasi |
|---|---|---|---|---|
| **Lokal** — `ExpiryReader.read()` langsung di laptop | 13 | 2 | 1 | **81%** |
| **Lewat deploy** — klien → Vercel → ngrok → FastAPI | **10** | **2** | **4** | **62%** |

Angka 81% yang ada di naskah berasal dari baris pertama.

## Selisih 19 poin itu BUKAN kesalahan pengenalan

Yang paling penting dari tabel di atas: **kolom SALAH sama persis — 2 berkas yang
sama** (`chees` dan `ovaltine`). Deploy tidak memunculkan satu pun jawaban salah
baru. Ketiga kegagalan tambahannya punya sebab yang sama sekali berbeda:

| berkas | lokal | deploy | sebab sesungguhnya |
|---|---|---|---|
| `202804_tolakangin2.PNG` | KOSONG | KOSONG | **Proksi Vercel menyerah 502 setelah 120,2 detik.** Terjadi di **3 dari 3** pengulangan — deterministik, bukan kebetulan |
| `20290211_kecapasin.JPG` | BENAR | **KOSONG** | **Antrean server penuh** (`server_sibuk`), 2 dari 3 pengulangan |
| `20290306_merica.JPG` | BENAR | **KOSONG** | **Antrean server penuh**, 1 dari 3 pengulangan |
| `20290821_tisu1.PNG` | BENAR | **KOSONG** | **Ditolak quality gate** — "foto terlalu gelap, nyalakan senter di ponselmu" |

Jadi: **3 kegagalan infrastruktur + 1 penolakan quality gate**, nol kesalahan
membaca tambahan.

## Kegagalan berantai, dan ini perlu ditulis sebagai temuan tersendiri

Urutannya terekam jelas di `06_waktu_respons_deploy.csv`:

```
tolakangin2   /foto 1,39s   /tanya 120,24s   status 200/502   (jawaban kosong)
kecapasin     /foto 23,26s  /tanya 13,17s    status 200/200   (server sibuk)
merica        /foto 2,73s   /tanya 2,61s     status 200/200   (server sibuk)
```

1. `/tanya` untuk `tolakangin2` berjalan lebih dari **120 detik**, yaitu batas
   proksi Vercel untuk semua paket. Vercel memutus dan membalas **502**.
2. **Server tidak ikut berhenti.** Ia terus memproses permintaan yang sudah
   ditinggalkan itu sambil memegang kunci antrean.
3. Dua giliran berikutnya karena itu ditolak dengan klip `server_sibuk` —
   termasuk `merica` yang biasanya selesai dalam 5 detik.

**Satu foto lambat merusak dua giliran sesudahnya.** Bagi pengguna tunanetra,
ketiganya terdengar sebagai kegagalan sistem tanpa sebab yang bisa ia pahami.

Angka 120 detik itu sebelumnya hanya tercatat sebagai risiko dengan "margin 20%"
terhadap kasus terburuk yang terukur (99,2 detik). Sekarang ia **terlanggar, dan
berulang pada ketiga pengulangan.**

## Penolakan quality gate juga baru terlihat di sini

`20290821_tisu1.PNG` dibaca dengan BENAR oleh skrip lokal, tetapi **ditolak
sebelum OCR** oleh aplikasi sungguhan. Sebabnya struktural: `ukur_kedaluwarsa.py`
memanggil `ExpiryReader.read()` **langsung**, jadi ia tidak pernah melewati
quality gate. Aplikasi melewatinya.

Artinya setiap angka akurasi yang diukur dengan skrip itu **mengabaikan satu
tahap penuh** yang dialami pengguna.

## Apa yang sebaiknya ditulis di jurnal

Angka 81% tetap boleh dipakai, tetapi **sebut jalurnya**:

> Akurasi 81% (13 benar / 2 salah / 1 kosong dari 16 kemasan) diukur dengan
> memanggil modul pembacaan secara langsung, tanpa melewati quality gate maupun
> lapisan jaringan. Diukur ulang melalui sistem yang ter-deploy, akurasinya 62%
> (10 / 2 / 4); selisihnya seluruhnya berasal dari tiga kegagalan infrastruktur
> dan satu penolakan quality gate, bukan dari kesalahan pembacaan tambahan —
> jumlah jawaban salah tetap dua dan pada kemasan yang sama.

Dan sebut batas 120 detiknya sebagai keterbatasan arsitektur yang diketahui,
bukan sebagai kegagalan acak.

## Angka waktu respons (48 percobaan, 16 gambar, 3 pengulangan)

| ukuran | TOTAL (A+B) | tahap A `/foto` | tahap B `/tanya` |
|---|---|---|---|
| **median** | **12,38 s** | 1,63 s | 11,94 s |
| rerata | 26,63 s | 2,81 s | 23,82 s |
| minimum | 1,90 s | — | — |
| **maksimum** | **121,63 s** | 23,26 s | 120,24 s |

**Pakai median, dan sebut maksimumnya.** Rerata 26,63 detik lebih dari dua kali
median 12,38 detik — sebarannya sangat miring, dan rerata ditarik oleh tiga
percobaan `tolakangin2` yang masing-masing mentok di batas 120 detik.

Catatan: median 12,38 detik ini **lebih besar** daripada 11,4 detik yang tercatat
di naskah, dan itu wajar — yang ini memuat jaringan, proksi, dan antrean,
sedangkan yang 11,4 detik tidak.

---

# PERBAIKAN 24-11: batas 120 detik ditutup, akurasi deploy 62% → 75%

Temuan di bagian sebelumnya ditindaklanjuti, bukan hanya dicatat.

## Apa yang diubah

Ditambahkan **anggaran waktu** pada `ExpiryReader.read()`
(`vision.expiry.budget_s`, bawaan **90 detik**). Sebelum tiap percobaan rotasi
gambar penuh, sistem memeriksa apakah **taksiran satu lintasan lagi** masih muat
di sisa anggaran — bukan sekadar "waktunya sudah lewat atau belum".

```python
lewat = time.perf_counter() - t_mulai
if anggaran and lewat + biaya_lintasan > anggaran:
    break
```

`biaya_lintasan` **diukur dari lintasan pertama, bukan ditebak**: tiap rotasi
mengulang pekerjaan yang sama persis. Memeriksa waktu lewat saja tetap
membiarkan satu lintasan 40 detik dimulai tepat sebelum batas, lalu berjalan
jauh melewatinya.

**Lintasan pertama tidak pernah dipotong**, berapa pun ketat anggarannya — foto
yang terbaca pada percobaan pertama tidak terpengaruh sama sekali. Ada tes
khusus untuk sifat itu.

Angka 90 detik diambil dari **batas arsitektur** — 120 detik proksi Vercel
dikurangi ruang untuk unggah foto, render suara, dan jaringan — **bukan** dari
apa yang kebetulan cocok untuk 16 kemasan uji. Menyetelnya pada set yang sama
adalah jebakan resubstitusi yang dijelaskan di bagian 1 berkas ini.

## Hasilnya, diukur ulang lewat deploy yang sama (48 percobaan)

| | sebelum perbaikan | sesudah perbaikan |
|---|---|---|
| **Akurasi lewat deploy** | 10 / 2 / 4 = **62%** | **12 / 2 / 2 = 75%** |
| **Maksimum** | **121,63 s** | **80,17 s** |
| Balasan 502 | 3 dari 3 pada `tolakangin2` | **nol** |
| Kegagalan infrastruktur | 3 gambar | **nol** |
| `/foto` maksimum | 23,26 s | 3,59 s |
| **Median TOTAL** | 12,38 s | **12,20 s** |
| Rerata TOTAL | 26,63 s | 23,73 s |

Tiga hal yang layak dibaca dari tabel ini:

1. **Median praktis tidak berubah** (12,38 → 12,20 detik). Perbaikan ini tidak
   membebani foto normal sama sekali; ia hanya memotong ekornya.
2. **Kegagalan berantainya hilang seluruhnya.** `kecapasin` dan `merica` yang
   sebelumnya ditolak `server_sibuk` kini keduanya BENAR. Itu menegaskan
   diagnosisnya: keduanya memang korban antrean yang tersumbat, bukan kemasan
   yang sulit dibaca.
3. **`tolakangin2` kini memberi jawaban, bukan galat jaringan.** Ia masih tidak
   menemukan tanggal — tetapi menjawab "tulisan terbaca, bukan tanggal" dalam
   80 detik, bukan dibalas 502 setelah 120 detik. Bagi pengguna tunanetra,
   bedanya adalah antara penjelasan yang bisa ditindaklanjuti dan kegagalan
   tanpa sebab.

## Akurasi lokal TIDAK berubah

Diukur ulang pada 16 kemasan: **13 BENAR / 2 SALAH / 1 KOSONG = 81%, identik
per berkas** dengan sebelum perbaikan. Anggaran tidak memakan satu pun jawaban
benar. 768 tes lulus (764 lama + 4 tes anggaran baru).

## Selisih yang tersisa antara lokal dan deploy

| | BENAR | SALAH | KOSONG | akurasi |
|---|---|---|---|---|
| Lokal (`ExpiryReader.read` langsung) | 13 | 2 | 1 | 81% |
| Lewat deploy, sesudah perbaikan | 12 | 2 | 2 | **75%** |

Selisihnya kini tinggal **satu berkas**: `20290821_tisu1.PNG`, yang **ditolak
quality gate** ("foto terlalu gelap") sebelum OCR. Skrip pengukur lokal memanggil
`ExpiryReader.read()` langsung sehingga tidak pernah melewati quality gate.

Itu bukan kegagalan infrastruktur dan bukan kesalahan membaca — itu tahap nyata
dalam aplikasi yang skrip pengukur lokal lewati. Untuk jurnal, cukup disebut
bahwa kedua angka mengukur cakupan yang berbeda.

### Dan penolakan itu sendiri ternyata artefak tangkapan layar

Ditelusuri 24-11. `20290821_tisu1.PNG` punya **38% bingkai berupa bilah hitam** —
344+344 piksel dari 1792, bawaan tangkapan layar yang menampilkan foto potret di
layar yang lebih lebar. Bilah itu menyeret rata-rata intensitasnya:

| berkas | bilah hitam | mean UTUH | mean TANPA bilah |
|---|---|---|---|
| `20290821_tisu1.PNG` | 38% | **51,4 → DITOLAK** | **83,5 → lolos** |
| `202804_tolakangin2.PNG` | 38% | 62,1 | 100,8 |
| `20290821_tisu2.PNG` | 7% | 66,5 | 71,1 |

Ambangnya `dark.max_mean = 60`. **Tiga nilai mean terendah di seluruh set adalah
tepat ketiga tangkapan layar**; foto kamera sungguhan semuanya **101–132**, jauh
di atas ambang dan tidak ada satu pun yang mendekatinya. Jadi yang gelap bukan
fotonya, melainkan letterbox-nya.

**Ambangnya sengaja TIDAK diturunkan.** Menyetelnya supaya `tisu1` lolos berarti
mengkalibrasi pada data uji yang tidak sah — kesalahan yang sudah tiga kali
tercatat di proyek ini. Perbaikannya mengganti ketiga tangkapan layar itu dengan
foto kamera, yaitu saran yang sama dengan bagian 1 berkas ini.

**Satu risiko yang belum pernah diperiksa, dan sebaiknya disebut sebagai
keterbatasan:** aplikasi sungguhan mengirim **potongan ketat sebatas kurung
jingga** (sisi pendek 841 piksel), bukan foto utuh — sedangkan `dark.max_mean`
masih nilai awal PRD dan belum pernah diuji terhadap potongan. Itu cacat
struktural yang sama dengan ambang buram yang terbukti salah 19 November.
Pengukuran waktu respons di berkas ini mengirim gambar **utuh**, jadi ia tidak
menguji perilaku tersebut.

---

# CARA MELAPORKANNYA DARI DATA YANG ADA: sebut DUA angka

Tiga berkas tangkapan layar itu tidak perlu dipotret ulang untuk diselesaikan.
Yang lebih kuat untuk jurnal: **laporkan angkanya dua kali** — seluruh 16 berkas,
dan subset 13 foto kamera saja. Pembaca lalu bisa melihat sendiri berapa besar
pengaruh mutu data uji, alih-alih harus memercayai satu angka.

Rinciannya di `08_subset_foto_kamera.txt`, dihitung dari hasil yang sudah ada —
bukan pengukuran baru.

| kondisi | BENAR | SALAH | KOSONG | n | akurasi |
|---|---|---|---|---|---|
| Lokal — seluruh berkas | 13 | 2 | 1 | 16 | 81% |
| **Lokal — foto kamera saja** | **11** | **2** | **0** | **13** | **85%** |
| Deploy — seluruh berkas | 12 | 2 | 2 | 16 | 75% |
| **Deploy — foto kamera saja** | **11** | **2** | **0** | **13** | **85%** |

## Tiga hal yang jatuh dari tabel ini

**1. Pada foto kamera saja, lokal dan deploy SAMA PERSIS: 11 / 2 / 0 = 85%.**

Seluruh selisih 81% lawan 75% yang dibahas di bagian sebelumnya ternyata berasal
dari tiga tangkapan layar itu, dan tidak ada sisanya. Itu penjelasan yang utuh:
begitu ketiganya dikeluarkan, sistem yang ter-deploy berperilaku **identik**
dengan pemanggilan modul di laptop.

**2. Nol jawaban KOSONG pada foto kamera.** Setiap foto kamera mendapat jawaban.
Satu-satunya KOSONG di seluruh set lokal adalah tangkapan layar.

**3. 85% melampaui target PRD ≥ 70% dengan margin lebih lebar**, dan komposisinya
lebih bersih: dua jawaban salah, nol diam.

## Yang tetap harus disebut

- **n turun dari 16 ke 13**, jadi satu berkas kini bernilai 7,7 poin persentase.
  Angka 85% berdiri di atas sampel yang lebih kecil, bukan lebih besar.
- **Dua jawaban salah tidak berubah** (`chees`, `ovaltine`). Tidak ada satu pun
  kesalahan membaca yang hilang karena penyaringan ini — yang hilang hanya
  kegagalan yang disebabkan mutu berkasnya.
- Angka 85% ini **tetap estimasi resubstitusi**: ke-13 foto itu bagian dari set
  yang sama yang dipakai menyetel tujuh keputusan (lihat bagian 1).

## Saran kalimat untuk naskah

> Pengujian dilakukan pada 16 berkas kemasan. Tiga di antaranya berupa tangkapan
> layar, bukan keluaran kamera, sehingga hasilnya dilaporkan untuk kedua
> himpunan: 81% pada seluruh 16 berkas dan 85% pada 13 foto kamera (11 benar,
> 2 salah, 0 tanpa jawaban). Diukur melalui sistem yang ter-deploy, kedua angka
> itu menjadi 75% dan 85% — pada foto kamera, hasil lokal dan hasil ter-deploy
> identik.
