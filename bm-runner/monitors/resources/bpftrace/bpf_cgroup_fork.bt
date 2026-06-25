# Copyright (C) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# SPDX-License-Identifier: MIT

from monitors.bpf_program import BPFProgram
from monitors.bpf_parser_histograms import BPFParserHistograms

class BPFCGroupFork(BPFProgram):
    name = "cgroup_fork"
    parser = BPFParserHistograms()
    program = """
kprobe:cgroup_can_fork,
kprobe:cgroup_fork 
/ __FILTER_CPU__ && __FILTER_PID__ /
{
    @start[tid] = nsecs;
}
kretprobe:cgroup_can_fork,
kretprobe:cgroup_fork /@start[tid]/ {
    $duration = (nsecs - @start[tid]) / 1000;
    @fork_latency[pid] = hist($duration);
    delete(@start[tid]);
}
"""
