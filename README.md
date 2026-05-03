# PromptPay Monitoring Dashboard

Real-time monitoring dashboard for PromptPay transactions — FastAPI backend + Streamlit frontend, containerized with Docker.

---

## Quick Start

### Option A — Docker (recommended)

```bash
cd promptpay-dashboard
docker compose up --build
```

Open http://localhost:8501

### Option B — Local (dev)

```bash
cd promptpay-dashboard
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# Terminal 1
uvicorn backend.main:app --port 8000 --reload

# Terminal 2
streamlit run frontend/dashboard.py
```

---

## Project Structure

```
.
├── data/                          # CSV data files (NOT committed to Git)
│   ├── Classification Summary.csv
│   ├── Hourly Volume.csv
│   ├── Proxy Type.csv
│   ├── TRL_TSC_CODE.csv
│   ├── Volume รายวัน (7 วันล่าสุด).csv
│   └── Volume รายชั่วโมง (วันนี้).csv
│
└── promptpay-dashboard/
    ├── backend/
    │   ├── Dockerfile
    │   ├── main.py                # FastAPI app — 7 REST endpoints
    │   ├── data_loader.py         # CSV loading and aggregation
    │   └── tests/                 # Property-based tests
    ├── frontend/
    │   ├── Dockerfile
    │   └── dashboard.py           # Streamlit dashboard — 6 pages
    ├── docker-compose.yml         # Build & run locally
    ├── docker-compose.hub.yml     # Run from Docker Hub images
    ├── Makefile                   # Convenience commands
    └── requirements.txt
```

---

## API Endpoints

| Endpoint | Description |
|---|---|
| `GET /api/health` | Backend health check |
| `GET /api/overview` | KPI summary (total TXN, success rate, fail count, amount) |
| `GET /api/hourly-volume` | Hourly volume by transaction type |
| `GET /api/trend` | 7-day daily volume trend |
| `GET /api/response-codes` | TSC response code frequency |
| `GET /api/proxy-type` | Proxy type distribution |
| `GET /api/hourly-proxy` | Hourly volume by proxy type |

---

## Sharing with Team

### Dev team (with source code)

```bash
git clone <repo-url>
cd promptpay-dashboard
# Place data/ folder at ../data/ relative to promptpay-dashboard/
docker compose up --build
```

### Non-dev / stakeholders (Docker Hub)

```bash
# 1. Publisher pushes images
export DOCKER_USERNAME=yourname
make push

# 2. Recipient — only needs docker-compose.hub.yml + data/ folder
DOCKER_USERNAME=yourname docker compose -f docker-compose.hub.yml up
```

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `DATA_DIR` | `../../data` | Path to CSV data directory (inside container: `/app/data`) |
| `BACKEND_URL` | `http://localhost:8000` | Backend URL for frontend to connect to |
| `DOCKER_USERNAME` | — | Docker Hub username for push/pull |
| `IMAGE_TAG` | `latest` | Docker image tag |
