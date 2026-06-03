#!/usr/bin/env python
# Copyright (C) Huawei Technologies Co., Ltd. 2026. All rights reserved.
# SPDX-License-Identifier: MIT

import time
import argparse
import sys
from benchkit.shell.shell import shell_out

def launch_container(index):
    container_name = f"cgroups_{index}"  # unique per run
    start_time = time.perf_counter()
    try:
        create_out = shell_out(command = f"sudo runc run -d {container_name}", print_shell_cmd=False,
                            print_output = False,
                            print_input  = False,
                            output_is_log=False,
                            print_file_shell_cmd=False,)
        delete_out = shell_out(command = f"sudo runc delete -f {container_name}",
                            print_input = False,
                            print_output = False,
                            print_shell_cmd=False,
                            output_is_log=False,
                            print_file_shell_cmd=False,)
        elapsed = time.perf_counter() - start_time
        # we write these to stderr, so that we don't pollute the output
        # with things bm-runner cannot parse. We redirect to stderr
        # for debugging purpose.
        print(f"Container creation output: {create_out}", file=sys.stderr)
        print(f"Container deletion output: {delete_out}", file=sys.stderr)
        return container_name, elapsed
    except Exception as e:
        print("Error in creating or destructing the container:", e, file=sys.stderr)
        sys.exit(1)

# ---------------------------
# Main Benchmark
# ---------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Container Scalability Benchmark")
    parser.add_argument("--index", help="Index of the container", default=0)
    args, index = parser.parse_known_args()

    instance_name, elapsed  = launch_container(args.index)
    print(f"instance_name={instance_name};time={elapsed:.3f}\n")
