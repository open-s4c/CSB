#!/bin/sh
# Copyright (C) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# SPDX-License-Identifier: MIT

set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")/../../.." && pwd)
src="$root/bm-external/ci-fanout/ci-fanout-micro.c"
out="$root/bm-external/ci-fanout/ci-fanout-micro"

${CC:-cc} -O2 -g -Wall -Wextra -Werror -pthread -o "$out" "$src"
