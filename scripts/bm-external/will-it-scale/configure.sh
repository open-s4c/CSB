#!/bin/sh
# Copyright (C) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# SPDX-License-Identifier: MIT

set -eu

SCRIPT_DIR="$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)"
CSB_ROOT="$(CDPATH='' cd -- "${SCRIPT_DIR}/../../.." && pwd)"
export CSB_ROOT
. "${CSB_ROOT}/scripts/bm-external/common.sh"

WILL_IT_SCALE_VERSION="${WILL_IT_SCALE_VERSION:-master}"
SOURCE_DIR="${EXTERNAL_DIR}/will-it-scale"

require_command make
clone_release https://github.com/antonblanchard/will-it-scale.git \
	"${SOURCE_DIR}" "${WILL_IT_SCALE_VERSION}"

(
	cd "${SOURCE_DIR}"
	make clean >/dev/null 2>&1 || true
	make -j "${BUILD_JOBS}"
)
