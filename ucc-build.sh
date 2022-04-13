#!/bin/bash


TA_VERSION="$(grep -E ^version pyproject.toml | awk '{print $NF}' | sed -E 's/"//g')"
APP_DIR="TA-pushover/"

echo "Running ucc-gen for version ${TA_VERSION}"
poetry run ucc-gen \
	--source package \
	--config globalConfig.json \
	--ta-version "${TA_VERSION}"

cd output || exit
echo "Compressing package..."
COPYFILE_DISABLE=1 tar czf ../TA-pushover.tgz "${APP_DIR}"
cd ..
echo "Done."
