#!/bin/bash
# Copyright (C) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# SPDX-License-Identifier: MIT

set -e

scriptpath=$(dirname "$0")

input_dir="$1"
output_dir="$2"

if [ -z "$1" ] || [ -z "$2" ]; then
    echo "usage: $0 input-directory output-directory"
fi
mkdir -p "$output_dir"

find "$input_dir" -name flamegraph.stacks | while read n; do
    suffname=$(echo "$n" | sed -e "s#${input_dir}[/]\?##g" | cut -d/ -f2-)
    i=$(echo "$n" | sed -e "s#${input_dir}[/]\?##g" | cut -d/ -f1)
    suff=$(dirname "$suffname")
    appname=$(jq -r '.[0].app' "$input_dir/$i/$suff/experiment_results.json")
    "$scriptpath/filter.sh" "$input_dir/$i/$suff/perf.data" "${appname:0:15}" "$output_dir"/"$appname".html;
done
