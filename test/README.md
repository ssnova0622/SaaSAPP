Test suite for SaasProject

How to run
1) Create and activate the virtualenv (optional if already active)
2) Install dev deps if needed: pip install -r requirements.txt pytest httpx
3) Run tests:
```
pytest -q
```

Structure
- conftest.py: shared fixtures (FastAPI TestClient or HTTP client base URL), helpers
- test_auth.py: auth/token smoke
- test_tenants.py: tenants list/get/update
