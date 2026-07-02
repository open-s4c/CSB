# Copyright (C) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# SPDX-License-Identifier: MIT

import os
import pandas as pd
from monitors.monitor import Monitor
from utils.logger import bm_log, LogType
from utils.process import BackgroundProcess
from benchkit.shell.shell import shell_out
from bm_utils import read_data_frame_from_csv
from visual.plotchart import PlotConfig, PlotChart


class PerfLock(Monitor):
    LOCK_CONTENTION_CSV = "lock-contention.csv"
    TARGET_METRIC = "avg_wait"
    LOCK_CONTENTION_SEPARATOR = ";"
    LOCK_CONTENTION_TOP_N = 20

    # The command `perf lock contention -x ";"` will output a CSV with the following header
    # output: contended; total wait; max wait; avg wait; type; caller
    header = ["contended", "total_wait", "max_wait", "avg_wait", "type", "caller"]

    def __init__(self, output_dir: str, args: list[str] = ["-a"]):
        super().__init__(dir=output_dir, args=args)
        self.name = "perf-lock"
        self.perf_lock_data = f"{self.name}.data"
        self.perf_contention_csv = os.path.join(self.dir, self.LOCK_CONTENTION_CSV)
        cmds = [
            "sudo",
            "perf",
            "lock",
            "record",
            "-g",
            "-e",
            "lock:contention_begin",
            "-e",
            "lock:contention_end",
            "--output",
            self.perf_lock_data,
        ]
        cmds.extend(args)

        self.perf_lock = BackgroundProcess(
            name=self.name,
            out_dir=output_dir,
            cmds=cmds,
            requires=["perf"],
            pin=self.get_cpus(),
        )

    def start(self):
        self.perf_lock.start()

    def stop(self):
        if self.perf_lock is not None:
            # perf lock record takes longer time to respond
            self.perf_lock.stop(timeout=60)

    def collect_results(self):
        output = ""
        if self.__run_lock_contention():
            df = read_data_frame_from_csv(self.perf_contention_csv, names=self.header)
            if df is not None and not df.empty:
                # dump detailed plot of head results
                self.__plot(df.head(self.LOCK_CONTENTION_TOP_N))
                # summary of all locks per run
                avg_wait = df["avg_wait"].mean()
                max_wait = df["max_wait"].max()
                total_wait = df["total_wait"].sum()
                # this will be appended to the final csv
                output += f"perf_lock_avg_wait={avg_wait};"
                output += f"perf_lock_max_wait={max_wait};"
                output += f"perf_lock_total_wait={total_wait};"
            else:
                bm_log(f"{self.name} did not produce a valid data-frame", LogType.ERROR)
        return output

    def __run_lock_contention(self) -> bool:
        cmd = [
            "sudo",
            "perf",
            "lock",
            "contention",
            "-k",  # sort by average wait
            self.TARGET_METRIC,
            "-i",  # input file is the output of `perf lock record`
            self.perf_lock_data,
            "-x",  # output report should be a CSV with `;` as delimiter
            ";",
            "--output",
            self.perf_contention_csv,
        ]
        try:
            # perf lock contention is not available on older kernel versions
            # the command can fail
            shell_out(command=cmd, current_dir=self.dir)
            return True
        except Exception:
            bm_log("perf lock raised an error, check if it is supported.", LogType.ERROR)
            return False

    def __plot(self, df: pd.DataFrame):
        subjects = [
            ("contended", "Contended"),
            ("avg_wait", "Average Wait"),
            ("total_wait", "Total Wait"),
            ("max_wait", "Max Wait"),
        ]
        for y, label in subjects:
            cfg = PlotConfig(
                y=y,
                y_lbl=label,
                x="caller",
                x_lbl="Caller Function",
                hue="type",
                hue_lbl="Lock Type",
                shape="barplot",
            )
            plot_file = os.path.join(self.dir, f"perf_lock_{y}")
            PlotChart.plot(cfg, df, plot_file)
