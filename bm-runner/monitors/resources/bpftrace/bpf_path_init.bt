# Copyright (C) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# SPDX-License-Identifier: MIT

from monitors.bpf_program import BPFProgram
from monitors.bpf_parser_histograms import BPFParserHistograms

class BPFPathInit(BPFProgram):
    name = "path_init"
    parser = BPFParserHistograms()
    program = """
kprobe:path_init
/ __FILTER_CPU__ && __FILTER_PID__ /
{ @start[tid] = nsecs; }

kretprobe:path_init
/ @start[tid] /
{ @ns[pid] = hist(nsecs - @start[tid]); delete(@start[tid]); }
"""
