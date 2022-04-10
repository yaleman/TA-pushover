#!/bin/bash

#python3 -m pip install -r requirements.txt

APP_DIR="TA-pushover"

poetry run find "${APP_DIR}/" -type f -name '*.conf' -exec ksconf check {} \;

echo "Creating ${APP_DIR}.tgz"

COPYFILE_DISABLE=1 tar czf "${APP_DIR}.tgz" "${APP_DIR}/"

echo "Done!"