#!/bin/bash
# Copyright (C) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# SPDX-License-Identifier: MIT
set -e

if [ ! -d results ] || [ ! -d bm-runner ] || [ ! -d ./scripts/fg-diff ] || [ ! -d deps ]; then
    echo "Run this script from the CSB directory"
    exit 1;
fi
export FLAMEGRAPH="$(realpath ./deps/FlameGraph)"

mkdir -p logs

export CSB_NO_CLEAN_BENCH=1
c=0
N_ARGS="$#"
for i in $*; do
    c=$((c+1))
    fbase=$(basename $i .json)
    echo "[$(date)] Benchmarking ${i} ${c}/${N_ARGS}"
    ./scripts/run-single.sh $(realpath "$i")
done

source ./venv/bin/activate

RESULTS_DIR="./results"
if [ ! -z "CSB_RESULTS_GROUP" ]; then
    RESULTS_DIR="./results/$CSB_RESULTS_GROUP"
fi

mkdir -p ./bench-select
echo "Preprocessing perf.data files from benchmark results"
./scripts/fg-diff/filter-all.sh "$RESULTS_DIR" ./bench-select
echo "Calculating difference between flamegraphs"
./scripts/fg-diff/diff-all.sh ./bench-select > ./bench-select/diff.csv

if [ ! -z "$CSB_SELECTED_OUTPUT" ]; then
    python3 ./scripts/fg-diff/diffset.py --cutoff 5 --input ./bench-select/diff.csv > "$CSB_SELECTED_OUTPUT"
else
    python3 ./scripts/fg-diff/diffset.py --cutoff 5 --input ./bench-select/diff.csv
fi
