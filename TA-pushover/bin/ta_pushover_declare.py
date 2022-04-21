"""
This module is used to filter and reload PATH.
This file is generated by Splunk add-on builder
"""

#pylint: disable=invalid-name

import os
import sys
import re

py_version = "aob_py3"

ta_name = 'TA-pushover'
ta_lib_name = 'ta_pushover'
pattern = re.compile(r"[\\/]etc[\\/]apps[\\/][^\\/]+[\\/]bin[\\/]?$")
new_paths = [path for path in sys.path if not pattern.search(path) or ta_name in path]
new_paths.insert(0, os.path.sep.join([os.path.dirname(__file__), ta_lib_name]))
new_paths.insert(0, os.path.sep.join([os.path.dirname(__file__), ta_lib_name, py_version]))
sys.path = new_paths