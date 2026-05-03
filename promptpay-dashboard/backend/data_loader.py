"""
data_loader.py — CSV loading and parsing for the PromptPay Monitoring Dashboard.

Reads six CSV files (no header rows) from the data/ directory located two levels
above this file (i.e. ../../data/ relative to backend/).
"""

from __future__ import annotations

import os
from pathlib import Path

import pandas as pd

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

# backend/ → promptpay-dashboard/ → workspace root → data/
_BACKEND_DIR = Path(__file__).parent
# Support Docker: DATA_DIR env var overrides the default relative path
_DATA_DIR = Path(os.environ.get("DATA_DIR", str(_BACKEND_DIR / ".." / ".." / "data")))

# ---------------------------------------------------------------------------
# Column definitions (CSVs have no header rows)
# ---------------------------------------------------------------------------

_CSV_COLUMNS: dict[str, list[str]] = {
    "Classification Summary.csv": ["date", "tx_type", "total", "success", "fail", "amount"],
    "Hourly Volume.csv": ["date", "hour", "tx_type", "total", "success", "fail"],
    "Proxy Type.csv": ["proxy_type", "count", "percentage"],
    "TRL_TSC_CODE.csv": ["tsc_code", "origin_iap", "dest_iap", "count"],
    "Volume รายวัน (7 วันล่าสุด).csv": ["date", "proxy_type", "sender_bank", "receiver_bank", "count"],
    "Volume รายชั่วโมง (วันนี้).csv": ["date", "hour", "proxy_type", "count"],
}

# Per-file dtype overrides: columns that should be read as strings to preserve
# their original representation (e.g. bank codes stored as integers in the CSV
# but compared as strings in tests).
_CSV_DTYPES: dict[str, dict[str, type]] = {
    "Volume รายวัน (7 วันล่าสุด).csv": {"sender_bank": str, "receiver_bank": str},
    # tsc_code must be string — it's a code, not a number (e.g. "381", "74")
    "TRL_TSC_CODE.csv": {"tsc_code": str},
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def load_all() -> dict[str, pd.DataFrame]:
    """Load all six CSV files and return them as a dict keyed by filename.

    Raises:
        FileNotFoundError: with the missing filename if any CSV is absent.
    """
    frames: dict[str, pd.DataFrame] = {}
    for filename, columns in _CSV_COLUMNS.items():
        path = _DATA_DIR / filename
        if not path.exists():
            raise FileNotFoundError(filename)
        df = pd.read_csv(
            path,
            header=None,
            names=columns,
            encoding="utf-8-sig",
            dtype=_CSV_DTYPES.get(filename),
            keep_default_na=False,
        )
        frames[filename] = df
    return frames


def get_overview(df: pd.DataFrame) -> dict:
    """Aggregate Classification Summary data across all transaction types.

    Args:
        df: DataFrame loaded from ``Classification Summary.csv``.

    Returns:
        dict with keys:
            - total_txn (int): sum of the ``total`` column
            - success_rate (float): sum(success) / sum(total)
            - fail_count (int): sum of the ``fail`` column
            - total_amount_thb (float): sum of the ``amount`` column
    """
    total = int(df["total"].sum())
    success = int(df["success"].sum())
    fail = int(df["fail"].sum())
    amount = float(df["amount"].sum())

    success_rate = success / total if total > 0 else 0.0

    return {
        "total_txn": total,
        "success_rate": success_rate,
        "fail_count": fail,
        "total_amount_thb": amount,
    }


def get_hourly_volume(df: pd.DataFrame) -> list[dict]:
    """Return one record per (date, hour, tx_type) from Hourly Volume data.

    Args:
        df: DataFrame loaded from ``Hourly Volume.csv``.

    Returns:
        List of dicts with keys: date, hour, tx_type, total, success, fail.
    """
    return df.to_dict(orient="records")


def get_trend(df: pd.DataFrame) -> list[dict]:
    """Return one record per (date, proxy_type, sender_bank, receiver_bank, count),
    excluding NULL proxy types.

    Args:
        df: DataFrame loaded from ``Volume รายวัน (7 วันล่าสุด).csv``.

    Returns:
        List of dicts with keys: date, proxy_type, sender_bank, receiver_bank, count.
    """
    filtered = df[df["proxy_type"].notna() & (df["proxy_type"] != "NULL")]
    return filtered.to_dict(orient="records")


def get_response_codes(df: pd.DataFrame) -> list[dict]:
    """Return all rows from TRL_TSC_CODE data.

    Args:
        df: DataFrame loaded from ``TRL_TSC_CODE.csv``.

    Returns:
        List of dicts with keys: tsc_code, origin_iap, dest_iap, count.
    """
    return df.to_dict(orient="records")


def get_proxy_type(df: pd.DataFrame) -> list[dict]:
    """Return proxy type rows, excluding entries where proxy_type == 'NULL'.

    The CSV stores NULL as a bare word which pandas reads as NaN, so we
    filter out both the string "NULL" and NaN values.

    Args:
        df: DataFrame loaded from ``Proxy Type.csv``.

    Returns:
        List of dicts with keys: proxy_type, count, percentage.
    """
    filtered = df[df["proxy_type"].notna() & (df["proxy_type"] != "NULL")]
    return filtered.to_dict(orient="records")


def get_hourly_proxy(df: pd.DataFrame) -> list[dict]:
    """Return all rows from the hourly proxy volume file, excluding NULL proxy types.

    Args:
        df: DataFrame loaded from ``Volume รายชั่วโมง (วันนี้).csv``.

    Returns:
        List of dicts with keys: date, hour, proxy_type, count.
    """
    filtered = df[df["proxy_type"].notna() & (df["proxy_type"] != "NULL")]
    return filtered.to_dict(orient="records")
