---
title: Gungfi Webhook BE
colorFrom: blue
colorTo: green
sdk: docker
pinned: false
---

# Gungfi Webhook BE

FastAPI backend pengganti workflow n8n `IniBukanBuatHackathon.json`.

Flow yang dipertahankan:

1. Terima Cloudinary webhook di `POST /cloudinary-trigger`.
2. Parse `body.context.custom` menjadi `id`, `latitude`, `longitude`, `description`, dan `before_img_url`.
3. Jalankan loop protection: kalau `Id` kosong, tidak meneruskan proses.
4. Download image dari Cloudinary, lalu kirim multipart form-data ke BE AI Pipeline `POST /process`.
5. Update Supabase tabel `reports` dengan `destruct_class`, `location_score`, `total_score`, dan `status=complete`.

## Setup

```powershell
uv venv
uv sync
Copy-Item .env.example .env
```

Isi `.env`, terutama `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, dan `CLOUDINARY_API_SECRET`.

## Run

```powershell
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Cloudinary notification URL:

```text
https://your-domain/cloudinary-trigger
```

Set URL tersebut sebagai global webhook Notification URL di Cloudinary Console, atau di upload preset yang dipakai aplikasi. Dengan begitu aplikasi upload tidak perlu mengirim parameter `notification_url` pada setiap request.

## Test

```powershell
uv run pytest
```

## CI/CD ke Hugging Face Spaces

Repository ini siap dideploy sebagai Docker Space. Buat Space di Hugging Face dengan SDK `Docker`, lalu tambahkan secret berikut di GitHub repository:

```text
HF_USERNAME=your-huggingface-username
HF_TOKEN=hf_...
HF_SPACE_ID=your-huggingface-username/your-space-name
```

Tambahkan juga environment variable aplikasi di Hugging Face Space settings:

```text
APP_NAME=gungfi-webhook-be
LOG_LEVEL=INFO
WEBHOOK_PATH=/cloudinary-trigger
AI_PIPELINE_URL=https://be-aipipeline.bluecoast-4238dc8b.eastasia.azurecontainerapps.io
AI_PIPELINE_TIMEOUT_SECONDS=60
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=replace-me
SUPABASE_TABLE=reports
CLOUDINARY_API_SECRET=replace-me
CLOUDINARY_SIGNATURE_REQUIRED=true
CLOUDINARY_SIGNATURE_TOLERANCE_SECONDS=7200
```

Setiap push ke branch `main` akan menjalankan test, lalu melakukan force-push isi repo ke Hugging Face Space.

## Test Upload Cloudinary

Tambahkan ini ke `.env`:

```text
CLOUDINARY_CLOUD_NAME=...
CLOUDINARY_API_KEY=...
CLOUDINARY_API_SECRET=...
```

Untuk test upload file `img/DSC06041.JPG` ke Cloudinary:

```powershell
uv run python scripts/upload_cloudinary_test.py
```

Kalau ingin Cloudinary memanggil FastAPI lokal, expose dulu server lokal ke HTTPS publik:

```powershell
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000
ngrok http 8000
```

Setelah dapat URL HTTPS dari tunnel, set global webhook Notification URL atau upload preset Notification URL di Cloudinary ke `https://your-tunnel-url/cloudinary-trigger`, lalu jalankan lagi script upload Cloudinary.
