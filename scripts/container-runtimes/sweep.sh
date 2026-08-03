#!/usr/bin/env bash
# Copyright (C) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# SPDX-License-Identifier: MIT

# Exercise the complete matrix; continue after failures and summarize at the end.
set -Eeuo pipefail
source "$(cd -- "$(dirname -- "$0")" && pwd)/lib/common.sh"
mode="${1:---plan}"; [[ "${mode}" =~ ^--(trace|no-trace|plan)$ ]] || die "expected --trace, --no-trace, or --plan"
failures=0
for tool in "${TOOLS[@]}"; do
  for point in "${POINTS[@]}"; do
    note "${tool}/${point}"
    "${HARNESS_DIR}/run.sh" "${mode}" "${tool}" "${point}" || failures=$((failures + 1))
  done
done
((failures == 0)) || die "${failures} matrix entries failed"
