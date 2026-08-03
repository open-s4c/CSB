#!/bin/bash
# Copyright (C) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# SPDX-License-Identifier: MIT


source helper/bm-generator-lib.sh

 : ${DIR_PROG:="./deserialized"}
 : ${DIR_OUT:="./extracted"}
 : ${MINCALLS:=10}
 : ${JOBS:=$(nproc)}

if [ ! -d "${DIR_PROG}" ]; then
  echo "Directory \"${DIR_PROG}\" with syz-lang programs does not exist."
  echo "Either run"
  echo "  ./`ls 02_*.sh`"
  echo "to generate it, or specify directory explicitly:"
  echo "  DIR_PROG=\"/path/to/prog/files/\" $0"

  exit 1
fi

DIR_PROG_ABS="`readlink -e ${DIR_PROG}`"

files=`find "${DIR_PROG_ABS}" -maxdepth 1 -name '*.prog'`

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

if [ ! -d "${DIR_OUT}" ]; then
  mkdir -p "${DIR_OUT}"
fi
DIR_OUT_ABS="`readlink -e ${DIR_OUT}`"

cd "${DIR_SYZ_SRC}"

numRunning() {
  echo `pgrep 'syz-extraction' | wc -l`
}

i=0
for file in $files; do
  while [ $(numRunning) -ge ${JOBS} ]; do
    sleep 1
  done
  echo $file
  dir="${DIR_OUT_ABS}/$i"
  mkdir -p "${dir}"
  prog_os="$(prog_target_os "${file}")"
  prog_arch="$(prog_target_arch "${file}")"
  bin/syz-extraction -os "${prog_os}" -arch "${prog_arch}" -prog "${file}" -deserialize "${dir}" -minCalls ${MINCALLS} &
  i=$(($i + 1))
done

wait

# remove empty directories
i=0
for file in $files; do
  dir="${DIR_OUT_ABS}/$i"
  if [ -z "$( ls -A ${dir} )" ]; then
    rmdir "${dir}"
  fi
  i=$(($i + 1))
done
