# Copyright (C) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# SPDX-License-Identifier: MIT

import os
import glob
import pandas as pd
from pandas import DataFrame
import statistics
from benchkit.utils.dir import parentdir
from config.plot import PlotConfig
from config.plot import PlotType
from pathlib import Path
from utils.logger import bm_log, LogType
from visual.plotchart import PlotChart
from monitors.bpftrace import BpfTrace
from visual.report import Report
from bm_utils import read_data_frame_from_csv


###########################################################################
def add_info_tbl(df, report: Report, result_file: str):
    info_points = [col for col in df.columns if df[col].nunique() == 1]
    data = {}
    data["Results file name:"] = result_file
    for info in info_points:
        value = df[info].unique()
        if len(value) == 1:
            data[info] = value[0]
        else:
            vals = ",".join(str(v) for v in value)
            if not isinstance(value[0], str):
                vals += f", mean = {statistics.mean(value)}"
            data[info] = vals
    report.add_table(data)


###########################################################################
def create_success_rate_plot(org_df, config: PlotConfig, dir) -> str:
    prefix = config.y
    count_col = f"{prefix}_count"
    succ_col = f"{prefix}_succ_count"
    succ_percent = f"{prefix}_succ_percent"
    df = org_df.copy()
    # calculate success rate of operations
    df[succ_percent] = list(
        map(
            lambda succ, total: (succ * 100) // total if total else 0,
            df[succ_col],
            df[count_col],
        )
    )
    # overwrite
    config.y = succ_percent
    return PlotChart.plot(plot=config, df=df, out_fig_name=f"{dir}/{prefix}_succ_percent")


###########################################################################
def create_min_max_avg_plot(org_df, config: PlotConfig, dir: str) -> str:
    """
    Treats `config.y` as a prefix and look for min, max, and avg values
    It assumes such columns exist in the dataframe <config.y>min,
    <config.y>max and, optionally, <config.y>percentile or <config.y>avg

    Args:
        org_df: dataframe
        config (PlotConfig): plot configuration.
        dir (str): where to store the plot.
    """
    prefix = config.y
    df = org_df.copy()
    pc = PlotChart(config)
    min_col = None
    avg_col = None
    max_col = None
    percentile = None
    metric = None

    def min_max_errorbar(vals):
        """
        Don't use statistics for error bar, as the number of points on
        graphs using this plot are not enough
        """
        return (vals.min(), vals.max())

    for c in df.columns:
        if c.startswith(prefix):
            if c.endswith("avg"):
                avg_col = c
            if c.endswith("percentile"):
                percentile = c

            if c.endswith("min"):
                min_col = c

            if c.endswith("max"):
                max_col = c

    if not min_col or not max_col:
        return ""

    # If both percentile and average are present, use percentile, as it
    # provides an expected value for the metric on most cases.

    if percentile:
        metric = percentile
    elif avg_col:
        metric = avg_col

    if metric:
        tmp_config = PlotConfig(**config)
        tmp_config.y = metric

        pc.add(
            tmp_config,
            df[[config.x, config.hue, metric]],
            estimator="mean",
        )

        # Mathplotlib will always calculate its own average line, calculated
        # using multiple Y samples for each X value. When the average metric
        # is calculated by the benchmark, we need to replace it by the data
        # calculated at by the tool, as otherwise the calculus will be wrong.
        # So, make the melt data average line invisible.
        linewidth = 0
        legend = False
    else:
        # Plot estimated average
        linewidth = 1
        legend = True

    transformed_data = pd.melt(
        df[[config.x, config.hue, min_col, max_col]],
        id_vars=[config.hue, config.x],
        value_vars=[min_col, max_col],
        value_name=config.y,
        var_name="metric",
    )

    pc.add(
        config,
        transformed_data,
        linewidth=linewidth,
        legend=legend,
        estimator="mean",
        # Mathplotlib doesn't really show max/min. Instead, it tries to
        # filter out too high or too low values by using either standard
        # deviation or percentile calculus. This requires multiple samples
        # of max/min values, which we may not have.
        # So, instead, just use max/min at the error bar without using any
        # statistics.
        errorbar=min_max_errorbar,
    )

    return pc.save(out_fig_name=f"{dir}/{config.y}_min_avg_max")


###########################################################################
def create_plot(df, plot: PlotConfig, dir, info: str) -> str:
    match plot.type:
        case PlotType.NORMAL:
            fig_name = f"{dir}/{plot.x}_vs_{plot.y}_{info}"
            return PlotChart.plot(plot=plot, df=df, out_fig_name=fig_name)
        case PlotType.MIN_MAX_AVG:
            return create_min_max_avg_plot(org_df=df, config=plot, dir=dir)
        case PlotType.SUCCESS_PERCENT:
            return create_success_rate_plot(org_df=df, config=plot, dir=dir)
        case PlotType.LINEARITY:
            return create_linearity_plot(df=df, plot=plot, dir=dir)
        case PlotType.MEAN:
            return create_mean_plot(df=df, plot=plot, dir=dir)
        case PlotType.BPFTRACE_HIST:
            return BpfTrace.dump_hist_data_heat_map(df=df, plot=plot, output_dir=dir)
        case _:
            bm_log(f"unsupported plot type: {plot.type} skipped!", LogType.WARNING)
            return ""


