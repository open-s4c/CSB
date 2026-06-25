# Copyright (C) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# SPDX-License-Identifier: MIT

from monitors.bpf_program import BPFProgram
from monitors.bpf_parser_histograms import BPFParserHistograms

class BPFSchedDomainsMutex(BPFProgram):
    name = "sched_domains_mutex"
    parser = BPFParserHistograms()
    program = """
kprobe:sched_domains_mutex_lock
/ __FILTER_CPU__ && __FILTER_PID__ /
{
    @start[tid] = nsecs;
}
kretprobe:sched_domains_mutex_lock
/ @start[tid] /
{
    $wait_ns = nsecs - @start[tid];
    @wait_time[pid] = hist($wait_ns);
    delete(@start[tid]);
}
"""
