#!/usr/bin/env bash
# Copyright (C) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# SPDX-License-Identifier: MIT

# Run exactly one tool/capture-point pair, optionally through collect_strace.sh.
set -Eeuo pipefail
source "$(cd -- "$(dirname -- "$0")" && pwd)/lib/common.sh"

usage() { printf 'usage: %s [--trace|--no-trace|--plan] TOOL POINT\n       %s --list\n' "$0" "$0"; }
if [[ "${1:-}" == --list ]]; then
  for t in "${TOOLS[@]}"; do for p in "${POINTS[@]}"; do printf '%s\t%s\n' "$t" "$p"; done; done
  exit 0
fi
mode="${1:---trace}"; [[ "${mode}" =~ ^--(trace|no-trace|plan)$ ]] || { usage; exit 2; }; shift
[[ $# == 2 ]] || { usage; exit 2; }
tool="$1" point="$2"
contains "${tool}" "${TOOLS[@]}" || die "unknown tool: ${tool}"
contains "${point}" "${POINTS[@]}" || die "unknown capture point: ${point}"
load_tool "${tool}"
clean_case_dir "${tool}" "${point}"
output="${TRACE_DIR}/$(host_arch)/${tool}/${point}.strace"
if ! tool_supports "${point}"; then
  if [[ "${mode}" == --plan ]]; then printf 'SKIP %s/%s: no distinct operation\n' "${tool}" "${point}"; exit 0; fi
  write_skip "${output}" "${tool} has no distinct ${point} operation"
  [[ "${STRICT_SKIPS:-0}" == 0 ]] || exit 1
  exit 0
fi
mapfile -d '' -t command < <(tool_command "${point}")
((${#command[@]})) || die "adapter emitted no command"
if [[ "${mode}" == --plan ]]; then printf '%q ' "${command[@]}"; printf '\n'; exit 0; fi
[[ "${ALLOW_NON_ARM64:-0}" == 1 ]] || require_arm64
run_mode="${mode#--}"
trace_or_run "${run_mode}" "${output}" "${command[@]}"
[[ "${run_mode}" == trace ]] && "${HARNESS_DIR}/verify.sh" "${output}" "${tool}" "${point}"
