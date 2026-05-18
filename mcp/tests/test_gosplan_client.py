import pytest

import gosplan_client as gc


class FakeResp:
    def __init__(self, status, json_data=None, content=b""):
        self.status_code = status
        self._json = json_data
        self.content = content
        self.headers = {}

    def json(self):
        return self._json


def test_get_purchase_ok(monkeypatch):
    monkeypatch.setattr(gc.requests, "get",
                        lambda *a, **k: FakeResp(200, {"purchase_number": "X"}))
    assert gc.get_purchase(44, "X")["purchase_number"] == "X"


def test_get_purchase_404_raises_notfound(monkeypatch):
    monkeypatch.setattr(gc.requests, "get", lambda *a, **k: FakeResp(404))
    with pytest.raises(gc.GosplanNotFound):
        gc.get_purchase(44, "MISSING")


def test_429_retries_then_raises(monkeypatch):
    calls = {"n": 0}

    def fake_get(*a, **k):
        calls["n"] += 1
        return FakeResp(429)

    monkeypatch.setattr(gc.requests, "get", fake_get)
    monkeypatch.setattr(gc.time, "sleep", lambda s: None)
    with pytest.raises(gc.GosplanError):
        gc.get_purchase(44, "X")
    assert calls["n"] == gc.MAX_RETRIES + 1


def test_api_key_header(monkeypatch):
    seen = {}

    def fake_get(url, headers=None, timeout=None, stream=False):
        seen.update(headers or {})
        return FakeResp(200, {"ok": 1})

    monkeypatch.setenv("GOSPLAN_API_KEY", "secret123")
    monkeypatch.setattr(gc.requests, "get", fake_get)
    gc.get_purchase(44, "X")
    assert seen.get(gc.API_KEY_HEADER) == "secret123"


def test_get_contract_procedures_url(monkeypatch):
    seen = {}

    def fake_get(url, headers=None, timeout=None, stream=False):
        seen["url"] = url
        return FakeResp(200, [{"doc_type": "contractProcedure"}])

    monkeypatch.setattr(gc.requests, "get", fake_get)
    out = gc.get_contract_procedures(44, "REG1")
    assert out == [{"doc_type": "contractProcedure"}]
    assert seen["url"].endswith("/fz44/contracts/REG1/procedures")


def test_get_contract_procedures_404_returns_empty(monkeypatch):
    monkeypatch.setattr(gc.requests, "get", lambda *a, **k: FakeResp(404))
    # нет этапов исполнения — это валидно (контракт без актов), не ошибка
    assert gc.get_contract_procedures(44, "REG1") == []
