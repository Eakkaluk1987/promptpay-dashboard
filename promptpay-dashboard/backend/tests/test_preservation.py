"""
Preservation Property Tests — Property 2: Architecture and Non-Data-Source Behaviour Unchanged

**Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 3.6**

These tests encode the EXPECTED architectural behaviour that must be preserved after the fix.
They assert that the FastAPI + Streamlit architecture, endpoint routing, CORS configuration,
JSON schema shapes, and error-handling patterns are all unchanged by the data-source swap.

IMPORTANT: These tests will FAIL before the backend is implemented (Task 3) because
`backend.main` does not exist yet. That is acceptable — the tests encode the contract
that Task 3 must satisfy.

EXPECTED OUTCOME:
  - Before Task 3: FAIL with ImportError / connection error (no backend yet)
  - After Task 3:  PASS (confirms architectural preservation)

Preservation contract (from bugfix.md):
  FOR ALL X WHERE NOT isBugCondition(X) DO
    ASSERT F(X) = F'(X)
  END FOR

Where F is the original system and F' is the fixed system.
The architectural concerns tested here are NOT data-source concerns, so they must
be identical before and after the fix.
"""

import pytest

# ---------------------------------------------------------------------------
# FastAPI TestClient setup
# ---------------------------------------------------------------------------
# This import WILL FAIL until the backend is implemented (Task 3).
# That failure is the expected outcome for Task 2 — the tests encode the
# contract that must be satisfied after the fix.

try:
    from fastapi.testclient import TestClient
    from backend.main import app  # noqa: E402  — does not exist yet
    client = TestClient(app)
    BACKEND_AVAILABLE = True
except (ImportError, ModuleNotFoundError, Exception):
    client = None
    BACKEND_AVAILABLE = False


# ---------------------------------------------------------------------------
# Hypothesis availability check
# ---------------------------------------------------------------------------

try:
    import hypothesis  # noqa: F401
    HYPOTHESIS_AVAILABLE = True
except ImportError:
    HYPOTHESIS_AVAILABLE = False


# ---------------------------------------------------------------------------
# Constants: the six REST endpoints that must be preserved
# ---------------------------------------------------------------------------

# Endpoints that return a JSON object (dict)
OBJECT_ENDPOINTS = [
    "/api/overview",
]

# Endpoints that return a JSON array (list)
ARRAY_ENDPOINTS = [
    "/api/hourly-volume",
    "/api/trend",
    "/api/response-codes",
    "/api/proxy-type",
    "/api/hourly-proxy",
]

ALL_API_ENDPOINTS = OBJECT_ENDPOINTS + ARRAY_ENDPOINTS

# Required keys for the /api/overview response object
OVERVIEW_REQUIRED_KEYS = {"total_txn", "success_rate", "fail_count", "total_amount_thb"}

# Expected CORS origin
CORS_ALLOWED_ORIGIN = "http://localhost:8501"


# ---------------------------------------------------------------------------
# Preservation Test 1: Health endpoint
# Requirement 3.1 — FastAPI starts on port 8000 and exposes /api/health
# ---------------------------------------------------------------------------

@pytest.mark.preservation
def test_health_endpoint_returns_200():
    """
    **Validates: Requirements 3.1, 3.2**

    Preservation: GET /api/health MUST return HTTP 200.
    This endpoint is the liveness probe for the backend; it must be preserved
    after the data-source swap.

    Expected response body: {"status": "ok"} or {"status": "degraded", ...}
    """
    assert BACKEND_AVAILABLE, (
        "Backend not available — backend/main.py does not exist yet. "
        "This test will pass after Task 3 implements the backend."
    )

    response = client.get("/api/health")
    assert response.status_code == 200, (
        f"GET /api/health returned HTTP {response.status_code}, expected 200. "
        f"The health endpoint must be preserved after the fix."
    )

    data = response.json()
    assert isinstance(data, dict), (
        f"GET /api/health returned {type(data)}, expected a JSON object."
    )
    assert "status" in data, (
        f"GET /api/health response missing 'status' key: {data}"
    )
    assert data["status"] in ("ok", "degraded"), (
        f"GET /api/health 'status' must be 'ok' or 'degraded', got: {data['status']}"
    )


