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

echo "Outputting requirements.txt"
mkdir -p package/lib/
uv sync --quiet --no-dev && \
	uv pip  freeze | awk -F'=' '{ print $1}' > package/lib/requirements.txt && \
	uv sync --quiet



echo "Running ucc-gen for version ${TA_VERSION}"
uv run ucc-gen \
	--source package \
	--config globalConfig.json \
	--ta-version "${TA_VERSION}"

uv run find "output/TA-pushover/" -type f -name '*.conf' -exec ksconf check {} \;

echo "Cleaning up"
# rm requirements.txt

if [ "$1" == "--package" ]; then
	echo "Compressing package..."
	OUTPUT_FILE="TA-pushover.spl"
	COPYFILE_DISABLE=1 tar czf "${OUTPUT_FILE}" -C output/ "TA-pushover/"
	echo "Done. Created ${OUTPUT_FILE}"
fi

