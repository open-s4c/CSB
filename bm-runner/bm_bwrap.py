# Copyright (C) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# SPDX-License-Identifier: MIT

import os
import resource
import subprocess
import sys

from bm_executer import Executer, ExecutionUnit
from bm_utils import resolve_path, stop_process
from config.application import Application
from config.benchmark import ExecutionType
from config.container import ContainersConfig
from utils.logger import bm_log, LogType


def preexec_process():
    os.setpgrp()
    fd_soft, fd_hard = resource.getrlimit(resource.RLIMIT_NOFILE)
    resource.setrlimit(resource.RLIMIT_NOFILE, (fd_hard, fd_hard))


class Bubblewrap(ExecutionUnit):
    def __init__(self, idx, home_dir, record_data_dir, core_set, app: Application):
        super().__init__(idx=idx, home_dir=home_dir, app=app, type=ExecutionType.BWRAP)
        self.record_data_dir = record_data_dir
        self.core_set = core_set
        self.process = None

    def get_results_dir(self) -> str:
        # Inside bwrap, CSB project dir is mounted at /home.
        return str(resolve_path(self.record_data_dir, use_in_container=True))

    def _bwrap_args(self) -> list[str]:
        host_home = os.path.abspath(self.home_dir)

        args = [
            "bwrap",
            # Namespace isolation.
            "--unshare-pid",
            "--unshare-ipc",
            "--unshare-uts",
            "--unshare-cgroup",
            # Keep network shared by default to match current native/container behavior
            # unless CSB later adds explicit networking policy.
            "--share-net",
            # Basic runtime filesystems.
            "--proc",
            "/proc",
            "--dev",
            "/dev",
            "--tmpfs",
            "/tmp",
            # Host resources needed by CSB benchmarks.
            "--bind",
            host_home,
            "/home",
            "--ro-bind",
            "/usr",
            "/usr",
            "--ro-bind",
            "/bin",
            "/bin",
            "--ro-bind",
            "/lib",
            "/lib",
            "--ro-bind",
            "/lib64",
            "/lib64",
            # These are writable/readable in current Docker container mode.
            # Keep them conservative at first; loosen only if specific benchmarks need it.
            "--ro-bind",
            "/etc",
            "/etc",
            "--chdir",
            "/home",
        ]

        # Some distros do not have /lib64.
        args = self._filter_existing_bind_sources(args)

        return args

    @staticmethod
    def _filter_existing_bind_sources(args: list[str]) -> list[str]:
        filtered = []
        i = 0
        bind_flags = {
            "--bind",
            "--ro-bind",
            "--dev-bind",
            "--dev-bind-try",
            "--ro-bind-try",
            "--bind-try",
        }

        while i < len(args):
            item = args[i]
            if item in bind_flags and i + 2 < len(args):
                src = args[i + 1]
                dst = args[i + 2]
                if item.endswith("-try") or os.path.exists(src):
                    filtered.extend([item, src, dst])
                i += 3
            else:
                filtered.append(item)
                i += 1

        return filtered

    def exec(self, command: str) -> bool:
        change_dir = ""
        if self.app.cd:
            assert self.app.path is not None, "path is not set while change directory is requested!"
            change_dir = f"cd {self.app.path} && "

        # CSB command is a shell string already, so run bash inside bwrap.
        inner_command = (
            f"{self.CMD_WHILE_NOT_START} "
            f"{change_dir}"
            f"taskset --cpu-list {self.core_set} {command}"
        )

        commands = self._bwrap_args() + ["/bin/bash", "-lc", inner_command]

        with open(resolve_path(self.err_file), "w") as err_file:
            with open(resolve_path(self.output_file), "w") as outfile:
                self.process = subprocess.Popen(
                    commands,
                    stdout=outfile,
                    stderr=err_file,
                    preexec_fn=preexec_process,
                    cwd=self.home_dir,
                )

        bm_log(f"launched bwrap {self.name} with {commands}")
        return True

    def wait(self):
        if self.process is None:
            return

        self.process.wait()
        if self.process.returncode != 0:
            bm_log(
                f"bwrap process {self.name} failed/crashed with return code {self.process.returncode}",
                LogType.FATAL,
            )
            sys.exit(1)

    def stop(self):
        if self.process is not None:
            stop_process(self.process.pid)


class Bubblewraps(Executer):
    def __init__(
        self,
        config: ContainersConfig,
        apps: list[Application],
        home_dir,
        count,
        record_data_dir,
    ):
        super().__init__(home_dir=home_dir, results_dir=record_data_dir)
        assert len(apps) == count, "[BUG] Application list length must be equal to count"

        for i in range(count):
            core_set = config.get_cpus(i)
            bwrap = Bubblewrap(
                idx=i,
                home_dir=home_dir,
                core_set=core_set,
                record_data_dir=record_data_dir,
                app=apps[i],
            )
            self.add_exec_unit(bwrap)
