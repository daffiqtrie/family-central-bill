# FamilyCentralAPI - Pre-Deployment Checklist

## 🔒 Security Fixes (WAJIB)

### 1. Ganti API Key Production

```bash
# Di server, edit .env:
FAMILY_API_KEY=<your-strong-secret-key>
```

> ⚠️ **Jangan pakai `DetigaPlus`** - ini untuk development only!

### 2. Disable Debug Mode

```bash
DEBUG=false
```

### 3. Update CORS Origins

```bash
# Sesuaikan dengan domain frontend (jika ada)
ALLOWED_ORIGINS=["https://your-domain.com"]
```

---

## 📦 Files yang HARUS Ada di Server

```
FamilyCentralAPI/
├── app/                    # ✅ Source code
├── .env                    # ✅ Environment config (COPY dari .env.example, edit values)
├── pyproject.toml          # ✅ Project metadata
├── requirements.txt        # ✅ Dependencies (sudah di-generate)
└── README.md               # Optional
```

### ❌ JANGAN Include:

- `venv/` - Buat baru di server
- `family.db` - Akan auto-create
- `__pycache__/` - Akan auto-generate
- `.git/` - Tidak diperlukan
- `*.egg-info/` - Development artifact

---

## 🚀 Setup di Server

### 1. Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Copy & Edit .env

```bash
cp .env.example .env
nano .env
# Edit: FAMILY_API_KEY, DEBUG=false
```

### 4. Run Server

```bash
# Development
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Production (dengan Gunicorn)
pip install gunicorn
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000
```

---

## ✅ Feature Checklist

| Feature                 | Status | Notes               |
| ----------------------- | ------ | ------------------- |
| PLN Bill Check          | ✅     | Sepulsa API         |
| PDAM Bill Check         | ✅     | Sepulsa API         |
| Indihome Bill Check     | ✅     | Sepulsa API         |
| Smart Caching (12h TTL) | ✅     | SQLite BillCache    |
| Stealth Headers         | ✅     | fake-useragent      |
| API Key Auth            | ✅     | X-FAMILY-KEY header |
| CORS                    | ✅     | Configurable        |
| Health Endpoint         | ✅     | GET /health         |
| Auto DB Migration       | ✅     | Tables auto-created |

---

## 🔍 API Endpoints

| Method | Path                            | Auth | Description         |
| ------ | ------------------------------- | ---- | ------------------- |
| GET    | `/`                             | ❌   | App info            |
| GET    | `/health`                       | ❌   | Health check        |
| GET    | `/docs`                         | ❌   | Swagger UI          |
| POST   | `/api/v1/bills/check`           | ✅   | Check bill          |
| POST   | `/api/v1/bills/check/{id}`      | ✅   | Check saved account |
| GET    | `/api/v1/bills/saved`           | ✅   | List saved accounts |
| POST   | `/api/v1/bills/check-all`       | ✅   | Check all accounts  |
| POST   | `/api/v1/utility-accounts`      | ✅   | Create account      |
| GET    | `/api/v1/utility-accounts`      | ✅   | List accounts       |
| GET    | `/api/v1/utility-accounts/{id}` | ✅   | Get account         |
| PUT    | `/api/v1/utility-accounts/{id}` | ✅   | Update account      |
| DELETE | `/api/v1/utility-accounts/{id}` | ✅   | Delete account      |

---

## 📝 Compress Command

```bash
cd /path/to/project
tar -czvf FamilyCentralAPI.tar.gz \
  --exclude='venv' \
  --exclude='__pycache__' \
  --exclude='*.pyc' \
  --exclude='.git' \
  --exclude='*.egg-info' \
  --exclude='family.db' \
  FamilyCentralAPI/
```

---

## ⚠️ Known Issues

1. **fake-useragent warning** - Normal, fallback to static UA
2. **Response 400 dari Sepulsa** - Berarti customer ID tidak punya tagihan atau nomor salah
