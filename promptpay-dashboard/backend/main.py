"""
main.py — FastAPI application for the PromptPay Monitoring Dashboard.

Loads all six CSV DataFrames at module import time via data_loader.load_all()
and serves them through REST endpoints. If any CSV file is missing, the health
endpoint reports "degraded" and all data endpoints return HTTP 503.
"""

from __future__ import annotations

import logging
import math
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend import data_loader

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Module-level state: DataFrames loaded once at import time
# ---------------------------------------------------------------------------

_frames: dict = {}
startup_error: str | None = None

try:
    _frames = data_loader.load_all()
    logger.info("All CSV files loaded successfully.")
except FileNotFoundError as exc:
    startup_error = str(exc)
    _frames = {}
    logger.error("CSV file missing at startup: %s", startup_error)
except Exception as exc:  # pragma: no cover
    startup_error = str(exc)
    _frames = {}
    logger.error("Unexpected error loading CSV files: %s", startup_error)

# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------

app = FastAPI(title="PromptPay Monitoring Dashboard API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8501"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _sanitize(value: Any) -> Any:
    """Recursively replace float NaN/Inf with None for JSON compliance."""
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    if isinstance(value, dict):
        return {k: _sanitize(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_sanitize(item) for item in value]
    return value


def _get_frame(filename: str):
    """Return the DataFrame for *filename*, or raise HTTP 503 if unavailable."""
    df = _frames.get(filename)
    if df is None:
        detail = f"CSV file missing: {startup_error or filename}"
        raise HTTPException(status_code=503, detail=detail)
    return df


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@app.get("/api/health")
def health():
    """Liveness probe. Returns 'ok' when all CSVs loaded, 'degraded' otherwise."""
    if startup_error:
        return {"status": "degraded", "error": startup_error}
    return {"status": "ok"}


@app.get("/api/overview")
def overview():
    """Aggregate KPI metrics from Classification Summary.csv."""
    df = _get_frame("Classification Summary.csv")
    return _sanitize(data_loader.get_overview(df))


@app.get("/api/hourly-volume")
def hourly_volume():
    """Hourly transaction volume breakdown from Hourly Volume.csv."""
    df = _get_frame("Hourly Volume.csv")
    return _sanitize(data_loader.get_hourly_volume(df))


@app.get("/api/trend")
def trend():
    """7-day daily volume trend from Volume รายวัน (7 วันล่าสุด).csv."""
    df = _get_frame("Volume รายวัน (7 วันล่าสุด).csv")
    return _sanitize(data_loader.get_trend(df))


@app.get("/api/response-codes")
def response_codes():
    """Response code summary from TRL_TSC_CODE.csv."""
    df = _get_frame("TRL_TSC_CODE.csv")
    return _sanitize(data_loader.get_response_codes(df))


@app.get("/api/proxy-type")
def proxy_type():
    """Proxy type distribution from Proxy Type.csv (NULL entries excluded)."""
    df = _get_frame("Proxy Type.csv")
    return _sanitize(data_loader.get_proxy_type(df))


@app.get("/api/hourly-proxy")
def hourly_proxy():
    """Hourly proxy volume from Volume รายชั่วโมง (วันนี้).csv."""
    df = _get_frame("Volume รายชั่วโมง (วันนี้).csv")
    return _sanitize(data_loader.get_hourly_proxy(df))
