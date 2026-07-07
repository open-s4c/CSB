# Copyright (C) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# SPDX-License-Identifier: MIT

from benchkit.benchmark import (
    Benchmark,
    PathType,
    RecordResult,
)
import sys
from typing import Optional, Dict, Any, List
import bm_utils
from bm_utils import get_cgroups_version
from config.benchmark import ExecutionType
import bm_config
from bm_executer import Executer
from utils.logger import bm_log, LogType
from utils.bm_builder import Builder
from benchkit.shell.shell import shell_out


class ScalabilityBenchmark(Benchmark):
    common_info: dict = {}

    def __init__(
        self,
        csb_dir: PathType,
    ):
        super().__init__(
            command_wrappers=[],
            command_attachments=[],
            shared_libs=[],
            post_run_hooks=[],
            pre_run_hooks=[],
        )
        self.csb_dir = csb_dir
        self.multi_app = False
        assert bm_config.g_config is not None
        self.container_cfg = bm_config.g_config.get_container_config()
        self.__set_common_info()

    def __set_common_info(self):
        kernel_info = shell_out(
            "uname -a",
            ignore_any_error_code=True,
            print_file_shell_cmd=False,
        )
        kernel_info = kernel_info.strip()
        self.common_info["kernel"] = kernel_info.replace("#", " ")
        self.common_info["Allowed CPUs"] = self.container_cfg.get_cpu_pool()
        self.common_info["cgroup"] = get_cgroups_version()

    def prebuild_bench(self, **_kwargs):
        b = Builder()
        b.build()
        bm_utils.save_sys_config(self._base_data_dir)
        bm_utils.save_docker_daemon_config(self._base_data_dir)
        # copy the configuration file and map it to the same name
        # as the csv.
        assert bm_config.g_config is not None
        bm_config.g_config.copy(f"{self._base_data_dir}.json")

    def build_bench(self, **_kwargs):
        pass

    def clean_bench(self):
        pass

    def single_run(  # ty: ignore[invalid-method-override]
        self,
        benchmark_duration_seconds: int,
        nb_threads: int,
        execution_type: ExecutionType,
        noise: int,
        initial_size: int,
        container_cnt: int,
        cpu_order: Optional[str] = None,
        master_thread_core: Optional[int] = None,
        record_data_dir: Optional[str] = None,
        **kwargs,
    ):
        assert bm_config.g_config is not None
        applications = bm_config.g_config.get_apps()
        self.multi_app = len(applications) > 1
        if self.multi_app:
            # Determine if the multi-apps are really different,
            # or if they only differ in the params
            different_apps = any(
                app.name != applications[0].name or app.path != applications[0].path
                for app in applications
            )
            if container_cnt < len(applications) and different_apps:
                bm_log(
                    f"Minimum number of containers must be greater or equal to the number of applications({len(applications)}). Adjust the `container_list` config and try again!",
                    LogType.FATAL,
                )
                sys.exit(1)
            bm_log(
                f"Your benchmark will run {len(applications)} apps, multi_app is enabled",
                LogType.INFO,
            )

        port_start = self.container_cfg.port
        # assign an app per container, this is relevant when there are multiple apps
        apps = [applications[i % len(applications)] for i in range(container_cnt)]
        executer = Executer(
            config=self.container_cfg,
            count=container_cnt,
            home_dir=self.csb_dir,
            apps=apps,
            results_dir=record_data_dir,
            type=execution_type,
        )

        executer.exec_all(
            threads=nb_threads,
            duration=benchmark_duration_seconds,
            noise=noise,
            initial_size=initial_size,
            port_start=port_start,
        )
        output = executer.collect_results()
        return output

    def parse_output_to_results(  # ty: ignore[invalid-method-override]
        self,
        command_output: str,
        build_variables: Dict[str, Any],
        run_variables: Dict[str, Any],
        record_data_dir: PathType,
        **_kwargs,
    ) -> RecordResult | List[RecordResult]:
        output = command_output.strip()
        lines = output.splitlines()
        dicts = []
        # transform the output from each line into a dictionary
        for output in lines:
            if output.strip() == "":
                continue
            if output.endswith(";"):
                output = output[:-1]
            splitted_output = output.split(";")
            result_dict = {v[0]: v[1] for v in [x.split("=", maxsplit=1) for x in splitted_output]}
            result_dict.update(self.common_info)
            dicts.append(result_dict)

        if self.multi_app:
            return bm_utils.dict_intersect(
                dicts=dicts, save_dir=record_data_dir, header_dict=run_variables
            )
        else:
            return dicts

    @staticmethod
    def get_build_var_names():
        return []

    @staticmethod
    def get_run_var_names():
        return [
            "benchmark_duration_seconds",
            "nb_threads",
            "noise",
            "initial_size",
            "cpu_order",
            "master_thread_core",
            "container_cnt",
            "execution_type",
        ]

    @staticmethod
    def get_tilt_var_names():
        return []

    @property
    def bench_src_path(self):
        return self.csb_dir