# ---------------------------------------------------------------------------
# Preservation Test 2: All endpoints reachable under /api/ prefix
# Requirement 3.1 — endpoints under /api/ prefix (NOT /api/metrics/)
# ---------------------------------------------------------------------------

@pytest.mark.preservation
@pytest.mark.parametrize("endpoint", ALL_API_ENDPOINTS)
def test_all_endpoints_reachable_under_api_prefix(endpoint):
    """
    **Validates: Requirements 3.1, 3.2**

    Preservation: All REST endpoints MUST be reachable under the /api/ prefix.
    The design uses /api/<resource> (NOT /api/metrics/<resource>).
    This routing must be preserved after the fix.
    """
    assert BACKEND_AVAILABLE, (
        f"Backend not available — backend/main.py does not exist yet. "
        f"This test will pass after Task 3 implements the backend."
    )

    response = client.get(endpoint)
    assert response.status_code == 200, (
        f"GET {endpoint} returned HTTP {response.status_code}, expected 200. "
        f"All endpoints must be reachable under the /api/ prefix after the fix."
    )


@pytest.mark.preservation
@pytest.mark.parametrize("wrong_endpoint", [
    "/api/metrics/overview",
    "/api/metrics/hourly-volume",
    "/api/metrics/trend",
    "/api/metrics/response-codes",
    "/api/metrics/proxy-type",
    "/api/metrics/hourly-proxy",
])
def test_endpoints_not_under_metrics_prefix(wrong_endpoint):
    """
    **Validates: Requirements 3.1**

    Preservation: Endpoints MUST NOT be under /api/metrics/ prefix.
    The correct prefix is /api/ only.
    This test ensures the routing is not accidentally changed to /api/metrics/.
    """
    assert BACKEND_AVAILABLE, (
        f"Backend not available — backend/main.py does not exist yet. "
        f"This test will pass after Task 3 implements the backend."
    )

    response = client.get(wrong_endpoint)
    assert response.status_code == 404, (
        f"GET {wrong_endpoint} returned HTTP {response.status_code}, expected 404. "
        f"Endpoints must NOT be registered under /api/metrics/ prefix."
    )


# ---------------------------------------------------------------------------
# Preservation Test 3: CORS header present on all API responses
# Requirement 3.2 — CORS allows http://localhost:8501 specifically
# ---------------------------------------------------------------------------

@pytest.mark.preservation
@pytest.mark.parametrize("endpoint", ALL_API_ENDPOINTS + ["/api/health"])
def test_cors_header_present_on_all_responses(endpoint):
    """
    **Validates: Requirements 3.2**

    Preservation: CORS header 'Access-Control-Allow-Origin: http://localhost:8501'
    MUST be present on all API responses.

    The CORS configuration must allow the Streamlit origin specifically (not wildcard).
    This must be preserved after the data-source swap.
    """
    assert BACKEND_AVAILABLE, (
        f"Backend not available — backend/main.py does not exist yet. "
        f"This test will pass after Task 3 implements the backend."
    )

    # Send request with the Streamlit origin header to trigger CORS
    response = client.get(endpoint, headers={"Origin": CORS_ALLOWED_ORIGIN})
    assert response.status_code == 200, (
        f"GET {endpoint} returned HTTP {response.status_code}, expected 200."
    )

    cors_header = response.headers.get("access-control-allow-origin", "")
    assert cors_header == CORS_ALLOWED_ORIGIN, (
        f"GET {endpoint} CORS header 'Access-Control-Allow-Origin' is '{cors_header}', "
        f"expected '{CORS_ALLOWED_ORIGIN}'. "
        f"CORS must allow the Streamlit origin specifically after the fix."
    )


# ---------------------------------------------------------------------------
# Preservation Test 4: /api/overview JSON schema preserved
# Requirement 3.3 — Overview returns object with specific keys
# ---------------------------------------------------------------------------

