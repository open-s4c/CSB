# Copyright (C) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# SPDX-License-Identifier: MIT

from monitors.bpf_program import BPFProgram
from monitors.bpf_parser_histograms import BPFParserHistograms

class BPFCopyFromUser(BPFProgram):
    name = "copy_from_user"
    parser = BPFParserHistograms()
    program = """
kprobe:bpf_copy_from_user 
/ __FILTER_CPU__ && __FILTER_PID__ /
{ @start[pid] = nsecs; }

kretprobe:bpf_copy_from_user
/ @start[pid] /
{ @ns[pid] = hist(nsecs - @start[pid]); delete(@start[pid]); }
"""
