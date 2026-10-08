"""API layer: endpoint correctness, error mapping, backoff, key tests."""

from __future__ import annotations

import vt_api


class _FakeResponse:
    def __init__(self, status=200, payload=None, headers=None):
        self.status_code = status
        self._payload = payload if payload is not None else {}
        self.headers = headers or {}

    def json(self):
        if isinstance(self._payload, Exception):
            raise self._payload
        return self._payload


def test_gemini_uses_the_current_api():
    assert "v1beta" in vt_api.ENDPOINTS["gemini"]["transcribe"]
    assert "generateContent" in vt_api.ENDPOINTS["gemini"]["transcribe"]
    assert "v1beta" in vt_api.ENDPOINTS["gemini"]["models"]


def test_every_engine_has_a_models_endpoint():
    for engine in ("openai", "groq", "gemini"):
        assert vt_api.ENDPOINTS[engine]["models"].startswith("https://")


def test_key_errors_are_translated_not_raw():
    for status, key in ((401, "err_api_key_invalid"), (429, "err_api_quota"),
                        (500, "err_api_server"), (400, "err_api_bad_request")):
        try:
            vt_api._check_response(_FakeResponse(status, {"error": {"message": "nope"}}),
                                   "openai", "en", "test")
        except vt_api.ApiFailure as exc:
            assert exc.hint_key == key, (status, exc.hint_key)
            assert str(exc)
        else:
            raise AssertionError("HTTP %s should fail" % status)


def test_http_retries_a_rate_limit_then_succeeds(monkeypatch):
    import vt_api as api

    calls = {"n": 0}
    sleeps = []

    def fake_request(*_args, **_kwargs):
        calls["n"] += 1
        if calls["n"] < 3:
            return _FakeResponse(429, {}, headers={"Retry-After": "0.01"})
        return _FakeResponse(200, {"ok": True})

    monkeypatch.setattr(api.time, "sleep", lambda s: sleeps.append(s))
    import requests

    monkeypatch.setattr(requests, "request", fake_request)

    response = api._http("GET", url="https://example.invalid/")
    assert response.status_code == 200
    assert calls["n"] == 3
    assert sleeps, "the pauses must be there"


def test_http_gives_up_after_three_tries(monkeypatch):
    import requests

    import vt_api as api

    monkeypatch.setattr(api.time, "sleep", lambda s: None)
    monkeypatch.setattr(
        requests, "request", lambda *a, **k: _FakeResponse(503, {})
    )
    response = api._http("GET", url="https://example.invalid/")
    assert response.status_code == 503


def test_test_key_needs_a_key():
    ok, message = vt_api.test_key("openai", "", "en")
    assert ok is False
    assert message
    ok_ar, message_ar = vt_api.test_key("openai", "", "ar")
    assert ok_ar is False
    assert message_ar != message  # the Arabic wording differs


def test_test_key_rejects_an_unknown_engine():
    ok, message = vt_api.test_key("nope", "x", "en")
    assert ok is False and message
