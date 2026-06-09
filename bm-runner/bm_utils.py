# Copyright (C) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# SPDX-License-Identifier: MIT

import os
import sys
import socket
from benchkit.shell.shell import shell_out
from benchkit.utils.dir import get_curdir
import psutil
import shutil
from typing import Optional
from pathlib import Path
import json
from utils.logger import bm_log, LogType
from benchkit.utils.types import PathType
from utils.bm_builder import Builder
import pandas as pd


def resolve_path(path: PathType, use_in_container: bool = False) -> PathType:
    """
    Returns the absolute path of the given path with respect to
    CSB root dir. The absolute path differs depending on
    use_in_container input.
    This function works under the assumption that CSB is mounted
    to /home inside the container.
    """
    csb_dir = Path(os.getcwd()).parent
    if Path(path).is_relative_to(csb_dir):
        path = Path(path).relative_to(csb_dir)
    homedir = "/home" if use_in_container else csb_dir
    new_path = os.path.join(homedir, path)
    return new_path


def check_data_directory(output_dir):
    if output_dir is None:
        bm_log(
            f"output directory: {output_dir}, does not exist. Recording of configuration is skipped.",
            LogType.WARNING,
        )
        return False
    return True


# saves all system configurations that
# might influence the performance of the benchmark
def save_sys_config(output_dir):
    if check_data_directory(output_dir):
        sys_config_dir = os.path.join(output_dir, "sys-config")
        script_path = "../scripts/get-system-info.sh"
        assert os.path.exists(output_dir), f"output dir {output_dir} does not exist!"
        if os.path.exists(script_path):
            shell_out(
                command=f"sudo {script_path} {sys_config_dir}",
                output_is_log=False,
                print_file_shell_cmd=False,
            )
            bm_log(f"system configuration saved in {sys_config_dir}.", LogType.INFO)
        else:
            bm_log(
                f"`get-system-info.sh` script does not exist in: {script_path}. system information will not be recorded.",
                LogType.ERROR,
            )


# saves all docker daemon configurations that
# might influence the performance of the benchmark
def save_docker_daemon_config(output_dir):
    if check_data_directory(output_dir):
        daemon_config_dir = os.path.join(output_dir, "docker-daemon-config")
        script_path = "../scripts/get-docker-daemon-info.sh"

        assert os.path.exists(output_dir), f"output dir {output_dir} does not exist!"
        if os.path.exists(script_path):
            shell_out(
                command=f"{script_path} {daemon_config_dir}",
                output_is_log=False,
                print_file_shell_cmd=False,
            )
            bm_log(
                f"docker daemon configuration saved in {daemon_config_dir}.",
                LogType.INFO,
            )
        else:
            bm_log(
                f"`get-docker-daemon-info.sh` script does not exist in: {script_path}. docker daemon information will not be recorded.",
                LogType.ERROR,
            )


# save all configuration specific to an individual container that
# might influence the performance of the benchmark
def save_container_config(output_dir, container_name):
    if check_data_directory(output_dir):
        container_config_dir = os.path.join(output_dir)
        script_path = "../scripts/get-docker-container-info.sh"

        assert os.path.exists(output_dir), f"output dir {output_dir} does not exist!"
        if os.path.exists(script_path):
            shell_out(
                [
                    script_path,
                    container_config_dir,
                    container_name,
                ],
                current_dir=get_curdir(__file__),
                output_is_log=True,
                print_file_shell_cmd=False,
            )
            bm_log(
                f"container configuration saved in {container_config_dir}.",
                LogType.INFO,
            )
        else:
            bm_log(
                f"`get-docker-container-info.sh` script does not exist in: {script_path}. docker container information will not be recorded.",
                LogType.ERROR,
            )


def is_port_free_to_use(port, host="127.0.0.1"):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(1)
        try:
            s.connect((host, port))
            return False  # connection succeeded → port is in use
        except (ConnectionRefusedError, OSError):
            return True  # connection failed → port is free


def stop_process(pid: int):
    """
    Kills the given process and all of its children
    """
    try:
        parent = psutil.Process(pid)
        for child in parent.children(recursive=True):
            child.kill()
        parent.kill()
    except psutil.NoSuchProcess:
        pass
    except psutil.AccessDenied:
        bm_log(
            f"Could not kill process with pid {pid}. Most likely need sudo to kill it.",
            LogType.ERROR,
        )


def exists_system_wide(cmd: str) -> bool:
    """
    Checks if a command exists system-wide
    """
    return shutil.which(cmd) is not None


