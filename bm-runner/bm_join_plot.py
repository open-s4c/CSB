#!/usr/bin/env python3
# Copyright (C) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Read benchmark CSVs, read linearity‑plot definitions from JSON
config files under a given root, generate a PNG for each
`execution_type` that compares the different kernel versions,
and produce a small HTML gallery that shows every image.

The output file names now follow the pattern:
    <app_name>-<execution_type>-<NNN>.png
where NNN is a zero‑padded counter per (app, exec_type) pair.

For example, if one wants to compare results on two directories
named node10 and node60:
    bm-runner/bm_join_plot.py node10 node60

The first version o this tool was LLM-generated on Ollama on a 16GB DRNA4
VRAM GPU using queries on: gpt-oss, gemma4, nemotron-cascade-2, qwen3.5,
qwen3.6.

Current version was manually adjusted to ensure that the code is working
as expected.
"""

import argparse
import json
import os
import re
import shlex
import sys

from glob import iglob
from typing import Dict, List, Optional

from bm_utils import read_data_frame_from_csv, construct_bm_name
from bm_visualize import create_plot
from visual.report import Report
from config.plot import PlotConfig
from utils.logger import bm_log, LogType

import matplotlib
import pandas as pd
import seaborn as sns

matplotlib.use("Agg")  # no GUI, pure file output
CSS_STYLE = """
    body {
        font-family:
        system-ui, -apple-system, sans-serif;
        margin: 30px;
        background: #fafafa;
        color: #333;
    }
    h1 {
        border-bottom: 2px solid #eee;
        padding-bottom: 10px;
    }
    img {
        max-width: 920px;
        height: auto;
        display: block;
        margin: 10px auto;
    }
