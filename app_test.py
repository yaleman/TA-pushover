"""test_app.py"""

# pylint: disable=logging-fstring-interpolation,assignment-from-none

import json

# import logging
from pathlib import Path
import sys
from time import sleep
from typing import Any, Optional, TypedDict

import click
from loguru import logger
import requests
from splunklib import client  # type: ignore[import-untyped]
from splunklib.results import JSONResultsReader, Message  # type: ignore[import-untyped]


class ConfigFile(TypedDict):
    """config file"""

    splunk_hostname: str
    splunk_port: int
    splunk_username: str
    splunk_password: str

    pushover_app_name: str
    pushover_user_key: str
    pushover_application_token: str
    pushover_device_name: Optional[str]


def load_config() -> ConfigFile:
    """loads config, funnily enough"""
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
    """does the configure app thing"""
    app_config_data = {
        "output_mode": "json",
        "name": config["pushover_app_name"],
        "user": config["pushover_user_key"],
        "app_token": config["pushover_application_token"],
    }
    if "pushover_device_name" in config and config["pushover_device_name"] is not None:
        app_config_data["device_name"] = config["pushover_device_name"]

    app = splunk.post(
        "/servicesNS/nobody/TA-pushover/ta_pushover_account/additional_parameters",
        body=app_config_data,
    )
    if "status" not in app:
        raise ValueError("No status result after attempting to configure app")
    if app["status"] not in [200, 201]:
        logger.error(
            "Didn't get a 200-ish back from configuring the app (got {})", app["status"]
        )
        logger.error(app["body"])
        return
    if "body" in app:
        print_results(app["body"])

    logger.info("Successfully configured the Pushover app!")


def get_baseurl(config: ConfigFile) -> str:
    """base url"""
    return f"http://{config['splunk_hostname']}:{config['splunk_port']}"


def install_app(
    config: ConfigFile,
    splunk: client.Service,
    filename: str,
) -> None:
    """installs app"""
    print(f"oh no {splunk}")
    url = f"https://{config['splunk_hostname']}:{config['splunk_port']}/en-GB/manager/appinstall/_upload"
    params = {
        "force": 1,
        "appfile": None,  # file bit
    }
    try:
        response = requests.post(
            url,
            params=params,
            verify=False,
            files=[
                (filename, f"./{filename}"),
            ],
            auth=(
                config["splunk_username"],
                config["splunk_password"],
            ),
        )
        print(response)
    except requests.exceptions.ConnectionError as connection_error:
        logger.error("Failed to connect to {}: {}", url, connection_error)
        sys.exit(1)


def print_results(results_object: Any) -> None:
    """printer"""
    results = JSONResultsReader(results_object)
    for result in results:
        if isinstance(result, Message):
            # Diagnostic messages may be returned in the results
            print(f"{result.type}: {result.message}")
        else:
            print(result.get("_raw"))


def send_and_check(splunk: client.Service) -> None:
    """send and check"""
    logger.info("Trying to send an alert")

    search_config = {
        "adhoc_search_level": "verbose",
        "count": 0,
        "output_mode": "json",
    }
    alert_job = splunk.jobs.oneshot(
        """| makeresults
        | eval message="Please delete, sent at "+strftime(_time,"%Y-%m-%d %H:%M:%S %Z"), title="TA-pushover test"
        | eval url_title="hello", url="https://google.com", priority=-1, sound="none"
        | sendalert pushover param.message=message, param.account=test param.url_title=url_title
        """,
        **search_config,
    )
    print_results(alert_job)

    print("Waiting a few seconds...")
    sleep(3)

    logger.info("Pulling internal logs")
    job = splunk.jobs.export(
        """
search index=_internal source=*/splunkd.log OR sourcetype=splunk_search_messages
NOT TERM(TailReader)
NOT "*splunk-dashboard-studio*" TERM(ExecProcessor)  OR TERM(SearchMessages)
NOT TERM(cron) NOT "New scheduled exec process" NOT "*IntrospectionGenerator*"
NOT "interval: run once" NOT "interval: * ms"
| sort _time
""",
        **search_config,
    )

    print_results(job)

    logger.info("Pulling source logs")
    job = splunk.jobs.export(
        """
search index=_internal source="/opt/splunk/var/log/splunk/pushover_modalert.log"
| sort _time
""",
        **search_config,
    )

    print_results(job)


@click.command()
@click.option("--install", is_flag=True, default=False, help="install the app")
@click.option("--send", is_flag=True, default=False, help="Just send the test alert")
def main(
    install: bool = False,
    send: bool = False,
) -> None:
    """main function"""
    configuration = load_config()

    # logger = logging.getLogger("mechanize")
    # logger.addHandler(logging.StreamHandler(sys.stdout))
    # logger.setLevel(logging.DEBUG)

    try:
        splunk = client.connect(
            host=configuration["splunk_hostname"],
            port=configuration["splunk_port"],
            username=configuration["splunk_username"],
            password=configuration["splunk_password"],
            autoLogin=True,
            scheme="https",
            # verify=True,
        )
    except Exception as error:
        logger.error(
            "Failed to connect to {} error: {}", configuration["splunk_hostname"], error
        )
        sys.exit(1)

    print("Login ok")

    if install:
        install_app(
            config=configuration,
            splunk=splunk,
            filename="TA-pushover.spl",
        )
        sys.exit(0)

    if not send:
        try:
            configure_app(configuration, splunk)
        except Exception as error:
            logger.error("Failed to configure app: {}", error)
            sys.exit(1)

    send_and_check(splunk)


if __name__ == "__main__":
    main()
