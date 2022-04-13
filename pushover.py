""" pushover alert action for splunk """

#pylint: disable=logging-fstring-interpolation

import json
import logging
from ssl import SSLCertVerificationError
import sys
from typing import Any, Dict, Optional

from urllib.parse import urlparse
import requests

from splunklib import client # type: ignore
from splunklib.binding import ResponseReader # type: ignore


class Pushover():
    """ pushover handler """
    api_url = "https://api.pushover.net/1/messages.json"

    # TODO: handle http 429 - rate limiting
    # TODO: maybe print headers?
    # X-Limit-App-Limit: 10000
    # X-Limit-App-Remaining: 7496
    # X-Limit-App-Reset: 1393653600

    def __init__(self, token: Optional[str]=None) -> None:
        """ setter """
        self.token = token

    def get_rate_limit(self, token: Optional[str]=None) -> Dict[str,str]:
        """ gets the rate limit endpoint """
        if token is not None:
            check_token = token
        elif self.token is not None:
            check_token = self.token
        else:
            raise ValueError("Please set a token")
        url = f"https://api.pushover.net/1/apps/limits.json?token={check_token}"
        return requests.get(url).json()

    @classmethod
    def check_lengths(cls, message_payload: Dict[str,str]) -> None:
        """ checks for lengths of things """
        length_checks = {
            "title" : 250,
            "message" : 1024,
            "url" : 512,
            "url_title" : 100,
        }
        for key_value, max_length in length_checks.items():
            if key_value in message_payload and len(str(message_payload[key_value])) > max_length:
                raise ValueError(f"Length of {key_value} is too long {len(str(message_payload[key_value]))} > {max_length}")

    @classmethod
    def validate_msg_format(
        cls,
        content: Dict[str, str],
        html_value: bool,
        monospace_value: bool,
        ) -> None:
        """ validates the html and monospace fields """
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
        priority_value: Optional[int]=None,
        ) -> None:
        """ validates the priority field """
        if priority_value is not None:
            # priority needs to be between -2 and 2
            if (-2 <= priority_value  <= 2) is False:
                raise ValueError("Priority needs to be between -2 and 2")
            content["priority"] = str(priority_value)

    #pylint: disable=too-many-arguments,too-many-branches,too-many-locals
    def send(
        self,
        token: str,
        user: str,
        message: str,
        # attachment: Optional[str]=None, # yeah nah
        priority: int=0,
        html: bool=False,
        monospace: bool=False,
        device: Optional[str]=None,
        sound: str="none",
        timestamp: Optional[int]=None,
        title: Optional[str]=None,
        url: Optional[str]=None,
        url_title: Optional[str]=None,
    ) -> None:
        """ send a pushover message

        API docs here: https://pushover.net/api#messages"""

        message_payload = {
            "token" : token,
            "user" : user,
            "message" :  message,
        }
        if sound != "_" and sound is not None:
            message_payload["sound"]=sound

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

        logger.debug(f"event message payload: {json.dumps(message_payload, default=str)}")

        message_send_response = requests.post(
            self.api_url,
            json=message_payload,
            )
        logger.info("message send response content: %s", message_send_response.content)

        responsedata = message_send_response.json()
        if not "status" in responsedata:
            raise ValueError(f"status not returned in response to m essage: {responsedata}")
        if responsedata["status"] != 1 and responsedata["status"] != "1":
            raise ValueError(f"Status code returned from API was: '{responsedata['status']}'")

def pull_config(
    service: client.Service,
    app: str,
    log_class: logging.Logger,
    ) -> Dict[str, str]:
    """ pulls the config from the app endpoint """
    response = service.request(
        "properties/ta_pushover_settings/additional_parameters",
        app=app,
        body={
            "output_mode" : "json",
        }
    )
    responsebody: ResponseReader = response["body"]
    try:
        response_dict: Dict[str, Any] = json.loads(responsebody.read())
        if "entry" in response_dict:
            configdata: Dict[str,Any] = {}
            for element in response_dict["entry"]:
                configdata[element["name"]] = element["content"]
    except json.JSONDecodeError as json_error:
        log_class.error("error when JSON decoding configuration pulled from Splunk REST API: %s", json_error)
        sys.exit(1)
    return configdata

