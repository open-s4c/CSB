#!/bin/sh
# Copyright (C) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# SPDX-License-Identifier: MIT

set -eu

SCRIPT_DIR="$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)"
CSB_ROOT="$(CDPATH='' cd -- "${SCRIPT_DIR}/../../.." && pwd)"
export CSB_ROOT
. "${CSB_ROOT}/scripts/bm-external/common.sh"

SYSBENCH_VERSION="${SYSBENCH_VERSION:-1.0.20}"
SOURCE_DIR="${EXTERNAL_DIR}/sysbench"

require_command make
require_command autoconf
require_command automake
require_command libtoolize
require_command pkg-config
clone_release https://github.com/akopytov/sysbench.git "${SOURCE_DIR}" \
	"${SYSBENCH_VERSION}"

(
	cd "${SOURCE_DIR}"
	make clean >/dev/null 2>&1 || true
	./autogen.sh
	./configure --with-mysql --with-pgsql --prefix="${SOURCE_DIR}"
	make -j "${BUILD_JOBS}"
	make install
)
