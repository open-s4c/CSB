# Copyright (C) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# SPDX-License-Identifier: MIT

### Reference: https://docker-py.readthedocs.io/en/stable/containers.html
import docker
import docker.errors
import os
import time
import sys
from benchkit.shell.shell import shell_out
from bm_exec_unit import ExecutionUnit
import bm_utils
from textwrap import indent
from typing import Optional
from config.application import Application
from config.nics import ContainerNicConfig
from config.benchmark import ExecutionType
from utils.logger import bm_log, LogType
from bm_utils import resolve_path


class Container(ExecutionUnit):
    def __init__(
        self,
        idx,
        image,
        home_dir,
        core_set,
        record_data_dir,
        app: Application,
        port: Optional[int] = None,
        nic: Optional[ContainerNicConfig] = None,
    ):
        super().__init__(idx=idx, type=ExecutionType.CONTAINER, home_dir=home_dir, app=app)
        self.client = docker.from_env()  # Initialize Docker client
        self.image = image
        self.core_set = core_set
        self.record_data_dir = record_data_dir
        self.port = port + self.idx if port else None
        self.nic = nic

    def get_results_dir(self) -> str:
        return str(resolve_path(self.record_data_dir, use_in_container=True))

    def __log_status(self, container):
        exit_code = container.attrs["State"].get("ExitCode")
        logs = container.logs().decode(errors="replace").strip()

        msg = f"Container {self.name}\n"
        msg += f"  Status      : {container.status}"

        if exit_code:
            msg += f"\n  Exit code   : {exit_code}"

        if logs:
            msg += f"\n  Logs:\n{indent(logs, '    ')}"

        bm_log(msg)

    def __wait_status(self, container, timeout):
        #
        # Wait up to timeout for one of those status: run/exit/dead
        # Status like created, restarting, removing and paused are ignored.
        #
        for _ in range(0, timeout * 10):
            container.reload()
            if container.status in ("running", "exited", "dead"):
                break
            # 100 milliseconds
            time.sleep(0.1)

    def wait(self, timeout=None):
        container = self.client.containers.get(self.name)
        bm_log(f"Waiting for Container: {self.name} to stop")
        result = container.wait(timeout=timeout)
        exit_code = result["StatusCode"]
        if exit_code != 0:
            try:
                logs = container.logs(stdout=True, stderr=True, timestamps=True, stream=False)
                logs_str = logs.decode("utf-8", errors="replace")
                bm_log(
                    f"Container: {self.name} has failed/or crashed with exit code {exit_code}.\n\n{logs_str}",
                    LogType.FATAL,
                )
            except Exception:
                bm_log(
                    f"Container: {self.name} has failed/or crashed with exit code {exit_code}",
                    LogType.FATAL,
                )
            sys.exit(1)

    def stop(self):
        bm_log(f"Stopping Container {self.name}")
        try:
            container = self.client.containers.get(self.name)
            container.stop()
            container.remove()
            # Remove network namespace as well
            if self.nic:
                shell_out(
                    f"sudo ip netns del {self.name}",
                    ignore_any_error_code=True,
                    print_file_shell_cmd=False,
                )
            self.__log_status(container)
        except docker.errors.NotFound:
            pass  # Container does not exist, nothing to do

    def add_nic(self, container):
        assert self.nic is not None
        # find the PID of the initial task of a container.
        pid = docker.APIClient().inspect_container(container.id)["State"]["Pid"]
        netcfg = self.nic
        smp_irq_affinity = (
            netcfg.core_affinity_offset
            if netcfg.core_affinity_offset is not None
            else self.core_set
        )
        # Configure the NIC
        shell_out(
            f"sudo ../scripts/add-nic-to-container.sh {netcfg.nic} {smp_irq_affinity} {pid} {self.name} {netcfg.ip} {netcfg.netmask}",
            print_file_shell_cmd=False,
        )

    def _host_home_dir(self):
        # Use home_dir on its canonical form
        home_dir = os.path.abspath(self.home_dir)

        if not os.path.exists("/.dockerenv"):
            return home_dir

        #
        # CSB is inside a docker container.
        #
        # Volume binds works like mount: when a volume is bound, any existing
        # contents on it will be hidden. The new content will be whatever the
        # host has.
        #
        # When running inside a docker container, we can't simply map the
        # entire home directory, as this will simply replace whatever content
        # it was already there by the ones from the host, which may be empty.
        # What we need, instead, is to bind the volume where we want writes
        # to be replicated within multiple containers, e.g. what is inside
        # BUILTIN_APP_DIR.
        #

        try:
            container = self.client.containers.get(os.uname().nodename)
        except Exception as e:
            bm_log(f"Unable to determine CSB container: {e}", LogType.ERROR)
            return None

        for mount in container.attrs.get("Mounts", []):
            dest = mount.get("Destination")
            source = mount.get("Source")
            if not source or not dest:
                continue

            bm_log(f"volume bind: host: {source} -> to: {dest}")
            if home_dir == dest:
                bm_log(f"Running CSB with volume bind: host: '{source}' to: {dest}")
                return source

        bm_log(
            f"CSB container doesn't map '{home_dir}'. Can't create sub-containers",
            LogType.ERROR,
        )
        return None

    def __start(self, commands):
        self.stop()

        host_home_dir = self._host_home_dir()

        volumes = {
            host_home_dir: {"bind": "/home", "mode": "rw"},
            "/usr": {"bind": "/usr", "mode": "rw"},
            "/mnt": {"bind": "/mnt", "mode": "rw"},
            "/lib/modules": {"bind": "/lib/modules", "mode": "rw"},
            "/etc": {"bind": "/etc", "mode": "rw"},
        }

        bm_log(f"Starting Container: {self.name}")
        try:
            ports = {f"{self.port}/tcp": ("0.0.0.0", self.port)} if self.port else None
            container = self.client.containers.run(
                image=self.image,
                command=["bash", "-c", commands],
                name=self.name,
                cpuset_cpus=self.core_set,
                volumes=volumes,
                privileged=True,  # privileged mode
                detach=True,  # detached mode
                working_dir="/home",
                ports=ports,
            )

            timeout = 20
            self.__wait_status(container, timeout)
            self.__log_status(container)

            if container.status != "running":
                bm_log(
                    f"Container {self.name} did not reach 'running' status in {timeout}s.",
                    LogType.ERROR,
                )

            bm_utils.save_container_config(self.record_data_dir, self.name)

            if self.nic:
                self.add_nic(container)

            bm_log(
                f"Container {self.name} is created, will run on {self.idx} => {self.port}, and will run on cores={self.core_set} and waiting for start signal"
            )
        except docker.errors.APIError as e:
            bm_log(f"Could not start container {self.name}: {str(e)}", LogType.ERROR)
            return False

        return True

    def exec(self, command):
        if self.app.cd:
            assert self.app.path is not None, "path is not set while change directory is requested!"
            command = f"cd {self.app.path} && {command}"
        commands = f"{self.CMD_WHILE_NOT_START} {command} > {resolve_path(self.output_file, use_in_container=True)} 2> {resolve_path(self.err_file, use_in_container=True)}"  # same as self.output_file outside container.
        return self.__start(commands)
