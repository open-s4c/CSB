import docker
import time
import concurrent.futures

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
def main():
    print("Checking host cgroup v2 support...")
    if not check_host_cgroup2():
        print("⚠️  Host/runtime does NOT appear to use cgroup v2. Benchmark may be invalid!")
        return
    print("✅ Host/runtime uses cgroup v2. Starting benchmark...")

    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(launch_container, i) for i in range(NUM_CONTAINERS)]
        for future in concurrent.futures.as_completed(futures):
            results.append(future.result())

    # ---------------------------
    # Report
    # ---------------------------
    print("\nBenchmark results:")
    total_time = 0
    for idx, elapsed, cg in sorted(results):
        if elapsed is not None:
            print(f"Container {idx:03d}: {elapsed:.3f}s, cgroup={cg}")
            total_time += elapsed
        else:
            print(f"Container {idx:03d}: ERROR {cg}")

    print(f"\nLaunched {NUM_CONTAINERS} containers in {total_time:.3f}s total.")
    print(f"Average per container: {total_time/NUM_CONTAINERS:.3f}s")

if __name__ == "__main__":
    main()
