# Using fio

Install `fio` with the host package manager. CSB provides native examples for
buffered-read LRU activity and mq-deadline contention:

```bash
sudo scripts/run-single.sh config/bm-external/fio/lru-buffered-read.json
sudo -E env CSB_FIO_DIRECTORY=/mnt/dedicated-test \
  scripts/run-single.sh config/bm-external/fio/mq-deadline.json
```

The wrapper creates one uniquely named test file in `CSB_FIO_DIRECTORY` (or
`/tmp`) and removes that exact file after each execution. Never point the
mq-deadline case at a live-data filesystem. Verify the target block device's
active scheduler in `/sys/block/DEVICE/queue/scheduler`; a successful smoke
run on another scheduler is not validation of the mq-deadline patch.

The committed file sizes, three-second duration, and single repetition are
functional examples. For performance claims, provision a dedicated filesystem,
increase the LRU working set beyond RAM, use at least 128 jobs and 120 seconds,
add a 30-second ramp, and run at least five repetitions per kernel. Hold the
device, scheduler, filesystem, mount options, affinity, and fio revision fixed.

Compare bandwidth or IOPS together with p95, p99, and p99.9 completion latency,
CPU cost per I/O, and device utilization. For the LRU case, confirm the target
folio/LRU paths in a profile. For mq-deadline, confirm both the scheduler and
the exact scheduler-lock path. The JSON adapter exposes these fio metrics
directly to CSB plots and result CSV files.
