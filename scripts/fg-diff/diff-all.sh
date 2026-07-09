#!/bin/bash
# Copyright (C) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# SPDX-License-Identifier: MIT

if [ -z "$1" ]; then
    echo "usage: %0 directory-with-stacks"
    exit 1
fi

stack_files=$(find "$1" -name \*.stacks)

i=0
for file_a in $stack_files; do
    bfa=$(basename "$file_a")
    j=0
    for file_b in $stack_files; do
	if [ $i -ge $j ]; then
	    bfb=$(basename "$file_b")
	    "$FLAMEGRAPH"/difffolded.pl "$file_a" "$file_b" | "$FLAMEGRAPH"/flamegraph.pl > diff-1.html
	    "$FLAMEGRAPH"/difffolded.pl "$file_b" "$file_a" | "$FLAMEGRAPH"/flamegraph.pl > diff-2.html
	    DIFFAMOUNT=$(cat diff-1.html diff-2.html | grep -o '%; [+-]\?[0-9]\+\.[0-9]\+' | sed -e 's/^%; [+-]\?//g' | sort -n | tail -n 1)
	    echo "$bfa,$bfb,$DIFFAMOUNT"
	    j=$((j+1))
	fi
    done
    i=$((i+1))
done
rm diff-1.html diff-2.html