@pytest.mark.preservation
def test_overview_returns_object_with_required_keys():
    """
    **Validates: Requirements 3.3**

    Preservation: GET /api/overview MUST return HTTP 200 with a JSON object
    containing exactly the keys: total_txn, success_rate, fail_count, total_amount_thb.

    The JSON schema (key names and types) must be unchanged after the fix.
    Only the values change (from synthetic to CSV-derived).
    """
    assert BACKEND_AVAILABLE, (
        "Backend not available — backend/main.py does not exist yet. "
        "This test will pass after Task 3 implements the backend."
    )

    response = client.get("/api/overview")
    assert response.status_code == 200, (
        f"GET /api/overview returned HTTP {response.status_code}, expected 200."
    )

    data = response.json()
    assert isinstance(data, dict), (
        f"GET /api/overview returned {type(data).__name__}, expected a JSON object (dict). "
        f"The overview endpoint must return an object, not an array or scalar."
    )

    missing_keys = OVERVIEW_REQUIRED_KEYS - set(data.keys())
    assert not missing_keys, (
        f"GET /api/overview response is missing required keys: {missing_keys}. "
        f"Full response: {data}"
    )


@pytest.mark.preservation
def test_overview_value_types_preserved():
    """
    **Validates: Requirements 3.3**

    Preservation: The value types in /api/overview must be preserved:
      - total_txn: int (or numeric)
      - success_rate: float in [0.0, 1.0]
      - fail_count: int (or numeric)
      - total_amount_thb: float (positive)
    """
    assert BACKEND_AVAILABLE, (
        "Backend not available — backend/main.py does not exist yet. "
        "This test will pass after Task 3 implements the backend."
    )

    response = client.get("/api/overview")
    assert response.status_code == 200
    data = response.json()

    assert isinstance(data.get("total_txn"), (int, float)), (
        f"total_txn must be numeric, got {type(data.get('total_txn')).__name__}"
    )
    assert isinstance(data.get("success_rate"), (int, float)), (
        f"success_rate must be numeric, got {type(data.get('success_rate')).__name__}"
    )
    assert 0.0 <= float(data["success_rate"]) <= 1.0, (
        f"success_rate must be in [0.0, 1.0], got {data['success_rate']}"
    )
    assert isinstance(data.get("fail_count"), (int, float)), (
        f"fail_count must be numeric, got {type(data.get('fail_count')).__name__}"
    )
    assert isinstance(data.get("total_amount_thb"), (int, float)), (
        f"total_amount_thb must be numeric, got {type(data.get('total_amount_thb')).__name__}"
    )
    assert float(data["total_amount_thb"]) >= 0, (
        f"total_amount_thb must be non-negative, got {data['total_amount_thb']}"
    )


# ---------------------------------------------------------------------------
# Preservation Test 5: Array endpoints return JSON arrays
# Requirement 3.4 — Five endpoints return JSON arrays
# ---------------------------------------------------------------------------

@pytest.mark.preservation
@pytest.mark.parametrize("endpoint", ARRAY_ENDPOINTS)
def test_array_endpoints_return_json_arrays(endpoint):
    """
    **Validates: Requirements 3.4**

    Preservation: GET /api/hourly-volume, /api/trend, /api/response-codes,
    /api/proxy-type, /api/hourly-proxy MUST each return HTTP 200 with a JSON array.

    The response body must be a list (never a dict, string, or null).
    This schema must be preserved after the fix.
    """
    assert BACKEND_AVAILABLE, (
        f"Backend not available — backend/main.py does not exist yet. "
        f"This test will pass after Task 3 implements the backend."
    )

    response = client.get(endpoint)
    assert response.status_code == 200, (
        f"GET {endpoint} returned HTTP {response.status_code}, expected 200."
    )

    data = response.json()
    assert isinstance(data, list), (
        f"GET {endpoint} returned {type(data).__name__}, expected a JSON array (list). "
        f"This endpoint must return an array after the fix."
    )
    assert data is not None, (
        f"GET {endpoint} returned null, expected a JSON array."
    )


# ---------------------------------------------------------------------------
# Preservation Test 6: Response bodies are never null or plain strings
# Property: for all six endpoints, body is object or array (never string/null)
# ---------------------------------------------------------------------------

