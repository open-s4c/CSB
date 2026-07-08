#!/usr/bin/env python3
# Copyright (C) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# SPDX-License-Identifier: MIT
import os
import argparse
import pandas as pd
from utils.logger import bm_log, LogType
from visual.plotchart import PlotChart
from bm_visualize import dump_graphs_to_doc
from config.plot import PlotConfig, PlotType
from bm_utils import write_to_file, get_all_files_by_ext, read_data_frame_from_csv
from datetime import datetime
from visual.report import Report

################################################################################################
# Input: directories
# Output: directory with many files
#   - <benchmark-name>.txt - a text table comparing the benchmark throughput on different kernels
#   - <benchmark-name>*.png - a png plot comparing the benchmark on different kernels
#   - results.html - all comparison plots in one file
#   - results.csv  - all results in one csv
#   - results.md   - all results in one md
#
# Process: The script looks for available CSV recursively in all given directories
#       the CSVs are expected to comply with the default output CSV of CSB
#       The subject of comparison is the kernel
################################################################################################


BENCHMARK_FIELD = "algo_name"
THROUGHPUT_FIELD = "throughput_min"
COUNT_FIELD = "container_cnt"
SUCCESS_FIELD = "univ_succ_percent"
COMPARISON_FIELD = "kernel"
EXEC_ENV_FIELD = "execution_type"
MEASUREMENT_FIELD = "throughput_avg"  # auto-computed
LINEARITY_FIELD = "linearity"  # auto-computed


COMPARISON_FILED_PRETTY_NAME = {
    "Linux localhost 6.6.0-138.0.0.119.oe2403sp3.x86_64  1 SMP Wed Feb  4 22:31:12 CST 2026 x86_64 x86_64 x86_64 GNU/Linux": "AMD 6.6.0",
    "Linux k920b 6.6.0ext4noprof  9 SMP Thu Apr  9 15:34:24 CEST 2026 aarch64 aarch64 aarch64 GNU/Linux": "k920b 6.6.0",
    "Linux localhost 7.1.0-rc1+  12 SMP PREEMPT_DYNAMIC Wed Apr 29 03:25:53 CST 2026 x86_64 x86_64 x86_64 GNU/Linux": "AMD 7.1.0-rc1",
    "ExecutionType.CONTAINER": "container",
    "ExecutionType.NATIVE": "native",
    "container_cnt": "#Instances",
}

group_by_fields: list[str] = [
    BENCHMARK_FIELD,
    EXEC_ENV_FIELD,
    "hostname",
    COMPARISON_FIELD,
    "nb_threads",
]


# this is a global variable that will be overwritten
output_dir_name = "analysis-results"

#########################################


def to_pretty_name(ugly: str) -> str:
    return COMPARISON_FILED_PRETTY_NAME.get(ugly, ugly)


def create_output_dir() -> str:
    now = datetime.now()
    timestamp = now.strftime("%Y-%m-%d-%H-%M-%S")  # Format: YYYYMMDD_HHMMSS
    dir = f"analysis-results-{timestamp}"
    os.makedirs(dir, exist_ok=True)
    return dir


def transform(file: str) -> list:
    """
    Processes a CSV file to compute per-run metrics.

    Steps:
    1. Reads the CSV into a DataFrame.
    2. Groups by `group_by_fields`.
    3. Aggregates throughput and success percent by mean per `COUNT_FIELD`.
    4. Computes linearity relative to the minimum count of containers.

    Parameters
    ----------
    file : str
        Path to the CSV file to process.

    Returns
    -------
    results : list of pd.DataFrame
        Each element corresponds to a group defined by `group_by_fields`,
        containing:
            - COUNT_FIELD column (e.g., container count)
            - throughput_avg (mean throughput)
            - success_avg (mean success %)
            - linearity relative to minimum container count
    """
    results = []
    # read the csv file as a dataframe
    df = read_data_frame_from_csv(file)
    if df is None:
        # there has been an error
        return []

    grouped = df.groupby(group_by_fields)
    for key_group, g in grouped:
        per_run = (
            g.groupby(COUNT_FIELD)
            .agg(throughput_avg=(THROUGHPUT_FIELD, "mean"), success_avg=(SUCCESS_FIELD, "mean"))
            .reset_index()
        )  # container_cnt becomes a column

        key_group = key_group if isinstance(key_group, tuple) else (key_group,)
        for idx, col in enumerate(group_by_fields):
            per_run[col] = key_group[idx]

        min_container = per_run[COUNT_FIELD].min()
        assert "throughput_avg" == MEASUREMENT_FIELD

        # baseline is the throughput associated with the minimum count of containers (usually 1)
        baseline = per_run.loc[per_run[COUNT_FIELD] == min_container, MEASUREMENT_FIELD].iloc[0]
        # calc linearity
        per_run[LINEARITY_FIELD] = per_run[MEASUREMENT_FIELD] / baseline
        results.append(per_run)
    return results


