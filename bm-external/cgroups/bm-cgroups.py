#!/usr/bin/env python
# Copyright (C) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# SPDX-License-Identifier: MIT

import time
import argparse
import sys
from benchkit.shell.shell import shell_out


def quiet_shell(command):
    return shell_out(
        command=command,
        print_shell_cmd=False,
        print_output=False,
        print_input=False,
        output_is_log=False,
        print_file_shell_cmd=False,
    )


def launch_container(index):
    container_name = f"cgroups_{index}"

    try:
        total_start = time.perf_counter()

        create_start = time.perf_counter()
        create_out = quiet_shell(f"sudo runc run -d  {container_name}")
        create_time = time.perf_counter() - create_start
        print(f"Container create output: {create_out}", file=sys.stderr)

        delete_start = time.perf_counter()
        delete_out = quiet_shell(f"sudo runc delete -f {container_name}")
        delete_time = time.perf_counter() - delete_start
        print(f"Container delete output: {delete_out}", file=sys.stderr)

        total_time = time.perf_counter() - total_start
        return container_name, create_time, delete_time, total_time

    except Exception as e:
        print("Error in container lifecycle:", e, file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Container Scalability Benchmark")
    parser.add_argument("--index", help="Index of the container", default=0)
    args, _ = parser.parse_known_args()

    instance_name, create_time, delete_time, elapsed = launch_container(args.index)

    print(
        f"instance_name={instance_name};"
        f"create_time={create_time:.6f};"
        f"delete_time={delete_time:.6f};"
        f"time={elapsed:.6f}"
    )
