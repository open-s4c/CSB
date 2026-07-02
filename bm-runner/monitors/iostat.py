# Copyright (C) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# SPDX-License-Identifier: MIT

import re
from typing import Any

import pandas as pd
from pandas import DataFrame

from monitors.monitor import Monitor
from utils.logger import LogType, bm_log
from utils.process import BackgroundProcess
from config.plot import PlotType, PlotConfig
from visual.plotchart import PlotChart
from bm_utils import str_to_json, get_block_devices
import os


class IoStat(Monitor):
    INTERVAL = 1
    DEVICE_COL = "disk_device"
    TIME_COL = "time"
    # plot title, plot file name, columns/metrics to be plotted together
    PLOT_SETS = [
        ("I/O operations per second", "iops", ["r/s", "w/s", "d/s", "f/s"]),
        ("Throughput (kB/s)", "throughput", ["rkB/s", "wkB/s", "dkB/s"]),
        ("Await time (ms)", "await", ["r_await", "w_await", "d_await", "f_await"]),
        ("Request size (kB)", "request-size", ["rareq-sz", "wareq-sz", "dareq-sz"]),
        ("Average queue size", "avg-queue-size", ["aqu-sz"]),
        ("Utilization percentage", "utilization-percent", ["util"]),
        ("Merge rate", "merge-rate", ["rrqm/s", "wrqm/s", "drqm/s"]),
        ("Merge percentage", "merge-percent", ["rrqm", "wrqm", "drqm"]),
    ]

    def __init__(self, output_dir: str, args: list[str] = []):
        super().__init__(dir=output_dir, args=args)
        cmds = ["iostat", "-dx", "-o", "JSON", "-y"]
        cmds.extend(get_block_devices())
        cmds.extend(args)
        cmds.append(str(self.INTERVAL))
        self.name = "iostat"
        self.stat = BackgroundProcess(
            name=self.name,
            ofile_name=f"{self.name}.json",
            cmds=cmds,
            out_dir=output_dir,
            requires=["iostat"],
            pin=self.get_cpus(),
        )

    def start(self):
        self.stat.start()

    def stop(self):
        self.stat.stop()

    def collect_results(self) -> str:
        mean_output = ""
        data = str_to_json(self.stat.read_output())
        if data is not None:
            dataframe = self.__transform_json_to_df(data)
            if not dataframe.empty and self.DEVICE_COL in dataframe.columns:
                mean_output = self.__get_metric_means(dataframe)
                # filter out inactive devices for the plots
                dataframe = self.__remove_inactive_devices(dataframe)
                self.__dump_plots(dataframe)
        return mean_output

    @classmethod
    def __transform_json_to_df(cls, data: dict[str, Any]) -> DataFrame:
        rows = []
        statistics = cls.__get_statistics(data)
        for sample_idx, stat in enumerate(statistics):
            for disk in stat.get("disk", []):
                row = dict(disk)
                row[cls.TIME_COL] = sample_idx * cls.INTERVAL
                rows.append(row)
        return pd.DataFrame(rows)

    def __get_metric_means(self, df: DataFrame) -> str:
        output = ""
        metric_cols = self.__get_numeric_columns(df)
        # group by device name, and calculate means
        means_by_device = df.groupby(self.DEVICE_COL)[metric_cols].mean(numeric_only=True)
        # iterate and for each device dump key_value names
        for device, row in means_by_device.iterrows():
            device_name = self.__sanitize_name(str(device))
            for metric, value in row.items():
                key = f"{self.name}_{device_name}_{self.__sanitize_name(metric)}"
                output += f"{key}={value};"

        return output

    def __dump_plots(self, df: DataFrame):
        for plot_title, plot_name, metrics in self.PLOT_SETS:
            # only consider present columns
            columns = [metric for metric in metrics if metric in df.columns]
            if len(columns) > 0:
                self.__dump_plot(df, plot_title, columns, plot_name)

    def __dump_plot(self, df: DataFrame, plot_title: str, columns: list[str], plot_name: str):
        plot_df = df[[self.TIME_COL, self.DEVICE_COL] + columns].copy()
        melted = plot_df.melt(
            id_vars=[self.TIME_COL, self.DEVICE_COL],
            value_vars=columns,
            var_name="metric",
            value_name="value",
        )
        melted["series"] = melted[self.DEVICE_COL].astype(str) + " " + melted["metric"]
        cfg = PlotConfig(
            x=self.TIME_COL,
            title=plot_title,
            x_lbl="Seconds Elapsed",
            y="value",
            hue="series",
            hue_lbl="Device/metric",
            type=PlotType.MEAN,
        )
        PlotChart.plot(
            df=melted, plot=cfg, out_fig_name=os.path.join(self.dir, f"{self.name}-{plot_name}")
        )

    @classmethod
    def __remove_inactive_devices(cls, df: DataFrame) -> DataFrame:
        """
        Removes devices that were never active during the run.
        """
        # check which metrics exist in the data frame, and keep those columns
        activity_metrics = [
            metric
            for metric in ["r/s", "w/s", "d/s", "f/s", "rkB/s", "wkB/s", "dkB/s", "util", "aqu-sz"]
            if metric in df.columns
        ]
        if len(activity_metrics) > 0:
            # Row-wise activity check: sum selected metrics and mark rows whose total activity > 0
            active_rows = df[activity_metrics].abs().sum(axis=1) > 0
            # Extract the set of devices associated with active rows
            active_devices = df.loc[active_rows, cls.DEVICE_COL].unique()
            if len(active_devices) > 0:
                # keep those devices that has been active at least once.
                return df[df[cls.DEVICE_COL].isin(active_devices)]

        return df

    @classmethod
    def __get_numeric_columns(cls, df: DataFrame) -> list[str]:
        return [
            col
            for col in df.columns
            if col not in [cls.DEVICE_COL, cls.TIME_COL] and pd.api.types.is_numeric_dtype(df[col])
        ]

    @staticmethod
    def __sanitize_name(name: str) -> str:
        return re.sub(r"[^0-9A-Za-z]+", "_", name).strip("_")

    @staticmethod
    def __get_statistics(data: dict[str, Any]) -> list[dict[str, Any]]:
        try:
            return data["sysstat"]["hosts"][0]["statistics"]
        except (KeyError, IndexError, TypeError):
            bm_log("iostat JSON does not contain sysstat.hosts[0].statistics", LogType.ERROR)
            return []
