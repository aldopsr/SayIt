# Folder "sesudah" sengaja kosong

**Anotasi ini belum diperbaiki per 30 Oktober 2026.**

Isi folder `sebelum/` adalah keadaan yang masih berlaku sekarang, bukan keadaan lama.

## Mengapa belum diperbaiki

Memperbaikinya bukan sekadar merapikan kotak. Fotonya memuat **lebih dari satu objek
uang** dan jumlah lembarnya tidak dapat dipastikan dari gambar:

- Satu lembar **Rp5.000** dipegang di tangan — angka "5000" terbaca jelas
- Ada **tumpukan Rp20.000** di meja kanan bawah — angka "20000" terbaca pada lembar
  teratas, tetapi **jumlah lembar dalam tumpukan tidak dapat dihitung** karena bertumpuk
- Di bagian bawah lembar yang dipegang tampak tepi nota lain yang tidak dapat
  dipastikan nominalnya

Melabeli ulang berarti **menebak jumlah lembar**. Itu persis jenis kesalahan yang dulu
membuat dataset publik tidak dapat dipakai (label tertukar), sehingga kami tidak
melakukannya.

## Yang cacat pada anotasi sekarang

| Masalah | Bukti |
| :--- | :--- |
| Objek tidak lengkap | Hanya satu kotak, padahal ada uang lain di bingkai yang sama |
| Kotak tidak melokalisasi | Lebar kotak **99,87% dari lebar bingkai**, tinggi 70,82%. Kotak itu mencakup tangan, meja, laptop, dan orang di latar |

Isi berkas labelnya satu baris:

    2 0.499893 0.485510 0.998700 0.708150

Kelas 2 adalah Rp5.000. Empat angka berikutnya adalah pusat-x, pusat-y, lebar, dan
tinggi dalam koordinat ternormalisasi.

## Akibatnya pada hasil

Anotasi ini **ikut melatih** model (pada empat lipatan) dan **ikut menguji** model (pada
satu lipatan, dengan harapan total Rp5.000).

- Saat melatih: uang yang tidak dilabeli mengajari model bahwa area itu **bukan uang**
- Saat menguji: bila model benar mendeteksi lebih dari satu lembar, ia justru dinilai
  **salah**

Batas pengaruhnya: bila foto ini dikeluarkan, ketepatan menjadi **72/80 (90,0%)** atau
**73/80 (91,25%)**, bergantung pada apakah foto ini semula dinilai benar. Penilaiannya
tidak dapat ditelusuri karena nama berkas tersalin tidak dapat dipetakan balik.

## Langkah perbaikan yang disarankan

Keluarkan foto ini dari dataset (bukan melabeli ulang), lalu **latih ulang kelima lipatan
dan model akhir**, kemudian ukur ulang. Perlu dijalankan di Google Colab.

Memindahkan fotonya keluar folder dataset, bukan sekadar menghapus berkas `.txt` —
penghapusan berkas label saja sudah terbukti tidak bertahan terhadap sinkronisasi Drive.
