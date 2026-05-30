#!/usr/bin/env bash
set -eu

RELEASE_REPO="ConcaveTrillion/pd-ocr-labeler"
RELEASE_VERSION_SOURCE="uv"
RELEASE_VERSION_FILES="pyproject.toml uv.lock"

. "$(dirname "$0")/release-common.sh"
pd_release_main "$@"
