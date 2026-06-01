#!/usr/bin/env python
import docker
import time
import concurrent.futures
import argparse
import sys
from benchkit.shell.shell import shell_out
# ---------------------------
# Config
# ---------------------------
IMAGE_NAME = "busybox:latest"   # lightweight image
NUM_CONTAINERS = 50             # how many containers to launch
TIMEOUT = 60                    # seconds


## TODO: for this to work everything needs to run with sudo :/

def launch_container(index):
    """Launch a minimal container lifecycle benchmark."""
    container_name = f"cgroups_{index}"  # unique per run
    start_time = time.perf_counter()
    try:
        create_out = shell_out(command = f"sudo runc run -d {container_name}", print_shell_cmd=False,
                            print_input = False,
                            output_is_log=False,
                            print_file_shell_cmd=False,)
        delete_out = shell_out(command = f"sudo runc delete -f {container_name}",
                            print_input = False,
                            print_shell_cmd=False,
                            output_is_log=False,
                            print_file_shell_cmd=False,)
        elapsed = time.perf_counter() - start_time
        print(create_out, file=sys.stderr)
        print(delete_out, file=sys.stderr)
        return index, elapsed
    except Exception as e:
        print("Error in creating or destructing the container:", e, file=sys.stderr)
        sys.exit(1)
        return index, elapsed

# ---------------------------
# Main Benchmark
# ---------------------------
def main(count:int, index: int):
    results = []

    if count == 1:
        output = launch_container(index)
        results.append(output)
    else:
        # launches stuff in parallel
        with concurrent.futures.ThreadPoolExecutor(max_workers=count) as executor:
            futures = [executor.submit(launch_container, i) for i in range(count)]
            for future in concurrent.futures.as_completed(futures):
                results.append(future.result())

    # ---------------------------
    # Report
    # ---------------------------
    total_time = 0
    for idx, elapsed in sorted(results):
        if elapsed is not None:
            total_time += elapsed
        else:
            print(f"Container {idx:03d}", file=sys.stderr)
    print(f"num_containers={count};time={total_time/count:.3f}\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Container Scalability Benchmark")
    parser.add_argument("--instances", help="", default=NUM_CONTAINERS, type=int)
    parser.add_argument("--index", help="", default=TIMEOUT)
    args, index = parser.parse_known_args()
    main(count=args.instances, index=args.index)
