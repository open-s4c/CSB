# Copyright (C) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# SPDX-License-Identifier: MIT

import os
import pandas as pd
from jsonpath_ng import parse
from monitors.monitor import Monitor
from utils.logger import bm_log, LogType
from utils.process import BackgroundProcess
from bm_utils import str_to_json
from visual.plotchart import PlotChart
from config.plot import PlotConfig


class SystemStats(Monitor):
    INTERVAL = 1  # collect every 1 second

    def __init__(self, output_dir: str, args: list[str] = ["-A"]):
        super().__init__(dir=output_dir, args=args)
        cmds = ["mpstat", "-o", "JSON"]
        cmds.extend(args)
        cmds.append(f"{self.INTERVAL}")
        self.stat = BackgroundProcess(
            name="mpstat",
            ofile_name="mpstat.json",
            cmds=cmds,
            out_dir=output_dir,
            requires=["mpstat"],
            pin=self.get_cpus(),
        )

    def start(self):
        self.stat.start()

    def stop(self):
        self.stat.stop()

    def transform(self, df: pd.DataFrame) -> str:
        """
        Flattens and transforms the table into a key=val; form
        so that it can be appended to the results file(s)
        """
        results: str = ""
        for idx, row in df.iterrows():
            cpu = row["cpu"]
            for col, val in row.items():
                results += f"{col}_c{cpu}={val};"
        return results

    def query(self, data, query_str):
        query = parse(query_str)
        matches = [match.value for match in query.find(data)]
        return matches

    def avg_results_p_cpu(self, matches) -> str:
        df = pd.DataFrame(matches).groupby("cpu").mean().reset_index()
        return self.transform(df)

    def get_sum_interrupts(self, data):
        matches = self.query(data, "$.sysstat.hosts[*].statistics[*].sum-interrupts[*]")
        return self.avg_results_p_cpu(matches)

    def get_cpu_load(self, data):
        matches = self.query(data, "$.sysstat.hosts[*].statistics[*].cpu-load[*]")
        return self.avg_results_p_cpu(matches)

    def get_soft_interrupts(self, data):
        matches = self.query(data, "$.sysstat.hosts[*].statistics[*].soft-interrupts[*]")
        rows = []
        # we want to flatten
        # from   {"cpu": "1", "intr": [ {"name": "HI", "value": 0.00}, ... ] }
        # to "cpu": "1", "intr": "HI", value: "0.00"
        for cpu in matches:
            for intr in cpu["intr"]:
                rows.append({"cpu": cpu["cpu"], "intr": intr["name"], "value": intr["value"]})
        df = pd.DataFrame(rows)
        # now we want the interrupt name to become column and we aggregate the values per cpu by mean
        # after this we should have
        # cpu, HI, ... all interrupts as col, and their avg(values)
        # 1, 0.00, ...
        df = df.pivot_table(
            index="cpu", columns="intr", values="value", aggfunc="mean"
        ).reset_index()
        return self.transform(df)

    def collect_results(self) -> str:
        if self.stat:
            data = str_to_json(self.stat.read_output())
            if data:
                self.dump_plot(data)
                results = self.get_cpu_load(data)
                results += self.get_sum_interrupts(data)
                results += self.get_soft_interrupts(data)
                return results
        else:
            bm_log(
                "Could not read output of sys stats, `self.stat` is not initialized!", LogType.ERROR
            )
        return ""

    # TODO: decide if the generate should stay here, and if it should be part of the final html
    def dump_plot(self, data):
        """
        Creates a plot for CPU usage over time.
        """
        stats = []
        for stat in data["sysstat"]["hosts"][0]["statistics"]:
            for cpu_load in stat["cpu-load"]:
                stats.append(
                    {
                        "time": stat["timestamp"],
                        "usr": cpu_load["usr"],
                        "sys": cpu_load["sys"],
                        "iowait": cpu_load["iowait"],
                        "idle": cpu_load["idle"],
                        "softirq": cpu_load["soft"],
                        "irq": cpu_load["irq"],
                        "cpu": cpu_load["cpu"],
                    }
                )
        cpucores = set(map(lambda e: e["cpu"], stats))
        for core in cpucores:
            filtered_stats = list(filter(lambda e: e["cpu"] == core, stats))
            df = pd.DataFrame(filtered_stats)
            # convert to datetime column
            try:
                df["time"] = pd.to_datetime(df["time"], format="%I:%M:%S %p")
            except ValueError:
                bm_log(
                    "mpstat does not follow format yyyy:mm:dd am/pm. Make sure that en_US.UTF-8 locale package is installed (on openEuler, install package glibc-all-languages).",
                    LogType.ERROR,
                )
                return

            # calc seconds elapsed
            df["time"] = (df["time"] - df["time"].iloc[0]).dt.total_seconds()
            # If some offsets are negative due to wraparound at midnight, add number of seconds in
            # a day to make the number positive:
            df["time"] = df["time"] + (df["time"] < 0) * (24 * 60 * 60)
            cpu_cols = ["usr", "sys", "iowait", "idle", "softirq", "irq"]
            plot_df = df.reset_index().melt(
                id_vars=["time"],
                value_vars=cpu_cols,
                var_name="metric",
                value_name="value",
            )
            plt_cfg = PlotConfig(
                x="time",
                x_lbl="Seconds Elapsed",
                y="value",
                y_lbl="CPU utilization (%)",
                hue="metric",
                shape="lineplot",
                title=f"CPU Usage Over Time - core {core}",
            )
            filename = os.path.join(self.dir, f"mpstat-core-{core}")
            PlotChart.plot(plt_cfg, plot_df, filename)