"""


#
# Helper functions
#
def read_results_metadata(csv_file: str) -> dict:
    """
    Pull out kernel_version and campaign_name from CSV header.
    """
    header = {}
    re_header = re.compile(r"# ([\w\s]+):\s*(.*)")

    try:
        with open(csv_file, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                # Check if the header ended
                if not line.startswith("#"):
                    break

                match = re_header.match(line)
                if not match:
                    continue

                key = match.group(1).lower()
                value = match.group(2)
                if key == "kernel":
                    tokens = shlex.split(value)

                    if len(tokens) < 3:
                        continue

                    header["host"] = tokens[1]
                    header["kernel"] = tokens[2]
                else:
                    header[key] = value.strip()

    except Exception as e:
        print(f"Warning: Could not read metadata from {csv_file}: {e}")

    # Complement with data from cpu.txt if available
    fname = csv_file.removesuffix(".csv") + "/sys-config/cpu.txt"
    re_key_value = re.compile(r"([\w\s]+):\s*(.*)")

    try:
        with open(fname, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                match = re_key_value.match(line)
                if match:
                    key = match.group(1).lower()
                    header[key] = match.group(2).strip()

    except Exception as e:
        print(f"Warning: Could not read {fname}: {e}")

    return header


def get_csv_with_kernel_campaign(csv_file: str) -> Optional[pd.DataFrame]:
    """
    Read a single CSV,  adding two extra columns:
        kernel_version and campain
    both obtained from header comments.
    """

    df = read_data_frame_from_csv(csv_file)
    if df is None:
        return None

    header = read_results_metadata(csv_file)

    kernel = header.get("kernel")
    campaign = header.get("benchmark_campaign_name")

    machine = []

    host = header.get("host")
    if host:
        machine.append(host.split(".")[0])

    model = header.get("model name")
    if model:
        machine.append(model)

    arch = header.get("architecture")
    if arch:
        machine.append(f"({arch})")

    machine_name = " ".join(machine)

    if machine_name:
        df["machine"] = machine_name
    else:
        df["machine"] = ""

    if kernel:
        df["kernel_version"] = kernel

    if campaign:
        df["app"] = campaign
    else:
        df["app"] = os.path.splitext(os.path.basename(csv_file))[0]

    return df


def clear_string(text: str) -> str:
    """
    Cleanup a text, dropping special characters and replacing whitespaces.
    """
    text = re.sub(r"\s+", "_", text)
    text = re.sub(r"[^\w\-_.]", "", text)
    return text


def read_config(config_root: str) -> Dict[str, List[dict]]:
    """
    Read all config JSON files from CSB.
    """
    plots_by_app: Dict[str, List[dict]] = {}

    if not os.path.isdir(config_root):
        print(f"Warning: Config root {config_root} does not exist.")
        return plots_by_app

    for root, _, files in os.walk(config_root):
        for f in files:
            if not f.lower().endswith(".json"):
                continue

            json_path = os.path.join(root, f)
            try:
                with open(json_path, "r", encoding="utf-8") as ff:
                    data = json.load(ff)
            except Exception as e:
                print(f"Failed to load {json_path}: {e}")
                continue

            app = construct_bm_name(json_path)
            plots_by_app[app] = data.get("plots")

    return plots_by_app


def generate_html(
    structured_plots: Dict[str, Dict[str, Dict[str, Dict[str, List[str]]]]],
    out_dir: str,
) -> str:
    """Generate a clean, indented HTML gallery and write it to out_dir/index.html"""
    cols = ["NATIVE", "CONTAINER"]

    report = Report(title="Benchmark Comparison", css_style=CSS_STYLE, add_title_date=False)

    for machine, apps in structured_plots.items():
        s = f" on {machine}" if machine else ""

        report.add_chapter(f"Benchmark Comparison{s}")

        plots = []

        for app, base_type in apps.items():
            for title, types in base_type.items():
                others = []
                table_cols = {}

                for etype, item_cols in types.items():
                    matched = False
                    for col in cols:
                        if col.upper() in etype.upper():
                            table_cols[col] = item_cols
                            matched = True
                            break
                    if not matched:
                        others.append(etype)

                cur_plots = [""] * 2

                for pos, col in enumerate(cols):
                    for rel_path in table_cols.get(col, []):
                        if cur_plots[pos]:
                            bm_log(
                                f"Multiple values for {machine}/{app}/{title}/{etype} found!",
                                LogType.WARNING,
                            )
                            cur_plots.append(os.path.join(out_dir, rel_path))
                        else:
                            cur_plots[pos] = os.path.join(out_dir, rel_path)

                # Just in case, output other columns, if any
                for o_type in others:
                    for rel_path in types[o_type]:
                        cur_plots.append(os.path.join(out_dir, rel_path))

                plots.append(cur_plots)

        report.embed_plots(plots, show_path=False)

        report.add_line("")

    html_path = os.path.join(out_dir, "index.html")
    report.save(html_path)

    print(f"\nHTML with plots written to: {html_path}")
    return html_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate linearity plots from benchmark CSVs.")
    parser.add_argument("csv_dirs", nargs="+", help="Directories that contain CSV files.")
    parser.add_argument("-d", "--debug", action="store_true", help="Enable debug.")
    parser.add_argument(
        "--config-root",
        default="config",
        help="Root directory with JSON config files (default: %(default)s).",
    )
    parser.add_argument(
        "--output-dir",
        default="plots",
        help="Directory where PNGs and index.html will be written (default: %(default)s).",
    )
    args = parser.parse_args()

    config_root = os.path.abspath(args.config_root)
    out_dir = os.path.abspath(args.output_dir)
    os.makedirs(out_dir, exist_ok=True)

    # Collect CSV files
    csv = []
    for d in args.csv_dirs:
        for f in iglob(os.path.join(d, "**/*.csv"), recursive=True):
            new_csv = get_csv_with_kernel_campaign(f)
            if new_csv is not None:
                if args.debug:
                    print(f"Appending data from {f}")
                csv.append(new_csv)

    if not csv:
        sys.exit(f"No valid data loaded at {args.csv_dirs:}. Exiting.")

    df = pd.concat(csv, ignore_index=True)

    # Generate a list of kernels, apps and exec_types
    kernels = sorted(df["kernel_version"].dropna().unique())
    apps = df["app"].dropna().unique()
    exec_types = df["execution_type"].dropna().unique()

    # Generate a global palette to preserve same colors on all graphs
    global_palette = dict(zip(kernels, sns.color_palette("tab10", len(kernels))))

    # Load plots from JSON config
    plots_by_app = read_config(config_root)
    if not plots_by_app:
        sys.exit(f"No linearity plots found under {config_root}. Exiting.")

    # Filter by app using pandas boolean indexing (exactly as requested)
    structured_plots: Dict[str, Dict[str, Dict[str, Dict[str, List[str]]]]] = {}

    for machine in df["machine"].dropna().unique():
        structured_plots[machine] = {}

        filter_machine = df["machine"] == machine

        for app in apps:
            structured_plots[machine][app] = {}

            filter_app = df["app"] == app
            if app not in plots_by_app:
                bm_log(f"{app}: data empty or not found on plot", LogType.ERROR)
                continue

            if "execution_type" not in df:
                bm_log(f"{app}: can't find execution types", LogType.ERROR)
                continue

            if args.debug:
                print(f"Processing app: {app} ({len(exec_types)} execution types)")

            for etype in exec_types:

                filter_et = df["execution_type"] == etype

                etype_name = etype.removeprefix("ExecutionType.").lower()

                # Group dataframe per machine, app and exec_type
                df_filtered = df[filter_machine & filter_app & filter_et]

                if df_filtered.empty:
                    continue

                plot_defs = plots_by_app[app]

                host = machine.split(" ")[0]

                for plot_def in plot_defs:
                    title = plot_def["title"]

                    plot_def["hue"] = "kernel_version"
                    plot_def["hue_lbl"] = "Kernel"
                    plot_def["palette"] = global_palette

                    # As hue is non-numerical, barplot won't work
                    if plot_def["shape"] == "barplot":
                        plot_def["shape"] = "lineplot"

                    # Ensure that the type will do what we need
                    if "type" not in plot_def or plot_def["type"] == "normal":
                        plot_def["type"] = "mean"

                    plot = PlotConfig(**plot_def)
                    plot.title = f"{host}: {title} ({etype_name})"

                    if title not in structured_plots[machine][app]:
                        structured_plots[machine][app][title] = {}

                    if etype not in structured_plots[machine][app][title]:
                        structured_plots[machine][app][title][etype] = []

                    try:
                        out_path = create_plot(df=df_filtered, plot=plot, dir=out_dir, info=app)
                    except Exception as e:
                        bm_log(f"{app}, {etype}: {plot.title}: {repr(e)}", LogType.ERROR)
                        continue

                    if not out_path:
                        continue

                    if args.debug:
                        print(f"Plot '{plot.title}': {out_path}")

                    rel_path = os.path.relpath(out_path, out_dir)

                    structured_plots[machine][app][title][etype].append(rel_path)

    # Generate HTML gallery
    if structured_plots:
        generate_html(structured_plots, out_dir)

    if args.debug:
        print(f"\nAll plots written to: {out_dir}")


if __name__ == "__main__":
    main()
