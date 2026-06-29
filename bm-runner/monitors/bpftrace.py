# Copyright (C) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# SPDX-License-Identifier: MIT
from monitors.monitor import Monitor
from utils.process import BackgroundProcess
from bm_utils import resolve_path
import os
from utils.logger import bm_log, LogType
import re
import pandas as pd
from bm_visualize import plot_chart, PlotConfig
import bm_config

# TODO: pass along information about apps names to the monitors?
import sys


class BpfTrace(Monitor):
    # TODO: move to scripts
    RESOURCES_PATH = "bm-runner/monitors/resources"

    def __init__(self, output_dir: str, args: list[str] = []):
        super().__init__(dir=output_dir, args=args)
        self.name = "bpftrace"
        self.traces = {}
        # regular expression to parse the following format
        #   @<name>[<pid>, <comm>]: <count>
        # e.g. @page_fault_user[1975977, rocksdb_min_roc]: 2
        self.count_pattern = re.compile(
            r"@(?P<name>\w+)\[(?P<pid>\d+),\s*(?P<comm>\w+)\]:\s*(?P<count>\d+)"
        )

        self.hist_header = re.compile(
            r"@(?P<name>\w+)\[(?P<pid>\d+),\s*(?P<comm>[^\]]+)\]:"
        )
        self.hist_bucket = re.compile(
            r"\[(?P<bucket>[^\]]+)\]\s+(?P<count>\d+)"
        )

        for bt in args:
            cmds = ["sudo", "bpftrace"]
            out_name = f"{bt}.txt"
            err_name = f"{bt}.err"
            bt_file = str(resolve_path(os.path.join(self.RESOURCES_PATH, f"{self.name}/{bt}")))

            try:
                with open(bt_file, "r") as f:
                    # only first 16 chars (including null terminator) are in comm.
                    contents = f.read().replace("__FILTER__", self.__get_filter())
                    cmds.append("-e")
                    cmds.append(contents)
                    trace = BackgroundProcess(
                        name=self.name,
                        ofile_name=out_name,
                        efile_name=err_name,
                        cmds=cmds,
                        out_dir=output_dir,
                        requires=["bpftrace"],
                        pin=self.get_cpus(),
                    )
                    self.traces[bt] = trace
            except Exception as e:
                bm_log(f"{self.name} cannot read/parse {bt_file}. Exception {e}", LogType.FATAL)
                sys.exit(1)

    def __get_filter(self) -> str:
        if bm_config.g_config is None:
            bm_log(
                "Configuration object is not set. Unexpected behavior encountered!", LogType.FATAL
            )
            sys.exit(1)
            return ""
        apps = bm_config.g_config.get_apps()
        if len(apps) > 1:
            bm_log(f"{self.name} does not support multi app mode", LogType.FATAL)
        # 16 chars because that's the maximum length of comm
        # TODO: check if it can be read from env-vars or somewhere reliable.
        comm = apps[0].name[:15].strip()
        return f'/ comm == "{comm}" /'

    def start(self):
        for trace in self.traces.values():
            trace.start()

    def stop(self):
        for name, trace in self.traces.items():
            ret = trace.stop()
            if ret != 0:
                bm_log(
                    f"bpftrace program {name} failed. With error code {ret}. Check {trace.err_file_name}",
                    LogType.ERROR,
                )

    def collect_results(self) -> str:
        output = ""
        for name, trace in self.traces.items():
            output += self.__parse_trace(name, trace)
        return output

    def __parse_trace(self, name: str, trace: BackgroundProcess) -> str:
        count_trace = name.endswith("_count.bt")
        hist_trace = name.endswith("_hist.bt")
        with open(trace.output_file_name, "r") as f:
            content = f.read()
            if count_trace:
               return self.__parse_count(content, trace.output_file_name)
            elif hist_trace:
                return self.__parse_hist(content)
        return ""


    def __parse_count(self, content:str, fname) -> str:
        output = ""
        df = pd.DataFrame(m.groupdict() for m in self.count_pattern.finditer(content))
        if not df.empty:
            counter_subject = df["name"].unique()
            if len(counter_subject) > 1:
                bm_log(
                    "Multiple counters detected, this case is not handled", LogType.FATAL
                )
                sys.exit(1)
            assert len(counter_subject) == 1, "No counter detected!"
            counter_subject = counter_subject[0]
            cfg = PlotConfig(
                x="pid",
                x_lbl="PID",
                y_lbl="Count",
                y="count",
                hue="pid",
                shape="barplot",
                title=counter_subject,
            )
            df["count"] = df["count"].astype(int)
            plot_chart(plot=cfg, df=df, out_fig_name=fname)
            count_col = df["count"]
            output += f"{counter_subject}_sum={count_col.sum()};"
            output += f"{counter_subject}_avg={count_col.mean()};"
            output += f"{counter_subject}_min={count_col.min()};"
            output += f"{counter_subject}_max={count_col.max()};"
        return output

    def __parse_hist(self, content:str) -> str:
        bm_log("Histogram parsing", LogType.FATAL)
        return ""
