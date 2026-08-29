#!/bin/sh
# Copyright (C) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# SPDX-License-Identifier: MIT

set -eu

workers=1
steps=1024
warmup_steps=32

usage()
{
    echo "Usage: $0 [--workers N] [--steps N] [--warmup-steps N]" >&2
}

require_uint()
{
    name=$1
    value=$2
    case "$value" in
        ''|*[!0-9]*)
            echo "$name must be a positive integer" >&2
            exit 2
            ;;
    esac
    if [ "$value" -lt 1 ]; then
        echo "$name must be a positive integer" >&2
        exit 2
    fi
}

while [ "$#" -gt 0 ]; do
    case "$1" in
        --workers)
            [ "$#" -ge 2 ] || { usage; exit 2; }
            workers=$2
            shift 2
            ;;
        --steps)
            [ "$#" -ge 2 ] || { usage; exit 2; }
            steps=$2
            shift 2
            ;;
        --warmup-steps)
            [ "$#" -ge 2 ] || { usage; exit 2; }
            warmup_steps=$2
            shift 2
            ;;
        *)
            usage
            exit 2
            ;;
    esac
done

require_uint --workers "$workers"
require_uint --steps "$steps"
require_uint --warmup-steps "$warmup_steps"

script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
makefile=$script_dir/Makefile

for command in make cc date awk; do
    command -v "$command" >/dev/null 2>&1 || {
        echo "Required command is unavailable: $command" >&2
        exit 1
    }
done

# Warm executable pages, compiler files, and the fixture outside measurement.
make --no-print-directory -s -f "$makefile" -j "$workers" STEPS="$warmup_steps"

start_ns=$(date +%s%N)
make --no-print-directory -s -f "$makefile" -j "$workers" STEPS="$steps"
end_ns=$(date +%s%N)
elapsed_ns=$((end_ns - start_ns))

elapsed_seconds=$(awk -v value="$elapsed_ns" 'BEGIN { printf "%.9f", value / 1000000000 }')
steps_per_second=$(awk -v count="$steps" -v value="$elapsed_ns" \
    'BEGIN { printf "%.6f", count * 1000000000 / value }')
elapsed_per_step_us=$(awk -v count="$steps" -v value="$elapsed_ns" \
    'BEGIN { printf "%.3f", value / count / 1000 }')

printf 'steps_per_second=%s;completed=%s;failures=0;elapsed_seconds=%s;elapsed_per_step_us=%s;workers=%s;task=gnu_make_cc_syntax;\n' \
    "$steps_per_second" "$steps" "$elapsed_seconds" "$elapsed_per_step_us" "$workers"
