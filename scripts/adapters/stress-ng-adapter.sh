#!/bin/bash
# Copyright (C) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# SPDX-License-Identifier: MIT

awk '
/stress-ng: metr(c|ic):/ && $5 ~ /^[0-9]+([.][0-9]+)?$/ && $6 ~ /^[0-9]+([.][0-9]+)?$/ {
    if ($6 == "nanosecs" || $6 == "%")
        next
    stressor = $4
    ops = $5
    real_time = $6
    usr_time = $7
    sys_time = $8
    throughput_real = $9
    throughput_cpus = $10
    cpu_percent = $11
    rss_max = $12
}
/stress-ng: metr(c|ic):/ && $6 == "nanosecs" {
    pthread_start_ns = $5
}
/stress-ng: metr(c|ic):/ && $6 == "%" {
    pthread_created_percent = $5
}
/stress-ng: info:/ && $4 == "skipped:" {
    skipped = $5
    sub(/:$/, "", skipped)
}
/stress-ng: info:/ && $4 == "passed:" {
    passed = $5
    sub(/:$/, "", passed)
}
/stress-ng: info:/ && $4 == "failed:" {
    failed = $5
    sub(/:$/, "", failed)
}
/stress-ng: info:/ && $4 == "metrics" && $5 == "untrustworthy:" {
    untrustworthy = $6
}
END {
    if (stressor == "")
        exit 1
    printf "stressor=%s;ops=%s;real_time=%s;usr_time=%s;sys_time=%s;throughput_real=%s;throughput_cpus=%s;cpu_percent=%s;rss_max=%s;skipped=%s;passed=%s;failed=%s;untrustworthy=%s;",
           stressor, ops, real_time, usr_time, sys_time, throughput_real,
           throughput_cpus, cpu_percent, rss_max, skipped, passed, failed,
           untrustworthy
    if (pthread_start_ns != "")
        printf "pthread_start_ns=%s;", pthread_start_ns
    if (pthread_created_percent != "")
        printf "pthread_created_percent=%s;", pthread_created_percent
    printf "\n"
}'
