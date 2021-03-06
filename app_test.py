"""test_app.py """

# pylint: disable=logging-fstring-interpolation,assignment-from-none

import json
# import logging
from pathlib import Path
import sys
from time import sleep
from typing import Optional, TypedDict

import click
from loguru import logger
import requests
from splunklib import client
# from splunklib.binding import ResponseReader
from splunklib.results import JSONResultsReader, Message

class ConfigFile(TypedDict):
    """ config file """
    splunk_hostname: str
    splunk_port: int
    splunk_username: str
    splunk_password: str

    pushover_user_key: str
    pushover_application_token: str
    pushover_device_name: Optional[str]

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
    ) -> None:
    """ does the configure app thing """
    app_config_data = {
            'output_mode': 'json',
            'user_key': config['pushover_user_key'],
            'application_token': config['pushover_application_token'],
        }
    if "pushover_device_name" in config and config["pushover_device_name"] is not None:
        app_config_data["device_name"] = config["pushover_device_name"]

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
    """ base url """
    return f"http://{config['splunk_hostname']}:{config['splunk_port']}"


def install_app(
    config: ConfigFile,
    splunk: client.Service,
    filename: str,
    ) -> None:
    """ installs app """
    print(f"oh no {splunk}")
    url= f"http://{config['splunk_hostname']}:{config['splunk_port']}/en-GB/manager/appinstall/_upload"
    params = {
        "force" : 1,
        "appfile" : None # file bit
    }
    try:
        response = requests.post(
            url,
            params=params,
            files=[ (filename, f"./{filename}"), ],
            auth=(config["splunk_username"], config["splunk_password"],)
        )
        print(response)
    except requests.exceptions.ConnectionError as connection_error:
        logger.error(connection_error)
        sys.exit(1)

def print_results(results_object) -> None:
    """ printer """
    results = JSONResultsReader(results_object)
    for result in results:
        if isinstance(result, Message):
            # Diagnostic messages may be returned in the results
            print(f"{result.type}: {result.message}")
        else:
            print(result.get("_raw"))

@click.command()
@click.option("--install", is_flag=True, default=False, help="install the app")
def main(
    install: bool=False,
):
    """ main function """
    configuration = load_config()

    # logger = logging.getLogger("mechanize")
    # logger.addHandler(logging.StreamHandler(sys.stdout))
    # logger.setLevel(logging.DEBUG)


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

    if install:
        install_app(
            config=configuration,
            splunk=splunk,
            filename="TA-pushover.spl",
        )
        sys.exit(0)

    configure_app(configuration, splunk)

    logger.info("Trying to send an alert")

    search_config =  {
        "adhoc_search_level": "verbose",
        "count": 0,
        "output_mode" : 'json',
    }
    alert_job = splunk.jobs.oneshot(
        '''| makeresults
        | eval message="Please delete, sent at "+strftime(_time,"%Y-%m-%d %H:%M:%S %Z"), title="TA-pushover test"
        | eval url_title="hello", url="https://google.com", priority=-1, sound="none"
        | sendalert pushover
        ''',
        **search_config
    )
    print_results(alert_job)

    print("Waiting a few seconds...")
    sleep(3)

    print("Pulling internal logs")
    job = splunk.jobs.export(
        '''
search index=_internal source=*/splunkd.log OR sourcetype=splunk_search_messages
NOT TERM(TailReader)
NOT "*splunk-dashboard-studio*" TERM(ExecProcessor)  OR TERM(SearchMessages)
NOT TERM(cron) NOT "New scheduled exec process" NOT "*IntrospectionGenerator*"
NOT "interval: run once" NOT "interval: * ms"
| sort _time
''',
        **search_config
    )

    print_results(job)

if __name__ == "__main__":
    main()