###########################################################################
def create_plots(df, plots: list[PlotConfig], dir, info: str):
    for plot in plots:
        try:
            create_plot(df, plot, dir, info)
        except Exception as e:
            bm_log(
                f"Failed to generate plot {plot.title}. The following error occurred {e}.",
                LogType.ERROR,
            )


###########################################################################
def dump_graphs_to_doc(dir, report: Report, split=1):
    # find all generated plots and embed them into the HTML document
    dir = os.path.realpath(dir)
    png = glob.glob(os.path.join(dir, "**", "*.png"), recursive=True)
    svg = glob.glob(os.path.join(dir, "**", "*.svg"), recursive=True)
    plots = png + svg
    plots.sort()
    plots = [plots[i : i + split] for i in range(0, len(plots), split)]
    report.embed_plots(plots)


###########################################################################
def split_data_frame(df: DataFrame) -> dict:
    frames = {}
    threads = df["nb_threads"].unique()
    for t in threads:
        key = f"t={t}"
        frames[key] = df[df["nb_threads"] == t]
    return frames


def create_mean_plot(df: DataFrame, plot: PlotConfig, dir):
    return PlotChart.plot(
        plot=plot,
        df=df,
        out_fig_name=f"{dir}/{plot.y}_mean",
        add_points=True,
        estimator="mean",
    )


def create_linearity_plot(df: DataFrame, plot: PlotConfig, dir):
    count_col: str = plot.x  # e.g. container count
    subject_col: str = plot.y  # e.g. throughput
    group_col: str = plot.hue  # e.g. execution env native/container

    assert pd.api.types.is_integer_dtype(df[count_col]), f"{count_col} column must be integer dtype"
    assert pd.api.types.is_numeric_dtype(df[subject_col]), f"{subject_col} must be a number"

    envs = df[group_col].unique()
    counts = df[count_col].unique()

    cols = [group_col, count_col, "linearity"]
    lin_df = pd.DataFrame(columns=cols)  # ty: ignore[invalid-argument-type]
    for e in envs:
        for c in counts:
            # calculate the avg/mean for the given count and group
            n_avg = df.loc[(df[count_col] == c) & (df[group_col] == e), subject_col].mean()
            # get the values mapped to one execution unit
            one_eu = df.loc[(df[count_col] == 1) & (df[group_col] == e), subject_col].values
            # deduce the performance of one container/execution unit
            if len(one_eu) == 0:
                bm_log(
                    "Cannot generate linearity plot. Make sure to add 1 to the container count in `container_list`",
                    LogType.ERROR,
                )
                return
            one_avg = one_eu[0]
            if one_avg == 0.0:
                bm_log(
                    "Cannot generate linearity plot. Result for 1 container is 0.0, avoiding division by zero.",
                    LogType.ERROR,
                )
                return
            # calculate linearity
            lin = n_avg / one_avg
            # add a row to the data frame
            lin_df.loc[len(lin_df)] = {group_col: e, count_col: c, "linearity": lin}

    plot.y = "linearity"
    plot.y_lbl = "Linearity"
    return PlotChart.plot(plot=plot, df=lin_df, out_fig_name=f"{dir}/linearity")


###########################################################################
# puts all generated graphs in one
def visualize_in_html(output_dir: Path, title: str, plots: list[PlotConfig]):
    """
    Gets and prints the spreadsheet's header columns

    Parameters
    ----------
    out_dir : str
        results folder
    title: str
        HTML/Benchmark title.
    plots: list[PlotConfig]
        list of PlotConfig objects describing the plots to be generated
    Returns
    -------
    """

    # number of graphs displayed in the same row
    hostname = ""
    # load data frame
    result_file = f"{output_dir}.csv"
    data_frame = read_data_frame_from_csv(result_file)
    if data_frame is None:
        return
    hostname = data_frame["hostname"].unique()[0]
    report = Report(title=f"{hostname}-{title}")
    # we split the data-frame into multiple data frames to help with visualization
    data_frames = split_data_frame(data_frame)
    # For each data frame we'll generate the related graphs
    # and print related information
    for key, df in data_frames.items():
        add_info_tbl(df, report, result_file)
        create_plots(df, plots, output_dir, info=key)
        # dump graphs to HTML document
        dump_graphs_to_doc(output_dir, report)

    output_file_name = os.path.join(parentdir(output_dir), f"{output_dir}.html")
    report.save(output_file_name)
    bm_log(
        f"visualized results can be found in {output_file_name} with {title}",
        LogType.INFO,
    )
