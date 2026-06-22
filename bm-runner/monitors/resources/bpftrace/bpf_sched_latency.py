# Copyright (C) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# SPDX-License-Identifier: MIT

import os
import pandas as pd
from monitors.bpf_program import BPFProgram
from monitors.bpf_parser_histograms import BPFParserHistograms

class BPFSchedLatency(BPFProgram):
    name = "sched_latency"
    parser = BPFParserHistograms()
    program= """
#ifndef BPFTRACE_HAVE_BTF                                                                                                                                                                                                                                                                           :(
#include <linux/sched.h>
#else
#define TASK_RUNNING 0
#endif
tracepoint:sched:sched_wakeup,
tracepoint:sched:sched_wakeup_new
/ __FILTER_CPU__ && __FILTER_PID__ /
{
  @qtime[args.pid] = nsecs;
}

tracepoint:sched:sched_switch
/ __FILTER_CPU__ && __FILTER_PID__ /
{
  if (args.prev_state == TASK_RUNNING) {
    @qtime[args.prev_pid] = nsecs;
  }
  // Ignore the idle task
  if (args.next_pid == 0) {
    return;
  }

  $ns = @qtime[args.next_pid];
  if $ns {
    @nsecs = hist(nsecs - $ns);
    // Swallowing deletion failures as they are expected
    $ignore = delete(@qtime, args.next_pid);
  }
}

END
{
  clear(@qtime);
}
"""
