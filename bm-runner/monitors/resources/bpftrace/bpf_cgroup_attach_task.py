# Copyright (C) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# SPDX-License-Identifier: MIT

from monitors.bpf_program import BPFProgram
from monitors.bpf_parser_histograms import BPFParserHistograms

class BPFCGroupAttachTask(BPFProgram):
    name = "cgroup_attach_task"
    parser = BPFParserHistograms()
    program = """
kprobe:cgroup_attach_task
/ __FILTER_CPU__ && __FILTER_PID__ /
{
    @start[tid] = nsecs;
}
kretprobe:cgroup_attach_task /@start[tid]/ {
    $duration = (nsecs - @start[tid]) / 1000;
    @attach_latency[pid] = hist($duration);
    delete(@start[tid]);
}
"""
