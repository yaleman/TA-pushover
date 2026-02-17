"""Unit tests for TA-pushover runtime logic."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any, Dict, Iterator, List, Mapping, Optional

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from package.bin.ta_pushover.modalert_pushover_helper import process_event  # noqa: E402
from package.bin.ta_pushover.pushover_common import (  # noqa: E402
    PushoverClient,
    event_value_or_literal,
    extract_account_credentials,
    parse_priority,
)


class _FakeResponse:
    def __init__(self, status_code: int, payload: Dict[str, Any], text: str = "") -> None:
        self.status_code = status_code
        self._payload = payload
        self.text = text

    def json(self) -> Dict[str, Any]:
        return self._payload


class _FakeHelper:
    def __init__(
        self,
        *,
        params: Mapping[str, str],
        account: Mapping[str, str],
        events: Optional[List[Dict[str, str]]] = None,
    ) -> None:
        self._params = dict(params)
        self._account = dict(account)
        self._events = list(events or [])
        self.logged: List[str] = []

    def get_param(self, key: str) -> Optional[str]:
        return self._params.get(key)

    def get_user_credential_by_account_id(self, account_id: str) -> Mapping[str, str]:
        if account_id != self._params.get("account"):
            raise ValueError("wrong account requested")
        return self._account

    def get_events(self) -> Iterator[Dict[str, str]]:
        return iter(self._events)

    def log_info(self, message: str) -> None:
        self.logged.append(message)


def test_parse_priority() -> None:
    assert parse_priority(None) == 0
    assert parse_priority("") == 0
    assert parse_priority("-1") == -1
    assert parse_priority(2) == 2
    with pytest.raises(ValueError):
        parse_priority(3)


def test_event_value_or_literal() -> None:
    event = {"message": "hello"}
    assert event_value_or_literal("message", event) == "hello"
    assert event_value_or_literal("literal text", event) == "literal text"
    assert event_value_or_literal("", event) is None


def test_extract_account_credentials_supports_ucc_and_legacy_shapes() -> None:
    assert extract_account_credentials({"user": "u", "app_token": "t"}) == ("u", "t")
    assert extract_account_credentials({"username": "u", "password": "t"}) == ("u", "t")
    with pytest.raises(ValueError):
        extract_account_credentials({"user": "u"})


def test_pushover_client_send_success(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: Dict[str, Any] = {}

    def _fake_post(url: str, json: Dict[str, Any], timeout: int) -> _FakeResponse:
        captured["url"] = url
        captured["json"] = json
        captured["timeout"] = timeout
        return _FakeResponse(200, {"status": 1, "request": "abc123"})

    monkeypatch.setattr("requests.post", _fake_post)

    response = PushoverClient().send(
        token="token",
        user="user",
        message="hello",
        priority=1,
        sound="none",
        title="title",
    )

    assert response["status"] == 1
    assert captured["json"]["priority"] == "1"
    assert captured["json"]["message"] == "hello"
    assert captured["json"]["sound"] == "none"


def test_pushover_client_send_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    def _fake_post(url: str, json: Dict[str, Any], timeout: int) -> _FakeResponse:
        del url, json, timeout
        return _FakeResponse(400, {"status": 0, "errors": ["bad request"]})

    monkeypatch.setattr("requests.post", _fake_post)

    with pytest.raises(ValueError, match="Pushover rejected message"):
        PushoverClient().send(token="token", user="user", message="hello")


def test_alert_process_event_sends(monkeypatch: pytest.MonkeyPatch) -> None:
    sent_payloads: List[Dict[str, Any]] = []

    def _fake_send(self: PushoverClient, **kwargs: Any) -> Dict[str, Any]:
        del self
        sent_payloads.append(kwargs)
        return {"status": 1}

    monkeypatch.setattr(PushoverClient, "send", _fake_send)

    helper = _FakeHelper(
        params={
            "account": "prod",
            "message": "message",
            "title": "title",
            "priority": "priority",
            "sound": "sound",
            "url": "url",
            "url_title": "url_title",
        },
        account={"user": "user_key", "app_token": "app_token"},
        events=[
            {
                "message": "hello from event",
                "title": "my title",
                "priority": "1",
                "sound": "none",
                "url": "https://example.com",
                "url_title": "Example",
            }
        ],
    )

    result = process_event(helper)

    assert result == 0
    assert len(sent_payloads) == 1
    assert sent_payloads[0]["message"] == "hello from event"
    assert sent_payloads[0]["priority"] == 1
    assert sent_payloads[0]["title"] == "my title"


def test_alert_process_event_errors_on_missing_account_data() -> None:
    helper = _FakeHelper(
        params={"account": "prod", "message": "hello"},
        account={"user": "user_only"},
        events=[],
    )
    with pytest.raises(ValueError, match="application token"):
        process_event(helper)


def test_live_pushover_send_if_configured() -> None:
    token = os.getenv("PUSHOVER_TOKEN")
    user = os.getenv("PUSHOVER_USER")
    if token is None or user is None:
        pytest.skip("PUSHOVER_TOKEN or PUSHOVER_USER is not set")

    response = PushoverClient().send(
        token=token,
        user=user,
        message="TA-pushover live test message",
        priority=0,
        sound="none",
    )
    assert str(response.get("status")) == "1"
