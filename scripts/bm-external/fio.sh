#!/bin/bash
# Copyright (C) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# SPDX-License-Identifier: MIT

set -euo pipefail

fio_dir=${CSB_FIO_DIRECTORY:-/tmp}
fio_file=$(mktemp --tmpdir="${fio_dir}" csb-fio.XXXXXX)
cleanup()
{
    rm -f -- "${fio_file}"
}
trap cleanup EXIT

fio "$@" --filename="${fio_file}"
