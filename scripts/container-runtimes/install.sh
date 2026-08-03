#!/usr/bin/env bash
# Copyright (C) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# SPDX-License-Identifier: MIT

# Install one adapter into PREFIX. Versions may be pinned through TOOL_VERSION.
set -Eeuo pipefail
source "$(cd -- "$(dirname -- "$0")" && pwd)/lib/common.sh"

usage() { printf 'usage: %s TOOL|--all\n' "$0"; }
[[ $# == 1 ]] || { usage; exit 2; }
mkdir -p "${BIN_DIR}"
targets=("$1"); [[ "$1" == --all ]] && targets=("${TOOLS[@]}")
for tool in "${targets[@]}"; do
  contains "${tool}" "${TOOLS[@]}" || die "unknown tool: ${tool}"
  unset -f tool_install 2>/dev/null || true
  load_tool "${tool}"
  note "installing ${tool} under ${PREFIX}"
  tool_install
done
