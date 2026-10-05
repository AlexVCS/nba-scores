from fastapi.testclient import TestClient

from server.ask.config import AskConfig
from server.ask import router
from server.main import app


def test_routes_exist_but_are_disabled_by_default(monkeypatch):
    monkeypatch.setattr(router, "_config", AskConfig(enabled=False))
    client = TestClient(app)
    response = client.post("/ask", json={"question": "Games on 2026-09-29?"})
    assert response.status_code == 200
    assert response.json()["outcome"] == "unavailable"
    suggest = client.get("/ask/suggest", params={"q": "Knicks", "hidden": True})
    assert suggest.status_code == 200
    assert suggest.json() == {"query": "Knicks", "games": [], "entities": [], "questions": []}


def test_router_runs_enabled_pipeline_inside_bounded_worker(monkeypatch):
    original_pipeline = router._pipeline
    class Limits:
        def __init__(self):
            self.clients = []
            self.run_count = 0

        def check_rate(self, client_id):
            self.clients.append(client_id)

        def run_bounded(self, work, timeout_seconds):
            self.run_count += 1
            return work()

    class Pipeline:
        def answer(self, query):
            assert query.question == "Games on 2026-09-29?"
            return original_pipeline.disabled(query.question)

    limits = Limits()
    monkeypatch.setattr(router, "_config", AskConfig(enabled=True))
    monkeypatch.setattr(router, "_limits", limits)
    monkeypatch.setattr(router, "_pipeline", Pipeline())
    response = TestClient(app).post("/ask", json={"question": "Games on 2026-09-29?"})
    assert response.status_code == 200
    assert response.json()["outcome"] == "unavailable"
    assert limits.clients == ["testclient"] and limits.run_count == 1


def test_router_rejects_invalid_query_before_work(monkeypatch):
    monkeypatch.setattr(router, "_config", AskConfig(enabled=False))
    response = TestClient(app).post("/ask", json={"question": ""})
    assert response.status_code == 422
    response = TestClient(app).post("/ask", json={"question": "hi", "resolution": "x" * 513})
    assert response.status_code == 422
