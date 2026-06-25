# Copyright (C) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# SPDX-License-Identifier: MIT

from monitors.bpf_program import BPFProgram
from monitors.bpf_parser_counts import BPFParserCounts

class BPFPageFaultKernel(BPFProgram):
    name = "page_fault_kernel"
    parser = BPFParserCounts()
    program = """
tracepoint:exceptions:page_fault_kernel
/ __FILTER_CPU__ && __FILTER_PID__ /
{ @fault[pid] = count(); }
"""
