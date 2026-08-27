#!/bin/sh
# Copyright (C) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# SPDX-License-Identifier: MIT

set -eu

: "${CSB_ROOT:?CSB_ROOT must name the CSB source directory}"

EXTERNAL_DIR="${CSB_EXTERNAL_DIR:-${CSB_ROOT}/bm-external}"
BUILD_JOBS="${BUILD_JOBS:-$(getconf _NPROCESSORS_ONLN 2>/dev/null || echo 1)}"

info() {
	printf '[external-setup] %s\n' "$*"
}

die() {
	printf '[external-setup] error: %s\n' "$*" >&2
	exit 1
}

require_command() {
	command -v "$1" >/dev/null 2>&1 || die "required command not found: $1"
}

clone_release() {
	repository=$1
	directory=$2
	revision=$3
	require_command git

	if [ -d "${directory}/.git" ]; then
		if ! git -C "${directory}" diff --quiet ||
			! git -C "${directory}" diff --cached --quiet; then
			die "refusing to replace modified source tree ${directory}"
		fi
		info "updating ${directory} to ${revision}"
		git -C "${directory}" fetch --depth 1 origin "${revision}"
		git -C "${directory}" checkout --detach FETCH_HEAD
		return
	fi
	if [ -e "${directory}" ]; then
		die "${directory} exists but is not a git checkout"
	fi

	mkdir -p "$(dirname "${directory}")"
	info "cloning ${repository} at ${revision}"
	git clone --depth 1 --branch "${revision}" "${repository}" "${directory}"
}
