# 🏠 FamilyCentralAPI

> Lightweight REST API berbasis FastAPI untuk mengelola akun utilitas keluarga dan mengecek tagihan PLN, PDAM, serta Indihome dari satu service internal.

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.128-green.svg)](https://fastapi.tiangolo.com)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 📌 Ringkasan

**FamilyCentralAPI** dirancang sebagai API kecil untuk home server, dashboard keluarga, atau otomasi reminder tagihan. Project ini berfokus pada prinsip:

- **Lightweight** — stack minimal: FastAPI, SQLAlchemy async, SQLite, dan httpx.
- **Scalable** — struktur layer API/service/schema/model terpisah sehingga provider atau storage bisa dikembangkan bertahap.
- **Secure by default** — endpoint bisnis dilindungi `X-FAMILY-KEY`, API docs tidak diekspos secara default, dan secret provider dibaca dari environment.
- **Professional code quality** — request divalidasi Pydantic, error ditangani konsisten, cache fallback tersedia, dan test regresi disediakan.

### Fitur Utama

| Fitur | Keterangan |
| --- | --- |
| ⚡ PLN Postpaid | Cek tagihan listrik pascabayar. |
| 💧 PDAM Padang | Cek tagihan air PDAM Kota Padang. |
| 🌐 Indihome | Cek tagihan internet Telkom/Indihome. |
| 🧾 Saved Accounts | Simpan, ubah, list, dan hapus akun utilitas keluarga. |
| 🔐 API Key Auth | Protected endpoint wajib header `X-FAMILY-KEY`. |
| 💾 Smart Cache | Cache hasil cek tagihan selama 12 jam dan fallback ke stale cache jika provider gagal. |
| 🧪 Regression Tests | Test untuk auth, validasi request, dan parsing konfigurasi. |

---

## 🏗️ Arsitektur Proyek

```text
FamilyCentralAPI/
├── app/
│   ├── main.py                   # FastAPI app, middleware, routes, lifespan
│   ├── api/v1/endpoints/         # Endpoint HTTP versi 1
│   │   ├── bills.py              # API cek tagihan dan saved bills
│   │   └── utility_accounts.py   # API CRUD akun utilitas
│   ├── core/                     # Config, security middleware, exceptions
│   ├── db/                       # Async SQLAlchemy engine/session/base
│   ├── models/                   # SQLAlchemy models
│   ├── schemas/                  # Pydantic request/response schemas
│   └── services/                 # Business logic dan provider integrations
│       ├── bill_orchestrator.py  # Cache-first bill orchestration
│       └── bills/                # PLN, PDAM, Indihome checker
├── tests/                        # Regression tests
├── .env.example                  # Template konfigurasi environment
├── pyproject.toml                # Metadata dan konfigurasi tooling
├── requirements.txt              # Dependency lock/pin sederhana
└── README.md
```

### Alur Cek Tagihan

```text
Request /api/v1/bills/check
        │
        ▼
Validasi provider + customer_id digit-only
        │
        ▼
Cek cache bill_cache (< 12 jam?)
        │
   ┌────┴────┐
   │ Fresh   │ Stale/miss/force_refresh
   ▼         ▼
Return   Panggil provider checker
cache         │
              ▼
       Success? update cache
              │
              ▼
       Return fresh response
```

Jika provider gagal dan cache lama tersedia, API mengembalikan data cache dengan pesan `[STALE CACHE]`.

---

## ⚙️ Konfigurasi Environment

Copy `.env.example` menjadi `.env`, lalu isi minimal `FAMILY_API_KEY`.

```bash
cp .env.example .env
```

Contoh konfigurasi aman untuk local development:

```env
APP_NAME=FamilyCentralAPI
DEBUG=false
EXPOSE_API_DOCS=true
DATABASE_URL=sqlite+aiosqlite:///./family.db
FAMILY_API_KEY=change-with-a-long-random-secret
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8080

# Provider mode
PLN_CHECK_URL=mock
PDAM_CHECK_URL=mock
INDIHOME_CHECK_URL=mock

# Jika memakai endpoint Sepulsa nyata, isi secret ini via environment/secret manager.
SEPULSA_API_KEY=

HTTP_TIMEOUT=30.0
HTTP_MAX_RETRIES=3
```

### Daftar Environment Variable

| Variable | Default | Wajib? | Keterangan |
| --- | --- | --- | --- |
| `APP_NAME` | `FamilyCentralAPI` | Tidak | Nama aplikasi. |
| `DEBUG` | `false` | Tidak | Aktifkan mode debug. Jangan aktifkan di production. |
| `EXPOSE_API_DOCS` | `false` | Tidak | Jika `true`, membuka `/docs`, `/redoc`, dan `/openapi.json`. Docs juga aktif otomatis saat `DEBUG=true`. |
| `DATABASE_URL` | `sqlite+aiosqlite:///./family.db` | Tidak | URL database async SQLAlchemy. |
| `FAMILY_API_KEY` | `None` | **Ya** | Secret yang harus dikirim lewat header `X-FAMILY-KEY`. Jika kosong, protected endpoint akan fail-closed dengan `503 AUTH_NOT_CONFIGURED`. |
| `ALLOWED_ORIGINS` | `http://localhost:3000,http://localhost:8080` | Tidak | Origin CORS. Bisa list JSON atau comma-separated string. |
| `PLN_CHECK_URL` | kosong | Tidak | Isi `mock` untuk simulasi PLN. Integrasi saat ini memakai checker Sepulsa jika tidak mock. |
| `PDAM_CHECK_URL` | kosong | Tidak | Isi `mock` untuk simulasi PDAM. |
| `INDIHOME_CHECK_URL` | kosong | Tidak | Isi `mock` untuk simulasi Indihome. |
| `PLN_API_KEY` / `PDAM_API_KEY` / `INDIHOME_API_KEY` | kosong | Tidak | Reserved untuk endpoint provider khusus. |
| `SEPULSA_API_KEY` | kosong | Tergantung provider | API key Sepulsa. Tidak ada secret hard-coded di kode. |
| `HTTP_TIMEOUT` | `30.0` | Tidak | Timeout request provider dalam detik. |
| `HTTP_MAX_RETRIES` | `3` | Tidak | Reserved untuk strategi retry. |

> **Catatan keamanan:** jangan commit file `.env`, jangan gunakan secret pendek, dan gunakan secret manager/environment variable pada production.

---

## 🚀 Instalasi dan Menjalankan Project

### Prasyarat

- Python 3.10+
- pip
- Git

### 1. Clone Repository

```bash
git clone https://github.com/41116120010/family-central-bill.git
cd family-central-bill
```

### 2. Buat Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate      # Linux/macOS
# venv\Scripts\activate      # Windows PowerShell/CMD
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

Untuk development tooling dari `pyproject.toml`:

```bash
pip install -e '.[dev]'
```

### 4. Setup `.env`

```bash
cp .env.example .env
```

Edit `.env`:

```env
FAMILY_API_KEY=change-with-a-long-random-secret
DEBUG=false
EXPOSE_API_DOCS=true
PLN_CHECK_URL=mock
PDAM_CHECK_URL=mock
INDIHOME_CHECK_URL=mock
```

### 5. Jalankan Server

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Health check:

```bash
curl http://localhost:8000/health
```

Response:

```json
{"status":"healthy"}
```

### 6. Buka Interactive API Docs

`/docs`, `/redoc`, dan `/openapi.json` **tidak aktif secara default**. Untuk local development, set salah satu:

```env
EXPOSE_API_DOCS=true
# atau
DEBUG=true
```

Lalu akses:

- Swagger UI: <http://localhost:8000/docs>
- ReDoc: <http://localhost:8000/redoc>
- OpenAPI JSON: <http://localhost:8000/openapi.json>

---

## 🔐 Autentikasi

Endpoint berikut public:

- `GET /`
- `GET /health`
- Docs route hanya public jika `EXPOSE_API_DOCS=true` atau `DEBUG=true`.

Semua endpoint `/api/v1/**` wajib memakai header:

```http
X-FAMILY-KEY: change-with-a-long-random-secret
```

Contoh error:

```json
{
  "detail": "Missing X-FAMILY-KEY header",
  "error_code": "AUTH_MISSING_KEY"
}
```

Jika `FAMILY_API_KEY` belum dikonfigurasi, protected endpoint akan mengembalikan:

```json
{
  "detail": "API authentication is not configured",
  "error_code": "AUTH_NOT_CONFIGURED"
}
```

---

## 📚 API Documentation

### Konvensi Umum

#### Base URL

```text
http://localhost:8000
```

#### Header Protected Endpoint

```http
X-FAMILY-KEY: <FAMILY_API_KEY>
Content-Type: application/json
```

#### Provider

Nilai provider yang valid:

- `PLN`
- `PDAM`
- `INDIHOME`

#### Status Tagihan

| Status | Arti |
| --- | --- |
| `UNPAID` | Ada tagihan belum dibayar. |
| `PAID` | Tidak ada tagihan / sudah lunas. |
| `OVERDUE` | Tagihan lewat jatuh tempo. |
| `NOT_FOUND` | Nomor pelanggan tidak ditemukan/tidak valid di provider. |
| `ERROR` | Terjadi error saat cek provider. |

#### Validasi Input Penting

- `customer_id` akan di-trim dan wajib hanya digit (`0-9`).
- `customer_id` maksimal 50 karakter pada schema umum.
- Checker provider tetap punya validasi spesifik, misalnya PLN 12 digit.
- `account_id` path parameter wajib integer `>= 1`.
- Pagination `skip >= 0`, `limit` antara `1` dan `100`.

---

## 🩺 Health Endpoints

### `GET /`

Root endpoint untuk info aplikasi.

```bash
curl http://localhost:8000/
```

Response contoh:

```json
{
  "app": "FamilyCentralAPI",
  "version": "0.1.0",
  "status": "running",
  "database": "SQLite"
}
```

### `GET /health`

Endpoint liveness sederhana.

```bash
curl http://localhost:8000/health
```

Response:

```json
{
  "status": "healthy"
}
```

---

## 🧾 Utility Accounts API

Utility account adalah akun pelanggan utilitas yang disimpan di database lokal agar bisa dicek ulang tanpa mengirim provider/customer_id setiap kali.

### 1. List Utility Accounts

```http
GET /api/v1/utility-accounts/?skip=0&limit=100
```

Query parameters:

| Parameter | Default | Validasi | Keterangan |
| --- | --- | --- | --- |
| `skip` | `0` | `>= 0` | Jumlah data yang dilewati. |
| `limit` | `100` | `1..100` | Maksimal data yang dikembalikan. |

Contoh:

```bash
curl 'http://localhost:8000/api/v1/utility-accounts/?skip=0&limit=20' \
  -H 'X-FAMILY-KEY: change-with-a-long-random-secret'
```

Response `200`:

```json
[
  {
    "provider": "PLN",
    "customer_id": "123456789012",
    "alias": "Rumah Utama",
    "id": 1,
    "is_active": true,
    "created_at": "2026-05-29T10:00:00",
    "updated_at": "2026-05-29T10:00:00"
  }
]
```

### 2. Create Utility Account

```http
POST /api/v1/utility-accounts/
```

Request body:

```json
{
  "provider": "PLN",
  "customer_id": "123456789012",
  "alias": "Rumah Utama",
  "is_active": true
}
```

Contoh:

```bash
curl -X POST http://localhost:8000/api/v1/utility-accounts/ \
  -H 'X-FAMILY-KEY: change-with-a-long-random-secret' \
  -H 'Content-Type: application/json' \
  -d '{"provider":"PLN","customer_id":"123456789012","alias":"Rumah Utama","is_active":true}'
```

Response `201`:

```json
{
  "provider": "PLN",
  "customer_id": "123456789012",
  "alias": "Rumah Utama",
  "id": 1,
  "is_active": true,
  "created_at": "2026-05-29T10:00:00",
  "updated_at": "2026-05-29T10:00:00"
}
```

Error umum:

- `409 RESOURCE_DUPLICATE` jika `customer_id` sudah ada.
- `422` jika `customer_id` mengandung karakter selain digit.

### 3. Get Utility Account by ID

```http
GET /api/v1/utility-accounts/{account_id}
```

Contoh:

```bash
curl http://localhost:8000/api/v1/utility-accounts/1 \
  -H 'X-FAMILY-KEY: change-with-a-long-random-secret'
```

Response `200`: sama seperti response create.

Error umum:

- `404 RESOURCE_NOT_FOUND` jika account tidak ada.
- `422` jika `account_id < 1`.

### 4. Update Utility Account

```http
PATCH /api/v1/utility-accounts/{account_id}
```

Semua field optional; hanya field yang dikirim akan diubah.

Request body contoh:

```json
{
  "alias": "Rumah Orang Tua",
  "is_active": false
}
```

Contoh:

```bash
curl -X PATCH http://localhost:8000/api/v1/utility-accounts/1 \
  -H 'X-FAMILY-KEY: change-with-a-long-random-secret' \
  -H 'Content-Type: application/json' \
  -d '{"alias":"Rumah Orang Tua","is_active":false}'
```

Response `200`: object utility account terbaru.

### 5. Delete Utility Account

```http
DELETE /api/v1/utility-accounts/{account_id}
```

Contoh:

```bash
curl -X DELETE http://localhost:8000/api/v1/utility-accounts/1 \
  -H 'X-FAMILY-KEY: change-with-a-long-random-secret'
```

Response sukses: `204 No Content`.

---

## 💰 Bills API

### 1. Check Bill by Provider and Customer ID

```http
POST /api/v1/bills/check?force_refresh=false
```

Query parameters:

| Parameter | Default | Keterangan |
| --- | --- | --- |
| `force_refresh` | `false` | Jika `true`, bypass cache dan panggil provider checker. |

Request body:

```json
{
  "provider": "PLN",
  "customer_id": "123456789012"
}
```

Contoh:

```bash
curl -X POST 'http://localhost:8000/api/v1/bills/check?force_refresh=false' \
  -H 'X-FAMILY-KEY: change-with-a-long-random-secret' \
  -H 'Content-Type: application/json' \
  -d '{"provider":"PLN","customer_id":"123456789012"}'
```

Response `200` contoh tagihan belum dibayar:

```json
{
  "provider": "PLN",
  "customer_id": "123456789012",
  "customer_name": "BUDI SANTOSO",
  "status": "UNPAID",
  "bills": [
    {
      "period": {
        "month": 5,
        "year": 2026
      },
      "amount": "350000",
      "admin_fee": "2500"
    }
  ],
  "total_amount": "352500",
  "due_date": null,
  "meter_number": null,
  "tariff_class": "R1/1300VA",
  "power_rating": "1300VA",
  "checked_at": "2026-05-29T10:00:00Z",
  "message": "MOCK MODE - Data simulasi"
}
```

Response `200` contoh sudah lunas:

```json
{
  "provider": "PLN",
  "customer_id": "123456789012",
  "customer_name": "BUDI SANTOSO",
  "status": "PAID",
  "bills": [],
  "total_amount": "0",
  "due_date": null,
  "meter_number": null,
  "tariff_class": "R1/1300VA",
  "power_rating": "1300VA",
  "checked_at": "2026-05-29T10:00:00Z",
  "message": "Tidak ada tagihan"
}
```

### 2. Check Bill for Saved Account

```http
POST /api/v1/bills/check/{account_id}?force_refresh=false
```

Contoh:

```bash
curl -X POST 'http://localhost:8000/api/v1/bills/check/1?force_refresh=true' \
  -H 'X-FAMILY-KEY: change-with-a-long-random-secret'
```

Endpoint ini mengambil `provider` dan `customer_id` dari utility account yang tersimpan, lalu memakai flow cache yang sama.

### 3. Get Saved Accounts via Bills Namespace

```http
GET /api/v1/bills/saved?active_only=true
```

Query parameters:

| Parameter | Default | Keterangan |
| --- | --- | --- |
| `active_only` | `true` | Jika `true`, hanya account aktif yang dikembalikan. |

Contoh:

```bash
curl 'http://localhost:8000/api/v1/bills/saved?active_only=true' \
  -H 'X-FAMILY-KEY: change-with-a-long-random-secret'
```

Response sama seperti list utility accounts.

### 4. Check Bills for All Saved Accounts

```http
POST /api/v1/bills/check-all?active_only=true&force_refresh=false
```

Query parameters:

| Parameter | Default | Keterangan |
| --- | --- | --- |
| `active_only` | `true` | Jika `true`, hanya account aktif yang dicek. |
| `force_refresh` | `false` | Jika `true`, bypass cache untuk semua account. |

Contoh:

```bash
curl -X POST 'http://localhost:8000/api/v1/bills/check-all?active_only=true&force_refresh=false' \
  -H 'X-FAMILY-KEY: change-with-a-long-random-secret'
```

Response `200`: array `BillCheckResponse`.

---

## 🧩 Schema Reference

### `UtilityAccountCreate`

```json
{
  "provider": "PLN | PDAM | INDIHOME",
  "customer_id": "digits only, max 50 chars",
  "alias": "optional, max 100 chars",
  "is_active": true
}
```

### `UtilityAccountUpdate`

```json
{
  "provider": "PLN | PDAM | INDIHOME (optional)",
  "customer_id": "digits only, optional",
  "alias": "optional",
  "is_active": true
}
```

### `BillCheckRequest`

```json
{
  "provider": "PLN | PDAM | INDIHOME",
  "customer_id": "digits only, max 50 chars"
}
```

### `BillCheckResponse`

```json
{
  "provider": "PLN",
  "customer_id": "123456789012",
  "customer_name": "BUDI SANTOSO",
  "status": "UNPAID | PAID | OVERDUE | NOT_FOUND | ERROR",
  "bills": [
    {
      "period": { "month": 5, "year": 2026 },
      "amount": "350000",
      "admin_fee": "2500"
    }
  ],
  "total_amount": "352500",
  "due_date": null,
  "meter_number": null,
  "tariff_class": null,
  "power_rating": null,
  "checked_at": "2026-05-29T10:00:00Z",
  "message": null
}
```

---

## 💾 Database dan Cache

### Database

Default database adalah SQLite file lokal:

```text
family.db
```

Tabel dibuat otomatis saat aplikasi startup menggunakan metadata SQLAlchemy.

### Cache Tagihan

- Tabel cache: `bill_cache`.
- Key cache: kombinasi `provider` + `customer_id`.
- TTL cache: 12 jam.
- `force_refresh=true` akan bypass cache fresh.
- Jika provider gagal tetapi cache lama tersedia, API akan mengembalikan stale cache dengan prefix pesan `[STALE CACHE]`.

---

## 🧪 Quality Checks dan Testing

Jalankan sebelum membuat perubahan/PR:

```bash
python -m ruff check app tests
python -m compileall app tests
pytest -q
```

Format file tertentu dengan Ruff:

```bash
python -m ruff format app tests
```

---

## 🖥️ Deploy ke Server

### Rekomendasi Production

- Set `DEBUG=false`.
- Set `EXPOSE_API_DOCS=false` kecuali benar-benar dibutuhkan.
- Set `FAMILY_API_KEY` panjang dan random.
- Simpan secret lewat environment variable atau secret manager.
- Jalankan di balik reverse proxy (Nginx/Caddy/Traefik) dengan HTTPS.
- Tambahkan rate limiting di reverse proxy.
- Backup file SQLite jika tetap memakai SQLite.

### Contoh Systemd Service

```ini
[Unit]
Description=FamilyCentralAPI
After=network.target

[Service]
User=www-data
WorkingDirectory=/var/www/family-central-bill
EnvironmentFile=/var/www/family-central-bill/.env
Environment="PATH=/var/www/family-central-bill/venv/bin"
ExecStart=/var/www/family-central-bill/venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Command:

```bash
sudo systemctl daemon-reload
sudo systemctl enable familyapi
sudo systemctl start familyapi
sudo systemctl status familyapi
```

### Contoh Nginx Reverse Proxy Ringkas

```nginx
limit_req_zone $binary_remote_addr zone=familyapi:10m rate=5r/s;

server {
    listen 443 ssl http2;
    server_name familyapi.example.com;

    location / {
        limit_req zone=familyapi burst=20 nodelay;
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

---

## 🧯 Troubleshooting

### Protected endpoint mengembalikan `503 AUTH_NOT_CONFIGURED`

`FAMILY_API_KEY` belum terbaca. Pastikan `.env` ada, environment service memuat file tersebut, dan aplikasi direstart.

### `/docs` 404

Docs memang nonaktif secara default. Set `EXPOSE_API_DOCS=true` untuk local development lalu restart server.

### `422 Unprocessable Entity` untuk `customer_id`

`customer_id` hanya boleh digit. Spasi awal/akhir akan otomatis di-trim, tetapi huruf/simbol ditolak.

### Provider mengembalikan `ERROR`

Cek konfigurasi mode provider:

- Untuk simulasi: set `PLN_CHECK_URL=mock`, `PDAM_CHECK_URL=mock`, `INDIHOME_CHECK_URL=mock`.
- Untuk integrasi nyata: pastikan `SEPULSA_API_KEY` dan jaringan outbound tersedia.

### Database tidak muncul

Aplikasi membuat tabel saat startup. Pastikan proses punya permission write pada working directory jika memakai SQLite default.

---

## 📚 Tech Stack

| Komponen | Teknologi |
| --- | --- |
| Framework | FastAPI |
| ASGI Server | Uvicorn |
| Database | SQLite + SQLAlchemy async |
| HTTP Client | httpx |
| Validation | Pydantic v2 |
| Settings | pydantic-settings |
| Tests | pytest + FastAPI TestClient |
| Lint/Format | Ruff |

---

## 🤝 Kontribusi

1. Buat branch baru.
2. Jalankan `python -m ruff check app tests`, `python -m compileall app tests`, dan `pytest -q`.
3. Pastikan tidak ada secret di commit.
4. Buat pull request dengan ringkasan perubahan dan hasil testing.

---

## 📄 License

MIT License — silakan digunakan untuk kebutuhan pribadi maupun komersial.
