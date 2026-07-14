# Copyright (C) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# SPDX-License-Identifier: MIT

import sys
from typing import Optional
from config.adapter import Adapter
from pathlib import Path
from bm_utils import ensure_exists
from utils.logger import bm_log, LogType


class Application(dict):
    CONFIG_KEY: str = "applications"
    DISTRIBUTION_SUM = 1024
    BUILTIN_APP_DIR = "build/bench"

    def __init__(
        self,
        name: str,
        operations: list[int] = [],
        path: Optional[Path] = None,
        args: Optional[str] = None,
        adapter: Optional[Adapter] = None,
        cd: bool = False,
    ):
        """
        An application is either a builtin benchmark binary from the `bench` directory,
        or an external application/benchmark binary.
        This configuration defines an array of applications, each with their own setup.
        If this array has more than one application.
        each container will run an application from the array in a round robin fashion.
        Represented as a JSON array of objects.

        Parameters
        ----------
        name: str
            The name of the application/benchmark binary.
        path: Optional[Path]
            Specifies the relative path where the benchmark binary/script exists. This is
            relevant to running external benchmarks that do not exist system wide under e.g. in `/usr/bin`.
            Note that the path here should be relative to CSB (project) dir, which is mounted as
            `/home` dir in the containers. When running an external benchmark, place its parent folder under
            the project directory e.g. `CSB/bm-external/will-it-scale`, then specify `path` as
            `bm-external/will-it-scale`.
        operations: list[int]
            A list of integers representing the distribution of operations.
            The sum of all values in the list must be equal to 1024.
            Each index represents a specific operation as defined by the benchmark/application.
            This is only relevant for builtin benchmarks.
        args: Optional[str] = -t={threads} -n=0 -d={duration} -p={port}
            A string that represents the command line arguments of the application.
            It can contain place holders for dynamic values. Available place holders:
            are `{threads}`, `{duration}`, `{index}`, `{port}` and `{host_ip}`.
            They are replaced at runtime with the actual values: number of threads,
            duration of the benchmark in seconds, the index of the execution unit in the current benchmarking run, network port, and the host IP where CSB is running respectively.
            If any of the above is relevant for the external application they can be used in the args
            string. Otherwise they can be omitted.
        adapter: Optional[Adapter] = {}
            An adapter object.
            This is only relevant for external applications/benchmarks.
        cd: bool = false
            When set to `true`, it changes the current directory to the given `path`, and
            then runs the binary/script with the given `name`. When set to `false` and `path`
            is given, the binary is run from the project directory as `path/name`. Use this
            configuration with caution! This configuration is useful when running external
            benchmarks that require to be run from their own directory, because they use
            relative paths like unix bench.
        -
        """
        super().__init__(
            name=name, path=path, op_distributions=operations, args=args, adapter=adapter, cd=cd
        )
        self.name = name
        self.path = path
        self.operations = operations
        self.cd = cd
        # Set default framework arguments
        self.args = "-t={threads} -n=0 -d={duration} -p={port}" if args is None else args
        self.adapter = Adapter(**adapter) if adapter is not None else None
        if len(self.operations) > 0 and sum(self.operations) != self.DISTRIBUTION_SUM:
            bm_log(
                f"The operations distribution sum must be equal to {self.DISTRIBUTION_SUM}",
                LogType.FATAL,
            )
            sys.exit(1)
        if self.cd and self.path is None:
            self.cd = False
            bm_log(
                f"Ignoring `cd` in configuration of {name}. `path` must be set when `cd` is set to `true`",
                LogType.ERROR,
            )

    def __get_runnable_cmd(self, work_dir: Path) -> str:
        if self.path:
            fname = ensure_exists(name=self.name, dir=self.path)
            # if changing directory is required, the command
            # will be just the app name.
            fname = f"./{self.name}" if self.cd else fname
        else:
            # if path is None, then we are either running a builtin benchmark
            # or one that is available system wide
            fname = ensure_exists(name=self.name, dir=self.BUILTIN_APP_DIR)
        return f"{fname}"

    def get_cmd(
        self,
        plugins_cmds: str,
        threads: int,
        duration: int,
        port: int,
        index: int,
        work_dir: Path,
        n_units: int,
        homedir: str,
        res_dir: str,
        host_ip: str = "127.0.0.1",
    ) -> str:
        """
        Returns full command line for a single benchmark run.
        This command line is composed of:
        application's command with arguments; the distribution of operations; and plugins that run with the application.

        This step also formats the command line, using variables such as `homedir`.
        """
        cmd = self.__get_runnable_cmd(work_dir)
        ops = " ".join(f"-op{idx}={val}" for idx, val in enumerate(self.operations))
        args = self.args

        # NOTE: Filter removes any empty string
        cmd = " ".join(filter(None, [plugins_cmds, cmd, ops, args]))

        cmd = cmd.format(
            threads=threads,
            duration=duration,
            port=port,
            index=index,
            n_units=n_units,
            homedir=homedir,
            res_dir=res_dir,
            host_ip=host_ip,
        )
        bm_log(f"generated command: {cmd}")
        return cmd
