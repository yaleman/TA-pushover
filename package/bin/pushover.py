"""Pushover alert action for Splunk"""

# Always put this line at the beginning of this file
try:
    import import_declare_test  # type: ignore[import-not-found]  # noqa: F401
except ImportError:
    pass

import sys
import traceback
from typing import Any

import requests

from splunktaucclib.alert_actions_base import ModularAlertBase  # type: ignore
from ta_pushover import modalert_pushover_helper


class AlertActionWorkerpushover(ModularAlertBase):  # type: ignore
    """pushover worker"""

    def __init__(self, ta_name: str, alert_name: str) -> None:
        """init"""
        self.message_url = "https://api.pushover.net/1/messages.json"
        super().__init__(ta_name, alert_name)

    def build_http_connection(
        self,
        config: dict[str, Any],
        timeout: int = 120,
        disable_ssl_validation: bool = False,
    ) -> requests.Response:
        """does a thing"""
        with requests.Session() as session:
            session.verify = not disable_ssl_validation
            return session.request(timeout=timeout, **config)

    def validate_params(self) -> bool:
        """validates input parameters"""

        if not self.get_param("message"):
            self.log_error(
                "'message' is a mandatory parameter, but its value is missing."
            )
            self.log_error("Got the following configuration: %s" % self.configuration)
            return False

        if not self.get_param("account"):
            self.log_error(
                "'account' is a mandatory parameter, but its value is missing."
            )
            return False
        return True

    def process_event(self, *args: Any, **kwargs: Any) -> int:
        status = 0
        try:
            if not self.validate_params():
                return 3
            status = modalert_pushover_helper.process_event(self, *args, **kwargs)
        except (AttributeError, TypeError) as attribute_error:
            self.log_error(
                f"Error: {attribute_error}.",
            )
            return 4
        except Exception as error:  # pylint: disable=broad-except
            msg = "Unexpected error: {}."
            if str(error):
                self.log_error(msg.format(str(error)))
            else:
                self.log_error(msg.format(traceback.format_exc()))
            return 5
        return status


if __name__ == "__main__":
    sys.exit(AlertActionWorkerpushover("TA-pushover", "pushover").run(sys.argv))
