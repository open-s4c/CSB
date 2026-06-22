# Copyright (C) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# SPDX-License-Identifier: MIT

from monitors.bpf_program import BPFProgram
from monitors.bpf_parser_counts import BPFParserCounts

class BPFSchedMigrateTask(BPFProgram):
    name = "sched_migrate_task"
    parser = BPFParserCounts()
    program = """
tracepoint:sched:sched_migrate_task
/ __FILTER_CPU__ && __FILTER_PID__ /
{@migrations[pid] = count();}
"""