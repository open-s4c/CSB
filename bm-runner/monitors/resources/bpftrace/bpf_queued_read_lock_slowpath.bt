# Copyright (C) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# SPDX-License-Identifier: MIT

from monitors.bpf_program import BPFProgram
from monitors.bpf_parser_histograms import BPFParserHistograms

class BPFQueuedReadLockSlowpath(BPFProgram):
    name = "queued_read_lock_slowpath"
    parser = BPFParserHistograms()
    program = """
kprobe:queued_read_lock_slowpath
/ __FILTER_CPU__ && __FILTER_PID__ /
{ @start[tid] = nsecs; }

kretprobe:queued_read_lock_slowpath
/ @start[tid] /
{ @ns[pid] = hist(nsecs - @start[tid]); delete(@start[tid]); }
"""
