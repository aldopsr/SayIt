# 13. Contoh prediksi

## Syarat pemakaian — penting

Gambar di folder ini dihasilkan oleh **model akhir v2 pada foto yang ikut melatihnya**.

Jadi gambar-gambar ini **tidak boleh dipakai sebagai bukti akurasi**. Fungsinya
memperlihatkan **bentuk keluaran sistem**: letak kotak, kelas yang diberikan, skor
keyakinan, serta perbandingan total harapan dan total prediksi.

Angka akurasi yang sah tetap **90,1%** dari validasi silang (lihat `00_BACA_DULU.md`).

## Isi

| Folder | Isi |
| :--- | :--- |
| `benar/` | Tiga contoh jawaban benar: Rp100.000, Rp20.000 (dua foto berbeda) |
| `salah/` | Dua contoh jawaban salah |

Setiap contoh punya dua berkas:

- `*__asli.jpg` — foto masukan
- `*__deteksi.jpg` — foto yang sama dengan kotak, kelas, dan skor; pita bawah memuat
  total harapan, total prediksi, dan statusnya

---

## Temuan dari contoh salah `100000_dipegang_ (4)` — layak masuk pembahasan

Ini bukan sekadar contoh kegagalan, melainkan **bukti sebab-akibat** yang terukur.

| Deteksi | Skor | Letak |
| :--- | ---: | :--- |
| 100000 | 0,86 | lembar uang sungguhan di tangan |
| **1000** | **0,78** | **gambar uang di LAYAR LAPTOP** di latar belakang |

Totalnya menjadi Rp101.000 — **salah**.

Ketika bagian layar laptop disamarkan lalu foto yang sama dideteksi ulang, deteksi palsu
itu **hilang sama sekali**, dan jawabannya menjadi **Rp100.000 (benar)** dengan skor yang
justru sedikit naik menjadi 0,88.

**Kesimpulannya: model tidak membedakan uang fisik dari citra uang di layar.** Ini bukan
dugaan — penyebabnya dihilangkan, lalu kesalahannya ikut hilang.

Pola yang sama sudah tercatat saat pelabelan: deteksi palsu paling sering muncul pada
gambar uang di layar laptop di bagian atas bingkai.

### Mengapa penyaring skor relatif tidak menolongnya

`relative_score_min = 0,80` membuang deteksi yang skornya di bawah 0,80 kali skor
tertinggi. Di sini: 0,78 dibandingkan 0,80 × 0,86 = 0,688. Karena 0,78 lebih besar dari
0,688, deteksi palsu itu **lolos**.

Jadi penyaring tersebut bekerja sesuai rancangannya, tetapi jarak skornya memang tidak
cukup jauh. Ini batas dari aturan pasca-pemrosesan, dan hanya bisa diperbaiki lewat data
latih yang memuat contoh negatif berupa layar berisi gambar uang.

---

## Catatan privasi

Dua gambar disamarkan sebagian:

| Berkas | Yang disamarkan | Alasan |
| :--- | :--- | :--- |
| `salah/100000_dipegang_ (4)` | pita atas 25% | layar laptop memuat nama orang dan angka transaksi |
| `benar/20000_dipegang_2` | pita atas 29% | ada orang lain di latar belakang |

Pada `100000_dipegang_ (4)__deteksi.jpg`, **kotak deteksi dihitung dari foto asli yang
belum disamarkan**, lalu digambar di atas versi yang sudah disamarkan. Jadi kotak dan
skornya adalah keadaan sebenarnya, hanya isi layarnya yang tidak terbaca.

Berkas asli yang belum disamarkan ada di dataset dan **jangan dilampirkan ke naskah**.

---

## Mengapa hanya dua contoh salah

Pada 81 foto lokal, model akhir hanya salah pada **dua** foto — karena foto-foto itu
ikut melatihnya. Pada evaluasi yang sah (validasi silang) kesalahannya **delapan**.
Daftar lengkap kedelapan kesalahan itu ada di `03_hasil_per_foto.csv`, kolom `status`
bernilai `SALAH`.

## Konfigurasi yang dipakai

Sama persis dengan aplikasi pada 30 Oktober 2026: pra-pemrosesan `[resize]` tanpa CLAHE,
`score_min = 0,30`, `relative_score_min = 0,80`, `nested_area_ratio = 0,85`,
`imgsz = 640`, CPU. Lihat `10_konfigurasi_aplikasi/`.
