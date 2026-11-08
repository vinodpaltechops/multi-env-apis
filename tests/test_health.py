from fastapi.testclient import TestClient

from app import db, main

client = TestClient(main.app)


def test_healthz_does_not_touch_db(monkeypatch):
    def boom():
        raise AssertionError("db must not be called")

    monkeypatch.setattr(db, "check_database", boom)
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_readyz_ok(monkeypatch):
    monkeypatch.setattr(db, "check_database", lambda: None)
    r = client.get("/readyz")
    assert r.status_code == 200
    assert r.json() == {"status": "ready"}


def test_readyz_db_down(monkeypatch):
    def fail():
        raise RuntimeError("down")

    monkeypatch.setattr(db, "check_database", fail)
    r = client.get("/readyz")
    assert r.status_code == 503


def test_readyz_shutting_down(monkeypatch):
    monkeypatch.setattr(db, "check_database", lambda: None)
    main._shutting_down.set()
    try:
        assert client.get("/readyz").status_code == 503
    finally:
        main._shutting_down.clear()
