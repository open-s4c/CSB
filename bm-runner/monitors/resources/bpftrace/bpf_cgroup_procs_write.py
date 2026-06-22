# Copyright (C) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# SPDX-License-Identifier: MIT

import os
import pandas as pd
from monitors.bpf_program import BPFProgram
from monitors.bpf_parser_histograms import BPFParserHistograms

class BPFCGroupProcsWrite(BPFProgram):
    name = "cgroup_procs_write"
    parser = BPFParserHistograms()
    program = """
kprobe:__cgroup_procs_write 
/ __FILTER_CPU__ && __FILTER_PID__ /
{
    @start[tid] = nsecs;
}
kretprobe:__cgroup_procs_write /@start[tid]/ {
    $duration = (nsecs - @start[tid]) / 1000;
    @migration_latency[pid] = hist($duration);
    delete(@start[tid]);
}
"""
