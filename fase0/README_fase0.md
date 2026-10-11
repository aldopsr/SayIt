# SayIt Fase 0: Uji STT dan TTS di Windows

Tujuan: memilih ukuran model Whisper dan mesin TTS berdasarkan data, bukan tebakan (PRD Bagian 15, butir 1–3).

## 1. Instalasi (sekali saja)

1. Pasang **Python 3.11** dari python.org. Saat instalasi, centang **Add python.exe to PATH**.
2. Buka **Command Prompt** di folder ini, lalu jalankan:

```bat
py -3.11 -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements-fase0.txt
```

Jika muncul error DLL saat memuat torch atau faster-whisper, pasang **Microsoft Visual C++ Redistributable (x64)** terbaru, lalu coba lagi.

Unduhan pertama model Whisper dan MMS-TTS berukuran ratusan MB dan membutuhkan internet. Setelah itu, keduanya berjalan offline.

## 2. Urutan uji

Selalu aktifkan venv dulu: `.venv\Scripts\activate`

| Langkah | Perintah | Keterangan |
| :--- | :--- | :--- |
| Cek lingkungan | `python fase0_audio.py cek` | Mengecek pustaka, level mikrofon, dan daftar suara Windows |
| Rekam (tenang) | `python fase0_audio.py rekam --penutur nama` | 15 kalimat perintah, 4 detik per kalimat |
| Rekam (bising) | `python fase0_audio.py rekam --penutur nama --kondisi bising` | Nyalakan TV/musik pelan atau rekam di tempat ramai |
| Uji STT | `python fase0_audio.py stt --model tiny base small` | Bisa 10–30 menit di CPU |
| Pembanding prompt | `python fase0_audio.py stt --model small --tanpa-prompt` | Mengukur manfaat `initial_prompt` |
| Uji TTS | `python fase0_audio.py tts` | Hasil suara di `fase0_hasil/tts/` |

Target rekaman: **minimal 3 penutur**, masing-masing kondisi tenang dan bising. Semakin beragam suaranya (laki-laki, perempuan, logat), semakin bisa dipercaya hasilnya.

Setelah uji TTS, minta minimal 3 anggota tim mendengarkan setiap file suara dan mengisi `fase0_hasil/penilaian_tts.csv`. Perhatikan terutama apakah angka seperti "seratus sepuluh ribu" terdengar jelas.

## 3. Aturan keputusan

**STT:** pilih model **terkecil** yang memenuhi:
- WER rata-rata ≤ 25% (target PRD), termasuk pada kondisi bising;
- latensi median ≤ 3 detik untuk rekaman 4 detik (agar total alur tetap ≤ 8 detik).

**TTS:** pilih mesin **offline** yang memenuhi:
- rata-rata skor kejelasan ≥ 4 dari minimal 3 penilai;
- waktu sintesis ≤ 2 detik per kalimat.

gTTS hanya boleh menjadi cadangan berlabel "mode online".

Catatan lisensi: model MMS-TTS berlisensi CC-BY-NC 4.0 (non-komersial). Aman untuk tugas kuliah, tetapi wajib dicantumkan di laporan.

## 4. Yang dikirim ke tim / Claude

- Output lengkap `python fase0_audio.py cek`
- Tabel **RINGKASAN STT** dari setiap uji
- Tabel **RINGKASAN TTS** dan `penilaian_tts.csv` yang sudah diisi
- Spesifikasi laptop: prosesor dan RAM

Isi `fase0_hasil/rekaman/` berisi suara anggota tim. Jangan diunggah ke repositori publik.
