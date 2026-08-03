#!/bin/bash
# Copyright (C) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# SPDX-License-Identifier: MIT

set -e

# Check that exactly one argument is given
if [ $# != 1 ]; then
  echo "Usage: $0 </path/to/strace/log/file>"
  exit 1
fi

TRACE="$1"

source helper/bm-generator-lib.sh

if [ ! -f "${TRACE}" ]; then
  echo "Specified trace file ${TRACE} does not exist."
  exit 1
fi

TRACE_ABS="`readlink -e ${TRACE}`"
TRACE_OS_RESOLVED="$(trace_target_os "${TRACE_ABS}")"
TRACE_ARCH_RESOLVED="$(trace_target_arch "${TRACE_ABS}")"

# Check that syzkaller source directory is known
SCRIPT_SYZ_SRC="helper/find_syzkaller_src.sh"
 : ${DIR_SYZ_SRC:=$(${SCRIPT_SYZ_SRC})}

if [ ! -d "${DIR_SYZ_SRC}" ]; then
  echo "syzkaller source dir not found. Try to run:"
  echo "  ./`ls -1 01_*.sh`"
  echo ""
  echo "If the syzkaller source dir is not beneath $(pwd), then run this script as:"
  echo "  DIR_SYZ_SRC=\"</path/to/syzkaller/source>\" $0"
  exit 1
fi

DIR_CUR="`pwd`"

# Check and create directory for syz-lang .prog files
 : ${DIR_PROG:="./deserialized"}

if [ ! -d "${DIR_PROG}" ]; then
    mkdir -p "${DIR_PROG}"
fi

DIR_PROG_ABS="`readlink -e ${DIR_PROG}`"

# Check if directory for syz-lang .prog files is empty, abort if not
if [ ! -n "$(find "$DIR_PROG_ABS" -maxdepth 0 -type d -empty 2>/dev/null)" ]; then
    echo "Directory for deserialization not empty!"
    echo "  ${DIR_PROG_ABS}"
    exit 1
fi

# Change to syzkaller source
cd "${DIR_SYZ_SRC}"

bin/syz-trace2syz -vv 0 -os "${TRACE_OS_RESOLVED}" -arch "${TRACE_ARCH_RESOLVED}" -file "${TRACE_ABS}" --deserialize "${DIR_PROG_ABS}" --nocorpus

cd "${DIR_CUR}"

compgen -G "${DIR_PROG_ABS}/*.prog" >/dev/null || {
  echo "Trace translation produced no syzlang programs." >&2
  exit 1
}
./helper/compare_strace_to_syzprog.sh "${TRACE_ABS}" "${DIR_PROG_ABS}"
