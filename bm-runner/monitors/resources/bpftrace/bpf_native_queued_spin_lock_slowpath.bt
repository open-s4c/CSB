# Copyright (C) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# SPDX-License-Identifier: MIT

from monitors.bpf_program import BPFProgram
from monitors.bpf_parser_histograms import BPFParserHistograms

class BPFNativeQueuedSpinLockSlowpath(BPFProgram):
    name = "native_queued_spin_lock_slowpath"
    parser = BPFParserHistograms()
    program = """
kprobe:native_queued_spin_lock_slowpath
/ __FILTER_CPU__ && __FILTER_PID__ /
{ @start[tid] = nsecs; }

kretprobe:native_queued_spin_lock_slowpath
/ @start[tid] /
{ @ns[pid] = hist(nsecs - @start[tid]); delete(@start[tid]); }
"""
