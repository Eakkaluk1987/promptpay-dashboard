"""
Bug Condition Exploration Test — Property 1: MockDataEngine Used Instead of CSV Data

**Validates: Requirements 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7**

CRITICAL: This test MUST FAIL on unfixed code.
  - If the backend does not exist yet → fails with ImportError / connection error (expected)
  - If the backend uses MockDataEngine → fails because synthetic values ≠ CSV values (expected)

The bug condition is universal: isBugCondition(X) = True for every dashboard request,
because ALL data paths go through MockDataEngine in the unfixed system.

This test encodes the EXPECTED CORRECT behaviour after the fix:
  result.data_source = "CSV"
  result.synthetic_data_used = False
  result.values_match_csv_records(X.csv_file)

When the fix is applied (Task 3), re-running this test should PASS.

Counterexample shape (what failure looks like):
  GET /api/overview returns total_txn=18432 but CSV aggregation yields total_txn=8066226
  GET /api/hourly-volume returns records with tx_type="MOBILE" but CSV has tx_type="CsB_Inbound"
  GET /api/trend returns records with proxy_type="CITIZEN_ID" but CSV has proxy_type="BILLERID"
  GET /api/response-codes returns tsc_code="51" but CSV has tsc_code=381
  GET /api/proxy-type returns proxy_type="MOBILE_NUMBER" but CSV has proxy_type="BILLERID"
  GET /api/hourly-proxy returns count=999 but CSV row has count=9057
"""

import os
import csv
import math
import pathlib
import pytest

# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------

# Workspace root: test file is at promptpay-dashboard/backend/tests/test_bug_condition.py
# parents[0] = tests/, parents[1] = backend/, parents[2] = promptpay-dashboard/, parents[3] = workspace root
WORKSPACE_ROOT = pathlib.Path(__file__).resolve().parents[3]
DATA_DIR = WORKSPACE_ROOT / "data"


