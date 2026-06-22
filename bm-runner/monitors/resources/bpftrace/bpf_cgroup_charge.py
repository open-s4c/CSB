# Copyright (C) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# SPDX-License-Identifier: MIT

from monitors.bpf_program import BPFProgram
from monitors.bpf_parser_histograms import BPFParserHistograms

class BPFCGroupCharge(BPFProgram):
    name = "cgroup_charge"
    parser = BPFParserHistograms()
    program = """
kprobe:__mem_cgroup_charge 
/ __FILTER_CPU__ && __FILTER_PID__ /
{
    @start[tid] = nsecs;
}
kretprobe:__mem_cgroup_charge /@start[tid]/ {
    $duration = (nsecs - @start[tid]) / 1000;
    @charge_latency[pid] = hist($duration);
    delete(@start[tid]);
}
"""
