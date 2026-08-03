#!/bin/bash
# Copyright (C) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# SPDX-License-Identifier: MIT
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/helper/bm-generator-lib.sh"

TMP_DIR="$(mktemp -d)"
trap 'rm -rf "${TMP_DIR}"' EXIT

check_eq() {
  got="$1"
  want="$2"
  msg="$3"
  if [ "${got}" != "${want}" ]; then
    echo "${msg}: got \"${got}\", want \"${want}\""
    exit 1
  fi
}

for arch in amd64 arm64; do
  trace="${TMP_DIR}/${arch}.log"
  meta="${trace}.meta"
  prog="${TMP_DIR}/${arch}.prog"

  touch "${trace}"
  {
    echo "csb.trace.os=linux"
    echo "csb.trace.arch=${arch}"
  } > "${meta}"
  {
    echo "# csb.trace.os=linux"
    echo "# csb.trace.arch=${arch}"
    echo "openat(0xffffffffffffff9c, &(0x7f0000000000)='/tmp/x\\x00', 0x0, 0x0)"
  } > "${prog}"

  check_eq "$(trace_target_os "${trace}")" "linux" "trace os for ${arch}"
  check_eq "$(trace_target_arch "${trace}")" "${arch}" "trace arch for ${arch}"
  check_eq "$(prog_target_os "${prog}")" "linux" "prog os for ${arch}"
  check_eq "$(prog_target_arch "${prog}")" "${arch}" "prog arch for ${arch}"
done

TRACE_ARCH=arm64
export TRACE_ARCH
old_trace="${TMP_DIR}/old.log"
touch "${old_trace}"
check_eq "$(trace_target_arch "${old_trace}")" "arm64" "TRACE_ARCH fallback for old trace"

echo "architecture metadata helper tests passed"
