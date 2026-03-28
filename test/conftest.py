import pytest

try:
    import mongomock
except ImportError:
    mongomock = None

try:
    _db_mod = __import__("app_ref.services.db", fromlist=["get_db"])
except ModuleNotFoundError:
    try:
        _db_mod = __import__("app.services.db", fromlist=["get_db"])
    except ModuleNotFoundError:
        _db_mod = None


@pytest.fixture(autouse=True)
def mock_db(monkeypatch):
    """Override db elements to return a fresh mongomock database for each test (when mongomock and app db exist)."""
    if mongomock is None or _db_mod is None:
        return None
    client = mongomock.MongoClient()
    db = client.get_database("test_db")
    monkeypatch.setattr(_db_mod, "_client", client, raising=False)
    monkeypatch.setattr(_db_mod, "_db", db, raising=False)
    monkeypatch.setattr(_db_mod, "get_db", lambda: db, raising=False)
    return db

@pytest.fixture
def tenant_id():
    return "test-tenant"
