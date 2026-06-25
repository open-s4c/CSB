# Copyright (C) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# SPDX-License-Identifier: MIT

from monitors.bpf_program import BPFProgram
from monitors.bpf_parser_counts import BPFParserCounts

class BPFCGroupRstatLockCont(BPFProgram):
    name = "cgroup_rstat_lock"
    parser = BPFParserCounts()
    program = """

tracepoint:cgroup:cgroup_rstat_lock_contended
/ __FILTER_CPU__ && __FILTER_PID__ /
{
    @contended[pid] = count();
}
"""