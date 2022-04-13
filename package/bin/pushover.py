""" Pushover alert action for Splunk"""

# Always put this line at the beginning of this file
# import import_declare_test

# import os
import sys
import traceback

import requests

from splunktaucclib.alert_actions_base import ModularAlertBase
from ta_pushover import modalert_pushover_helper

class AlertActionWorkerpushover(ModularAlertBase):
    """ pushover worker """
    def __init__(self, ta_name, alert_name):
        """ init """
        self.message_url = "https://api.pushover.net/1/messages.json"
        super().__init__(ta_name, alert_name)

    def build_http_connection(
        self,
        config,
        timeout=120,
        disable_ssl_validation=False,
        ):
        """ does a thing """
        with requests.Session() as session:
            session.verify = (not disable_ssl_validation)
            return session.request(timeout=timeout, **config)

    def validate_params(self):
        """validates input parameters"""

        if not self.get_param("message"):
            self.log_error('message is a mandatory parameter, but its value is None.')
            return False

        # if not self.get_param("title"):
            # self.log_error('action is a mandatory parameter, but its value is None.')
            # return False

        if not self.get_param("account"):
            self.log_error('account is a mandatory parameter, but its value is None.')
            return False
        return True

    def process_event(self, *args, **kwargs):
        status = 0
        try:
            if not self.validate_params():
                return 3
            status = modalert_pushover_helper.process_event(self, *args, **kwargs)
        except (AttributeError, TypeError) as attribute_error:
            self.log_error(
                f"Error: {attribute_error}. Please double check spelling and also verify that a compatible version of Splunk_SA_CIM is installed.",
                )

            return 4
        except Exception as error: # pylint: disable=broad-except
            msg = "Unexpected error: {}."
            if str(error):
                self.log_error(msg.format(str(error)))
            else:
                self.log_error(msg.format(traceback.format_exc()))
            return 5
        return status

if __name__ == "__main__":
    sys.exit(AlertActionWorkerpushover("TA-pushover", "pushover").run(sys.argv))
