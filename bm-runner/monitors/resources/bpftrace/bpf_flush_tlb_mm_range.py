# Copyright (C) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# SPDX-License-Identifier: MIT

from monitors.bpf_program import BPFProgram
from monitors.bpf_parser_counts import BPFParserCounts

class BPFFlushTlbMMRange(BPFProgram):
    name = "flush_tlb_mm_range"
    parser = BPFParserCounts()
    program = """
kprobe:flush_tlb_mm_range
/ __FILTER_CPU__ && __FILTER_PID__ /
{ @tlb[pid] = count(); }
"""
