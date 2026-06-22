# Copyright (C) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# SPDX-License-Identifier: MIT

from monitors.bpf_program import BPFProgram
from monitors.bpf_parser_histograms import BPFParserHistograms
class BPFIrqHandler(BPFProgram):
    name = "irq_handler"
    parser = BPFParserHistograms()
    program = """
tracepoint:irq:irq_handler_entry
/ __FILTER_CPU__ && __FILTER_PID__ /
{ @start[pid] = nsecs; }

tracepoint:irq:irq_handler_exit
/ @start[pid] /
{ @ns[pid] = hist(nsecs - @start[pid]); delete(@start[pid]); }
"""
