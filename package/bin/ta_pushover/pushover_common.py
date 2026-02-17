"""Core Pushover helpers shared by alert actions and search commands."""

from __future__ import annotations

import json
import logging
from typing import Any, Mapping, Optional, Tuple

import requests

PUSHOVER_API_URL = "https://api.pushover.net/1/messages.json"


def _as_optional_string(value: Any) -> Optional[str]:
    if value is None:
        return None
    string_value = str(value)
    if string_value == "":
        return None
    return string_value


def parse_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    lowered_value = str(value).strip().lower()
    return lowered_value in {"1", "t", "true", "y", "yes", "on"}


def parse_priority(value: Any, default: int = 0) -> int:
    if value is None or value == "":
        return default
    parsed_value = int(value)
    if parsed_value < -2 or parsed_value > 2:
        raise ValueError("Priority needs to be between -2 and 2")
    return parsed_value


def event_value_or_literal(
    configured_value: Optional[str], event: Optional[Mapping[str, Any]]
) -> Optional[str]:
    if configured_value is None:
        return None
    if event is not None:
        event_value = event.get(configured_value)
        if event_value is not None and str(event_value) != "":
            return str(event_value)
    if configured_value == "":
        return None
    return configured_value


def extract_account_credentials(account_data: Mapping[str, Any]) -> Tuple[str, str]:
    user = _as_optional_string(account_data.get("user")) or _as_optional_string(
        account_data.get("username")
    )
    app_token = _as_optional_string(account_data.get("app_token")) or _as_optional_string(
        account_data.get("password")
    )
    if user is None:
        raise ValueError("Account is missing a Pushover user key")
    if app_token is None:
        raise ValueError("Account is missing a Pushover application token")
    return user, app_token


class PushoverClient:
    """Lightweight client for Pushover message delivery."""

    def __init__(
        self,
        logger: Optional[logging.Logger] = None,
        api_url: str = PUSHOVER_API_URL,
        timeout_seconds: int = 30,
    ) -> None:
        self.logger = logger or logging.getLogger(__name__)
        self.api_url = api_url
        self.timeout_seconds = timeout_seconds

    @staticmethod
    def check_lengths(message_payload: Mapping[str, Any]) -> None:
        length_checks = {
            "title": 250,
            "message": 1024,
            "url": 512,
            "url_title": 100,
        }
        for key_name, max_length in length_checks.items():
            key_value = message_payload.get(key_name)
            if key_value is not None and len(str(key_value)) > max_length:
                raise ValueError(
                    f"Length of {key_name} is too long {len(str(key_value))} > {max_length}"
                )

    @staticmethod
    def validate_msg_format(message_payload: dict[str, str], html: bool, monospace: bool) -> None:
        if monospace and html:
            raise ValueError("You need to set either monospace or html, not both")
        if monospace:
            message_payload["monospace"] = "1"
        if html:
            message_payload["html"] = "1"

    def send(
        self,
        *,
        token: str,
        user: str,
        message: str,
        priority: int = 0,
        html: bool = False,
        monospace: bool = False,
        device: Optional[str] = None,
        sound: Optional[str] = None,
        timestamp: Optional[int] = None,
        title: Optional[str] = None,
        url: Optional[str] = None,
        url_title: Optional[str] = None,
    ) -> dict[str, Any]:
        message_payload: dict[str, str] = {
            "token": token,
            "user": user,
            "message": message,
            "priority": str(parse_priority(priority)),
        }

        if _as_optional_string(sound) not in {None, "_"}:
            message_payload["sound"] = str(sound)
        if device is not None:
            message_payload["device"] = device
        if timestamp is not None:
            message_payload["timestamp"] = str(timestamp)
        if title is not None:
            message_payload["title"] = title
        if url is not None:
            message_payload["url"] = url
            if url_title is not None:
                message_payload["url_title"] = url_title

        self.validate_msg_format(message_payload, html, monospace)
        self.check_lengths(message_payload)

        self.logger.debug(
            "Sending Pushover payload: %s",
            json.dumps(message_payload, default=str),
        )

        response = requests.post(
            self.api_url,
            json=message_payload,
            timeout=self.timeout_seconds,
        )
        self.logger.info("Pushover HTTP status: %s", response.status_code)
        try:
            response_data: dict[str, Any] = response.json()
        except json.JSONDecodeError as decode_error:
            raise ValueError(
                f"Pushover response was not valid JSON: {response.text}"
            ) from decode_error

        if "status" not in response_data:
            raise ValueError(f"status not returned in response: {response_data}")

        if response_data["status"] not in (1, "1"):
            errors = response_data.get("errors")
            if errors:
                raise ValueError(f"Pushover rejected message: {errors}")
            raise ValueError(
                f"Status code returned from API was: '{response_data['status']}'"
            )

        return response_data
