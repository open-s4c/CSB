# Using stress-ng

Install `stress-ng` with the host package manager. CSB provides native
scalability examples for kernel paths exercised by the `exec`, `pthread`, and
`prctl` stressors:

```bash
sudo scripts/run-single.sh config/bm-external/stress-ng/exec.json
sudo scripts/run-single.sh config/bm-external/stress-ng/pthread.json
sudo scripts/run-single.sh config/bm-external/stress-ng/prctl.json
```

The examples deliberately use one CSB execution unit and vary stress-ng's
worker count. This keeps all workers in one host workload while CSB records the
worker count as `nb_threads`. The execution unit is assigned eight physical
cores. Adjust `core_count` and the thread list together when testing a larger
machine.

stress-ng refuses to run its `exec` stressor as root. If CSB was started with
`sudo`, the wrapper runs stress-ng as `SUDO_UID`/`SUDO_GID`; otherwise it keeps
the current user. The wrapper also merges stress-ng's stderr metrics into the
stream consumed by the CSB adapter.

The `exec` example retains stress-ng's pthread launcher and forces `fork` plus
`execve`. The `pthread` example records both throughput and stress-ng's
pthread-start latency. The `prctl` stressor includes many prctl operations, so
its aggregate throughput is only useful when a profile confirms that the
kernel path under investigation is material.

The committed settings are short functional examples. For performance claims,
increase `duration`, set `repeat` to at least five, include the target high
worker counts, stabilize CPU frequency, and report every repetition and
failure counter. stress-ng metrics are supporting evidence rather than a
substitute for a focused reproducer and matching kernel profile.
