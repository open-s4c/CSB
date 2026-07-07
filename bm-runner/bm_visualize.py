# Copyright (C) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# SPDX-License-Identifier: MIT

import os
import datetime
import glob
from dominate import document
from dominate.tags import style, table, tr, td, div, img, h1, h2, a, iframe
import pandas as pd
from pandas import DataFrame
import base64
import statistics
import math
from benchkit.utils.dir import parentdir
from config.plot import PlotConfig
from config.plot import PlotType
from pathlib import Path
import re
from utils.logger import bm_log, LogType
from visual.plotchart import PlotChart
from monitors.bpftrace import BpfTrace


# TODO: refactor histogram building not to use global vars
# TODO: document functions
###########################################################################
def _add_css_style(doc: document):
    doc.add(
        style(
            """table {
                width: 100%;
                background-color: #FFFFFF;
                border-collapse: collapse;
                border-width: 2px;
                border-color: #7ea8f8;
                border-style: solid;
                color: #000000;
            }
            td,  th {
                border-width: 2px;
                border-color: #7ea8f8;
                border-style: solid;
                padding: 5px;
            }
            thead {
                background-color: #7ea8f8;
            }
            h1, h2 {
                text-align: center;
                font-color: blue;
            }
            .png_title {
                font-size: 14px;
                font-style: italic;
            }
            """
        )
    )


###########################################################################
def embed_img(path) -> div:
    data_uri = base64.b64encode(open(path, "rb").read()).decode("utf-8")
    img_tag = f"data:image/png;base64,{data_uri}"
    return div(img(src=img_tag))


def embed_svg(path) -> div:
    with open(path, "r") as file:
        svg_content = file.read()
    # extract height from svg content
    height = re.search(r'height="([^"]+)"', svg_content)
    h = height.group(1) if height else "1200"
    # Note that we put each svg into an iframe to avoid all types of conflicts
    # on IDs, styles, global variable names etc.
    # The content of iframe will be rendered as a separate html document
    return div(iframe(srcdoc=svg_content, width="100%", height=f"{h}px"))


###########################################################################
def get_common_fields(df: DataFrame) -> list[str]:
    return [col for col in df.columns if df[col].nunique() == 1]


###########################################################################
def add_info_tbl(df, doc: document, result_file: str):
    info_points = get_common_fields(df)
    tbl = table()
    r = tr()
    r.add(td("Results file name:"))
    r.add(td(result_file))
    tbl.add(r)
    for info in info_points:
        value = df[info].unique()
        r = tr()
        r.add(td(info))
        if len(value) == 1:
            r.add(td(value[0]))
        else:
            vals = ",".join(str(v) for v in value)
            if not isinstance(value[0], str):
                vals += f", mean = {statistics.mean(value)}"
            r.add(td(vals))
        tbl.add(r)
    doc.add(tbl)


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


###########################################################
# TODO: do we need to pass it as a param?
bucket_avg = []


def gen_row(smr, threads, i):
    # todo find real value instead of i+1
    return [smr, threads, bucket_avg[i]]


def log_scale(cnt):
    if cnt == 0:
        return 0
    else:
        return int(math.log2(cnt) + 1)


def gen_rows_from_histogram(smr, threads, histogram):
    # split the column value into an array
    # map bucket i to the number of elements of the bucket
    buckets = histogram.split(",")
    return [
        # add the row log_scale(int(count)] times
        # to not use log_scale just use count directly
        [gen_row(smr, threads, i)] * log_scale(int(count))
        for i, count in enumerate(buckets)
    ]


def implicit_add_columns(trans_df, subdf, histo, x_col, gp_name):
    res_l = list(
        map(
            gen_rows_from_histogram,
            subdf[gp_name],
            subdf[x_col],
            subdf[histo],
        )
    )
    res = [item for sublist in res_l for sublist_2 in sublist for item in sublist_2]
    o_df = pd.DataFrame(res)
    trans_df[[gp_name, x_col, "latency"]] = o_df[[0, 1, 2]]


###########################################################
def create_histogram_plot(df, plot: PlotConfig, dir) -> str:
    col_prefix = plot.y
    histo = f"{col_prefix}_histogram"
    subdf = df[[plot.x, plot.hue, histo]].copy()

    ############################################################
    cols = range(1, 61)  # TODO: align with C
    bucket_min = 0
    bucket_max = 99
    for i in cols:
        bucket_avg.append((bucket_max + bucket_min) / 2)
        bucket_max, bucket_min = (
            bucket_max + int((bucket_max - bucket_min + 1) * 1.1),
            bucket_max + 1,
        )

    ############################################################
    # Transformation
    trans_df = pd.DataFrame()
    implicit_add_columns(trans_df, subdf, histo, plot.x, plot.hue)
    ############################################################
    plot.y = "latency"  # TODO configure
    return PlotChart.plot(plot=plot, df=trans_df, out_fig_name=f"{dir}/{histo}_boxplot")


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
        case PlotType.HISTOGRAM:
            return create_histogram_plot(df=df, plot=plot, dir=dir)
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
def dump_graphs_to_doc(dir, doc: document, num_plot_in_row=2):
    # find all generated plots and embed them into the HTML document
    png = glob.glob(os.path.join(dir, "**", "*.png"), recursive=True)
    svg = glob.glob(os.path.join(dir, "**", "*.svg"), recursive=True)
    graphs = png + svg
    graphs.sort()
    tbl = table()
    for i, graph in enumerate(graphs):
        if graph.endswith(".svg"):
            img_div = embed_svg(graph)
        else:
            img_div = embed_img(graph)
        if i % num_plot_in_row == 0:
            line = tr()
            tbl.add(line)
        clickable_path = os.path.relpath(graph, "./results")
        line.add(
            td(
                img_div,
                # add a link to the image file
                div().add(a(clickable_path, href=clickable_path, _class="png_title")),
            )
        )
    # append the plots/graphs table to the given document
    doc.add(tbl)


###########################################################################
def split_data_frame(df: DataFrame) -> dict:
    frames = {}
    noises = df["noise"].unique()
    threads = df["nb_threads"].unique()
    for n in noises:
        for t in threads:
            key = f"n={n}-t={t}"
            frames[key] = df[(df["nb_threads"] == t) & (df["noise"] == n)]
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
    NUM_PLOTS_PER_ROW = 1  # TODO: make configurable.
    doc = document()
    _add_css_style(doc)
    doc.add(h1(f"Title: {title}"))
    doc.add(h2(f"Datetime: {datetime.datetime.now().strftime('%d.%m.%Y %H:%M:%S.%f')}"))
    hostname = ""
    # load data frame
    result_file = f"{output_dir}.csv"
    data_frame = pd.read_csv(
        result_file, sep=";", comment="#", engine="python", on_bad_lines="error"
    )
    hostname = data_frame["hostname"].unique()
    # we split the data-frame into multiple data frames to help with visualization
    data_frames = split_data_frame(data_frame)
    # For each data frame we'll generate the related graphs
    # and print related information
    for key, df in data_frames.items():
        add_info_tbl(df, doc, result_file)
        create_plots(df, plots, output_dir, info=key)
        # dump graphs to HTML document
        dump_graphs_to_doc(output_dir, doc, NUM_PLOTS_PER_ROW)

    output_file_name = os.path.join(parentdir(output_dir), f"{output_dir}.html")
    doc.title = f"Results of: {hostname[0]}({title})"
    with open(output_file_name, "w") as f:
        f.write(doc.render())
    bm_log(
        f"visualized results can be found in {output_file_name} with {title}",
        LogType.INFO,
    )
