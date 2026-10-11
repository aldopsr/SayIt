# Backend SayIt untuk Hugging Face Spaces (SDK: docker).
#
# Vercel tidak bisa memuat ini: torch 531 MB + paddle 400 MB + cv2 158 MB,
# sedangkan batas serverless function Vercel 250 MB. Vercel hanya untuk frontend.
#
# Bobot model (`models/*.pt`, 130 MB) TIDAK ikut Git. Unggah langsung ke repo
# Space-nya; HF memakai Git LFS untuk berkas besar.

FROM python:3.11-slim

# libGL dan libglib dibutuhkan opencv; ffmpeg tidak perlu karena klien
# sudah mengirim WAV (lihat keWav di web/app/page.js).
RUN apt-get update && apt-get install -y --no-install-recommends \
        libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY sayit/ sayit/
COPY server/ server/
COPY config/ config/
COPY assets/ assets/
COPY models/ models/

# oneDNN tidak bisa dipakai paddlepaddle 3.3.1 - lihat config/settings.yaml.
ENV FLAGS_use_mkldnn=0 \
    PYTHONUNBUFFERED=1

# HF Spaces mengharapkan port 7860.
EXPOSE 7860
CMD ["uvicorn", "server.app:app", "--host", "0.0.0.0", "--port", "7860"]
