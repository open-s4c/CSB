# Copyright (C) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# SPDX-License-Identifier: MIT
from monitors.monitor import Monitor
from utils.process import BackgroundProcess
from bm_utils import resolve_path
import os


class BpfTrace(Monitor):
    RESOURCES_PATH = "bm-runner/monitors/resources"

    def __init__(self, output_dir: str, args: list[str] = []):
        super().__init__(dir=output_dir, args=args)
        self.name = "bpftrace"
        self.traces = []
        for bt in args:
            cmds = ["sudo", "bpftrace"]
            out_name = f"{bt}.txt"
            err_name = f"{bt}.err"
            bt_file = str(resolve_path(os.path.join(self.RESOURCES_PATH, f"{self.name}/{bt}")))
            cmds.append(bt_file)
            trace = BackgroundProcess(
                name=self.name,
                ofile_name=out_name,
                efile_name=err_name,
                cmds=cmds,
                out_dir=output_dir,
                requires=["bpftrace"],
                pin=self.get_cpus(),
            )
            self.traces.append(trace)

    def start(self):
        for trace in self.traces:
            trace.start()

    def stop(self):
        for trace in self.traces:
            trace.stop()

    def collect_results(self) -> str:
        # plot_perf_hist_for_comm(self.trace.output_file_name, "rocksdb_min_roc", os.path.join(self.dir, "bpftrace.png"))
        return ""
