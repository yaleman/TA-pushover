"""helper"""

import json
import logging
from typing import Any, Dict, Optional

import requests


class Pushover:
    """pushover handler"""

    api_url = "https://api.pushover.net/1/messages.json"

    # TODO: handle http 429 - rate limiting
    # TODO: maybe print headers?
    # X-Limit-App-Limit: 10000
    # X-Limit-App-Remaining: 7496
    # X-Limit-App-Reset: 1393653600

    def __init__(
        self,
        token: Optional[str] = None,
        logger: logging.Logger = logging.getLogger(),
    ) -> None:
        """setter"""
        self.token = token
        self.logger = logger

    def get_rate_limit(self, token: Optional[str] = None) -> Dict[str, str]:
        """gets the rate limit endpoint"""
        if token is not None:
            check_token = token
        elif self.token is not None:
            check_token = self.token
        else:
            raise ValueError("Please set a token")
        url = f"https://api.pushover.net/1/apps/limits.json?token={check_token}"
        res: Dict[str, str] = requests.get(url).json()
        return res

    @classmethod
    def check_lengths(cls, message_payload: Dict[str, str]) -> None:
        """checks for lengths of things"""
        length_checks = {
            "title": 250,
            "message": 1024,
            "url": 512,
            "url_title": 100,
        }
        for key_value, max_length in length_checks.items():
            if (
                key_value in message_payload
                and len(str(message_payload[key_value])) > max_length
            ):
                raise ValueError(
                    f"Length of {key_value} is too long {len(str(message_payload[key_value]))} > {max_length}"
                )

    @classmethod
    def validate_msg_format(
        cls,
        content: Dict[str, str],
        html_value: bool,
        monospace_value: bool,
    ) -> None:
        """validates the html and monospace fields"""
        if monospace_value and html_value:
            raise ValueError("You need to set either monospace or html, not both")
        if monospace_value:
            content["monospace"] = "1"
        if html_value:
            content["html"] = "1"

    @classmethod
    def validate_priority(
        cls,
        content: Dict[str, str],
        priority_value: Optional[int] = None,
    ) -> None:
        """validates the priority field"""
        if priority_value is not None:
            # priority needs to be between -2 and 2
            if (-2 <= priority_value <= 2) is False:
                raise ValueError("Priority needs to be between -2 and 2")
            content["priority"] = str(priority_value)

    # pylint: disable=too-many-arguments,too-many-branches,too-many-locals
    def send(
        self,
        token: str,
        user: str,
        message: str,
        # attachment: Optional[str]=None, # yeah nah
        priority: int = 0,
        html: bool = False,
        monospace: bool = False,
        device: Optional[str] = None,
        sound: str = "none",
        timestamp: Optional[int] = None,
        title: Optional[str] = None,
        url: Optional[str] = None,
        url_title: Optional[str] = None,
    ) -> None:
        """send a pushover message

        API docs here: https://pushover.net/api#messages"""

        message_payload = {
            "token": token,
            "user": user,
            "message": message,
        }
        if sound != "_" and sound is not None:
            message_payload["sound"] = sound

        if device is not None:
            message_payload["device"] = device
        if timestamp is not None:
            message_payload["timestamp"] = str(timestamp)
        if title is not None:
            message_payload["title"] = title

        if url is not None:
            message_payload["url"] = url
            # only set the url title if there's a URL
            if url_title is not None:
                message_payload["url_title"] = url_title

        self.validate_priority(message_payload, priority)
        self.validate_msg_format(message_payload, html, monospace)
        self.check_lengths(message_payload)

        self.logger.debug(
            f"event message payload: {json.dumps(message_payload, default=str)}"
        )

        message_send_response = requests.post(
            self.api_url,
            json=message_payload,
        )
        self.logger.info(
            "message send response content: %s", message_send_response.content
        )

        responsedata = message_send_response.json()
        if "status" not in responsedata:
            raise ValueError(
                f"status not returned in response to m essage: {responsedata}"
            )
        if responsedata["status"] != 1 and responsedata["status"] != "1":
            raise ValueError(
                f"Status code returned from API was: '{responsedata['status']}'"
            )


def process_event(helper: Any, *args: Any, **kwargs: Any) -> int:
    """
    # IMPORTANT
    # Do not remove the anchor macro:start and macro:end lines.
    # These lines are used to generate sample code. If they are
    # removed, the sample code will not be updated when configurations
    # are updated.

    [sample_code_macro:start]

    # The following example gets the alert action parameters and prints them to the log
    name = helper.get_param("name")
    helper.log_info("name={}".format(name))

    all_incidents = helper.get_param("all_incidents")
    helper.log_info("all_incidents={}".format(all_incidents))

    table_list = helper.get_param("table_list")
    helper.log_info("table_list={}".format(table_list))

    action = helper.get_param("action")
    helper.log_info("action={}".format(action))

    account = helper.get_param("account")
    helper.log_info("account={}".format(account))


    # The following example adds two sample events ("hello", "world")
    # and writes them to Splunk
    # NOTE: Call helper.writeevents() only once after all events
    # have been added
    helper.addevent("hello", sourcetype="test:incident")
    helper.addevent("world", sourcetype="test:incident")
    helper.writeevents(index="summary", host="localhost", source="localhost")

    # The following example gets the events that trigger the alert
    events = helper.get_events()
    for event in events:
        helper.log_info("event={}".format(event))

    # helper.settings is a dict that includes environment configuration
    # Example usage: helper.settings["server_uri"]
    helper.log_info("server_uri={}".format(helper.settings["server_uri"]))
    [sample_code_macro:end]
    """

    helper.log_info("Alert action pushover process_event started.")

    account = helper.get_param("account")
    message = helper.get_param("message")

    helper.log_info(f"account={account}")
    helper.log_info(f"message={message}")

    events = helper.get_events()
    for event in events:
        helper.log_info(f"got {event=}")

    return 0
