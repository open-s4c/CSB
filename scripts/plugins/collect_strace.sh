#!/bin/bash
# Copyright (C) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# SPDX-License-Identifier: MIT


FILE_LOG=$1
shift
FILE_META="${FILE_LOG}.meta"

if [ -z "`command -v strace`" ]; then
  echo "\"strace\" command not found in \$PATH. Either install strace or add it to PATH"
  exit 1
fi

if [ $# -lt 1 ]; then
  echo "Usage:"
  echo "  $0 <output_fname> <command> [<arg1>] [<arg2>] ..."
  exit 1
fi

if [ -f "${FILE_LOG}" ]; then
  echo "Output file \"${FILE_LOG}\" already exists. (re)move it, or use a different output file name. Example:"
  echo "  FILE_LOG=strace_output.log $0 $@"
  exit 1
fi

if [ -f "${FILE_META}" ]; then
  echo "Metadata file \"${FILE_META}\" already exists. (re)move it, or use a different output file name."
  exit 1
fi

uname_arch="$(uname -m)"
case "${uname_arch}" in
  x86_64|amd64)
    syz_arch="amd64"
    ;;
  aarch64|arm64)
    syz_arch="arm64"
    ;;
  riscv64)
    syz_arch="riscv64"
    ;;
  *)
    syz_arch="${uname_arch}"
    ;;
esac

{
  echo "csb.trace.os=linux"
  echo "csb.trace.arch=${syz_arch}"
  echo "csb.trace.uname_machine=${uname_arch}"
  echo "csb.trace.uname=$(uname -a)"
  if command -v strace >/dev/null 2>&1; then
    echo "csb.trace.strace_version=$(strace -V 2>/dev/null | head -n 1)"
  fi
} > "${FILE_META}"

strace -o "${FILE_LOG}" -a 1 -s 65500 -v -xx -f -Xraw --raw=wait4 $@
