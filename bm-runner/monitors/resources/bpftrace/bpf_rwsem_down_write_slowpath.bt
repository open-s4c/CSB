# Copyright (C) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# SPDX-License-Identifier: MIT

from monitors.bpf_program import BPFProgram
from monitors.bpf_parser_histograms import BPFParserHistograms

class BPFRWSemDownWriteSlowpath(BPFProgram):
    name = "rwsem_down_write_slowpath"
    parser = BPFParserHistograms()
    program = """
kprobe:rwsem_down_write_slowpath
/ __FILTER_CPU__ && __FILTER_PID__ /
{ @start[tid] = nsecs; }

kretprobe:rwsem_down_write_slowpath
/ @start[tid] /
{ @ns[pid] = hist(nsecs - @start[tid]); delete(@start[tid]); }
"""
