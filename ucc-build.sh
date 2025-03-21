#!/bin/bash

set -e

if [ "$1" == "--help" ] || [ "$1" == "-h" ]; then
	echo "Usage: ucc-build.sh [--package]"
	echo ""
	echo "Regenerates the UCC app files."
	echo ""
	echo "  Options:"
	echo ""
	echo "  --help     Show this help"
	echo ""
	exit
fi

rm -rf ./output/ && mkdir -p output

TA_VERSION="$(grep -E ^version pyproject.toml | awk '{print $NF}' | sed -E 's/"//g')"

# TODO: fix this for when ucc-gen doesn't use python -m pip
# echo "Outputting requirements.txt"
# mkdir -p package/lib/
# uv sync --quiet --no-dev && \
# 	uv run pip freeze | awk -F'=' '{ print $1}' > package/lib/requirements.txt && \
# 	uv sync --quiet

echo "Running ucc-gen build for version ${TA_VERSION}"
uv run ucc-gen build \
	--source package \
	--config globalConfig.json \
	--ta-version "${TA_VERSION}"

uv run find "output/TA-pushover/" -type f -name '*.conf' -exec ksconf check {} \;

echo "Cleaning up"
# rm requirements.txt

echo "Compressing package..."
OUTPUT_FILE="TA-pushover.spl"
COPYFILE_DISABLE=1 tar czf "${OUTPUT_FILE}" -C output/ "TA-pushover/"
echo "Done. Created ${OUTPUT_FILE}"

