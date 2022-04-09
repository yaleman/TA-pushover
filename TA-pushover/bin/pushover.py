""" pushover alert action for splunk """

# import ta_pushover_declare

import json
from ssl import SSLCertVerificationError
import sys

from urllib.parse import urlparse
# import requests

from splunklib import client
# import traceback

# from ta_pushover.alert_actions_base import ModularAlertBase
# from ta_pushover import modalert_pushover_helper

# class AlertActionWorkerpushover(ModularAlertBase):
#     """ the alert action """

#     def validate_params(self):
#         """ validates parameters """
#         if not self.get_global_setting("user_key"):
#             self.log_error('user_key is a mandatory setup parameter, but its value is None.')
#             return False

#         if not self.get_param("message"):
#             self.log_error('message is a mandatory parameter, but its value is None.')
#             return False
#         return True

#     def process_event(self, *args, **kwargs):
#         """ actually does the thing """
#         status = 0
#         try:
#             if not self.validate_params():
#                 return 3
#             status = modalert_pushover_helper.process_event(self, *args, **kwargs)
#         except (AttributeError, TypeError) as attribute_error:
#             self.log_error(f"Error: {str(attribute_error)}. Please double check spelling and also verify that a compatible version of Splunk_SA_CIM is installed.")
#             return 4
#         except Exception as error: #pylint: disable=broad-except
#             msg = "Unexpected error: {}."
#             if error:
#                 self.log_error(msg.format(str(error)))
#             else:
#                 self.log_error(msg.format(traceback.format_exc()))
#             return 5
#         return status

if __name__ == "__main__":
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
    # client.connect(
    #     host=parsed_url.hostname,
    #     port=parsed_url.port,
    #     scheme=parsed_url.scheme,
    #     token=config["session_key"]
    # )

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
