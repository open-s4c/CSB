# Copyright (C) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# SPDX-License-Identifier: MIT
from monitors.monitor import Monitor
from utils.process import BackgroundProcess
from bm_utils import resolve_path
import os
from utils.logger import bm_log, LogType
import re
import pandas as pd
from visual.plotchart import PlotChart, PlotConfig
import bm_config
import sys
from pathlib import Path
from config.env_config import UniversalConfig, EnvUniversalConfig
import math
import seaborn as sns
import matplotlib.pyplot as plt


class BpfTrace(Monitor):
    RESOURCES_PATH = "scripts"
    BUCKET_COL_SEPARATOR = "-"
    BUCKET_EQUAL_CHAR = "!"
    PID = "pid"
    COMM = "comm"
    NAME = "name"
    COUNT = "count"
    BUCKET = "bucket"

    HEADER_REGEX = rf"@(?P<{NAME}>\w+)\[(?P<{PID}>\d+),\s*(?P<{COMM}>.+)\]:"

    def __init__(self, output_dir: str, args: list[str] = []):
        super().__init__(dir=output_dir, args=args)
        """
        Launches `bpftrace` with the given `bpftrace` programs (`args`).

        This monitor relies on the follow conventions:
            - given programs exist under `scripts/bpftrace`.
            - if the program name has suffix `_count.bt` its output is parsed under the assumption
            it respects the following format `@name[pid, comm]: count`
            - if the program name has suffix `_hist.bt` its output is parsed under the assumption
            it respects the following format `@name[pid, comm]:` followed by bucket lines
            - if neither `_count.bt` nor `_hist.bt` is used as a suffix, the output will not be parsed and
            no plots will be generated.
            - Every .bt program should include `__FILTER__` where the process filter belongs. The monitor
            auto replaces that with '/ comm == "<app-name>" /' where `<app-name>` is the first 15 characters
            of the benchmark application name. Users can overwrite the filter by setting env var
            `CSB_BPFTRACE_FILTER` to the desired filter. e.g. `export CSB_BPFTRACE_FILTER='/ comm == "runc" /'`

        Current Limitations:
            - At the moment, this monitor does not support multi-app mode of CSB.
            - By default, it filters based on the value of `comm`, which is defined to be of 16 character length
            including null terminator, hence only the first 15 chars of the application name is considered.
            This can yield inaccurate results if one or more applications share the first `15` characters.

        Parameters
        ----------
        output_dir: [str]
            Where output and error logs of the current run should be dumped.
        args: list[str]
            a list of `bpftrace` program file names, e.g. `<program>.bt` to be run with `bpftrace`.
            For each program there will be an instance of `bpftrace` launched.
            The program pool to choose from or add to is under `scripts/bpftrace`.
        """
        self.name = "bpftrace"
        self.traces = {}
        # we do it in the constructor for early error detection.
        self.__set_app_name()
        assert self.app_name is not None, "Post condition failed! app_name is not set!"
        # regular expression to parse the following format
        #   @<name>[<pid>, <comm>]: <count>
        # e.g. @page_fault_user[1975977, rocksdb_min_roc]: 2
        self.count_pattern = re.compile(rf"{self.HEADER_REGEX}\s*(?P<{self.COUNT}>\d+)")
        # regular expression to parse header line of each histogram
        #   @<name>[<pid>, <comm>]:
        self.hist_header = re.compile(rf"{self.HEADER_REGEX}")
        # regular expression to parse bucket line of a histogram
        self.hist_bucket = re.compile(
            rf"\[(?P<{self.BUCKET}>[^\]\)]+(?:,\s*[^\)\]]+)?)[])]\s+(?P<{self.COUNT}>\d+)"
        )

        for bt in args:
            cmds = ["sudo", "bpftrace"]
            prefix = Path(bt).stem
            out_name = f"{prefix}.txt"
            err_name = f"{prefix}.err"
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
                    self.traces[prefix] = trace
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
        filter = EnvUniversalConfig.get(UniversalConfig.CSB_BPFTRACE_FILTER)
        if filter is None:
            # Note that comm is defined to be 16 chars including null terminator
            # hence we take the first real 15 chars.
            comm = self.app_name[:15].strip()
            filter = f'/ comm == "{comm}" /'
        return filter

    def start(self):
        for trace in self.traces.values():
            trace.start()
        self.__await_probes_attached()

    def __await_probes_attached(self):
        for prefix, trace in self.traces.items():
            if trace.await_token("Attaching"):
                bm_log(f"{self.name}:{prefix} probe attached successfully.")
            else:
                bm_log(f"{self.name}:{prefix} cannot confirm probe is attached!", LogType.ERROR)

    def stop(self):
        for prefix, trace in self.traces.items():
            ret = trace.stop()
            if ret != 0:
                bm_log(
                    f"bpftrace program {prefix} failed. With error code {ret}. Check {trace.err_file_name}",
                    LogType.ERROR,
                )

    def collect_results(self) -> str:
        output = ""
        for prefix, trace in self.traces.items():
            output += self.__parse_output(prefix, trace)
        return output

    def __parse_output(self, prefix: str, trace: BackgroundProcess) -> str:
        try:
            with open(trace.output_file_name, "r") as f:
                content = f.read()
                if prefix.endswith("_count"):
                    return self.__parse_count_output(prefix, content, trace.output_file_name)
                elif prefix.endswith("_hist"):
                    return self.__parse_hist_output(prefix, content, trace.output_file_name)
                else:
                    bm_log(
                        f"{self.name}: Could not determine parser for {prefix}. Output will not be parsed. Consider adding `_count` or `_hist` as a program suffix, or implement a suitable parser.",
                        LogType.WARNING,
                    )
        except Exception as e:
            bm_log(
                f"{self.name} Parsing of {trace.output_file_name} failed. Error: {e}", LogType.ERROR
            )
        return ""

    def __parse_count_output(self, prefix: str, content: str, fname) -> str:
        output = ""
        sum = 0
        avg = 0
        min = 0
        max = 0
        df = pd.DataFrame(m.groupdict() for m in self.count_pattern.finditer(content))
        if df.empty:
            bm_log(f"No count data collected in {fname}", LogType.WARNING)
        else:
            trace_point = self.__get_trace_point_name(df)
            cfg = PlotConfig(
                x=self.PID,
                x_lbl="PID",
                y_lbl="Count",
                y=self.COUNT,
                hue=self.PID,
                shape="barplot",
                title=trace_point,
            )
            df[self.COUNT] = df[self.COUNT].astype(int)
            PlotChart.plot(plot=cfg, df=df, out_fig_name=fname)
            count_col = df[self.COUNT]
            sum = count_col.sum()
            avg = count_col.mean()
            min = count_col.min()
            max = count_col.max()
        # we always append to the output, even if the dataframe is empty
        # this way we can maintain a sound CSV with each row has same
        # number of columns, even when an error occurs.
        output += f"{prefix}_sum={sum};"
        output += f"{prefix}_avg={avg};"
        output += f"{prefix}_min={min};"
        output += f"{prefix}_max={max};"
        return output

    def __get_trace_point_name(self, df: pd.DataFrame) -> str:
        if self.NAME in df.columns:
            names = df[self.NAME].unique()
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

    def __parse_hist_df(self, content: str) -> pd.DataFrame:
        rows = []
        row = {}
        for line in content.splitlines():
            line = line.strip()
            # Parse histogram header information
            if m := self.hist_header.match(line):
                if row:
                    rows.append(row)
                row = {}
                row[self.NAME] = m[self.NAME]
                row[self.PID] = int(m[self.PID])
                row[self.COMM] = m[self.COMM]
            # Parse buckets information
            elif m := self.hist_bucket.match(line):
                low, sep, high = m["bucket"].partition(",")
                low = low.strip()
                high = low if high.strip() == "" else high.strip()
                row[f"{low}{self.BUCKET_COL_SEPARATOR}{high}"] = int(m[self.COUNT])
        # append last row
        if row:
            rows.append(row)
        # convert to a dataframe and fill absent (NaN) bucket counts with 0
        return pd.DataFrame(rows).fillna(0)

    def __parse_hist_output(self, prefix: str, content: str, fname) -> str:
        hist_data = ""
        df = self.__parse_hist_df(content)
        if df.empty:
            bm_log(f"No histogram data collected in {fname}", LogType.WARNING)
        else:
            trace_point = self.__get_trace_point_name(df)
            bucket_cols = [c for c in df.columns if self.BUCKET_COL_SEPARATOR in c]
            plot_df = df.melt(
                id_vars=[self.PID, self.COMM],
                value_vars=bucket_cols,
                var_name="bucket",
                value_name=self.COUNT,
            )
            cfg = PlotConfig(
                x="bucket",
                x_lbl="Bucket",
                y_lbl="Count",
                y=self.COUNT,
                hue=self.PID,
                shape="barplot",
                title=trace_point,
            )
            PlotChart.plot(plot=cfg, df=plot_df, out_fig_name=fname)
            if len(df[self.COMM].unique()) > 1:
                bm_log(
                    f"{fname}: Multiple COMM values detected. All will be treated as same process!",
                    LogType.WARNING,
                )
            # In order to create data that summarizes the full run
            # we remove PID, COMM cols and sum up data of all processes.
            summary_df = (
                df.drop(columns=[self.PID, self.COMM]).groupby([self.NAME], as_index=False).sum()
            )
            # since we expect the data to be related to one trace point, we expect to have
            # only one row.
            if len(summary_df) > 1:
                bm_log(f"{fname}: multi trace points is not supported", LogType.ERROR)
            else:
                # we compress the data of all buckets into on string
                for _, row in summary_df.iterrows():
                    hist_data = ",".join(
                        f"{col}{self.BUCKET_EQUAL_CHAR}{int(val)}"
                        for col, val in row[bucket_cols].items()
                    )
        # always output to maintain same number of cols in CSV
        output = f"{prefix}='{hist_data}';"
        return output

    @staticmethod
    def __parse_size_to_bytes(bucket_desc: str) -> int | float:
        bucket_desc = str(bucket_desc).strip().upper()
        match = re.fullmatch(r"(\d+)([KMGTP]?)", bucket_desc)
        if not match:
            return math.inf

        value = int(match.group(1))
        unit = match.group(2)

        scale = {
            "": 1,
            "K": 1024,
            "M": 1024**2,
            "G": 1024**3,
            "T": 1024**4,
            "P": 1024**5,
        }

        return value * scale[unit]

    @staticmethod
    def __sort_bucket_key(bucket: str) -> int | float:
        lower = str(bucket).split("-", 1)[0]
        return BpfTrace.__parse_size_to_bytes(lower)

    @staticmethod
    def __parse_hist_col_into_buckets(
        df: pd.DataFrame, hist_col_name: str
    ) -> tuple[pd.DataFrame, list]:
        # fill empty values with an empty string, convert to string
        # strip away leading or trailing single quotes.
        stripped = df[hist_col_name].fillna("").astype(str).str.strip("'")

        # Parse hist data column value into separate buckets.
        parsed = stripped.apply(
            lambda hist_data: {
                # key is the bucket description e.g. 512-1024
                # value is the count associated with the bucket
                k: int(v)
                for bucket in hist_data.split(",")
                if bucket
                for k, v in [bucket.split(BpfTrace.BUCKET_EQUAL_CHAR)]
            }
        )

        bucket_cols: list[str] = sorted(
            dict.fromkeys(k for d in parsed for k in d),
            key=BpfTrace.__sort_bucket_key,
        )

        hist_df = pd.DataFrame(parsed.tolist(), columns=pd.Index(bucket_cols)).fillna(0).astype(int)

        df = df.drop(columns=hist_col_name).join(hist_df)

        id_vars = [c for c in df.columns if c not in bucket_cols]
        df_long = df.melt(
            id_vars=id_vars,
            value_vars=bucket_cols,
            var_name="bucket",
            value_name="count",
        )

        return df_long, bucket_cols

    @staticmethod
    def dump_hist_data_heat_map(df: pd.DataFrame, plot: PlotConfig, output_dir: str) -> str:
        x_col = plot.x  # container_cnt
        hue_col = plot.hue  # execution_type
        hist_col = plot.y  # bpftrace histogram column

        df = df[[x_col, hue_col, hist_col]].copy()

        df_long, bucket_cols = BpfTrace.__parse_hist_col_into_buckets(df, hist_col)

        if df_long.empty:
            bm_log(f"Cannot plot {plot.title}. Dataframe is empty!", LogType.WARNING)
            return ""

        hues = df[hue_col].unique()

        fig, axes = plt.subplots(
            1,
            len(hues),
            figsize=(8 * len(hues), 5),
            sharey=True,
        )

        if len(hues) == 1:
            axes = [axes]

        for subplot, hue_val in zip(axes, hues):
            df_hue = df_long[df_long[hue_col].astype(str) == str(hue_val)]

            heatmap_data = (
                df_hue.pivot_table(
                    index="bucket",
                    columns=x_col,
                    values="count",
                    aggfunc="mean",
                )
                .reindex(index=bucket_cols)
                .fillna(0)
            )

            sns.heatmap(
                heatmap_data,
                annot=True,
                fmt=".0f",
                ax=subplot,
                cmap="magma",
            )

            subplot.set(
                title=f"{plot.title} ({hue_val})",
                xlabel=plot.x_lbl,
                ylabel="Buckets",
            )

        figure_name = f"{output_dir}/{plot.title}"
        fig.tight_layout()
        fig.savefig(f"{figure_name}.png", dpi=300, bbox_inches="tight")
        plt.close(fig)

        return figure_name
