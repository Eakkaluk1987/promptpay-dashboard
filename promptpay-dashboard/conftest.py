"""
conftest.py — adds the promptpay-dashboard/ directory to sys.path so that
`from backend.main import app` works correctly in tests.
"""
import sys
import pathlib

# promptpay-dashboard/ directory (parent of this file)
DASHBOARD_ROOT = pathlib.Path(__file__).resolve().parent

if str(DASHBOARD_ROOT) not in sys.path:
    sys.path.insert(0, str(DASHBOARD_ROOT))
