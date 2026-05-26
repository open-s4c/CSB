#!/usr/bin/env python
import docker
import time
import concurrent.futures
import argparse

# ---------------------------
# Config
# ---------------------------
IMAGE_NAME = "busybox:latest"   # lightweight image
NUM_CONTAINERS = 50             # how many containers to launch
CONTAINER_COMMAND = "sh -c 'cat /sys/fs/cgroup/cgroup.controllers || echo v1'"  # verify cgroup v2
TIMEOUT = 60                    # seconds

# ---------------------------
# Docker client
# ---------------------------
client = docker.from_env()

# ---------------------------
# Helper functions
# ---------------------------
def check_host_cgroup2():
    """Check if host Docker uses cgroup v2."""
    try:
        # Create a temporary container to inspect /sys/fs/cgroup
        container = client.containers.run(
            IMAGE_NAME,
            CONTAINER_COMMAND,
            detach=True,
            tty=True,
            remove=True
        )
        logs = container.logs().decode().strip()
        if "v1" in logs:
            return False
        else:
            return True
    except Exception as e:
        print("Error checking host cgroup:", e)
        return False

def launch_container(index):
    """Launch a single container, check cgroup, and measure time."""
    start_time = time.time()
    try:
        container = client.containers.run(
            IMAGE_NAME,
            CONTAINER_COMMAND,
            detach=True,
            tty=True,
        )
        logs = container.logs().decode().strip()
        cgroup2_used = "v2" if logs else "v1"
        container.remove(force=True)
        elapsed = time.time() - start_time
        return index, elapsed, cgroup2_used
    except Exception as e:
        return index, None, f"error: {e}"

# ---------------------------
# Main Benchmark
# ---------------------------
def main(count:int, duration: int):
    cgroup = "v2" if check_host_cgroup2() else "v1"

    results = []

    if count == 1:
        output = launch_container(0)
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
    for idx, elapsed, cg in sorted(results):
        if elapsed is not None:
            total_time += elapsed
        else:
            print(f"Container {idx:03d}: ERROR {cg}")
    print(f"host_cgroup={cgroup};container_cgroup={cg};num_containers={count};time={total_time/count:.3f}\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Container Scalability Benchmark")
    parser.add_argument("--instances", help="", default=NUM_CONTAINERS, type=int)
    parser.add_argument("--duration", help="", default=TIMEOUT)
    args, others = parser.parse_known_args()
    main(count=args.instances, duration=args.duration)
