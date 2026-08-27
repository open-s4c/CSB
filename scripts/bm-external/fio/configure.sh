#!/bin/sh
# Copyright (C) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# SPDX-License-Identifier: MIT

set -eu

SCRIPT_DIR="$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)"
CSB_ROOT="$(CDPATH='' cd -- "${SCRIPT_DIR}/../../.." && pwd)"
export CSB_ROOT
. "${CSB_ROOT}/scripts/bm-external/common.sh"

FIO_VERSION="${FIO_VERSION:-fio-3.42}"
SOURCE_DIR="${EXTERNAL_DIR}/fio"

require_command make
clone_release https://github.com/axboe/fio.git "${SOURCE_DIR}" "${FIO_VERSION}"

(
	cd "${SOURCE_DIR}"
	make clean >/dev/null 2>&1 || true
	./configure
	make -j "${BUILD_JOBS}"
)
