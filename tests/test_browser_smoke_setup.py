"""Index preparation must wait for readiness without hiding a failed build."""

import io
import json

import pytest

import test_browser_smoke as smoke


def response(status):
    return io.BytesIO(json.dumps(status).encode())


def test_index_setup_waits_for_an_available_ready_index(monkeypatch):
    states = iter([
        {"state": "building", "available": True},
        {"state": "ready", "available": False},
        {"state": "ready", "available": True},
    ])
    calls = []

    def fetch(url, timeout):
        calls.append((url, timeout))
        return response(next(states))

    monkeypatch.setattr(smoke, "urlopen", fetch)
    monkeypatch.setattr(smoke.time, "sleep", lambda _delay: None)
    smoke._wait_for_search_index("http://fixture/api/search/status")
    assert calls == [("http://fixture/api/search/status", 2.0)] * 3


def test_index_setup_reports_database_failure_immediately(monkeypatch):
    monkeypatch.setattr(smoke, "urlopen", lambda *_args, **_kwargs: response(
        {"state": "error", "available": False, "error": "disk I/O error"}
    ))
    with pytest.raises(RuntimeError, match="disk I/O error"):
        smoke._wait_for_search_index("http://fixture/api/search/status")


def test_index_setup_has_a_bounded_deadline_and_reports_last_progress(monkeypatch):
    clock = iter([0.0, 0.0, 2.0])
    monkeypatch.setattr(smoke.time, "monotonic", lambda: next(clock))
    monkeypatch.setattr(smoke.time, "sleep", lambda _delay: None)
    monkeypatch.setattr(smoke, "urlopen", lambda *_args, **_kwargs: response(
        {"state": "building", "available": True, "percent": 27}
    ))
    with pytest.raises(TimeoutError, match="'percent': 27"):
        smoke._wait_for_search_index("http://fixture/api/search/status", timeout=1.0)
