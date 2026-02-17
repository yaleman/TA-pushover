#!/usr/bin/env bash

set -euo pipefail

if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
    echo "Usage: ucc-build.sh"
    echo ""
    echo "Builds the UCC add-on from a temporary source copy and creates TA-pushover.spl."
    exit 0
fi

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${ROOT_DIR}"

: "${UV_CACHE_DIR:=/tmp/uv-cache}"
export UV_CACHE_DIR

TA_VERSION="$(awk -F'"' '/^version = / { print $2; exit }' pyproject.toml)"
if [[ -z "${TA_VERSION}" ]]; then
    echo "Failed to determine version from pyproject.toml"
    exit 1
fi

WORK_DIR="$(mktemp -d /tmp/ta-pushover-build.XXXXXX)"
SOURCE_DIR="${WORK_DIR}/source"
BUILD_OUTPUT_DIR="${WORK_DIR}/output"
trap 'rm -rf "${WORK_DIR}"' EXIT

mkdir -p "${SOURCE_DIR}"
cp -R package "${SOURCE_DIR}/package"
cp globalConfig.json "${SOURCE_DIR}/globalConfig.json"

tmp_file="$(mktemp)"
jq --arg version "${TA_VERSION}" '.meta.version = $version' \
    "${SOURCE_DIR}/globalConfig.json" > "${tmp_file}"
mv "${tmp_file}" "${SOURCE_DIR}/globalConfig.json"

tmp_file="$(mktemp)"
jq --arg version "${TA_VERSION}" '.info.id.version = $version' \
    "${SOURCE_DIR}/package/app.manifest" > "${tmp_file}"
mv "${tmp_file}" "${SOURCE_DIR}/package/app.manifest"

if [[ -f "${SOURCE_DIR}/package/default/app.conf" ]]; then
    awk -v version="${TA_VERSION}" '
BEGIN { section = "" }
/^\[/ { section = $0 }
section == "[launcher]" && $1 == "version" { $0 = "version = " version }
section == "[id]" && $1 == "version" { $0 = "version = " version }
{ print }
' "${SOURCE_DIR}/package/default/app.conf" > "${SOURCE_DIR}/package/default/app.conf.updated"
    mv "${SOURCE_DIR}/package/default/app.conf.updated" "${SOURCE_DIR}/package/default/app.conf"
fi

echo "Running ucc-gen build for version ${TA_VERSION}"
uv run ucc-gen build \
    --source "${SOURCE_DIR}/package" \
    --config "${SOURCE_DIR}/globalConfig.json" \
    --ta-version "${TA_VERSION}" \
    --output "${BUILD_OUTPUT_DIR}"

while IFS= read -r -d '' conf_file; do
    uv run ksconf check "${conf_file}"
done < <(find "${BUILD_OUTPUT_DIR}/TA-pushover" -type f -name "*.conf" -print0)

rm -rf output
mkdir -p output
cp -R "${BUILD_OUTPUT_DIR}/TA-pushover" output/

OUTPUT_FILE="TA-pushover.spl"
COPYFILE_DISABLE=1 tar czf "${OUTPUT_FILE}" -C output "TA-pushover"
echo "Done. Created ${OUTPUT_FILE}"
