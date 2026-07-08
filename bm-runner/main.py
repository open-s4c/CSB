# Copyright (C) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# SPDX-License-Identifier: MIT

import argparse
import pathlib
import sys
from pathlib import Path
import bm_visualize
from benchmark import ScalabilityBenchmark
from benchkit.campaign import CampaignCartesianProduct, CampaignSuite
from typing import Iterable, Optional, Dict, Any
import bm_config
from bm_config import CampaignConfig
from config.benchmark import ExecutionType
import traceback
from bm_utils import remove_files_by_ext
from utils.logger import bm_log, LogType
from config.env_config import EnvUniversalConfig, UniversalConfig
from utils.bm_builder import Builder
from bm_utils import is_process_running, kill_all
import os


def csbCampaign(
    name: str = "CSB",
    nb_runs: int = 3,
    benchmark_duration_seconds: int = 5,
    nb_threads: Iterable[int] = (1,),
    noise: Iterable[int] = (0,),
    execution_type: Iterable[ExecutionType] = (ExecutionType.CONTAINER,),
    container_cnt: Iterable[int] = (1,),
    initial_size: Iterable[int] = (0,),
    debug: bool = False,
    gdb: bool = False,
    enable_data_dir: bool = False,
    continuing: bool = False,
    constants: Optional[Dict[str, Any]] = None,
    pretty: Optional[Dict[str, str]] = None,
) -> CampaignCartesianProduct:
    variables = {
        "nb_threads": nb_threads,
        "noise": noise,
        "initial_size": initial_size,
        "container_cnt": container_cnt,
        "execution_type": execution_type,
    }

    pretty_dict = None
    if pretty is not None:
        pretty_dict = {"lock": pretty}

    return CampaignCartesianProduct(
        name=name,
        benchmark=ScalabilityBenchmark(
            csb_dir=Builder.get_project_dir(),
        ),
        nb_runs=nb_runs,
        variables=variables,
        constants=constants,
        debug=debug,
        gdb=gdb,
        enable_data_dir=enable_data_dir,
        continuing=continuing,
        benchmark_duration_seconds=benchmark_duration_seconds,
        pretty=pretty_dict,
        results_dir=os.path.join(
            "../results", EnvUniversalConfig.get(UniversalConfig.CSB_RESULTS_GROUP) or ""
        ),
    )


###########################################################################
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Container Scalability Benchmark")
    parser.add_argument(
        "--replot",
        help="Rebuild plots instead of running the benchmark.",
        action="store_true",
    )
    parser.add_argument("--title", help="The Benchmark title.")
    parser.add_argument(
        "--config",
        help="Path to JSON config file of the benchmark.",
        type=pathlib.Path,
        required=True,
    )
    (args, dir_arg) = parser.parse_known_args()

    # As CSB requires to be at bm-runner dir to run, ensure that all
    # patches are converted into absolute path.
    if args.config:
        args.config = os.path.realpath(os.path.expanduser(args.config))
    if dir_arg:
        for i, d in enumerate(dir_arg):
            dir_arg[i] = os.path.realpath(os.path.expanduser(d)).removesuffix(".csv")

    # Ensure that bm-runner will use bm-runner/ directory
    os.chdir(os.path.realpath(os.path.dirname(__file__)))

    arg_continue = args.replot
    arg_title = args.title if args.title else os.path.basename(args.config).removesuffix(".json")
    arg_config = args.config

    # Parse configuration file
    try:
        bm_config.g_config = CampaignConfig(arg_config)
    except Exception as e:
        bm_log(
            f"Exception {type(e).__name__} occurred while loading {arg_config}: {e}", LogType.FATAL
        )
        traceback.print_exc()
        sys.exit(1)

    # get json file name without extension and path
    benchmark_name = Path(arg_config).stem

    # Campaign Parameters
    assert bm_config.g_config is not None
    container_cfg = bm_config.g_config.get_container_config()
    benchmark_config = bm_config.g_config.get_benchmark_cfg()
    threads = benchmark_config.threads

    # Create campaign
    campaign = csbCampaign(
        name=benchmark_name,
        benchmark_duration_seconds=benchmark_config.duration,
        container_cnt=container_cfg.get_container_cnt_list(),
        nb_threads=threads,
        execution_type=list(benchmark_config.exec_env.keys()),
        noise=benchmark_config.noise,
        initial_size=benchmark_config.initial_size,
        nb_runs=benchmark_config.repeat,
        continuing=arg_continue,
        enable_data_dir=True,
    )

    try:
        campaign_suite = CampaignSuite(campaigns=[campaign])
        if not arg_continue:
            campaign_suite.print_durations()
            campaign_suite.run_suite()
            results_dir = campaign.base_data_dir()
        else:
            results_dir = dir_arg[0]
            remove_files_by_ext(results_dir, ["png", "pdf"])
            bm_log(
                f"re-visualizing results on {results_dir}, old plots will be removed.", LogType.INFO
            )

        # generate an html with the results
        if results_dir is not None:
            bm_visualize.visualize_in_html(
                Path(results_dir), arg_title, bm_config.g_config.get_plots()
            )
        else:
            bm_log("results_dir/base_data_dir is None, cannot visualize results.", LogType.FATAL)
            sys.exit(1)
    finally:
        # This is only a fallback. Can only happen if the user did ctrl+c twice
        # interrupting the proper cleanup process.
        if is_process_running(name="perf"):
            bm_log("Perf is running and is going to be forcefully killed", LogType.WARNING)
            kill_all("perf")
