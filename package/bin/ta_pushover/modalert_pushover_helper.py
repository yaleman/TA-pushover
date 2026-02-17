"""Helpers for the TA-pushover modular alert action."""

from __future__ import annotations

import logging
from typing import Any, Dict, Iterator, Mapping, Optional

from .pushover_common import (
    PushoverClient,
    event_value_or_literal,
    extract_account_credentials,
    parse_bool,
    parse_priority,
)

Pushover = PushoverClient


def _iter_events(helper: Any) -> Iterator[Dict[str, str]]:
    events = helper.get_events()
    if events is None:
        yield {}
        return

    saw_event = False
    for event in events:
        saw_event = True
        yield event

    if not saw_event:
        yield {}


def _resolve_account(helper: Any, account_name: str) -> tuple[str, str]:
    account_data = helper.get_user_credential_by_account_id(account_name)
    if account_data is None:
        raise ValueError(f"Account '{account_name}' was not found")
    if not isinstance(account_data, Mapping):
        raise ValueError(f"Account '{account_name}' returned an invalid record")
    return extract_account_credentials(account_data)


def _to_optional_int(value: Optional[str]) -> Optional[int]:
    if value is None or value == "":
        return None
    return int(value)


def process_event(helper: Any, *args: Any, **kwargs: Any) -> int:
    del args, kwargs  # Unused by this implementation.

    helper.log_info("Alert action pushover process_event started.")

    account = helper.get_param("account")
    if not account:
        raise ValueError("'account' is required")

    message_template = helper.get_param("message")
    if not message_template:
        raise ValueError("'message' is required")

    user_key, app_token = _resolve_account(helper, account)
    logger = getattr(helper, "_logger", logging.getLogger(__name__))
    client = PushoverClient(logger=logger)

    title_template = helper.get_param("title")
    url_template = helper.get_param("url") or helper.get_param("additional_url")
    url_title_template = helper.get_param("url_title")
    priority_template = helper.get_param("priority")
    sound_template = helper.get_param("sound")
    html_template = helper.get_param("html")
    monospace_template = helper.get_param("monospace")
    timestamp_template = helper.get_param("timestamp")
    device_template = helper.get_param("device")

    sent_count = 0
    for event in _iter_events(helper):
        message = event_value_or_literal(message_template, event)
        if message is None:
            raise ValueError("Message resolved to an empty value")

        priority = parse_priority(event_value_or_literal(priority_template, event), 0)
        timestamp = _to_optional_int(event_value_or_literal(timestamp_template, event))

        client.send(
            token=app_token,
            user=user_key,
            message=message,
            priority=priority,
            html=parse_bool(event_value_or_literal(html_template, event)),
            monospace=parse_bool(event_value_or_literal(monospace_template, event)),
            device=event_value_or_literal(device_template, event),
            sound=event_value_or_literal(sound_template, event),
            timestamp=timestamp,
            title=event_value_or_literal(title_template, event),
            url=event_value_or_literal(url_template, event),
            url_title=event_value_or_literal(url_title_template, event),
        )
        sent_count += 1

    helper.log_info(
        f"Sent {sent_count} Pushover message(s) using account '{account}'."
    )
    return 0
