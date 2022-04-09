"""test_app.py """

# pylint: disable=logging-fstring-interpolation,assignment-from-none

import json
import logging
from pathlib import Path
import sys
from typing import TypedDict

from splunklib import client
from splunklib.results import JSONResultsReader, Message

class ConfigFile(TypedDict):
    """ config file """
    splunk_hostname: str
    splunk_port: int
    splunk_username: str
    splunk_password: str

    pushover_user_key: str
    pushover_application_token: str
    pushover_device_name: str

def load_config() -> ConfigFile:
    """ loads config, funnily enough """
    filepath = Path("~/.config/ta-pushover.json").expanduser().resolve()

    if not filepath.exists():
        raise FileNotFoundError(filepath)

    with filepath.open(encoding="utf-8") as config_filehandle:
        config_file: ConfigFile = json.load(config_filehandle)
    return config_file

# log in

def configure_app(
    config: ConfigFile,
    splunk: client,
    logger: logging.Logger,
    ) -> None:
    """ does the configure app thing """
    app_config_data = {
            'output_mode': 'json',
            'user_key': config['pushover_user_key'],
            'application_token': config['pushover_application_token'],
            'device_name': config['pushover_device_name'],
        }
    app = splunk.post(
        "/servicesNS/nobody/TA-pushover/TA_pushover_settings/additional_parameters",
        body=app_config_data,
        )
    if "status" not in app:
        raise ValueError("No status result after attempting to configure app")
    if app["status"] != 200:
        logger.error("Didn't get a 200 back from configuring the app")
        return
    if "body" in app:
        print_results(app["body"])

    logger.info("Successfully configured the Pushover app!")



def get_baseurl(config: ConfigFile) -> str:
    """ bas url """
    return f"http://{config['splunk_hostname']}:{config['splunk_port']}"

def print_results(results_object) -> None:
    """ printer """
    results = JSONResultsReader(results_object)
    for result in results:
        if isinstance(result, Message):
            # Diagnostic messages may be returned in the results
            print(f"{result.type}: {result.message}")
        else:
            print(result.get("_raw"))

def main():
    """ main function """

    configuration = load_config()

    logger = logging.getLogger("mechanize")
    logger.addHandler(logging.StreamHandler(sys.stdout))
    logger.setLevel(logging.DEBUG)



    splunk = client.connect(
        host=configuration["splunk_hostname"],
        port=configuration["splunk_port"],
        username=configuration["splunk_username"],
        password=configuration["splunk_password"],
        autoLogin=True,
        scheme="https",
        # verify=True,
    )
    print("Login ok")

    configure_app(configuration, splunk, logger)

    logger.info("Trying to send an alert")

    search_config =  {
        "adhoc_search_level": "verbose",
        "count": 0,
        "output_mode" : 'json',
    }
    alert_job = splunk.jobs.oneshot(
        "| makeresults 1 | sendalert pushover",
        **search_config
    )
    print_results(alert_job)

    job = splunk.jobs.export(
        """
search index=_internal source=*/splunkd.log OR sourcetype=splunk_search_messages
NOT TERM(TailReader)
NOT "*splunk-dashboard-studio*" TERM(ExecProcessor)  OR TERM(SearchMessages)
NOT TERM(cron) NOT "New scheduled exec process" NOT "*IntrospectionGenerator*"
| sort _time

""",
        **search_config
    )

    print_results(job)

if __name__ == "__main__":
    main()
