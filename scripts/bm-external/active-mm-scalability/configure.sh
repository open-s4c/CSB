#!/bin/sh
# Copyright (C) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# SPDX-License-Identifier: MIT

set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/../../.." && pwd)
src="$root/bm-external/active-mm-scalability/active-mm-scalability.c"
out="$root/bm-external/active-mm-scalability/active-mm-scalability"

${CC:-cc} -O2 -g -Wall -Wextra -Werror -o "$out" "$src"
