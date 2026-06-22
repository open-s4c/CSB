# Copyright (C) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# SPDX-License-Identifier: MIT

from monitors.bpf_program import BPFProgram
from monitors.bpf_parser_counts import BPFParserCounts

class BPFSchedFork(BPFProgram):
    name = "sched_fork"
    parser = BPFParserCounts()
    program = """
tracepoint:sched:sched_process_fork
/ __FILTER_CPU__ && __FILTER_PID__ /
{ @[args->parent_pid] = count(); }
"""
