# Copyright (C) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# SPDX-License-Identifier: MIT

from monitors.bpf_program import BPFProgram
from monitors.bpf_parser_histograms import BPFParserHistograms

class BPFBlockReq(BPFProgram):
    name = "block_req"
    parser = BPFParserHistograms()
    program = """
tracepoint:block:block_rq_complete
/ __FILTER_CPU__ && __FILTER_PID__ /
{ @requests[pid] = hist(args->nr_sector * 512) }
"""
