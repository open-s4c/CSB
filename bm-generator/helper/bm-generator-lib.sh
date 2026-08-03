#!/bin/bash
# Copyright (C) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# SPDX-License-Identifier: MIT

get_workspace_dir() {
    RES_DIR="gen-ws"
    if [ -n "$CSB_RESULTS_GROUP" ]; then
        RES_DIR="$CSB_RESULTS_GROUP"
    fi
    echo "$RES_DIR"
}

normalize_syz_arch() {
    case "$1" in
        x86_64|amd64)
            echo "amd64"
            ;;
        aarch64|arm64)
            echo "arm64"
            ;;
        *)
            echo "$1"
            ;;
    esac
}

read_csb_meta_value() {
    file="$1"
    key="$2"
    if [ -f "${file}" ]; then
        sed -n "s/^[#[:space:]]*${key}=//p" "${file}" | head -n 1
    fi
}

trace_meta_file() {
    trace="$1"
    if [ -f "${trace}.meta" ]; then
        echo "${trace}.meta"
    elif [ -f "${trace%.log}.meta" ]; then
        echo "${trace%.log}.meta"
    fi
}

prog_target_os() {
    prog="$1"
    os="$(read_csb_meta_value "${prog}" "csb.trace.os")"
    if [ -z "${os}" ]; then
        os="${TRACE_OS:-linux}"
    fi
    echo "${os}"
}

prog_target_arch() {
    prog="$1"
    arch="$(read_csb_meta_value "${prog}" "csb.trace.arch")"
    if [ -z "${arch}" ]; then
        arch="${TRACE_ARCH:-$(normalize_syz_arch "$(uname -m)")}"
        echo "WARNING: ${prog} has no csb.trace.arch metadata; using ${arch}" >&2
    fi
    normalize_syz_arch "${arch}"
}

trace_target_os() {
    trace="$1"
    meta="$(trace_meta_file "${trace}")"
    os="${TRACE_OS:-}"
    if [ -z "${os}" ] && [ -n "${meta}" ]; then
        os="$(read_csb_meta_value "${meta}" "csb.trace.os")"
    fi
    if [ -z "${os}" ]; then
        os="linux"
    fi
    echo "${os}"
}

trace_target_arch() {
    trace="$1"
    meta="$(trace_meta_file "${trace}")"
    arch="${TRACE_ARCH:-}"
    if [ -z "${arch}" ] && [ -n "${meta}" ]; then
        arch="$(read_csb_meta_value "${meta}" "csb.trace.arch")"
    fi
    if [ -z "${arch}" ]; then
        arch="$(normalize_syz_arch "$(uname -m)")"
        echo "WARNING: no trace architecture metadata found for ${trace}; using host arch ${arch}. Set TRACE_ARCH to override." >&2
    fi
    normalize_syz_arch "${arch}"
}