def get_password(
    service: client.Service,
    app: str,
    ) -> str:
    """ pulls the passwords from the app endpoint """
    response = service.request(
        "storage/passwords",
        app=app,
        body={
            "output_mode" : "json",
        }
    )
    responsebody: ResponseReader = response["body"]
    try:
        response_dict: Dict[str, Any] = json.loads(responsebody.read())
        if "entry" in response_dict:
            for entry in response_dict["entry"]:
                if "application_token" in entry.get("content",{}).get("clear_password",{}):
                    password_data = json.loads(entry["content"]["clear_password"])
                    return password_data["application_token"]
    except json.JSONDecodeError as json_error:
        logger.error("JSONDecodeError handling REST call to storage/passwords: %s",
            json_error,
        )
    logger.error(
        "Failed to pull application_token from password storage, bailing.",
    )
    return sys.exit(1)

def coalesce(
    key:str,
    event_data: Dict[str,str],
    app_data: Dict[str,str],
    default_value: Optional[str] = None
    ) -> Optional[str]:
    """ coalesce dicts, order is event -> config -> None """
    coalescelogger = logging.getLogger("coalesce")
    coalescelogger.setLevel(logging.DEBUG)
    if event_data.get(key) is not None:
        coalescelogger.debug("eventdata - %s = '%s'", key, event_data.get(key))
        return event_data[key]
    if app_data.get(key) is not None:
        coalescelogger.debug("configdata - %s = '%s'", key, app_data.get(key))
        return app_data[key]
    return default_value

# pylint: disable=too-many-arguments
def send_pushover_alert(
    logger_class: logging.Logger,
    user_key: str,
    app_token: str,
    event_config: Dict[str, str],
    event: Dict[str, Any]
    ) -> None:
    """ bleep bloop """
    logger_class.info("Alert action pushover started.")

    if "message" not in event:
        raise ValueError("You need to have a message field in each event.")

    logger_class.error(f"event={event}")

    html= False
    if coalesce("html", event, event_config) is not None:
        html = bool(coalesce("html", event, event_config))
    monospace = False
    if coalesce("monospace", event, event_config) is not None:
        monospace = bool(coalesce("monospace", event, event_config))

    tval = coalesce("timestamp", event, event_config)
    timestamp = int(tval) if tval is not None else None

    prival = coalesce("priority", event, event_config)
    if prival is None or prival == "":
        logger.debug("setting priority to 0")
        priority = 0
    else:
        logger.debug(f"Setting priority to int({prival})")
        priority = int(prival)

    Pushover().send(
        token=app_token,
        user=user_key,
        message=event["message"],
        priority=priority,
        html=html,
        monospace=monospace,
        device=coalesce("device_name", event, event_config),
        sound=str(coalesce("sound", event, event_config, "none")),
        timestamp=timestamp,
        title=coalesce("title", event, event_config),
        url=coalesce("url", event, event_config),
        url_title=coalesce("url_title", event, event_config),
    )

if __name__ == "__main__":
    # setup logging
    logger = logging.getLogger(
        "TA-pushover"
        )
    logger.setLevel(logging.DEBUG)
    for value in sys.argv:
        logger.debug(f"argv: {value}")

    # config data and results
    stdin = sys.stdin.read()
    logger.debug(f"stdin: {json.dumps(stdin)}")

    config = json.loads(stdin)

    # connect to the REST API to pull app config data
    parsed_url = urlparse(config["server_uri"])
    try:
        splunkclient = client.connect(
            host=parsed_url.hostname,
            port=parsed_url.port,
            scheme=parsed_url.scheme,
            token=config["session_key"]

        )
    # if it fails SSL verification, fall back
    except SSLCertVerificationError:
        logger.debug("Failed to connect to REST API (%s), ssl verification error", config["server_uri"])
        splunkclient = client.connect(
            host=parsed_url.hostname,
            port=parsed_url.port,
            scheme=parsed_url.scheme,
            token=config["session_key"],
            verify=False,
        )

    app_config = pull_config(
        splunkclient,
        config["app"],
        logger,
    )
    application_token = get_password(splunkclient, "TA-pushover")

    logger.debug("#"*50)
    logger.debug("app config")
    logger.debug(
        json.dumps(
            app_config,
            indent=4,
            default=str,
        )
    )
    logger.debug("#"*50)
    logger.debug("events")
    logger.debug(
        json.dumps(
            config["result"],
            indent=4,
            default=str,
        )
    )

    send_pushover_alert(
        logger,
        app_config["user_key"],
        app_token=application_token,
        event_config=config["configuration"],
        event=config["result"],
    )
