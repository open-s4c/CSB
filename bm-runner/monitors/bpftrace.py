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
        cmds = [
            "sudo",
            "bpftrace",
            str(resolve_path(os.path.join(self.RESOURCES_PATH, f"{self.name}/block_req.bt"))),
        ]

        self.trace = BackgroundProcess(
            name=self.name,
            ofile_name=f"{self.name}.txt",
            cmds=cmds,
            out_dir=output_dir,
            requires=["bpftrace"],
            pin=self.get_cpus(),
        )

    def start(self):
        self.trace.start()

    def stop(self):
        self.trace.stop()

    def collect_results(self) -> str:
        return ""
