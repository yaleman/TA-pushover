""" pushover alert action for splunk """

import json
import logging
from ssl import SSLCertVerificationError
import sys
from typing import Any, Dict, List, Optional

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
        sound: Optional[str]=None,
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
        if device is not None:
            message_payload["device"] = device
        if sound is not None:
            message_payload["sound"] = sound
        if timestamp is not None:
            message_payload["timestamp"] = str(timestamp)
        if title is not None:
            message_payload["title"] = title
        if url is not None:
            message_payload["url"] = url
        if url_title is not None:
            message_payload["url_title"] = url_title
        # priority needs to be between -2 and 2
        if priority is not None:
            if (-2 < priority  < 2) is False:
                raise ValueError("Priority needs to be between -2 and 2")
            message_payload["priority"] = str(priority)

        if monospace and html:
            raise ValueError("You need to set either monospace or html, not both")
        if monospace:
            message_payload["monospace"] = "1"
        if html:
            message_payload["html"] = "1"

        self.check_lengths(message_payload)

        print(f"{json.dumps(message_payload, default=str)=}")

        message_send_response = requests.post(
            self.api_url,
            json=message_payload,
            )
        print(f"{message_send_response.content=}")
        responsedata = message_send_response.json()

        if not "status" in responsedata:
            raise ValueError(f"status not returned in response to m essage: {responsedata}")
        if responsedata["status"] != 1 and responsedata["status"] != "1":
            raise ValueError(f"Status code returned from API was: '{responsedata['status']}'")

def pull_config(
    service: client.Service,
    app: str,
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
        print(json_error)
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
        print(json_error)
        print("Failed to pull application_token from password storage, bailing.")
        sys.exit(1)
    print(
        "Failed to pull application_token from password storage, bailing.",
        file=sys.stderr,
    )
    sys.exit(1)

def coalesce(
    key:str,
    coalesce_config: Dict[str,str],
    event_data: Dict[str,str],
    ) -> Optional[str]:
    """ coalesce dicts, order is event -> config -> None """
    if key in event_data:
        return event_data[key]
    if key in coalesce_config:
        return event_data[key]
    return None

# pylint: disable=too-many-arguments
def send_pushover_alert(
    logger_class: logging.Logger,
    user_key: str,
    app_token: str,
    event_config: Dict[str, str],
    events: List[Dict[str, Any]]
    ) -> None:
    """ bleep bloop """
    logger_class.info("Alert action pushover started.")

    for event in events:
        if "message" not in event:
            raise ValueError("You need to have a message field in each event.")

        logger_class.info(f"event={event}")

        if coalesce("html", event, event_config) is not None:
            html = bool(coalesce("html", event, event_config))
        else:
            html= False
        if coalesce("monospace", event, event_config) is not None:
            monospace = bool(coalesce("monospace", event, event_config))
        else:
            monospace = False

        tval = coalesce("timestamp", event, event_config)
        if tval is not None:
            timestamp = int(tval)
        else:
            timestamp = None

        prival = coalesce("priority", event, event_config)
        if prival is None:
            priority = 0
        else:
            priority = int(prival)

        Pushover().send(
            token=app_token,
            user=user_key,
            message=event["message"],
            priority=priority,
            html=html,
            monospace=monospace,
            device=coalesce("device_name", event, event_config),
            sound=coalesce("sound", event, event_config),
            timestamp=timestamp,
            title=coalesce("title", event, event_config),
            url=coalesce("additional_url", event, event_config),
            url_title=coalesce("url_title", event, event_config),
        )

if __name__ == "__main__":
    logger = logging.getLogger("TA-pushover")
    for value in sys.argv:
        print(f"argv: {value}", file=sys.stderr)
    stdin = sys.stdin.read()

    print(f"stdin: {json.dumps(stdin)}", file=sys.stderr)

    config = json.loads(stdin)

    headers = {
        "Authorization" : f"Bearer {config['session_key']}",
    }

    parsed_url = urlparse(config["server_uri"])


    print("dumping global config")

    try:
        splunkclient = client.connect(
            host=parsed_url.hostname,
            port=parsed_url.port,
            scheme=parsed_url.scheme,
            token=config["session_key"]

        )
    except SSLCertVerificationError:
        print("Failed to connect, ssl verification error")
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
    )

    application_token = get_password(splunkclient, "TA-pushover")

    print("#"*50)
    print("app config")
    print(
        json.dumps(
            app_config,
            indent=4,
            default=str,
        )
    )
    print("#"*50)
    print("events")
    print(
        json.dumps(
            config["result"],
            indent=4,
            default=str,
        )
    )

    if isinstance(config["result"], list):
        events_list = config["result"]
    elif isinstance(config["result"], dict):
        events_list = [config["result"],]
    else:
        raise ValueError(f"config['result'] is not either a list or dict, it's a {type(config['result'])}: {config['result']}")

    print("#"*50)
    send_pushover_alert(
        logger,
        app_config["user_key"],
        app_token=application_token,
        event_config=config["configuration"],
        events=events_list,
    )

# stdin: {
# "app":"TA-pushover",
# "owner":"admin",
# "results_file":"/opt/splunk/var/run/splunk/dispatch/scheduler__admin_VEEtcHVzaG92ZXI__spam_at_1649498040_4/sendalert_temp_results.csv.gz",
# "results_link":"http://22072aa942a9:8000/app/TA-pushover/@go?sid=scheduler__admin_VEEtcHVzaG92ZXI__spam_at_1649498040_4",
# "search_uri":"/servicesNS/admin/TA-pushover/saved/searches/spam",
# "server_host": "22072aa942a9",
# "server_uri": "https://127.0.0.1:8089",
# "session_key": "aYAUg6hQDWJyV_UuSlXWEsgwUhFE5UasbI1vzUSiaV8DZAu7aah49lrZog^BxMgcUmIj6fe8p6wPxcA7DfUo6LgZk5g^z^VV2ePsbtBNpKGG7zr4QrdNSIVgxTQ9aOE6rGlv^CpDLMzRDsF1BmU0zNmaQDuF3S9VmZSMnG_Dm_kySo",
# "sid":"scheduler__admin_VEEtcHVzaG92ZXI__spam_at_1649498040_4",
# "search_name":"spam",
# "configuration":{
#   "additional_url":"additional_url",
#   "message":"Message - hello world",
#   "priority":"0",
#   "sound":"_",
#   "title":"title",
#   "url_title":"URL"
# },
# "result":{"_time":"1649498041","message":"hello world"}}
    # sys.exit(AlertActionWorkerpushover("TA-pushover", "pushover").run(sys.argv))
