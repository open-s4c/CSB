---
name: csb
description: "Use for operating the CSB Container Scalability Benchmarks framework: preparing the runtime environment, choosing JSON configs for a target application, running bm-runner campaigns, configuring linux-perf-friendly monitors, replotting existing results for ordinary benchmark runs."
---

# CSB Usage

Use this skill to run CSB benchmark campaigns. Stay on the user-facing surfaces: `config/`, `scripts/`, `bench/targets/`, `results/`, `doc/`, and runner commands.

## First Checks

Start at the CSB root:

```bash
pwd
sed -n '1,220p' README.md
sed -n '1,260p' doc/bm-runner.md
sed -n '1,260p' doc/bm-config.md
rg --files config scripts bench/targets doc -g '*.json' -g '*.sh' -g '*.md' -g '*.h'
```

## Prepare The Runtime Environment

Use existing scripts rather than hand-rolling setup:

```bash
scripts/prepare.sh
```

For one benchmark config, prefer:

```bash
scripts/run-single.sh config/<file>.json [extra main.py args]
```

Useful environment toggles can be found in `doc/bm-config.md#environment-variables`.

Running full benchmarks may require Docker access, `perf`, `sysstat`, sudo-able NIC operations, and host permissions. If these fail, report the exact missing capability.

## Configure A Specific Application

Primary config surface: JSON under `config/`, documented in `doc/bm-config.md`. Refer to this document for any further application specific configuration.

## Run, Replot, And Inspect

Normal interactive run:

```bash
./run.sh
```

Direct runner:

```bash
scripts/run-single.sh config/<file>.json [extra main.py args]
```

Replot without rerunning workloads:

```bash
cd bm-runner
python3 main.py --replot --title '<title>' --config ../config/<file>.json ../results/<run-dir>
```

Bulk configs:

```bash
scripts/run-all.sh '<pattern>'
```

Expected complete result siblings:

- `results/<run>/`
- `results/<run>.json`
- `results/<run>.html`
- `results/<run>.csv`

Per-run monitor files usually live below:

`execution_type-*/container_cnt-*/nb_threads-*/run-*`

For post-run performance analysis, use `csb-analysis`.

## linux-perf-Friendly Runs

When the user's goal is kernel performance analysis, scaling diagnosis, or later patch selection, configure the system so that user and other analysis tools and skills can have actionable feedback.

Whenever perf data would materially improve the run or later analysis, try to enable full perf visibility before running the benchmark:

```bash
cat /proc/sys/kernel/perf_event_paranoid
echo -1 | sudo tee /proc/sys/kernel/perf_event_paranoid
cat /proc/sys/kernel/perf_event_paranoid
```

In CSB, `perf` and `perf_lock` monitors can conflict with each other, causing corruption of the `perf` monitor results. If both monitors are enabled in the configuration, ask the user to leave only one of these monitors enabled.

The results of the `perf` monitor can be hard to interpret without the `mpstat` monitor. If `perf` monitor is enabled, but `mpstat` monitor is not, suggest to also enable `mpstat`, but don't insist on this.

The aim of `mpstat` monitor is to capture the CPU utilization of one benchmark execution unit (process or container). To this end, check that the list of cores passed to mpstat matches the full list of cores of one of the benchmark execution units.

If `mpstat` monitor's `iowait` results suggest active disk IO, but `iostat` monitor is missing, suggest to the user to add it.

For perf tracepoints, bpftrace, scheduler/block events, and other trace-based monitors, also check tracefs. Prefer `/sys/kernel/tracing`; fall back to `/sys/kernel/debug/tracing` only when needed:

```bash
TRACEFS=/sys/kernel/tracing
test -d "$TRACEFS" || TRACEFS=/sys/kernel/debug/tracing
findmnt -T "$TRACEFS"
test -r "$TRACEFS/events" && test -x "$TRACEFS/events"
sudo mount -o remount,mode=755 "$TRACEFS"
test -r "$TRACEFS/events" && test -x "$TRACEFS/events"
```

If tracefs is not mounted, try mounting it before the remount:

```bash
sudo mount -t tracefs nodev /sys/kernel/tracing
```

If sudo is denied, unavailable, or policy blocks the change, continue with the best available monitors and record that perf or tracefs collection was permission-limited. Do not silently downgrade to weaker evidence. After enabling perf and tracefs access, run a useful small benchmark point that can verify the hypothesis, usually baseline count, peak/plateau count, and cliff or largest count with the relevant perf monitor enabled.

Before running a benchmark check if necessary toolins for configured monitors are available and produce useful results.

If host permissions prevent perf, c2c, lock, or bpftrace monitors, do not hide the failure by disabling analysis silently. Record the missing permission in the result notes or final response.

Before relying on tracepoint events, verify that they are visible to `perf`, for example:

```bash
perf list 'block:*' 'sched:*' 'syscalls:*' >/tmp/csb-perf-tracepoint-list.txt
```

If the list is empty or perf reports tracefs permission errors, fix tracefs permissions or document the limitation in the run notes.
