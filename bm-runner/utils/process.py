# Copyright (C) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# SPDX-License-Identifier: MIT

import os
import signal
import subprocess
from utils.logger import bm_log, LogType
from typing import Optional
from bm_utils import ensure_exists
from bm_utils import stop_process


class BackgroundProcess:
    TIMEOUT_SEC = 5
    Env = {"LANG": "en_US.UTF-8", "LC_ALL": "en_US.UTF-8"}

    def __init__(
        self,
        name: str,
        out_dir: str,
        cmds: list[str],
        wdir: Optional[str] = None,
        ofile_name: Optional[str] = None,
        efile_name: Optional[str] = None,
        pin: Optional[list[int]] = None,
        requires: list[str] = [],
    ):
        """
        Launches the specified application, represented by `cmds`, in the background.

        Parameters
        ----------
        name: str
            The name of the process being launched, primarily used for logging purposes.
        out_dir: str
            The directory where the process's `stdout` and `stderr` should be saved.
        cmds: list[str]
            A list of commands, including the process name and its arguments, to launch the process.
        wdir: Optional[str]
            The working directory where the process will be executed. If not provided, `out_dir` will be used as the working directory.
        ofile_name: Optional[str]
            The name of the file to save `stdout` to. If not provided, a given `name` with a `.log` extension will be used.
        efile_name: Optional[str]
            The name of the file to save `stderr` to. If not provided, a given `name` with a `.err` extension will be used.
        pin: Optional[list[int]]
            Optional list of CPUs to assign to the process with taskset.
            If None, the process will not be assigned specific CPUs.
        requires: list[str]
            A list of required applications that must be available for the launch to succeed. Each application is checked for existence.
        """
        assert len(cmds) > 0, "expected at least the process name"
        self.name = name
        if efile_name is None:
            self.efile_name = os.path.join(out_dir, f"{self.name}.err")
        else:
            self.efile_name = os.path.join(out_dir, efile_name)

        if ofile_name is None:
            self.ofile_name = os.path.join(out_dir, f"{self.name}.log")
        else:
            self.ofile_name = os.path.join(out_dir, ofile_name)
        self.wdir = out_dir if wdir is None else wdir
        self.process: Optional[subprocess.Popen] = None
        self.ofile = None
        self.efile = None
        if pin is None:
            self.cmds = cmds
        else:
            cpus = ",".join([str(c) for c in pin])
            cmd_prefix = ["taskset", "--cpu-list", cpus]
            self.cmds = cmd_prefix + cmds

        # ensure process exist
        for tool in requires:
            ensure_exists(tool)

    def start(self):
        """
        Starts the process in the background.
        """
        assert self.process is None, "it seems, it has already been started!"
        self.ofile = open(self.ofile_name, "w")
        self.efile = open(self.efile_name, "w")
        self.process = subprocess.Popen(
            self.cmds,
            stdout=self.ofile,
            stderr=self.efile,
            env=self.Env,
            preexec_fn=os.setpgrp,
            cwd=self.wdir,
        )
        cmd_str = " ".join(self.cmds)
        bm_log(f"[{self.name}] started: {cmd_str}")

    def __close_file(self, file):
        try:
            if file:
                file.close()
        except Exception as e:
            bm_log(f"Failed to close file {e}", LogType.ERROR)

    def __terminate(self):
        if self.process is not None and self.process.poll() is None:
            self.process.terminate()
            self.process.wait()
            bm_log(f" {self.name} terminated with {self.process.returncode}")

    def force_stop(self):
        """
        Kills the process and whatever children the process spawned.
        """
        if self.process:
            bm_log(f"Killing {self.name}, with PID = {self.process.pid}")
            stop_process(self.process.pid)

    def is_alive(self) -> bool:
        """
        Returns true if the process is alive and running normally.
        """
        if self.process:
            rc = self.process.poll()
            if rc is None or rc == 0:
                return True
        bm_log(f"{self.name} is not alive!", LogType.ERROR)
        return False

    def wait_indefinitely(self):
        """
        Waits for the process to finish without timeout.
        This method can block for a long time and will not attempt to cancel or terminate the process.
        """
        if self.process is None:
            return
        bm_log(
            f"Waiting for {self.name} without timeout, with PID = {self.process.pid} to terminate"
        )
        self.process.wait()

    def stop(self, timeout=TIMEOUT_SEC) -> int:
        """
        Sends ctrl+c signal to the process if it is still running.
        On timeout the process will be terminated.
        """
        if self.process is None:
            return 0
        bm_log(f"[{self.name}] stopping, timeout given {timeout}s")
        self.process.send_signal(signal.SIGINT)
        try:
            self.process.wait(timeout)
            bm_log(f"[{self.name}] stopped with return code {self.process.returncode}")
        except subprocess.TimeoutExpired:
            bm_log(f"[{self.name}] timeout on exit!", LogType.ERROR)
            self.__terminate()
        finally:
            self.__terminate()
            self.__close_file(self.ofile)
            self.__close_file(self.efile)
        return self.process.returncode

    def read_output(self):
        """
        Returns the content of the `stdout` file.
        """
        try:
            with open(self.ofile_name, "r") as file:
                return file.read()
        except Exception as e:
            bm_log(f"Failed to read {self.ofile_name} {e}", LogType.ERROR)
            return ""

    @property
    def output_file_name(self):
        """
        Returns the full path of the output file name of the process.
        """
        return self.ofile_name

    @property
    def err_file_name(self):
        """
        Returns the full path of the error file name of the process.
        """
        return self.efile_name
