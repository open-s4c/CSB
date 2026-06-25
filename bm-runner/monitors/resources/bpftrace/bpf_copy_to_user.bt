# Copyright (C) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# SPDX-License-Identifier: MIT

import os
import pandas as pd
from monitors.bpf_program import BPFProgram
from monitors.bpf_parser_histograms import BPFParserHistograms

class BPFCopyToUser(BPFProgram):
    name = "copy_to_user"
    parser = BPFParserHistograms()
    program = """
kprobe:bpf_copy_to_user 
/ __FILTER_CPU__ && __FILTER_PID__ /
{ @start[pid] = nsecs; }

kretprobe:bpf_copy_to_user
/ @start[pid] /
{ @ns[pid] = hist(nsecs - @start[pid]); delete(@start[pid]); }
"""
