# 🏠 FamilyCentralAPI

> API untuk cek tagihan listrik (PLN), air (PDAM), dan internet (Indihome) dalam satu tempat.

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.128-green.svg)](https://fastapi.tiangolo.com)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 📖 Apa Ini?

**FamilyCentralAPI** adalah REST API yang memungkinkan kamu mengecek tagihan utilitas rumah tangga secara programatis. Cocok untuk:

- 🏡 **Home Server** - Jalankan di Raspberry Pi atau mini PC di rumah
- 📱 **Integrasi App** - Backend untuk aplikasi mobile/web keluarga
- 🤖 **Automasi** - Reminder tagihan via bot Telegram/WhatsApp
- 📊 **Dashboard** - Data source untuk monitoring keuangan

### Fitur Utama

| Fitur           | Keterangan                            |
| --------------- | ------------------------------------- |
| ⚡ PLN Postpaid | Cek tagihan listrik pascabayar        |
| 💧 PDAM Padang  | Cek tagihan air PDAM Kota Padang      |
| 🌐 Indihome     | Cek tagihan internet Telkom           |
| 🔐 API Key Auth | Keamanan dengan header `X-FAMILY-KEY` |
| 💾 Smart Cache  | Hemat request dengan cache 12 jam     |
| 🥷 Stealth Mode | Rotating User-Agent anti-blokir       |

---

## 🏗️ Arsitektur Proyek

```
FamilyCentralAPI/
├── app/                          # 📦 Source code utama
│   ├── main.py                   # Entry point aplikasi
│   ├── api/                      # 🌐 API Layer
│   │   └── v1/
│   │       ├── router.py         # Kumpulan semua routes
│   │       └── endpoints/
│   │           ├── bills.py      # Endpoint cek tagihan
│   │           └── utility_accounts.py
│   ├── core/                     # ⚙️ Konfigurasi & Security
│   │   ├── config.py             # Baca .env file
│   │   ├── security.py           # Middleware API key
│   │   └── exceptions.py         # Custom error handling
│   ├── db/                       # 🗄️ Database Layer
│   │   ├── base_class.py         # Base model SQLAlchemy
│   │   └── session.py            # Koneksi database
│   ├── models/                   # 📊 Database Models
│   │   ├── bill.py               # Tabel cache tagihan
│   │   └── utility_account.py    # Tabel akun tersimpan
│   ├── schemas/                  # 📝 Pydantic Schemas
│   │   ├── bill.py               # Request/Response tagihan
│   │   └── utility_account.py
│   └── services/                 # 🔧 Business Logic
│       ├── bill_orchestrator.py  # Smart caching logic
│       └── bills/
│           ├── base.py           # Abstract base checker
│           ├── pln.py            # Scraper PLN
│           ├── pdam.py           # Scraper PDAM
│           └── indihome.py       # Scraper Indihome
├── .env.example                  # Template environment
├── pyproject.toml                # Metadata proyek
└── requirements.txt              # Daftar dependencies
```

### Penjelasan Struktur (Biar Paham):

#### 1. **`app/main.py`** - Pintu Masuk

Ini adalah file pertama yang dijalankan. Di sini FastAPI di-setup, middleware ditambahkan, dan routes didaftarkan.

#### 2. **`app/api/`** - Tempat Endpoint

Semua URL yang bisa diakses user didefinisikan di sini. Misal `/api/v1/bills/check` ada di `endpoints/bills.py`.

#### 3. **`app/core/`** - Pengaturan & Keamanan

- `config.py` = Baca setting dari file `.env`
- `security.py` = Cek apakah request punya API key yang valid

#### 4. **`app/models/`** - Bentuk Tabel Database

Pakai SQLAlchemy ORM. Definisi kolom-kolom tabel ada di sini.

#### 5. **`app/schemas/`** - Validasi Data

Pakai Pydantic. Definisi format JSON request/response ada di sini.

#### 6. **`app/services/`** - Otak Bisnis

Logika utama ada di sini. Scraping ke Sepulsa, caching, parsing response.

---

## 🚀 Cara Install (Step by Step)

### Prasyarat

- **Python 3.10+** - Cek: `python3 --version`
- **pip** - Biasanya sudah include dengan Python
- **Git** - Untuk clone repository

### Step 1: Clone Repository

```bash
git clone https://github.com/41116120010/family-central-bill.git
cd family-central-bill
```

### Step 2: Buat Virtual Environment

Virtual environment itu "kotak" khusus biar package Python proyek ini tidak campur dengan proyek lain.

```bash
# Buat virtual environment
python3 -m venv venv

# Aktifkan (Linux/Mac)
source venv/bin/activate

# Aktifkan (Windows)
venv\Scripts\activate

# Kalau berhasil, prompt akan berubah jadi: (venv) $
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Setup Environment Variables

```bash
# Copy template
cp .env.example .env

# Edit sesuai kebutuhan
nano .env
```

**Isi `.env` yang WAJIB diubah:**

```env
# Ganti dengan API key rahasia kamu (bebas, terserah kamu)
FAMILY_API_KEY=kunci-rahasia-keluarga-123

# Untuk production, set ke false
DEBUG=false
```

### Step 5: Jalankan Server

```bash
# Development mode (auto-reload)
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Kalau sukses, akan muncul:

```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

### Step 6: Test API

Buka browser: **http://localhost:8000/docs**

Atau pakai curl:

```bash
curl -X POST http://localhost:8000/api/v1/bills/check \
  -H "X-FAMILY-KEY: kunci-rahasia-keluarga-123" \
  -H "Content-Type: application/json" \
  -d '{"provider": "PLN", "customer_id": "123456789012"}'
```

---

## 📡 Penggunaan API

### Header Wajib

Semua request (kecuali `/`, `/health`, `/docs`) harus pakai header:

```
X-FAMILY-KEY: <api-key-kamu>
```

### Endpoints

#### 🔍 Cek Tagihan

```http
POST /api/v1/bills/check
```

**Request Body:**

```json
{
  "provider": "PLN",
  "customer_id": "123456789012"
}
```

**Provider yang didukung:**

- `PLN` - ID Pelanggan 12 digit
- `PDAM` - Nomor Pelanggan 8-12 digit
- `INDIHOME` - Nomor Internet 12-14 digit

**Response Sukses (Ada Tagihan):**

```json
{
  "provider": "PLN",
  "customer_id": "123456789012",
  "customer_name": "JOHN DOE",
  "status": "UNPAID",
  "bills": [
    {
      "period": { "month": 1, "year": 2026 },
      "amount": "350000",
      "admin_fee": "2500"
    }
  ],
  "total_amount": "352500",
  "message": "Periode: JAN 2026"
}
```

**Response (Sudah Lunas):**

```json
{
  "provider": "PLN",
  "customer_id": "123456789012",
  "status": "PAID",
  "message": "Bill Already Paid/ Not Available"
}
```

**Response (Nomor Salah):**

```json
{
  "provider": "PLN",
  "customer_id": "000000000000",
  "status": "NOT_FOUND",
  "message": "Nomor salah / terblokir / expired."
}
```

#### 🔄 Force Refresh (Bypass Cache)

```http
POST /api/v1/bills/check?force_refresh=true
```

---

## 💾 Sistem Caching

API ini menggunakan **Smart Caching** untuk menghemat request ke provider:

```
Request masuk
     │
     ▼
[Cache ada & < 12 jam?]──YES──► Return cache
     │
     NO
     ▼
Fetch dari Sepulsa API
     │
     ▼
[Sukses?]──YES──► Simpan ke cache ──► Return data
     │
     NO
     ▼
[Ada cache lama?]──YES──► Return cache lama + warning "[STALE]"
     │
     NO
     ▼
Return error
```

**Manfaat:**

- Hemat kuota API
- Response lebih cepat untuk data yang sudah di-cache
- Tetap bisa return data meski provider down (pakai cache lama)

---

## 🔐 Keamanan

### 1. API Key Authentication

Semua endpoint dilindungi dengan header `X-FAMILY-KEY`. Tanpa key yang benar, request akan ditolak dengan status `401 Unauthorized`.

### 2. Stealth Headers

Setiap request ke provider menggunakan User-Agent yang berbeda-beda (rotating) untuk menghindari deteksi dan pemblokiran.

### 3. Rate Limiting (Rekomendasi)

Untuk production, tambahkan reverse proxy (Nginx) dengan rate limiting:

```nginx
limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
```

---

## 🖥️ Deploy ke Server

### Pakai Systemd (Recommended)

1. Buat service file:

```bash
sudo nano /etc/systemd/system/familyapi.service
```

2. Isi dengan:

```ini
[Unit]
Description=FamilyCentralAPI
After=network.target

[Service]
User=www-data
WorkingDirectory=/var/www/FamilyCentralAPI
Environment="PATH=/var/www/FamilyCentralAPI/venv/bin"
ExecStart=/var/www/FamilyCentralAPI/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

3. Enable dan start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable familyapi
sudo systemctl start familyapi
```

4. Cek status:

```bash
sudo systemctl status familyapi
```

---

## ❓ FAQ

### Q: Kenapa response 400 "Bill Already Paid"?

**A:** Customer ID tidak punya tagihan yang belum dibayar. Status `PAID` berarti lunas.

### Q: Kenapa ada warning "fake-useragent"?

**A:** Normal. Library fallback ke User-Agent statis karena tidak bisa fetch dari internet. Tidak mempengaruhi fungsi.

### Q: Bagaimana cara tambah provider baru?

**A:**

1. Buat file baru di `app/services/bills/` (copy dari `pln.py`)
2. Tambahkan ke factory di `app/services/bills/__init__.py`
3. Update enum di `app/schemas/bill.py`

### Q: Database di mana?

**A:** SQLite, file `family.db` di root folder. Auto-create saat pertama run.

---

## 📚 Tech Stack

| Komponen    | Teknologi           |
| ----------- | ------------------- |
| Framework   | FastAPI             |
| Database    | SQLite + SQLAlchemy |
| HTTP Client | httpx               |
| Validation  | Pydantic            |
| Server      | Uvicorn             |

---

## 📄 License

MIT License - Silakan digunakan untuk keperluan pribadi maupun komersial.

---

## 🤝 Kontribusi

Pull request welcome! Untuk perubahan besar, buka issue dulu untuk diskusi.

---

**Made with ❤️ and Claude Opus 4.6(Antigravity)**
