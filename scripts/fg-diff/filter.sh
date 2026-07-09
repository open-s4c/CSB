#!/usr/bin/bash
# Copyright (C) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# SPDX-License-Identifier: MIT

set -e

file="$1"
target="$2"
outfile="$3"

if [ -z "$1" ] || [ -z "$2" ] || [ -z "$3" ]; then
    echo "usage: $0 input-perf-data-path process-target-regex output-files-path"
    exit 1
fi

sudo perf script -i "$file" --dsos='[kernel.kallsyms]' | awk -vtarget="$target" '
BEGIN {started = 0}
started == 1 && NF==0 {started = 0; print;}
started == 1 && $NF=="([kernel.kallsyms])" {print}
$NF=="cycles:" || $NF=="cycles:P:" || $NF=="cpu-clock:" {if ($1 ~ target) {sub(target"[-]?[0-9]*", "THR")}; started = 1; print}
' | "$FLAMEGRAPH"/stackcollapse-perf.pl | tee "$outfile.stacks" | "$FLAMEGRAPH"/flamegraph.pl --width=1920 --title="Flame graph: $(basename $outfile)" > "$outfile"
