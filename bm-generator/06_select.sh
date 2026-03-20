#!/bin/bash
# Copyright (C) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# SPDX-License-Identifier: MIT

set -ex

source helper/bm-generator-lib.sh
group="$(get_workspace_dir)"

scriptpath=$(dirname "$0")

cd "$scriptpath/../"

if [ -e "./results/$group" ]; then
    echo "Directory ./results/$group exists. Remove it before proceeding."
    exit 1
fi

mkdir -p results

export CSB_RESULTS_GROUP="$group"

export CSB_SELECTED_OUTPUT="$(mktemp)"

./scripts/fg-diff/select-benchmarks.sh ./config/"$group"/fg_*.json

echo "The selected benchmarks are (available in $CSB_SELECTED_OUTPUT):"
cat "$CSB_SELECTED_OUTPUT"

export FLAMEGRAPH="deps/FlameGraph"

./scripts/fg-merge/filter-merge.sh "./results/$group" ./bench-select "$CSB_SELECTED_OUTPUT"
if [ -e ./bench-select/all.html ]; then
    echo "The aggregation of individual benchmark flamegraphs is available in $(realpath ./bench-select/all.html)"
fi
