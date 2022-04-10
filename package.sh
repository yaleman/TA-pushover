#!/bin/bash

#python3 -m pip install -r requirements.txt

APP_DIR="TA-pushover"

poetry run find "${APP_DIR}/" -type f -name '*.conf' -exec ksconf check {} \;

echo "Creating ${APP_DIR}.tgz"

if [ -d "${APP_DIR}/bin/ta_pushover/aob_py3/lib2to3/tests/" ]; then
    echo "Removing ${APP_DIR}/bin/ta_pushover/aob_py3/lib2to3/tests/"
    rm -rf "${APP_DIR}/bin/ta_pushover/aob_py3/lib2to3/tests/"
fi
find . -type d -name __pycache__ -delete
COPYFILE_DISABLE=1 tar czf "${APP_DIR}.tgz" --exclude '*/__pycache__/*' "${APP_DIR}/"

echo "Done!"