# 2. Status pengujian ulang

**Per 30 Oktober 2026.**

## Jawaban singkat untuk empat pertanyaan

| Pertanyaan | Jawaban |
| :--- | :--- |
| Apakah anotasi sudah diperbaiki? | **Belum** |
| Apakah model dilatih ulang? | **Sudah**, 26 Oktober 2026 — tetapi bukan karena anotasi itu |
| Apakah evaluasi diulang? | **Sudah**, 26 Oktober — tetapi tetap memakai anotasi yang cacat |
| Hasil mana yang terbaru? | **90,1%** (73 benar / 8 salah / 0 diam dari 81 foto) |

Perlu ditegaskan: pelatihan ulang dan evaluasi ulang memang terjadi, tetapi **keduanya
berjalan di atas anotasi yang masih cacat**. Jadi tidak benar bila ditulis bahwa
"anotasi diperbaiki lalu diuji ulang".

---

## Urutan kejadian

| Tanggal | Kejadian |
| :--- | :--- |
| 23 Okt | Anotasi `5000_dipegang_ (3)` **dihapus dengan sengaja** karena fotonya memuat lebih dari satu lembar dan tidak bisa dilabeli dengan yakin |
| 23 Okt | Dataset diunggah ke Google Drive untuk pelatihan |
| 24 Okt | Pelatihan lima lipatan v2 berjalan |
| 26 Okt | Model akhir `money_kfold_v2_final` dilatih, 100 epoch |
| 26 Okt | Evaluasi dijalankan, hasil awal **84,0%** |
| 26 Okt | Ditemukan **alat ukurnya** tidak menjalankan penyaring skor relatif yang dipakai aplikasi; setelah diperbaiki hasilnya **90,1%** |
| 28 Okt | Bobot v2 dipasang ke aplikasi |
| 29 Okt | Ditemukan berkas anotasi yang dihapus 23 Okt **sudah ada kembali** di laptop |
| 30 Okt | Diperiksa isinya: cacat, dan sudah ikut melatih serta menguji v2 |

**Anotasi itu tidak pernah benar-benar keluar dari dataset.** Penghapusannya pada 23
Oktober hanya berupa menghapus berkas `.txt` di laptop, sedangkan salinan di Drive tetap
ada — dan belakangan tersalin balik ke laptop. Jadi keputusan 23 Oktober terbalik
**lewat sinkronisasi berkas, bukan lewat keputusan**.

---

## Kenaikan 84,0% menjadi 90,1% bukan karena model

Ini perlu ditulis eksplisit di naskah supaya tidak disalahartikan.

Modelnya **sama persis**. Yang berubah hanya alat ukurnya: evaluasi di notebook tidak
menjalankan penyaring `relative_score_min = 0,80` yang dipakai aplikasi, yaitu aturan
yang membuang deteksi berskor jauh di bawah deteksi terkuat pada foto yang sama.

Petunjuknya terlihat dari pola kesalahannya — **lima dari tiga belas kesalahan** berbentuk
"satu lembar dijawab dua lembar", misalnya Rp100.000 dijawab Rp102.000. Itu persis pola
yang dirancang dibuang aturan tersebut. Setelah penyaring diterapkan, kelima kesalahan
itu hilang seluruhnya.

| | Sebelum perbaikan alat ukur | Sesudah |
| :--- | ---: | ---: |
| Benar | 68 | **73** |
| Salah | 13 | **8** |
| Diam | 0 | 0 |
| Ketepatan | 84,0% | **90,1%** |

Delapan kesalahan yang tersisa **semuanya** berbentuk satu lembar dijawab satu lembar,
yaitu murni salah mengenali nominal. Tidak ada lagi kesalahan menghitung jumlah lembar.

---

## Apa yang perlu dilakukan untuk benar-benar memperbaikinya

Memperbaiki anotasi itu **bukan sekadar merapikan kotaknya**. Fotonya memuat lebih dari
satu objek uang dan jumlah lembarnya tidak dapat dipastikan (lihat bahan nomor 1), jadi
melabeli ulang berarti menebak — persis kesalahan yang dulu membuat dataset publik tidak
terpakai.

Pilihan yang tersedia:

| Pilihan | Konsekuensi |
| :--- | :--- |
| **A. Keluarkan fotonya dari dataset** (disarankan) | Dataset menjadi 80 foto. **Wajib melatih ulang kelima lipatan dan model akhir**, lalu mengukur ulang. Perlu Colab |
| B. Potret ulang satu lembar Rp5.000 saja sebagai penggantinya | Sama seperti A, ditambah memotret |
| C. Biarkan dan laporkan apa adanya | Tidak ada pekerjaan tambahan; batas pengaruhnya sudah dihitung (90,0%–91,25%) |

Sampai salah satu dikerjakan, **angka yang berlaku tetap 90,1% dengan catatan ini
disebutkan**.
