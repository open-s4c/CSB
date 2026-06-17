# Copyright (C) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# SPDX-License-Identifier: MIT

import re
from pathlib import Path
from typing import Any

import pandas as pd
from pandas import DataFrame

from monitors.monitor import Monitor
from utils.logger import LogType, bm_log
from utils.process import BackgroundProcess
from bm_visualize import plot_chart, PlotConfig, PlotType
from bm_utils import str_to_json


class IoStat(Monitor):
    INTERVAL = 1
    DEVICE_COL = "disk_device"
    TIME_COL = "time"

    PLOTSETS = [
        ("I/O operations per second", "iostat-iops", ["r/s", "w/s", "d/s", "f/s"]),
        ("Throughput (kB/s)", "iostat-throughput", ["rkB/s", "wkB/s", "dkB/s"]),
        ("Await time (ms)", "iostat-await", ["r_await", "w_await", "d_await", "f_await"]),
        ("Request size (kB)", "iostat-request-size", ["rareq-sz", "wareq-sz", "dareq-sz"]),
        ("Average queue size", "iostat-queue", ["aqu-sz"]),
        ("Utilization percentage", "iostat-util", ["util"]),
        ("Merge rate", "iostat-merge-rate", ["rrqm/s", "wrqm/s", "drqm/s"]),
        ("Merge percentage", "iostat-merge-percent", ["rrqm", "wrqm", "drqm"]),
    ]

    def __init__(self, output_dir: str, args: list[str] = []):
        super().__init__(dir=output_dir, args=args)
        cmds = ["iostat", "-x", "-o", "JSON", "-y"]
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
        data = str_to_json(self.stat.read_output())
        if data is None:
            return ""
        dataframe = self.dataframe_from_json(data)
        self.dump_plots(dataframe, self.dir)
        return self.aggregate_results(dataframe)

    @classmethod
    def dataframe_from_json(cls, data: dict[str, Any]) -> DataFrame:
        rows = []
        statistics = cls._statistics(data)
        for sample_idx, stat in enumerate(statistics):
            for disk in stat.get("disk", []):
                row = dict(disk)
                row[cls.TIME_COL] = sample_idx * cls.INTERVAL
                rows.append(row)
        return pd.DataFrame(rows)

    @classmethod
    def aggregate_results(cls, df: DataFrame) -> str:
        if df.empty or cls.DEVICE_COL not in df:
            return ""

        results = []
        metric_cols = cls.metric_columns(df)
        for device, device_df in df.groupby(cls.DEVICE_COL):
            means = device_df[metric_cols].mean(numeric_only=True)
            device_name = cls.safe_name(str(device))
            for metric, value in means.items():
                results.append(f"iostat_{device_name}_{cls.safe_name(metric)}={value}")
        return ";".join(results) + (";" if results else "")

    @classmethod
    def dump_plots(cls, df: DataFrame, output_dir: Path):
        if df.empty or cls.DEVICE_COL not in df:
            return

        df = cls.active_devices(df)
        for title, fname, metrics in cls.PLOTSETS:
            present_metrics = [metric for metric in metrics if metric in df.columns]
            if not present_metrics:
                continue
            cls.dump_plot(df, title, present_metrics, output_dir / f"{fname}")

    @classmethod
    def dump_plot(cls, df: DataFrame, title: str, metrics: list[str], filename: Path):
        plot_df = df[[cls.TIME_COL, cls.DEVICE_COL] + metrics].copy()
        melted = plot_df.melt(
            id_vars=[cls.TIME_COL, cls.DEVICE_COL],
            value_vars=metrics,
            var_name="metric",
            value_name="value",
        )
        melted["series"] = melted[cls.DEVICE_COL].astype(str) + " " + melted["metric"]
        cfg = PlotConfig(
            x=cls.TIME_COL,
            title=title,
            x_lbl="Seconds Elapsed",
            y="value",
            hue="series",
            hue_lbl="Device/metric",
            type=PlotType.MEAN,
        )
        plot_chart(df=melted, plot=cfg, out_fig_name=filename)

    @classmethod
    def active_devices(cls, df: DataFrame) -> DataFrame:
        activity_metrics = [
            metric
            for metric in ["r/s", "w/s", "d/s", "f/s", "rkB/s", "wkB/s", "dkB/s", "util", "aqu-sz"]
            if metric in df.columns
        ]
        if not activity_metrics:
            return df

        active_rows = df[activity_metrics].abs().sum(axis=1) > 0
        active_devices = df.loc[active_rows, cls.DEVICE_COL].unique()
        if len(active_devices) == 0:
            return df
        return df[df[cls.DEVICE_COL].isin(active_devices)]

    @classmethod
    def metric_columns(cls, df: DataFrame) -> list[str]:
        return [
            col
            for col in df.columns
            if col not in [cls.DEVICE_COL, cls.TIME_COL] and pd.api.types.is_numeric_dtype(df[col])
        ]

    @staticmethod
    def safe_name(name: str) -> str:
        return re.sub(r"[^0-9A-Za-z]+", "_", name).strip("_")

    @staticmethod
    def _statistics(data: dict[str, Any]) -> list[dict[str, Any]]:
        try:
            return data["sysstat"]["hosts"][0]["statistics"]
        except (KeyError, IndexError, TypeError):
            bm_log("iostat JSON does not contain sysstat.hosts[0].statistics", LogType.ERROR)
            return []
