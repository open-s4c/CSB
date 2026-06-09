# Copyright (C) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# SPDX-License-Identifier: MIT

from monitors.monitor import Monitor
from utils.logger import bm_log, LogType
from utils.process import BackgroundProcess
from bm_utils import read_data_frame_from_csv


class PerfStat(Monitor):
    def __init__(self, output_dir: str, args: list[str] = []):
        super().__init__(dir=output_dir, args=args)
        self.name = "perf-stat"
        cmds = ["perf", "stat", "-x", ";", "-o", self.name]
        cmds.extend(args)

        self.stat = BackgroundProcess(
            name=self.name,
            ofile_name=self.name,
            cmds=cmds,
            out_dir=output_dir,
            requires=["perf"],
            pin=self.get_cpus(),
        )

    def start(self):
        self.stat.start()

    def stop(self):
        self.stat.stop()

    def collect_results(self) -> str:
        output = ""
        if self.stat:
            df = read_data_frame_from_csv(
                self.stat.output_file_name,
                names=["counter_val", "unit", "event", "runtime", "percentage", "1", "2"],
            )
            if df is None:
                bm_log(f"{self.name} did not produce a valid data-frame", LogType.ERROR)
                return ""
            for _, row in df.iterrows():
                output += f"{row['event']}={row['counter_val']};"
            return output
        else:
            bm_log(
                "Could not read output of perf stat, `self.stat` is not initialized!", LogType.ERROR
            )
        return ""