def generate_patch_measurement(df, bm_name, env=""):
    subjects = df[COMPARISON_FIELD].unique()

    # Pivot table
    table = df.pivot_table(
        index=COUNT_FIELD, columns=COMPARISON_FIELD, values=MEASUREMENT_FIELD
    ).reset_index()

    # Flatten MultiIndex if it exists (common with pivot_table)
    if isinstance(table.columns, pd.MultiIndex):
        table.columns = [col[1] if col[1] else col[0] for col in table.columns]

    # Inject improvement column between first two pretty-named columns
    if len(subjects) >= 2:
        # First, compute improvements vs the first column (numeric!)
        first = subjects[0]
        first_numeric = pd.to_numeric(table[first], errors="coerce")
        for col in subjects[1:]:
            second = col
            second_numeric = pd.to_numeric(table[second], errors="coerce")
            table[f"Improvement. ({second}) %"] = (
                (second_numeric - first_numeric) / first_numeric * 100
            ).round(2)

    table.rename(columns={COUNT_FIELD: to_pretty_name(COUNT_FIELD)}, inplace=True)
    # Convert to Markdown and write
    md_table = table.to_markdown(index=False, tablefmt="grid")
    md_info = f"- {bm_name}\n"
    md_info += f"- Execution environment: {env}\n"

    write_to_file(dir=output_dir_name, fname=f"{bm_name}-{env}.txt", content=md_info + md_table)


def generate_comparison_plot(
    df, bm_name, y="linearity", y_lbl="Linearity", plot_type=PlotType.NORMAL, env=""
):
    plot_cfg = PlotConfig(
        hue=COMPARISON_FIELD,
        y=y,
        y_lbl=y_lbl,
        x=COUNT_FIELD,
        x_lbl="#Executions Units",
        title=f"{bm_name}({env})",
        type=plot_type,
    )
    PlotChart.plot(plot=plot_cfg, df=df, out_fig_name=f"{output_dir_name}/{bm_name}-{env}-{y_lbl}")


def add_to_linearity_summary(df, bm, env, idx, tolerance=0.1) -> str:
    summary = f"## {idx}. {bm} ({env})\n"
    summary += f"|{COMPARISON_FIELD} | Linear | Drops at|\n"
    summary += "|--- |--- |---|\n"

    for kernel, g in df.groupby(COMPARISON_FIELD):
        g_sorted = g.sort_values(COUNT_FIELD)
        drops = g_sorted[g_sorted[LINEARITY_FIELD] < 1 - tolerance]
        summary += f"|{to_pretty_name(kernel)}|"

        if drops.empty:
            summary += "✔️|-|\n"
        else:
            first_drop_cnt = drops[COUNT_FIELD].iloc[0]
            first_drop_val = drops[LINEARITY_FIELD].iloc[0]
            summary += f"❌|{first_drop_cnt} (linearity={first_drop_val:.2f})|\n"

    return summary


def generate_comparison_reports(df):
    benchmarks = df[BENCHMARK_FIELD].unique()
    envs = df[EXEC_ENV_FIELD].unique()
    benchmarks.sort()
    df[COMPARISON_FIELD] = df[COMPARISON_FIELD].map(lambda x: f"{to_pretty_name(x)}")
    Linearity_md = "# Linearity Summary\n"
    idx = 1
    # get all results mapped to a certain benchmark
    for bm in benchmarks:
        for env in envs:
            bm_df = df[(df[BENCHMARK_FIELD] == bm) & (df[EXEC_ENV_FIELD] == env)]
            nice_env = to_pretty_name(env)
            generate_patch_measurement(bm_df, bm, env=nice_env)
            generate_comparison_plot(
                bm_df, bm, y=MEASUREMENT_FIELD, y_lbl="Throughput Average", env=nice_env
            )
            generate_comparison_plot(
                bm_df,
                bm,
                y="success_avg",
                y_lbl="Success Average (%)",
                env=nice_env,
                plot_type=PlotType.SUCCESS_PERCENT,
            )
            generate_comparison_plot(bm_df, bm, env=nice_env)
            Linearity_md += add_to_linearity_summary(
                bm_df, bm, env=nice_env, idx=idx, tolerance=0.1
            )
        idx += 1

    write_to_file(Linearity_md, "linearity.md", output_dir_name)


def get_all_csvs(dirs: list[str]):
    all_files = []
    for dir in dirs:
        if not os.path.isdir(dir):
            bm_log(f"Skipping {dir}. It is not a valid directory.", LogType.ERROR)
            continue
        files = get_all_files_by_ext(dir=dir, extension=".csv")
        bm_log(f"Found {len(files)} CSV in {dir}.")
        all_files.extend(files)
    return all_files


if __name__ == "__main__":
    """ """
    parser = argparse.ArgumentParser(description="Process one or more folders.")
    parser.add_argument(
        "folders", nargs="+", help="Path(s) to folder(s) to process"  # One or more arguments
    )

    args = parser.parse_args()
    output_dir_name = create_output_dir()

    # process
    files = get_all_csvs(args.folders)
    bm_log(f"Processing {len(files)} files", LogType.INFO)
    all = []
    for f in files:
        res = transform(f)
        all.extend(res)

    final_df = pd.concat(all, ignore_index=True)
    md_table = final_df.to_markdown(index=False)

    per_bm = generate_comparison_reports(final_df)
    csv = final_df.to_csv(index=False)

    write_to_file(dir=output_dir_name, fname="results.md", content=md_table)
    write_to_file(dir=output_dir_name, fname="results.csv", content=csv)

    report = Report("Analysis Report")
    dump_graphs_to_doc(output_dir_name, report, split=3)
    report.save(os.path.join(output_dir_name, "results.html"))
    bm_log(f"Results written to {output_dir_name}", LogType.INFO)