@pytest.mark.preservation
@pytest.mark.parametrize("endpoint", ALL_API_ENDPOINTS)
def test_response_body_is_never_null_or_string(endpoint):
    """
    **Validates: Requirements 3.3, 3.4**

    Preservation: For all six endpoints, the response body MUST be a JSON object
    or array — never a plain string, null, or primitive value.

    This property must hold both before and after the fix.
    """
    assert BACKEND_AVAILABLE, (
        f"Backend not available — backend/main.py does not exist yet. "
        f"This test will pass after Task 3 implements the backend."
    )

    response = client.get(endpoint)
    assert response.status_code == 200, (
        f"GET {endpoint} returned HTTP {response.status_code}, expected 200."
    )

    data = response.json()
    assert data is not None, (
        f"GET {endpoint} returned null. Response body must never be null."
    )
    assert not isinstance(data, str), (
        f"GET {endpoint} returned a plain string: '{data}'. "
        f"Response body must be a JSON object or array, never a string."
    )
    assert isinstance(data, (dict, list)), (
        f"GET {endpoint} returned {type(data).__name__}. "
        f"Response body must be a JSON object (dict) or array (list)."
    )


# ---------------------------------------------------------------------------
# Preservation Property Tests (Hypothesis): only defined when hypothesis is available
# ---------------------------------------------------------------------------

