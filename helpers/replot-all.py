#!/usr/bin/env python3
# Copyright (C) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# SPDX-License-Identifier: MIT
"""
Replot all csv files from a directory, if the campaign name matches a
currently-existing JSON config file.
"""

import argparse
import os
import sys
import subprocess

from glob import iglob

SRC_DIR = os.path.realpath(os.path.dirname(__file__) + "/..")
VENV_PATH = os.path.join(SRC_DIR, "venv")
BM_RUNNER_DIR = os.path.join(SRC_DIR, "bm-runner")


def read_csv_header(filepath: str) -> str:
    """
    Get campaign name from CSV file.
    """

    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                if line.startswith("# benchmark_campaign_name:"):
                    return line.split(":", 1)[1].strip()
    except Exception as e:
        print(f"Warning: Could not read metadata from {filepath}: {e}")

    return None


def main():
    """Main code"""
    parser = argparse.ArgumentParser(description="Re-generate all graphs from CSV files.")
    parser.add_argument(
        "csv_dirs",
        nargs="*",
        default=["./results"],
        help="Directories that contain CSV files (default = %(default)s).",
    )
    parser.add_argument("-d", "--debug", action="store_true", help="Enable debug.")
    parser.add_argument(
        "--config-root",
        default="./config",
        help="Root directory with JSON config files (default = %(default)s).",
    )
    args = parser.parse_args()

    config_root = os.path.abspath(args.config_root)

    if not os.path.isdir(config_root):
        sys.exit(f"Config root {config_root} does not exist.")

    # set env to run bm-runner inside a Python virtual environment
    env = os.environ.copy()

    bin_dir = os.path.join(VENV_PATH, "bin")

    if not os.path.isfile(os.path.join(bin_dir, "activate")):
        sys.exit(f"Venv {VENV_PATH} not found.")

    env["PATH"] = bin_dir + ":" + env["PATH"]
    env["VIRTUAL_ENV"] = VENV_PATH
    if "PYTHONHOME" in env:
        del env["PYTHONHOME"]

    print(f"Using venv at {VENV_PATH}")

    # Set required env variables for CSB to run
    env["CSB_NO_BUILD_BENCH"] = "ON"

    # Get a list of CSV files
    csv = {}
    for d in args.csv_dirs:
        for fname in iglob(os.path.join(d, "**/*.csv"), recursive=True):
            campaign = read_csv_header(fname)

            if campaign not in csv:
                csv[campaign] = []

            csv[campaign].append(fname)

    if not csv:
        sys.exit("No CSV files to replot.")

    # Get a list of JSON config files
    json = {}
    for json_fname in iglob(os.path.join(config_root, "**/*.json"), recursive=True):
        campaign = os.path.basename(json_fname).removesuffix(".json")
        if campaign in json:
            print(f"Warning: duplicated campaign name: {campaign}")
        json[campaign] = json_fname

    # Run --replot for each CSV file inside each campaign
    for campaign in csv:
        if campaign not in json:
            print(f"Warning: ignoring {campaign} as couldn't find a JSON config file")
            continue

        json_fname = json[campaign]
        for csv_fname in csv[campaign]:
            csv_fname = os.path.abspath(csv_fname).removesuffix(".csv")

            print(f"Replotting {csv_fname}")
            cmd = [
                "python3",
                "main.py",
                "--title",
                campaign,
                "--config",
                json_fname,
                "--replot",
                csv_fname,
            ]

            print(" ".join(cmd))
            subprocess.run(cmd, check=False, cwd=BM_RUNNER_DIR, env=env)


if __name__ == "__main__":
    main()
