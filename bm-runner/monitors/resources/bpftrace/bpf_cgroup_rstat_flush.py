# Copyright (C) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# SPDX-License-Identifier: MIT

from monitors.bpf_program import BPFProgram
from monitors.bpf_parser_histograms import BPFParserHistograms

class BPFCGroupRstatFlush(BPFProgram):
    name = "cgroup_rstat_flush"
    parser = BPFParserHistograms()
    program = """
kprobe:mem_cgroup_css_rstat_flush
/ __FILTER_CPU__ && __FILTER_PID__ /
{
    @start[tid] = nsecs;
}
kretprobe:mem_cgroup_css_rstat_flush /@start[tid]/ {
    $duration = (nsecs - @start[tid]) / 1000;
    @flush_latency[pid] = hist($duration);
    delete(@start[tid]);
}
"""
