# Copyright (C) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# SPDX-License-Identifier: MIT

from monitors.bpf_program import BPFProgram
from monitors.bpf_parser_histograms import BPFParserHistograms

class BPFRawSpinLock(BPFProgram):
    name = "raw_spin_lock"
    parser = BPFParserHistograms()
    program = """
kprobe:_raw_spin_lock
/ __FILTER_CPU__ && __FILTER_PID__ /
{ @start[tid] = nsecs; }

kprobe:_raw_spin_unlock
/ @start[tid] /
{ @ns[pid] = hist(nsecs - @start[tid]); delete(@start[tid]); }
"""
