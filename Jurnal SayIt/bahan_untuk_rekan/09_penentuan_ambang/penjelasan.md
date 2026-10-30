# 9. Penentuan ambang

Dua ambang dipakai pada modul uang, dan **dasar buktinya tidak sama kuat**. Perbedaan itu
sengaja disebutkan.

---

## 9.1 Ambang skor `score_min = 0,30`

**Data yang dipakai memilihnya:** hasil validasi silang lima lipatan, 81 foto, yaitu data
yang sama dengan hasil utama. Dihitung ulang memakai bobot lipatan yang sudah ada,
**tanpa melatih ulang**.

Berkas: `sapuan_ambang_v2.csv`

| Ambang | Benar | Salah | Diam | Ketepatan |
| ---: | ---: | ---: | ---: | ---: |
| 0,15 | 73 | 8 | 0 | 90,1% |
| 0,20 | 73 | 8 | 0 | 90,1% |
| 0,25 | 73 | 8 | 0 | 90,1% |
| **0,30** | **73** | **8** | **0** | **90,1%** |
| 0,35 | 72 | 7 | 2 | 88,9% |
| 0,40 | 71 | 7 | 3 | 87,7% |
| 0,50 | 70 | 7 | 4 | 86,4% |
| 0,60 | 63 | 6 | 12 | 77,8% |

### Alasan memilih 0,30

Rentang 0,15 sampai 0,30 memberi hasil **identik**. Dipilih 0,30, yaitu **tepi atas
dataran itu**, dengan dua pertimbangan:

1. Menurunkannya di bawah 0,30 **tidak menambah apa pun** pada data ini, sementara
   risikonya nyata pada data baru: deteksi palsu berskor rendah pada latar ramai yang
   belum pernah kami foto akan menambah jawaban **salah**.
2. Menaikkannya ke 0,35 menukar **satu jawaban benar dengan dua kali diam**, hanya untuk
   mengurangi satu jawaban salah. Pertukaran itu tidak sepadan.

Nilai ini **menyimpang dari rancangan awal yang menulis 0,50**, dan penyimpangannya
disengaja serta berdasar pengukuran.

### Keterbatasan yang wajib disebut

Ambang ini **dipilih memakai data evaluasi yang sama dengan yang dilaporkan**. Jadi
angka 90,1% sedikit optimistis sebagai estimasi kinerja pada data baru. Cara yang benar
adalah validasi silang bersarang atau data uji terpisah; keduanya belum dikerjakan.

---

## 9.2 Penyaring skor relatif `relative_score_min = 0,80`

Aturannya: buang deteksi yang skornya **di bawah 0,80 kali skor deteksi terkuat pada
foto yang sama**. Dijalankan **sesudah** pembuangan kotak bersarang.

### Mengapa diperlukan

Ambang mutlak tidak menangkap pola kesalahan yang sebenarnya. Terukur pada 35 foto:
deteksi palsu lolos dengan skor **0,586–0,752**, sementara lembar aslinya **0,901–0,941**
**pada foto yang sama**. Yang membedakan bukan nilai skornya, melainkan **jaraknya**.

Arah kesalahannya selalu sama: **menggelembungkan jumlah**, tidak pernah mengecilkan.
Contohnya Rp5.000 diucapkan Rp25.000. Bagi pengguna tunanetra itu arah yang paling
berbahaya — ia menyerahkan uang lebih banyak daripada yang dikiranya.

### Dasar buktinya LEBIH LEMAH daripada `score_min`

Ini harus ditulis apa adanya.

| | Dasar |
| :--- | :--- |
| Sapuan yang memilih 0,80 | **35 foto yang seluruhnya ikut melatih model** saat itu |
| Hasil sapuan | 0 memberi 32/3/0; 0,70 memberi 33/2/0; **0,75–0,90 semuanya 34/1/0** |
| Diuji ulang pada data bersih | 14 foto yang belum pernah dilihat model: **nol efek**, semua nilai memberi hasil identik |

Jadi nilai 0,80 **tidak terbukti menaikkan akurasi pada data bersih**. Ia dipertahankan
sebagai **penjaga** terhadap pola kesalahan menggelembungkan jumlah yang nyata dan
berbahaya, bukan sebagai sumber peningkatan akurasi.

**Jangan tulis di naskah bahwa penyaring ini meningkatkan akurasi.** Datanya tidak
mendukung.

### Satu risiko yang belum dapat diuji

Data uji **banyak lembar hanya satu foto**. Jadi belum diketahui apakah ambang 0,80 ikut
membuang lembar kedua yang sah pada foto berisi beberapa lembar dengan pencahayaan tidak
merata. Wajib diukur ulang begitu foto banyak lembar tersedia.

---

## 9.3 Ambang lain pada modul uang

| Parameter | Nilai | Dasar |
| :--- | ---: | :--- |
| `nested_area_ratio` | 0,85 | Kotak yang ≥85% luasnya berada di dalam kotak sekelas dianggap uang yang sama |
| `same_class_iou` | 0,0 (mati) | Disapu dua kali dengan model berbeda, **nol efek** pada keduanya |
| `conflict_iou` | 0,5 | Dua kelas berbeda bertindihan di atas ini → hasil ditandai tidak yakin, sistem menolak menyebut angka |
| `imgsz` | 640 | Sapuan 06-10: 640 terbaik; **1280 justru jatuh ke 48,6%**. Menaikkan di atas ukuran latih merusak |
| `augment` (TTA) | mati | Sapuan 06-10: 640+TTA 62,9% lawan 640 tanpa TTA 65,7% |

Urutan pasca-pemrosesan **tidak boleh ditukar**: ambang skor → buang kotak bersarang →
penyaring skor relatif. Pernah dibalik dan langsung menggagalkan kasus uji: lembar utuh
bisa berskor lebih rendah daripada potret di dalamnya, sehingga penyaring relatif justru
membuang lembar aslinya dan menyisakan potretnya.
