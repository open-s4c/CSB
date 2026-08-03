#!/bin/bash
# Copyright (C) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# SPDX-License-Identifier: MIT

source helper/bm-generator-lib.sh

: ${DIR_PROG:="./extracted"}
: ${DIR_OUT:="./reduced"}
: ${JOBS:=$(nproc)}
: ${MAX_CALLS:=4096}
: ${MAX_MOTIF_INSTANCES:=8}
: ${MAX_LIVE_RESOURCES:=128}
: ${KEEP_FIRST:=2}
: ${KEEP_LAST:=1}
: ${MOTIF_CONSTS:=true}
: ${MOTIF_FILENAMES:=false}

if [ ! -d "${DIR_PROG}" ]; then
  echo "Directory \"${DIR_PROG}\" with extracted syz-lang programs does not exist."
  echo "Either run"
  echo "  ./`ls 03_*.sh`"
  echo "to generate it, or specify directory explicitly:"
  echo "  DIR_PROG=\"/path/to/prog/files/\" $0"
  exit 1
fi

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

mkdir -p "${DIR_OUT}"
DIR_OUT_ABS="`readlink -e ${DIR_OUT}`"
DIR_PROG_ABS="`readlink -e ${DIR_PROG}`"

if [ ! -x "${DIR_SYZ_SRC}/bin/syz-prog-reduce" ]; then
  echo "syz-prog-reduce not found. Try to run:"
  echo "  ./`ls -1 01_*.sh`"
  exit 1
fi

export DIR_SYZ_SRC DIR_PROG_ABS DIR_OUT_ABS MAX_CALLS MAX_MOTIF_INSTANCES MAX_LIVE_RESOURCES KEEP_FIRST KEEP_LAST MOTIF_CONSTS MOTIF_FILENAMES
export -f normalize_syz_arch read_csb_meta_value prog_target_os prog_target_arch

find "${DIR_PROG_ABS}" -type f -name '*.prog' -print0 | \
  xargs -0 -n 1 -P "${JOBS}" bash -c '
    in="$1"
    rel="${in#${DIR_PROG_ABS}/}"
    out="${DIR_OUT_ABS}/${rel}"
    mkdir -p "$(dirname "${out}")"
    prog_os="$(prog_target_os "${in}")"
    prog_arch="$(prog_target_arch "${in}")"
    "${DIR_SYZ_SRC}/bin/syz-prog-reduce" \
      -os "${prog_os}" \
      -arch "${prog_arch}" \
      -prog "${in}" \
      -out "${out}" \
      -max-calls "${MAX_CALLS}" \
      -max-motif-instances "${MAX_MOTIF_INSTANCES}" \
      -max-live-resources "${MAX_LIVE_RESOURCES}" \
      -keep-first "${KEEP_FIRST}" \
      -keep-last "${KEEP_LAST}" \
      -motif-consts="${MOTIF_CONSTS}" \
      -motif-filenames="${MOTIF_FILENAMES}"
  ' _