def ensure_exists(
    name: str, dir: Optional[PathType] = None, env_var_dir: Optional[str] = None
) -> str:
    """
    Checks if the given file with the given `name` exists under:
        - given path (abs/relative the project folder)
        - system wide
        - under path defined in given `env_var_dir`
    The check happens in the aforementioned order, and if found
    at any stage the function exits and returns:
        - absolute path+name if given path is absolute and it is found there
        - relative path+name to the project if given path is relative to project path
        - name found in system wide (e.g. under usr/bin/)
        - absolute path specified by env var+name if found there
        - otherwise, fatal error is logged and execution is aborted
    """
    bm_log(f"ensure_exists name: {name}, dir:{dir}, env_var_dir:{env_var_dir}")
    fname = name
    if dir is not None and os.path.isabs(fname):
        fname = os.path.join(dir, name)
        if Path(fname).exists():
            return fname
    if dir is not None:
        fname = os.path.join(dir, name)
        if Path(resolve_path(fname)).exists():
            return fname
    if exists_system_wide(name):
        return name
    if env_var_dir is not None:
        env_dir = os.getenv(env_var_dir)
        if env_dir is not None:
            fname = os.path.join(env_dir, name)
            if Path(fname).exists():
                return fname
        else:
            bm_log(f"Environment variable: '{env_var_dir}' is not set", LogType.FATAL)
            sys.exit(1)
    # try to build as a target if it a builtin-benchmark
    b = Builder()
    if b.target_exists(name):
        b.build_target(name)
        assert Path(resolve_path(fname)).exists()
        return fname
    # Was not found in given path, system wide, or under env-var
    # path
    bm_log(f"Could not find the given binary/file {fname}", LogType.FATAL)
    sys.exit(1)


def dict_intersect(dicts: list[dict], save_dir, header_dict: dict) -> list[dict]:
    """
    Checks if all the given dicts have same keys. If so it returns the same dict.
    Otherwise, it will filter out keys uncommon keys and returns a list of dicts
    where uncommon keys are dropped. The original dicts in this case is modified
    the given header_dict is appended to each and the results are saved under
    save_dir.
    """
    # find common keys
    common_keys = set.intersection(*(set(d.keys()) for d in dicts))
    # check if all dicts have all keys by comparing length
    keys_identical = all(len(d) == len(common_keys) for d in dicts)
    # All dicts contain same keys, no missing keys in any dict.
    if keys_identical:
        return dicts

    # keep only common columns in filter dict
    filtered = [{k: d[k] for k in common_keys} for d in dicts]

    # append header dict to each of the original dicts
    for d in dicts:
        d |= header_dict

    fname = os.path.join(save_dir, "experiment_results_full.json")
    with open(fname, "w", encoding="utf-8") as f:
        json.dump(dicts, f, indent=4, ensure_ascii=False)

    bm_log(
        f"Not all apps produce same dict results, only common keys will be added to the final CSV. A copy of the original results can still be viewed in the JSON {fname}",
        LogType.WARNING,
    )
    return filtered


def remove_files_by_ext(dir, extensions: list[str]):
    """
    Removes all files under the given `dir` that
    have an extension matching any of the given list
    of `extensions`
    """
    folder = Path(dir)
    for extension in extensions:
        for file in folder.rglob(f"*.{extension}"):
            file.unlink()


def kill_all(name: str):
    """
    Kills all processes with name equals to the given.
    Use with caution, as this might kill processes that were not created by the framework.
    """
    bm_log(f"killing all processes with the name {name}!", LogType.WARNING)
    shell_out(command=f"sudo pkill {name}", print_file_shell_cmd=False)


def is_process_running(name: str) -> bool:
    """
    Returns True if it find a running process with the given name.
    Otherwise, returns False.
    """
    for proc in psutil.process_iter(["pid", "name"]):
        try:
            # Check if the process name matches the given name
            if name.lower() in proc.info["name"].lower():
                bm_log(f"{name} is running {proc.info['pid']}.")
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    return False


def get_host_ip() -> str:
    # This creates a temporary socket connection to get the local IP
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # The IP doesn't need to be reachable; just used to get the local IP
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip


def write_to_file(content: str, fname: str, dir: str):
    os.makedirs(dir, exist_ok=True)
    file_path = os.path.join(dir, fname)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)


def get_all_files_by_ext(dir: str, extension: str = ".csv"):
    """
    Returns all files under the given dir and subdirs, which have the given file extension.
    """
    filtered_files = []
    for root, _, files in os.walk(dir):
        for file in files:
            if file.endswith(extension):
                abs_path = os.path.join(root, file)
                filtered_files.append(abs_path)
    return filtered_files


def read_data_frame_from_csv(
    file: str, names: Optional[list[str]] = None
) -> Optional[pd.DataFrame]:
    try:
        df = pd.read_csv(
            file, names=names, sep=";", comment="#", engine="python", on_bad_lines="error"
        )
        return df
    except Exception as e:
        bm_log(f"{e} on {file}", LogType.ERROR)
        return None


def get_cgroups_version() -> str:
    """
    Returns the used version of cgroups.
    """
    # if the following command returns `cgroup2fs`,
    # then cgroup v2 is in use. If it returns
    # `tmpfs` then most likely v1 is in use.
    cgroup = shell_out(
        command="cat /proc/mounts",
        output_is_log=False,
        print_output=False,
        print_file_shell_cmd=False,
    ).strip()
    version = "v2" if "cgroup2".lower() in cgroup.lower() else "v1"
    return f"{version}"