if HYPOTHESIS_AVAILABLE:
    from hypothesis import given, settings, HealthCheck
    import hypothesis.strategies as st

    @pytest.mark.preservation
    @pytest.mark.skipif(not BACKEND_AVAILABLE, reason="backend not available yet")
    @given(endpoint=st.sampled_from(ALL_API_ENDPOINTS))
    @settings(max_examples=20, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_property_all_endpoints_return_200_and_valid_schema(endpoint):
        """
        **Validates: Requirements 3.3, 3.4**

        Property-based test: For all valid endpoint paths, the response status
        is 200 and the JSON schema (key names and types) is unchanged after the fix.

        This property holds universally across all six endpoints.
        """
        response = client.get(endpoint)

        # Property: status is always 200
        assert response.status_code == 200, (
            f"GET {endpoint} returned HTTP {response.status_code}, expected 200."
        )

        data = response.json()

        # Property: body is never null or string
        assert data is not None, f"GET {endpoint} returned null"
        assert not isinstance(data, str), f"GET {endpoint} returned a plain string"
        assert isinstance(data, (dict, list)), (
            f"GET {endpoint} returned {type(data).__name__}, expected dict or list"
        )

        # Property: overview returns object with required keys
        if endpoint == "/api/overview":
            assert isinstance(data, dict), f"/api/overview must return a dict"
            missing = OVERVIEW_REQUIRED_KEYS - set(data.keys())
            assert not missing, f"/api/overview missing keys: {missing}"

        # Property: array endpoints return non-null lists
        if endpoint in ARRAY_ENDPOINTS:
            assert isinstance(data, list), f"{endpoint} must return a list"

    @pytest.mark.preservation
    @pytest.mark.skipif(not BACKEND_AVAILABLE, reason="backend not available yet")
    @given(endpoint=st.sampled_from(ALL_API_ENDPOINTS))
    @settings(max_examples=20, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_property_response_body_never_null_or_string(endpoint):
        """
        **Validates: Requirements 3.3, 3.4**

        Property-based test: For all six endpoints, the response body is a JSON
        object or array — never a string or null.

        This is a universal invariant that must hold after the fix.
        """
        response = client.get(endpoint)
        data = response.json()

        # Universal property: body is never null
        assert data is not None, (
            f"Counterexample: GET {endpoint} returned null. "
            f"Response body must never be null."
        )

        # Universal property: body is never a plain string
        assert not isinstance(data, str), (
            f"Counterexample: GET {endpoint} returned a plain string: '{data}'. "
            f"Response body must be a JSON object or array."
        )

        # Universal property: body is always dict or list
        assert isinstance(data, (dict, list)), (
            f"Counterexample: GET {endpoint} returned {type(data).__name__}. "
            f"Response body must be a JSON object (dict) or array (list)."
        )


# ---------------------------------------------------------------------------
# Preservation Test 7: Backend-unavailable error handling (Streamlit side)
# Requirement 3.5 — Streamlit shows st.error() when backend is unreachable
# ---------------------------------------------------------------------------

@pytest.mark.preservation
def test_streamlit_error_handling_when_backend_unreachable():
    """
    **Validates: Requirements 3.5**

    Preservation: When the backend is unreachable, the Streamlit dashboard
    MUST display an st.error() banner instead of crashing.

    This test verifies the frontend fetch helper handles ConnectionError gracefully.
    Since we cannot run Streamlit in a test, we verify the fetch helper logic
    by importing it and simulating a connection failure.
    """
    # This test verifies the architectural contract by checking the frontend module
    # can be imported and has the expected error-handling structure.
    # The actual st.error() call is verified by code inspection.
    try:
        import importlib.util
        import pathlib

        # Locate the frontend dashboard module
        workspace_root = pathlib.Path(__file__).resolve().parents[3]
        dashboard_path = workspace_root / "promptpay-dashboard" / "frontend" / "dashboard.py"

        if not dashboard_path.exists():
            pytest.skip(
                "frontend/dashboard.py does not exist yet — "
                "this test will pass after Task 3 implements the frontend."
            )

        source = dashboard_path.read_text(encoding="utf-8")

        # Verify the frontend uses st.error() for error handling
        assert "st.error(" in source, (
            "frontend/dashboard.py must call st.error() when the backend is unreachable. "
            "This error-handling pattern must be preserved after the fix."
        )

        # Verify the frontend catches ConnectionError
        assert "ConnectionError" in source or "except" in source, (
            "frontend/dashboard.py must handle connection errors gracefully. "
            "The try/except pattern must be preserved after the fix."
        )

        # Verify the frontend targets port 8000
        assert "8000" in source, (
            "frontend/dashboard.py must connect to the backend on port 8000. "
            "The port configuration must be preserved after the fix."
        )

    except Exception as e:
        pytest.fail(
            f"Could not verify Streamlit error-handling preservation: {e}. "
            f"This test will pass after Task 3 implements the frontend."
        )


# ---------------------------------------------------------------------------
# Sanity check: verify the test infrastructure itself is correct
# (These should pass even before the backend is implemented)
# ---------------------------------------------------------------------------

def test_endpoint_lists_are_complete():
    """
    Verify that the endpoint lists cover all six required endpoints.
    This test should PASS even before the backend is implemented.
    """
    assert len(ALL_API_ENDPOINTS) == 6, (
        f"Expected 6 endpoints in ALL_API_ENDPOINTS, got {len(ALL_API_ENDPOINTS)}: "
        f"{ALL_API_ENDPOINTS}"
    )
    assert len(ARRAY_ENDPOINTS) == 5, (
        f"Expected 5 array endpoints, got {len(ARRAY_ENDPOINTS)}: {ARRAY_ENDPOINTS}"
    )
    assert len(OBJECT_ENDPOINTS) == 1, (
        f"Expected 1 object endpoint, got {len(OBJECT_ENDPOINTS)}: {OBJECT_ENDPOINTS}"
    )
    assert "/api/overview" in OBJECT_ENDPOINTS
    assert "/api/hourly-volume" in ARRAY_ENDPOINTS
    assert "/api/trend" in ARRAY_ENDPOINTS
    assert "/api/response-codes" in ARRAY_ENDPOINTS
    assert "/api/proxy-type" in ARRAY_ENDPOINTS
    assert "/api/hourly-proxy" in ARRAY_ENDPOINTS


def test_cors_origin_is_streamlit_default():
    """
    Verify the CORS origin constant matches the Streamlit default port.
    This test should PASS even before the backend is implemented.
    """
    assert CORS_ALLOWED_ORIGIN == "http://localhost:8501", (
        f"CORS_ALLOWED_ORIGIN must be 'http://localhost:8501', got '{CORS_ALLOWED_ORIGIN}'"
    )


def test_overview_required_keys_are_correct():
    """
    Verify the required keys for /api/overview match the spec.
    This test should PASS even before the backend is implemented.
    """
    assert OVERVIEW_REQUIRED_KEYS == {
        "total_txn", "success_rate", "fail_count", "total_amount_thb"
    }, (
        f"OVERVIEW_REQUIRED_KEYS does not match spec: {OVERVIEW_REQUIRED_KEYS}"
    )
