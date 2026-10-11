# SayIt

Teknologi asistif berbasis Computer Vision dan suara untuk penyandang disabilitas netra.
Dokumen persyaratan: `docs/PRD_SayIt_v2_1.md`. Catatan keputusan: `docs/keputusan-teknis.md`.
Konteks untuk Claude Code: `CLAUDE.md`.

## Status modul

| Modul | File | Status |
| :--- | :--- | :--- |
| Konfigurasi | `config/settings.yaml`, `sayit/config.py` | Siap |
| Rekam/putar audio | `sayit/audio/io.py` | Siap (bip sebelum rekam) |
| Speech-to-Text | `sayit/audio/stt.py` | Siap (faster-whisper small + prompt, penjaga halusinasi prompt) |
| Text-to-Speech | `sayit/audio/tts.py` | Siap (gTTS hibrida, klip offline untuk uang dan tanggal) |
| Intent router | `sayit/intent/router.py` | Siap |
| Templat respons & angka ke kata | `sayit/response/` | Siap |
| Quality gate, pra-pemrosesan, uang, dokumen, kedaluwarsa | `sayit/vision/` | Belum |
| Pipeline & Streamlit | `sayit/pipeline.py`, `app.py` | Belum |

## Struktur

```
sayit/
├── .venv/                  lingkungan Python (tidak ikut Git)
├── assets/tts/             klip suara hasil scripts/build_tts_cache.py
├── config/settings.yaml    semua parameter
├── CLAUDE.md               konteks proyek untuk Claude Code
├── docs/                   PRD dan catatan keputusan
├── notebooks/              notebook Colab training model uang
├── fase0/                  skrip dan hasil uji Fase 0
├── models/                 bobot YOLO (tidak ikut Git)
├── sayit/                  kode utama
├── scripts/                build_tts_cache.py, demo_voice.py
└── tests/                  pytest
```

## Menjalankan (Windows, Command Prompt di folder `sayit`)

```bat
.venv\Scripts\activate
pip install -r requirements.txt
pip install -U gTTS
python -m pytest -q
python scripts\build_tts_cache.py
python scripts\demo_voice.py
```

- `pytest` harus lulus semua sebelum kode diubah atau di-commit.
- `build_tts_cache.py` butuh internet dan cukup dijalankan sekali (juga setiap kali kalimat di `sayit/response/templates.py` diubah; pakai `--force` untuk membuat ulang semuanya).
- `demo_voice.py` menguji alur suara tanpa kamera: bicara setelah bip, sistem menampilkan transkrip, intent, dan memutar jawaban **contoh**. Tambahkan `--offline` untuk menguji perilaku tanpa internet.

## Aturan privasi

- Teks yang dibacakan dengan gTTS dikirim ke server Google. Jangan memakai dokumen pribadi asli saat pengujian.
- Audio teks dinamis tidak disimpan ke disk (`tts.cache_dynamic_text: false`).
- Rekaman suara anggota tim di `fase0/fase0_hasil/rekaman/` tidak boleh diunggah ke repositori publik.
