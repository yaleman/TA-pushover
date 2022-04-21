#!/bin/bash

if [ "$1" == "--help" ] || [ "$1" == "-h" ]; then
	echo "Usage: ucc-build.sh [--package]"
	echo ""
	echo "Regenerates the UCC app files."
	echo ""
	echo "  Options:"
	echo ""
	echo "  --package  Build the .spl package"
	echo "  --help     Show this help"
	echo ""
	exit
fi

TA_VERSION="$(grep -E ^version pyproject.toml | awk '{print $NF}' | sed -E 's/"//g')"
APP_DIR="TA-pushover/"

echo "Running ucc-gen for version ${TA_VERSION}"
poetry run ucc-gen \
	--source package \
	--config globalConfig.json \
	--ta-version "${TA_VERSION}"


if [ "$1" == "--package" ]; then
	echo "Compressing package..."
	COPYFILE_DISABLE=1 tar czf TA-pushover.spl -C output/ "${APP_DIR}"
	echo "Done."
fi


