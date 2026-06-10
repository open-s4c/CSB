# Copyright (C) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# SPDX-License-Identifier: MIT

from monitors.monitor import Monitor
from utils.logger import bm_log, LogType
from utils.process import BackgroundProcess
from bm_utils import read_data_frame_from_csv
import pandas as pd


class PerfStat(Monitor):
    # we collect the usual defaults always, because
    # some of the metric values rely on multiple counters
    # to be calculated. e.g. `branch-misses` metric value
    # needs `branches` to be also monitored.
    DEFAULT_EVENTS = [
        "cpu-clock",
        "context-switches",
        "cpu-migrations",
        "page-faults",
        "cycles",
        "instructions",
        "branches",
        "branch-misses",
    ]

    def __init__(self, output_dir: str, args: list[str] = []):
        super().__init__(dir=output_dir, args=args)
        self.name = "perf-stat"
        events = ",".join(self.DEFAULT_EVENTS)
        cmds = ["sudo", "perf", "stat", "-x", ";", "-o", self.name, "-e", events]
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
            # header row is based on `man perf stat` CSV FORMAT section
            # We are interested in metric_value
            VALUE_COL = "metric_value"
            KEY_COL = "event"
            header = [
                "counter_value",
                "unit",
                KEY_COL,
                "runtime",
                "percentage",
                VALUE_COL,
                "metric_unit",
            ]
            df = read_data_frame_from_csv(
                self.stat.output_file_name,
                names=header,
            )
            if df is None:
                bm_log(f"{self.name} did not produce a valid data-frame", LogType.ERROR)
                return ""
            for _, row in df.iterrows():
                value = row[VALUE_COL]
                key = row[KEY_COL]
                # on some machines e.g. CI, monitoring some events
                # is not supported. In that case the value will be `<not supported>`.
                # Here we want to avoid adding meaningless values to the final CSV,
                # so we skip adding those with value N/A or not a number.
                if pd.notna(value) and pd.api.types.is_number(value):
                    output += f"{key}={value};"
                else:
                    bm_log(f"{self.name} could not read a valid value for {key}", LogType.ERROR)
            return output
        else:
            bm_log(
                "Could not read output of perf stat, `self.stat` is not initialized!", LogType.ERROR
            )
        return ""
