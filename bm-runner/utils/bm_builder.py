# Copyright (C) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# SPDX-License-Identifier: MIT

# This class is responsible of building builtin
# CSB targets/benchmarks

from benchkit.shell.shell import shell_out
import os
from utils.logger import bm_log, LogType
from config.env_config import EnvUniversalConfig, UniversalConfig
from pathlib import Path


class Builder:
    project_dir: Path
    build_dir: str = "build"
    CORES: int = 4
    required_targets: list[str] = ["server", "client", "redis-client"]

    def __init__(self):
        self.project_dir = Builder.get_project_dir()
        self.build_dir = os.path.join(self.project_dir, self.build_dir)

    @staticmethod
    def get_project_dir() -> Path:
        return Path(os.getcwd()).parent

    def __run_cmake_config(self):
        cmd = f"cmake -G Ninja -DCMAKE_BUILD_TYPE=Release -S{self.project_dir} -B{self.build_dir}"
        shell_out(cmd, output_is_log=False, print_file_shell_cmd=False)

    def __clean_build_dir(self):
        if EnvUniversalConfig.is_on(UniversalConfig.CSB_NO_CLEAN_BENCH):
            return
        shell_out(f"rm -rf {self.build_dir}/*", output_is_log=False, print_file_shell_cmd=False)

    def build(self):
        if EnvUniversalConfig.is_on(UniversalConfig.CSB_NO_BUILD_BENCH):
            # we still configure, for external apps to make
            # sure build dir is created
            self.__run_cmake_config()
            bm_log(
                "CSB_NO_BUILD_BENCH is set to true, skipping building all benchmarks.",
                LogType.WARNING,
            )
            return
        self.__clean_build_dir()
        self.__run_cmake_config()
        cmd = f"cmake --build {self.build_dir} -j {self.CORES}"
        shell_out(cmd, output_is_log=True, print_file_shell_cmd=False)

    def __build_target(self, target):
        cmd = f"cmake --build {self.build_dir} --target {target} -j {self.CORES}"
        shell_out(cmd, output_is_log=True, print_file_shell_cmd=False)

    def build_target(self, target):
        self.__clean_build_dir()
        self.__run_cmake_config()
        ts = self.required_targets.copy()
        ts.append(target)
        targets = " ".join(ts)
        self.__build_target(targets)

    def __get_targets(self) -> set[str]:
        self.__run_cmake_config()
        cmd = f"cmake --build {self.build_dir} --target help"
        output = shell_out(
            cmd, print_shell_cmd=False, print_output=False, print_file_shell_cmd=False
        )
        targets = set()
        try:
            # Example line:
            # mysql_min_mysql_brk_missing_0_0: phony
            lines = output.splitlines()
            for line in lines:
                s = line.split(":")
                if len(s) > 1 and s[1].strip() == "phony":
                    targets.add(s[0])
        except Exception as e:
            bm_log(f"Failed to parse list of targets from cmake. {e}", LogType.ERROR)
        return targets

    def target_exists(self, target: str) -> bool:
        targets = self.__get_targets()
        return target in targets
