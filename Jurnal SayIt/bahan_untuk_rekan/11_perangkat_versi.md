# 11. Perangkat dan versi pustaka

Dua lingkungan berbeda. Keduanya perlu disebut terpisah karena **pelatihan dan inferensi
tidak dijalankan di tempat yang sama**.

---

## Pelatihan — Google Colab

| Hal | Nilai |
| :--- | :--- |
| Lingkungan | Google Colab |
| GPU | **NVIDIA Tesla T4** |
| Ultralytics | **8.4.189** |
| Model dasar | YOLOv8n, bobot pralatih |
| RAM, CPU, sistem operasi Colab | **TIDAK TERCATAT** |
| Versi Python, PyTorch, CUDA di Colab | **TIDAK TERCATAT** |

Versi Ultralytics diambil **dari dalam berkas bobot**, bukan dari ingatan. Baris GPU
berasal dari pilihan runtime yang dipakai.

Baris yang ditandai TIDAK TERCATAT dapat dilengkapi dengan menjalankan `!nvidia-smi` dan
`!pip list` di notebook, lalu menyimpan keluarannya.

---

## Inferensi dan pengukuran waktu — laptop pengembang

| Hal | Nilai |
| :--- | :--- |
| Prosesor | **Intel Core i7-13650HX** (Intel64 Family 6 Model 183 Stepping 1) |
| RAM | **20 GB** |
| GPU | NVIDIA RTX 4050 6 GB — **tidak dipakai** |
| Perangkat inferensi | **CPU saja** (`torch.cuda.is_available()` bernilai False) |
| Sistem operasi | **Windows 11**, build 10.0.26300 |
| Python | **3.11.9** |
| PyTorch | **2.14.0+cpu** |
| Ultralytics | **8.4.155** |
| OpenCV | **4.10.0** |
| NumPy | **2.3.5** |

### Mengapa CPU, padahal ada GPU

Disengaja. Aplikasi harus dapat dijalankan anggota tim lain yang tidak punya GPU, dan
seluruh angka latensi yang dilaporkan harus mewakili keadaan itu. Karena itu
`config/settings.yaml` menyetel `device: cpu`.

### Catatan tentang beda versi Ultralytics

Pelatihan memakai **8.4.189**, inferensi memakai **8.4.155**. Perbedaan ini ada dan
sebaiknya disebut di naskah. Bobot tetap terbaca dan berjalan normal, dan seluruh angka
akurasi yang dilaporkan dihitung dengan versi yang sesuai dengan tempat hitungnya:

- angka validasi silang dihitung di Colab dengan 8.4.189
- angka latensi dan contoh prediksi dihitung di laptop dengan 8.4.155

---

## Latensi terukur

Diukur pada **81 foto, lima putaran per foto**, model dipanaskan lebih dulu, memakai
konfigurasi aplikasi yang sebenarnya.

| Tahap | Waktu |
| :--- | ---: |
| Muat bobot (sekali saat aplikasi mulai) | 2,06 detik |
| Panggilan pertama setelah dimuat (dingin) | 2.490 ms |
| **Pra-pemrosesan + inferensi, median (panas)** | **56,4 ms** |
| Rentang antar-foto | 33,7 – 125,3 ms |
| Latensi ujung-ke-ujung intent uang (STT + pipeline + suara) | **1,4 detik** |

### Peringatan tentang angka milidetik

Angka mutlaknya **bergerak antar-sesi** tergantung beban laptop. Pengukuran terpisah
pada hari yang sama memberi 46,9 ms untuk konfigurasi yang sekarang. Yang **stabil
lintas sesi adalah rasionya**.

Contohnya saat CLAHE dibuang: dua sesi pengukuran memberi penurunan 34,3% dan 36,2% —
rasionya konsisten, milidetiknya tidak. **Kutip rasionya, bukan milidetiknya**, kecuali
disertai keterangan sesi pengukurannya.
