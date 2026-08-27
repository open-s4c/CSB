#!/bin/sh
# Copyright (C) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# SPDX-License-Identifier: MIT

set -ex
SRC_DIR="$(readlink -f $(dirname "$0")/../../..)"
BUILD_DIR=${SRC_DIR}/bm-external

echo $BUILD_DIR

mkdir -p ${BUILD_DIR}
(
	cd ${BUILD_DIR}
	if [ ! -e will-it-scale/.git ]; then
		git clone https://github.com/antonblanchard/will-it-scale.git
	else
	    (cd will-it-scale && make clean|| true)
	fi
	cd will-it-scale
	cp "${SRC_DIR}/scripts/bm-external/will-it-scale/uname1.c" tests/uname1.c
	make
)
