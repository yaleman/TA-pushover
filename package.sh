#!/bin/bash

#python3 -m pip install -r requirements.txt

find . -type f -name '*.conf' -exec ksconf check {} \;

tar czf TA-pushover.tgz TA-pushover/

