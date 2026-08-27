#!/bin/bash
# Copyright (C) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# SPDX-License-Identifier: MIT

set -euo pipefail

work_dir=$(mktemp -d /tmp/csb-sysbench-fileio.XXXXXX)
file_num=${CSB_SYSBENCH_FILE_NUM:-32}
file_size=${CSB_SYSBENCH_FILE_SIZE:-256M}

cleanup()
{
    status=$?
    cd /
    rm -rf -- "${work_dir}"
    exit "${status}"
}
trap cleanup EXIT

cd "${work_dir}"
sysbench fileio --file-num="${file_num}" --file-total-size="${file_size}" \
    prepare >/dev/null
sysbench fileio --file-num="${file_num}" --file-total-size="${file_size}" \
    "$@" run