def csv_rows(filename: str) -> list[list[str]]:
    """Read a CSV file (no header) and return all rows as lists of strings."""
    path = DATA_DIR / filename
    with open(path, encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        return [row for row in reader if row]  # skip blank lines


# ---------------------------------------------------------------------------
# Expected values computed directly from CSV files
# ---------------------------------------------------------------------------

def expected_overview() -> dict:
    """
    Aggregate Classification Summary.csv:
      columns: date, tx_type, total, success, fail, amount
    Returns: total_txn, success_rate, fail_count, total_amount_thb
    """
    rows = csv_rows("Classification Summary.csv")
    total_txn = sum(int(r[2]) for r in rows)
    total_success = sum(int(r[3]) for r in rows)
    fail_count = sum(int(r[4]) for r in rows)
    total_amount_thb = sum(float(r[5]) for r in rows)
    success_rate = total_success / total_txn if total_txn > 0 else 0.0
    return {
        "total_txn": total_txn,
        "success_rate": success_rate,
        "fail_count": fail_count,
        "total_amount_thb": total_amount_thb,
    }


def expected_hourly_volume() -> list[dict]:
    """
    Parse Hourly Volume.csv:
      columns: date, hour, tx_type, total, success, fail
    Returns list of dicts with those keys.
    """
    rows = csv_rows("Hourly Volume.csv")
    return [
        {
            "date": r[0],
            "hour": int(r[1]),
            "tx_type": r[2],
            "total": int(r[3]),
            "success": int(r[4]),
            "fail": int(r[5]),
        }
        for r in rows
    ]


def expected_trend() -> list[dict]:
    """
    Parse 'Volume รายวัน (7 วันล่าสุด).csv':
      columns: date, proxy_type, sender_bank, receiver_bank, count
    Returns list of dicts with those keys.
    """
    rows = csv_rows("Volume รายวัน (7 วันล่าสุด).csv")
    return [
        {
            "date": r[0],
            "proxy_type": r[1],
            "sender_bank": r[2],
            "receiver_bank": r[3],
            "count": int(r[4]),
        }
        for r in rows
    ]


def expected_response_codes() -> list[dict]:
    """
    Parse TRL_TSC_CODE.csv:
      columns: tsc_code, origin_iap, dest_iap, count
    Returns list of dicts with those keys.
    """
    rows = csv_rows("TRL_TSC_CODE.csv")
    return [
        {
            "tsc_code": r[0],
            "origin_iap": r[1],
            "dest_iap": r[2],
            "count": int(r[3]),
        }
        for r in rows
    ]


def expected_proxy_type() -> list[dict]:
    """
    Parse Proxy Type.csv:
      columns: proxy_type, count, percentage
    Exclude rows where proxy_type == "NULL".
    Returns list of dicts with those keys.
    """
    rows = csv_rows("Proxy Type.csv")
    return [
        {
            "proxy_type": r[0],
            "count": int(r[1]),
            "percentage": float(r[2]),
        }
        for r in rows
        if r[0] != "NULL"
    ]


def expected_hourly_proxy() -> list[dict]:
    """
    Parse 'Volume รายชั่วโมง (วันนี้).csv':
      columns: date, hour, proxy_type, count
    Returns list of dicts with those keys.
    """
    rows = csv_rows("Volume รายชั่วโมง (วันนี้).csv")
    return [
        {
            "date": r[0],
            "hour": int(r[1]),
            "proxy_type": r[2],
            "count": int(r[3]),
        }
        for r in rows
    ]


# ---------------------------------------------------------------------------
# FastAPI TestClient setup
# ---------------------------------------------------------------------------
# This import WILL FAIL until the backend is implemented (Task 3).
# That failure is the expected outcome for Task 1 — it confirms the bug exists.
#
# When the backend is implemented, this import will succeed and the tests will
# assert that the endpoint responses match the CSV-derived expected values above.

try:
    from fastapi.testclient import TestClient
    from backend.main import app  # noqa: E402  — does not exist yet
    client = TestClient(app)
    BACKEND_AVAILABLE = True
except (ImportError, ModuleNotFoundError, Exception):
    client = None
    BACKEND_AVAILABLE = False


# ---------------------------------------------------------------------------
# Helper: assert two numeric values are approximately equal
# ---------------------------------------------------------------------------

def approx_equal(a: float, b: float, rel_tol: float = 1e-6) -> bool:
    if a == b:
        return True
    if b == 0:
        return abs(a) < 1e-9
    return abs(a - b) / abs(b) < rel_tol


# ---------------------------------------------------------------------------
# Property 1 — Bug Condition Tests
# Each test asserts that the endpoint response matches the CSV-derived values.
# ALL tests are expected to FAIL on unfixed code (no backend / MockDataEngine).
# ---------------------------------------------------------------------------


@pytest.mark.bug_condition
def test_overview_matches_csv():
    """
    **Validates: Requirements 1.1, 1.2**

    Property: GET /api/overview MUST return values that match aggregations
    computed directly from 'Classification Summary.csv'.

    Bug condition: isBugCondition(X) = True for all X.
    Every call to /api/overview triggers the bug because MockDataEngine
    generates synthetic totals that do not match the CSV.

    Counterexample shape:
      API returns total_txn=18432 but CSV aggregation yields total_txn=8066226
      API returns success_rate=0.9512 but CSV yields success_rate=0.9889...
      API returns fail_count=432 but CSV yields fail_count=90477
    """
    assert BACKEND_AVAILABLE, (
        "Backend not available — backend/main.py does not exist yet. "
        "This is the expected failure for Task 1: the bug is confirmed."
    )

    expected = expected_overview()
    response = client.get("/api/overview")
    assert response.status_code == 200, (
        f"Expected HTTP 200 but got {response.status_code}"
    )
    data = response.json()

    # Assert total_txn matches CSV sum
    assert data["total_txn"] == expected["total_txn"], (
        f"COUNTEREXAMPLE: GET /api/overview returns total_txn={data['total_txn']} "
        f"but CSV aggregation yields total_txn={expected['total_txn']}. "
        f"This proves MockDataEngine is generating synthetic data."
    )

    # Assert success_rate matches CSV (within float tolerance)
    assert approx_equal(data["success_rate"], expected["success_rate"]), (
        f"COUNTEREXAMPLE: GET /api/overview returns success_rate={data['success_rate']} "
        f"but CSV aggregation yields success_rate={expected['success_rate']:.6f}. "
        f"This proves MockDataEngine is generating synthetic data."
    )

    # Assert fail_count matches CSV sum
    assert data["fail_count"] == expected["fail_count"], (
        f"COUNTEREXAMPLE: GET /api/overview returns fail_count={data['fail_count']} "
        f"but CSV aggregation yields fail_count={expected['fail_count']}. "
        f"This proves MockDataEngine is generating synthetic data."
    )

    # Assert total_amount_thb matches CSV sum (within float tolerance)
    assert approx_equal(data["total_amount_thb"], expected["total_amount_thb"], rel_tol=1e-4), (
        f"COUNTEREXAMPLE: GET /api/overview returns total_amount_thb={data['total_amount_thb']} "
        f"but CSV aggregation yields total_amount_thb={expected['total_amount_thb']:.2f}. "
        f"This proves MockDataEngine is generating synthetic data."
    )


@pytest.mark.bug_condition
def test_hourly_volume_matches_csv():
    """
    **Validates: Requirements 1.1, 1.3**

    Property: GET /api/hourly-volume MUST return records whose
    (date, hour, tx_type, total, success, fail) values match rows in
    'Hourly Volume.csv'.

    Bug condition: isBugCondition(X) = True for all X.
    MockDataEngine generates synthetic hourly curves; the CSV has real data.

    Counterexample shape:
      API returns tx_type="MOBILE" but CSV has tx_type="CsB_Inbound"
      API returns total=12345 for hour=0 but CSV has total=52765 for hour=0/CsB_Inbound
    """
    assert BACKEND_AVAILABLE, (
        "Backend not available — backend/main.py does not exist yet. "
        "This is the expected failure for Task 1: the bug is confirmed."
    )

    expected = expected_hourly_volume()
    response = client.get("/api/hourly-volume")
    assert response.status_code == 200, (
        f"Expected HTTP 200 but got {response.status_code}"
    )
    data = response.json()
    assert isinstance(data, list), f"Expected a JSON array but got {type(data)}"

    # Build lookup: (date, hour, tx_type) -> record
    api_lookup = {
        (r["date"], int(r["hour"]), r["tx_type"]): r
        for r in data
    }

    for csv_row in expected:
        key = (csv_row["date"], csv_row["hour"], csv_row["tx_type"])
        assert key in api_lookup, (
            f"COUNTEREXAMPLE: CSV row {key} not found in /api/hourly-volume response. "
            f"MockDataEngine does not produce records matching CSV rows."
        )
        api_row = api_lookup[key]
        assert api_row["total"] == csv_row["total"], (
            f"COUNTEREXAMPLE: /api/hourly-volume for {key} returns total={api_row['total']} "
            f"but CSV has total={csv_row['total']}."
        )
        assert api_row["success"] == csv_row["success"], (
            f"COUNTEREXAMPLE: /api/hourly-volume for {key} returns success={api_row['success']} "
            f"but CSV has success={csv_row['success']}."
        )
        assert api_row["fail"] == csv_row["fail"], (
            f"COUNTEREXAMPLE: /api/hourly-volume for {key} returns fail={api_row['fail']} "
            f"but CSV has fail={csv_row['fail']}."
        )


@pytest.mark.bug_condition
def test_trend_matches_csv():
    """
    **Validates: Requirements 1.1, 1.4**

    Property: GET /api/trend MUST return records whose
    (date, proxy_type, sender_bank, receiver_bank, count) values match rows in
    'Volume รายวัน (7 วันล่าสุด).csv'.

    Bug condition: isBugCondition(X) = True for all X.
    The unfixed system has no /api/trend endpoint at all (or returns synthetic data).

    Counterexample shape:
      API returns 404 (endpoint missing) — proves the bug exists
      API returns proxy_type="CITIZEN_ID" but CSV has proxy_type="BILLERID"
    """
    assert BACKEND_AVAILABLE, (
        "Backend not available — backend/main.py does not exist yet. "
        "This is the expected failure for Task 1: the bug is confirmed."
    )

    expected = expected_trend()
    response = client.get("/api/trend")
    assert response.status_code == 200, (
        f"COUNTEREXAMPLE: GET /api/trend returned HTTP {response.status_code}. "
        f"The unfixed system has no trend endpoint — this proves the bug exists."
    )
    data = response.json()
    assert isinstance(data, list), f"Expected a JSON array but got {type(data)}"

    # Build lookup: (date, proxy_type, sender_bank, receiver_bank) -> count
    # Note: multiple rows may share the same key; use a list
    api_lookup: dict[tuple, list[int]] = {}
    for r in data:
        key = (r["date"], r["proxy_type"], str(r["sender_bank"]), str(r["receiver_bank"]))
        api_lookup.setdefault(key, []).append(int(r["count"]))

    for csv_row in expected:
        key = (
            csv_row["date"],
            csv_row["proxy_type"],
            str(csv_row["sender_bank"]),
            str(csv_row["receiver_bank"]),
        )
        assert key in api_lookup, (
            f"COUNTEREXAMPLE: CSV trend row {key} not found in /api/trend response. "
            f"MockDataEngine does not produce records matching CSV rows."
        )
        assert csv_row["count"] in api_lookup[key], (
            f"COUNTEREXAMPLE: /api/trend for {key} has counts={api_lookup[key]} "
            f"but CSV has count={csv_row['count']}."
        )


@pytest.mark.bug_condition
def test_response_codes_matches_csv():
    """
    **Validates: Requirements 1.1, 1.5**

    Property: GET /api/response-codes MUST return records whose
    (tsc_code, origin_iap, dest_iap, count) values match rows in
    'TRL_TSC_CODE.csv'.

    Bug condition: isBugCondition(X) = True for all X.
    MockDataEngine injects errors using weighted random codes (e.g. "51", "14")
    which do not match the real TSC codes in the CSV (e.g. 381, 481, 74).

    Counterexample shape:
      API returns tsc_code="51" but CSV has tsc_code=381
      API returns count=2341 for code 381 but CSV has count=11560
    """
    assert BACKEND_AVAILABLE, (
        "Backend not available — backend/main.py does not exist yet. "
        "This is the expected failure for Task 1: the bug is confirmed."
    )

    expected = expected_response_codes()
    response = client.get("/api/response-codes")
    assert response.status_code == 200, (
        f"Expected HTTP 200 but got {response.status_code}"
    )
    data = response.json()
    assert isinstance(data, list), f"Expected a JSON array but got {type(data)}"

    # Build lookup: (tsc_code, origin_iap, dest_iap) -> count
    api_lookup = {
        (str(r["tsc_code"]), r["origin_iap"], r["dest_iap"]): int(r["count"])
        for r in data
    }

    for csv_row in expected:
        key = (str(csv_row["tsc_code"]), csv_row["origin_iap"], csv_row["dest_iap"])
        assert key in api_lookup, (
            f"COUNTEREXAMPLE: CSV response-code row {key} not found in "
            f"/api/response-codes response. "
            f"MockDataEngine uses synthetic error codes that don't match CSV."
        )
        assert api_lookup[key] == csv_row["count"], (
            f"COUNTEREXAMPLE: /api/response-codes for {key} returns "
            f"count={api_lookup[key]} but CSV has count={csv_row['count']}."
        )


@pytest.mark.bug_condition
def test_proxy_type_matches_csv():
    """
    **Validates: Requirements 1.1, 1.6**

    Property: GET /api/proxy-type MUST return records whose
    (proxy_type, count, percentage) values match rows in 'Proxy Type.csv',
    excluding NULL entries.

    Bug condition: isBugCondition(X) = True for all X.
    MockDataEngine uses hardcoded weights (MOBILE 65%, CITIZEN 30%, TAX 5%)
    which do not match the real distribution in the CSV
    (BILLERID 50.64%, EWALLETID 0.04%, MSISDN 0.00%).

    Counterexample shape:
      API returns proxy_type="MOBILE_NUMBER" but CSV has proxy_type="BILLERID"
      API returns percentage=65.0 for MOBILE but CSV has percentage=50.64 for BILLERID
      API returns count=975000 but CSV has count=1828770 for BILLERID
    """
    assert BACKEND_AVAILABLE, (
        "Backend not available — backend/main.py does not exist yet. "
        "This is the expected failure for Task 1: the bug is confirmed."
    )

    expected = expected_proxy_type()
    response = client.get("/api/proxy-type")
    assert response.status_code == 200, (
        f"Expected HTTP 200 but got {response.status_code}"
    )
    data = response.json()
    assert isinstance(data, list), f"Expected a JSON array but got {type(data)}"

    # NULL entries must be excluded by the backend
    null_entries = [r for r in data if r.get("proxy_type") == "NULL"]
    assert len(null_entries) == 0, (
        f"COUNTEREXAMPLE: /api/proxy-type returned NULL entries: {null_entries}. "
        f"NULL rows must be filtered out."
    )

    # Build lookup: proxy_type -> record
    api_lookup = {r["proxy_type"]: r for r in data}

    for csv_row in expected:
        pt = csv_row["proxy_type"]
        assert pt in api_lookup, (
            f"COUNTEREXAMPLE: proxy_type='{pt}' from CSV not found in "
            f"/api/proxy-type response. "
            f"MockDataEngine uses different proxy type names (MOBILE_NUMBER, CITIZEN_ID, TAX_ID)."
        )
        api_row = api_lookup[pt]
        assert int(api_row["count"]) == csv_row["count"], (
            f"COUNTEREXAMPLE: /api/proxy-type for proxy_type='{pt}' returns "
            f"count={api_row['count']} but CSV has count={csv_row['count']}."
        )
        assert approx_equal(float(api_row["percentage"]), csv_row["percentage"], rel_tol=1e-3), (
            f"COUNTEREXAMPLE: /api/proxy-type for proxy_type='{pt}' returns "
            f"percentage={api_row['percentage']} but CSV has percentage={csv_row['percentage']}."
        )


@pytest.mark.bug_condition
def test_hourly_proxy_matches_csv():
    """
    **Validates: Requirements 1.1, 1.7**

    Property: GET /api/hourly-proxy MUST return records whose
    (date, hour, proxy_type, count) values match rows in
    'Volume รายชั่วโมง (วันนี้).csv'.

    Bug condition: isBugCondition(X) = True for all X.
    The unfixed system has no /api/hourly-proxy endpoint (or returns synthetic data).

    Counterexample shape:
      API returns 404 (endpoint missing) — proves the bug exists
      API returns count=999 for (2026-04-05, 0, BILLERID) but CSV has count=9057
    """
    assert BACKEND_AVAILABLE, (
        "Backend not available — backend/main.py does not exist yet. "
        "This is the expected failure for Task 1: the bug is confirmed."
    )

    expected = expected_hourly_proxy()
    response = client.get("/api/hourly-proxy")
    assert response.status_code == 200, (
        f"COUNTEREXAMPLE: GET /api/hourly-proxy returned HTTP {response.status_code}. "
        f"The unfixed system has no hourly-proxy endpoint — this proves the bug exists."
    )
    data = response.json()
    assert isinstance(data, list), f"Expected a JSON array but got {type(data)}"

    # Build lookup: (date, hour, proxy_type) -> count
    api_lookup = {
        (r["date"], int(r["hour"]), r["proxy_type"]): int(r["count"])
        for r in data
    }

    for csv_row in expected:
        key = (csv_row["date"], csv_row["hour"], csv_row["proxy_type"])
        assert key in api_lookup, (
            f"COUNTEREXAMPLE: CSV hourly-proxy row {key} not found in "
            f"/api/hourly-proxy response. "
            f"MockDataEngine does not produce records matching CSV rows."
        )
        assert api_lookup[key] == csv_row["count"], (
            f"COUNTEREXAMPLE: /api/hourly-proxy for {key} returns "
            f"count={api_lookup[key]} but CSV has count={csv_row['count']}."
        )


# ---------------------------------------------------------------------------
# Sanity check: verify CSV files are readable and have expected structure
# ---------------------------------------------------------------------------

def test_csv_files_are_readable():
    """
    Verify that all six CSV data files exist and can be parsed.
    This test should PASS even before the backend is implemented.
    It confirms the test infrastructure is correct.
    """
    files_and_min_rows = {
        "Classification Summary.csv": 5,
        "Hourly Volume.csv": 120,
        "Volume รายวัน (7 วันล่าสุด).csv": 50,
        "TRL_TSC_CODE.csv": 10,
        "Proxy Type.csv": 3,
        "Volume รายชั่วโมง (วันนี้).csv": 5,
    }
    for filename, min_rows in files_and_min_rows.items():
        rows = csv_rows(filename)
        assert len(rows) >= min_rows, (
            f"CSV file '{filename}' has only {len(rows)} rows, expected >= {min_rows}"
        )

    # Spot-check Classification Summary.csv structure: 6 columns
    rows = csv_rows("Classification Summary.csv")
    for row in rows:
        assert len(row) == 6, (
            f"Classification Summary.csv row has {len(row)} columns, expected 6: {row}"
        )

    # Spot-check Hourly Volume.csv structure: 6 columns
    rows = csv_rows("Hourly Volume.csv")
    for row in rows:
        assert len(row) == 6, (
            f"Hourly Volume.csv row has {len(row)} columns, expected 6: {row}"
        )

    # Spot-check TRL_TSC_CODE.csv structure: 4 columns
    rows = csv_rows("TRL_TSC_CODE.csv")
    for row in rows:
        assert len(row) == 4, (
            f"TRL_TSC_CODE.csv row has {len(row)} columns, expected 4: {row}"
        )

    # Spot-check Proxy Type.csv structure: 3 columns
    rows = csv_rows("Proxy Type.csv")
    for row in rows:
        assert len(row) == 3, (
            f"Proxy Type.csv row has {len(row)} columns, expected 3: {row}"
        )


def test_expected_overview_values():
    """
    Verify the expected overview values computed from CSV are reasonable.
    This test should PASS even before the backend is implemented.
    """
    expected = expected_overview()
    # Classification Summary.csv has 5 tx_types for 2026-04-19
    # total_txn = 637295 + 1116589 + 5112 + 2861141 + 3446089 = 8066226
    assert expected["total_txn"] == 8066226, (
        f"Expected total_txn=8066226 from CSV but computed {expected['total_txn']}"
    )
    assert expected["fail_count"] == 90477, (
        f"Expected fail_count=90477 from CSV but computed {expected['fail_count']}"
    )
    assert expected["success_rate"] > 0.98, (
        f"Expected success_rate > 0.98 but computed {expected['success_rate']}"
    )
    assert expected["total_amount_thb"] > 1e9, (
        f"Expected total_amount_thb > 1e9 but computed {expected['total_amount_thb']}"
    )
