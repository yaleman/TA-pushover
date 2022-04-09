""" pushover alert action for splunk """

# import ta_pushover_declare

import sys
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
        print(value)

    # sys.exit(AlertActionWorkerpushover("TA-pushover", "pushover").run(sys.argv))
