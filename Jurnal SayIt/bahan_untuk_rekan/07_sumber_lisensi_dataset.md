# 7. Sumber dan lisensi dataset

## Dataset publik

| Hal | Nilai |
| :--- | :--- |
| Penyedia | Roboflow |
| Workspace | `mochammadalthofsr-gmail-com` |
| Proyek | `deteksi-rupiah-jkkmu-zagcv` |
| Versi | 1 |
| Cara dipakai | mode `label_dari_nama` |
| **Tautan langsung** | **TIDAK TERCATAT** |
| **Tanggal unduh** | **TIDAK TERCATAT** |
| **Lisensi** | **TIDAK TERCATAT** |
| **Berkas lisensi** | **TIDAK ADA** |

Ketiga baris terakhir harus ditandai di naskah sebagai keterbatasan, atau dilengkapi
dengan membuka kembali proyeknya di Roboflow.

### Mengapa labelnya tidak dipakai apa adanya

Dataset ini **terbukti punya label tertukar** — uang Rp100.000 diberi label 5000, dan
seterusnya. Karena itu dipakai dengan mode `label_dari_nama`: label aslinya diabaikan,
dan nominal diambil dari nama berkas. Gambar yang nominalnya tidak dapat diverifikasi
dari nama berkas dibuang.

Dataset ini juga memuat **tiga salinan augmentasi per foto asal**. Hanya satu salinan per
foto asal yang dipakai, yaitu yang bingkai hitamnya paling sedikit, supaya hasil rotasi
Roboflow tidak ikut terbawa sebagai data berbeda.

Pernah diperoleh skor 0,947 dari dataset ini. **Skor itu tidak valid** dan tidak dipakai
di mana pun.

### Dataset publik kedua

Daftar dataset pada notebook memuat entri kedua, tetapi **slug proyeknya masih berupa
teks pengisi** (`isi-slug-project-dataset-B`) pada salinan notebook yang ada di repo.
Apakah entri itu benar-benar diisi saat menjalankan di Colab **tidak dapat dipastikan
dari berkas hasil**.

### Gambar latar COCO128

Notebook punya opsi menambahkan gambar latar tanpa uang dari COCO128 sebagai contoh
negatif. **Apakah opsi ini aktif saat pelatihan v2 tidak tercatat** pada berkas hasil.

---

## Foto sendiri

| Hal | Nilai |
| :--- | :--- |
| Jumlah | 81 foto, 81 berlabel, 82 kotak |
| Cara dipakai | mode `percaya_label` |
| Perangkat | kamera ponsel |
| Latar | meja kayu, dipegang di depan laptop, serta kiriman anggota tim dengan latar beragam |
| Lisensi | milik tim sendiri |

Sebarannya **sengaja tidak seimbang**. Tambahan pada 23 Oktober diarahkan ke tiga kelas
yang paling lemah pada evaluasi sebelumnya (Rp5.000, Rp2.000, Rp100.000), bukan dibagi
rata. Ini keputusan desain eksperimen, bukan kelalaian pengumpulan data.

Rinciannya di `08_rekap_dataset.csv`.

---

## Jumlah citra setelah penyaringan

**1.395 gambar** masuk ke proses pelatihan dan evaluasi v2.

| Bagian | Jumlah |
| ---: | :--- |
| Foto sendiri | **81** |
| Bukan foto sendiri | **1.314** |
| **Total** | **1.395** |

Angka ini **dapat diverifikasi**, tidak diambil dari ingatan. Setiap putaran pelatihan
menulis berkas `sidik_lipatan.json` yang memuat jumlah gambar dan jumlah foto uji, dan
kelima lipatan mencatat angka yang sama. Lihat `04_pembagian_lipatan.csv` dan tabel
identitas lipatan pada naskah.

**Perincian 1.314 gambar itu ke dataset publik pertama, dataset kedua, dan gambar latar
COCO128 TIDAK TERSEDIA.** Yang tercatat hanya jumlah totalnya.

---

## Tahun emisi

Model memakai **tujuh kelas nominal**, bukan empat belas kelas nominal × tahun emisi.

Metadata tahun emisi **tidak pernah dilabeli** dan **tidak ada di nama berkas**. Karena
itu cakupan tiap emisi dan perbedaan kinerjanya **tidak dapat dilaporkan sama sekali** —
bukan belum dihitung, melainkan datanya memang tidak ada.

Mengadakannya berarti melabeli ulang seluruh dataset dengan 14 kelas lalu melatih dari
nol.
