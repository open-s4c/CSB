# Copyright (C) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# SPDX-License-Identifier: MIT

from monitors.bpf_program import BPFProgram
from monitors.bpf_parser_histograms import BPFParserHistograms

class BPFExt4MbNewBLocks(BPFProgram):
    name = "ext4_mb_new_blocks"
    parser = BPFParserHistograms()
    program = """
kprobe:ext4_mb_new_blocks 
/ __FILTER_CPU__ && __FILTER_PID__ /
{ @start[pid] = nsecs; }

kretprobe:ext4_mb_new_blocks 
/ @start[pid] /
{ @ns[pid] = hist(nsecs - @start[pid]); delete(@start[pid]); }
"""
