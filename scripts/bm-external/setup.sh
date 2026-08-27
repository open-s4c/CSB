#!/bin/sh
# Copyright (C) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# SPDX-License-Identifier: MIT

set -eu

SCRIPT_DIR="$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)"
CSB_ROOT="$(CDPATH='' cd -- "${SCRIPT_DIR}/../.." && pwd)"
export CSB_ROOT
. "${SCRIPT_DIR}/common.sh"

TOOLS="fio stress-ng byte-unixbench will-it-scale sysbench"

usage() {
	cat <<EOF
Usage: $0 --all
       $0 TOOL [TOOL ...]
       $0 --check [TOOL ...]
       $0 --list

Download, build, and validate CSB's external benchmark tools under:
  ${EXTERNAL_DIR}

Supported tools:
  ${TOOLS}

The alias 'unixbench' is accepted for 'byte-unixbench'.
Set CSB_EXTERNAL_DIR to use another installation directory.
EOF
}

normalize_tool() {
	case "$1" in
	unixbench) printf '%s\n' byte-unixbench ;;
	fio | stress-ng | byte-unixbench | will-it-scale | sysbench)
		printf '%s\n' "$1"
		;;
	*) die "unsupported external tool: $1" ;;
	esac
}

tool_executable() {
	case "$1" in
	fio) printf '%s\n' "${EXTERNAL_DIR}/fio/fio" ;;
	stress-ng) printf '%s\n' "${EXTERNAL_DIR}/stress-ng/stress-ng" ;;
	byte-unixbench)
		printf '%s\n' "${EXTERNAL_DIR}/byte-unixbench/UnixBench/Run"
		;;
	will-it-scale)
		printf '%s\n' "${EXTERNAL_DIR}/will-it-scale/malloc1_processes"
		;;
	sysbench) printf '%s\n' "${EXTERNAL_DIR}/sysbench/bin/sysbench" ;;
	esac
}

check_tool() {
	tool=$1
	executable="$(tool_executable "${tool}")"
	[ -x "${executable}" ] || die "${tool} is not installed: ${executable}"
	info "${tool}: ready (${executable})"
}

setup_tool() {
	tool=$1
	"${SCRIPT_DIR}/${tool}/configure.sh"
	check_tool "${tool}"
}

mode=setup
case "${1:-}" in
--all)
	set -- fio stress-ng byte-unixbench will-it-scale sysbench
	;;
--check)
	mode=check
	shift
	if [ "$#" -eq 0 ]; then
		set -- fio stress-ng byte-unixbench will-it-scale sysbench
	fi
	;;
--list)
	printf '%s\n' fio stress-ng byte-unixbench will-it-scale sysbench
	exit 0
	;;
-h | --help)
	usage
	exit 0
	;;
"")
	usage >&2
	exit 2
	;;
esac

for requested_tool in "$@"; do
	tool="$(normalize_tool "${requested_tool}")"
	if [ "${mode}" = check ]; then
		check_tool "${tool}"
	else
		setup_tool "${tool}"
	fi
done
