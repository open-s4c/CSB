#!/bin/bash
# Copyright (C) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# SPDX-License-Identifier: MIT
set -e

SCRIPT_DIR="$(readlink -f $(dirname "$0")/..)"
cd $SCRIPT_DIR

if [ -z "$1" ]; then
    exit 1
fi

CONFIG="$(readlink -f $1)"
shift

TITLE=$(basename "$CONFIG" .json)

## this script is to be embedded in other scripts
HOSTNAME=$(hostname)
export CSB_NO_BUILD_BENCH=ON

BM_DIR=bm-runner

info() {
    echo "[run.sh] $1"
}

### Configure the env
${SCRIPT_DIR}/scripts/prepare.sh
. ./venv/bin/activate

### change dir to bm-runner
cd ${BM_DIR}

info "running $TITLE on $CONFIG"

FD_LIMIT=$(ulimit -H -n)
info "Setting the open files limit to $FD_LIMIT"
# set file limit to the max
ulimit -n $FD_LIMIT

python3 main.py --title "$TITLE" --config "$CONFIG" $*
