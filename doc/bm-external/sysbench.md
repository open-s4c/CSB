# Using Sysbench

Install sysbench dependencies. On openEuler:
```bash
sudo dnf install mariadb-server mariadb-devel mariadb-connector-c postgresql-server postgresql-server-devel libpq libpq-devel autoconf automake libtool gcc make
```

Install sysbench from git tree using:
```bash
sudo scripts/bm-external/sysbench/configure.sh
```

To run just one instance in bare metal host, run:
```bash
sudo scripts/bm-external/sysbench/prepare.py
```

## File I/O scalability

The host-package `sysbench` can also run a self-contained native fileio sweep:

```bash
sudo -E scripts/run-single.sh config/bm-external/sysbench/fileio.json
```

The wrapper prepares a uniquely named temporary file set for every execution
and removes that exact directory afterward. Set `CSB_SYSBENCH_FILE_NUM` and
`CSB_SYSBENCH_FILE_SIZE` to change the default 32 files and 256 MiB total.

The committed three-second, single-repeat case is a functional example. For an
mq-deadline comparison, use a dedicated filesystem on a device whose active
scheduler is verified, prepare at least 32 GiB, use the target high thread
count and a 30-second warm-up followed by at least 120 timed seconds. Run at
least five repetitions on each kernel with identical device, scheduler,
filesystem, affinity, and sysbench version. Compare reads/s, writes/s, and p95
latency. fio remains the primary scheduler test because it exposes more I/O
controls and latency percentiles.
