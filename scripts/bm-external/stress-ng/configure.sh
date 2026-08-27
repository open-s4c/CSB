#!/bin/sh
# Copyright (C) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# SPDX-License-Identifier: MIT

set -eu

SCRIPT_DIR="$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)"
CSB_ROOT="$(CDPATH='' cd -- "${SCRIPT_DIR}/../../.." && pwd)"
export CSB_ROOT
. "${CSB_ROOT}/scripts/bm-external/common.sh"

STRESS_NG_VERSION="${STRESS_NG_VERSION:-V0.22.00}"
SOURCE_DIR="${EXTERNAL_DIR}/stress-ng"

require_command make
clone_release https://github.com/ColinIanKing/stress-ng.git "${SOURCE_DIR}" \
	"${STRESS_NG_VERSION}"

(
	cd "${SOURCE_DIR}"
	make clean >/dev/null 2>&1 || true
	make -j "${BUILD_JOBS}"
)
