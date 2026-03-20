#!/bin/bash
# Copyright (C) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# SPDX-License-Identifier: MIT
set -e
export CSB_RESULTS_GROUP="ls"
source helper/bm-generator-lib.sh
STRACE_LOG="ls_strace.log"
APP="ls -la /dev"
../scripts/plugins/collect_strace.sh ${STRACE_LOG} ${APP}
echo "STEP#0: Initializing ..."
./00_init.sh
echo "STEP#1: Building ..."
./01_build.sh
echo "STEP#2: Parsing ${STRACE_LOG} ..."
./02_parse.sh ${STRACE_LOG}
echo "STEP#3: Extracting ..."
./03_extract.sh
echo "STEP#4: Preparing ..."
./04_prepare.sh
echo "STEP#5: Generating ..."
./05_generate.sh
echo "STEP#6 Selecting microbenchmarks using flamegraph-diff"
# Commented out until CI runner has python enabled.
./06_select.sh

#echo "STEP#7: Build and test ..."
#cd ../build
## We only want to build related targets not everything.
#WS=$(get_workspace_dir)
#find ../bench/targets/$WS -name "min_ls_*.h" | grep -v syz | sed "s/.*\/\(min_ls_.*\)\.h/${WS}_\1/" | xargs make
## We run only related tests
#ctest -R "$WS".*_ls_.* --output-on-failure
