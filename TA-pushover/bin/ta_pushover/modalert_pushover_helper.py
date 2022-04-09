""" modalert """

import json
import sys
import logging

import requests

API_URL = "https://api.pushover.net/1/messages.json"


def process_event(helper, *args, **kwargs):
    """
    [sample_code_macro:start]

    # The following example gets the setup parameters and prints them to the log
    user_key = helper.get_global_setting("user_key")
    helper.log_info("user_key={}".format(user_key))
    application_token = helper.get_global_setting("application_token")
    helper.log_info("application_token={}".format(application_token))
    device_name = helper.get_global_setting("device_name")
    helper.log_info("device_name={}".format(device_name))

    # The following example gets the alert action parameters and prints them to the log
    message = helper.get_param("message")
    helper.log_info("message={}".format(message))

    title = helper.get_param("title")
    helper.log_info("title={}".format(title))

    additional_url = helper.get_param("additional_url")
    helper.log_info("additional_url={}".format(additional_url))

    url_title = helper.get_param("url_title")
    helper.log_info("url_title={}".format(url_title))

    priority = helper.get_param("priority")
    helper.log_info("priority={}".format(priority))

    sound = helper.get_param("sound")
    helper.log_info("sound={}".format(sound))


    # The following example adds two sample events ("hello", "world")
    # and writes them to Splunk
    # NOTE: Call helper.writeevents() only once after all events
    # have been added
    helper.addevent("hello", sourcetype="sample_sourcetype")
    helper.addevent("world", sourcetype="sample_sourcetype")
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

    helper.log_info("Alert action pushover started.")

    user_key = helper.get_global_setting("user_key")
    application_token = helper.get_global_setting("application_token")

    optional_values = {
        'title' : helper.get_param("title"),
        'device' : helper.get_global_setting("device"),
        'url' : helper.get_param("additional_url"),
        'url_title' : helper.get_param("url_title"),
        'priority' : helper.get_param("priority"),
        'sound' : helper.get_param("sound"),
    }

    for event in helper.get_events():
        helper.log_info(f"event={event}")
        payload = {
            'user' : user_key,
            'message' : helper.get_param("message"),
        }
        for key in optional_values:
            if optional_values.get(key, ""):
                value = optional_values.get(key, "").strip()
                helper.log_info(f"Adding key {key} value {value}")
                payload[key] = value

        try:
            helper.log_info("Sending alert, payload:")
            helper.log_info(json.dumps(payload))
            helper.log_info("Adding token to payload")
            payload['token'] = application_token
            response = requests.post(url=API_URL,json=payload)
            response.raise_for_status()
        except Exception as exception_data: # pylint: disable=broad-except
            logging.error(exception_data)
            sys.exit(1)
        helper.log_debug(response.text)

    return 0
