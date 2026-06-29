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
import sys


###################################
# Current limitations:
# 1) does not support multi-app benchmarks
# 2) filters traces based on app name/comm first 16 chars
#
###################################
class BpfTrace(Monitor):
    RESOURCES_PATH = "scripts"

    def __init__(self, output_dir: str, args: list[str] = []):
        super().__init__(dir=output_dir, args=args)
        self.name = "bpftrace"
        self.traces = {}
        # we do it in the constructor for early error detection.
        self.__set_app_name()
        assert self.app_name is not None, "Post condition failed! app_name is not set!"
        # regular expression to parse the following format
        #   @<name>[<pid>, <comm>]: <count>
        # e.g. @page_fault_user[1975977, rocksdb_min_roc]: 2
        self.count_pattern = re.compile(
            r"@(?P<name>\w+)\[(?P<pid>\d+),\s*(?P<comm>[^\]]+)\]:\s*(?P<count>\d+)"
        )
        # regular expression to parse header line of each histogram
        #   @<name>[<pid>, <comm>]:
        self.hist_header = re.compile(r"@(?P<name>\w+)\[(?P<pid>\d+),\s*(?P<comm>[^\]]+)\]:")
        # regular expression to parse bucket line of a histogram
        self.hist_bucket = re.compile(
            r"\[(?P<bucket>[^\]\)]+(?:,\s*[^\)\]]+)?)[])]\s+(?P<count>\d+)"
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

    def __set_app_name(self) -> str:
        if bm_config.g_config is None:
            bm_log(
                "Configuration object is not set. Unexpected behavior encountered!", LogType.FATAL
            )
            sys.exit(1)
            return ""
        apps = bm_config.g_config.get_apps()
        if len(apps) > 1:
            bm_log(f"{self.name} does not support multi app mode", LogType.FATAL)
            sys.exit(1)
        self.app_name = apps[0].name
        return self.app_name

    def __get_filter(self) -> str:
        # 16 chars because that's the maximum length of comm
        # TODO: check if it can be read from env-vars or somewhere reliable.
        comm = self.app_name[:15].strip()
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
        # we rely on the encoded meta data in the program name
        # `_count` suffix indicates that only count is collected
        # `_hist` suffix indicates that only histogram data is collected
        count_trace = name.endswith("_count.bt")
        hist_trace = name.endswith("_hist.bt")
        with open(trace.output_file_name, "r") as f:
            content = f.read()
            if count_trace:
                return self.__parse_count(content, trace.output_file_name)
            elif hist_trace:
                return self.__parse_hist(content, trace.output_file_name)
        return ""

    def __parse_count(self, content: str, fname) -> str:
        output = ""
        df = pd.DataFrame(m.groupdict() for m in self.count_pattern.finditer(content))
        if not df.empty:
            trace_point = self.__get_trace_point_name(df)
            cfg = PlotConfig(
                x="pid",
                x_lbl="PID",
                y_lbl="Count",
                y="count",
                hue="pid",
                shape="barplot",
                title=trace_point,
            )
            df["count"] = df["count"].astype(int)
            plot_chart(plot=cfg, df=df, out_fig_name=fname)
            count_col = df["count"]
            output += f"{trace_point}_sum={count_col.sum()};"
            output += f"{trace_point}_avg={count_col.mean()};"
            output += f"{trace_point}_min={count_col.min()};"
            output += f"{trace_point}_max={count_col.max()};"
        return output

    def __get_trace_point_name(self, df: pd.DataFrame) -> str:
        if "name" in df.columns:
            names = df["name"].unique()
            if len(names) == 1:
                return names[0]
            else:
                bm_log(
                    f"{self.name} produced data-frame has multiple unique values of name, which is unexpected.",
                    LogType.FATAL,
                )
        else:
            bm_log(
                f"{self.name} produced data-frame does not contain trace point `name` column.",
                LogType.FATAL,
            )
        return ""

    def __parse_hist(self, content: str, fname) -> str:
        rows = []
        current = {}

        for line in content.splitlines():
            line = line.strip()
            if m := self.hist_header.match(line):
                if current:
                    rows.append(current)
                current = {}
                current["name"] = m["name"]
                current["pid"] = int(m["pid"])
                current["comm"] = m["comm"]
            elif m := self.hist_bucket.match(line):
                low, sep, high = m["bucket"].partition(",")
                low = low.strip()
                high = low if high.strip() == "" else high.strip()
                current[f"[{low},{high})"] = int(m["count"])

        # append last row
        if current:
            rows.append(current)

        # convert to a dataframe and fill absent (NaN) bucket counts with 0
        df = pd.DataFrame(rows).fillna(0)
        if df.empty:
            return ""
        title = self.__get_trace_point_name(df)
        bucket_cols = [c for c in df.columns if c.startswith("[")]
        plot_df = df.melt(
            id_vars=["pid", "comm"],
            value_vars=bucket_cols,
            var_name="bucket",
            value_name="count",
        )
        cfg = PlotConfig(
            x="bucket",
            x_lbl="Bucket",
            y_lbl="Count",
            y="count",
            hue="pid",
            shape="barplot",
            title=title,
        )
        plot_chart(plot=cfg, df=plot_df, out_fig_name=fname)
        return ""
