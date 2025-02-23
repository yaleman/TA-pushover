import logging
import os

import pytest

from package.bin.ta_pushover.modalert_pushover_helper import Pushover


def test_pushover() -> None:
    pushover = Pushover(token=os.getenv("PUSHOVER_TOKEN"))
    assert pushover is not None

    pushover.logger.level = logging.DEBUG

    user_key = os.getenv("PUSHOVER_USER")

    if pushover.token is None:
        pytest.skip("PUSHOVER_TOKEN environment variable is not set")
    if user_key is None:
        pytest.skip("PUSHOVER_USER environment variable is not set")

    pushover.send(token=pushover.token, message="test message", user=user_key)
