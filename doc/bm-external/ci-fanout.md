# Warm CI runner fan-out benchmarks

This paired external benchmark models a warm CI, package-build, or test runner
that dispatches many short processes concurrently. It targets large systems
where process creation and address-space teardown can limit job-dispatch
throughput.

## Actual workload

`config/bm-external/ci-fanout.json` uses existing production tools: GNU
`make`, `/bin/sh`, and the system C compiler. A fixed make DAG runs 1,024
independent `cc -fsyntax-only` checks at 1, 8, 32, 64, and 128-way
parallelism. The shell wrapper only warms the tools, measures the fixed-work
run, and emits CSB key/value output.

The primary metric is completed compile-validation steps per second. The
benchmark also reports fixed-work elapsed time, average elapsed contribution
per step, completed steps, and failures. A valid comparison requires exactly
1,024 completed steps and zero failures at every point.

## Mechanism companion

`config/bm-external/ci-fanout-micro.json` keeps a focused attribution test next
to the actual workload. A memory-resident coordinator faults in a 256 MiB cache
and uses 1, 8, 32, 64, or 128 threads to perform explicit `fork()` plus
`execve("/bin/true")` cycles. It reports aggregate fork/exec throughput and
latency. This test is not the real-world result; it helps determine whether a
change in the make/compiler workload follows the expected process-MM mechanism.

Build the companion and run both configs with:

```bash
scripts/bm-external/ci-fanout/configure.sh
scripts/run-single.sh config/bm-external/ci-fanout-micro.json
scripts/run-single.sh config/bm-external/ci-fanout.json
```

Both configs run natively and inside `ubuntu:latest`. CSB starts the container
before releasing its workload barrier, so image pull and container creation
are outside the timed region. The supplied configs target a 128-CPU host and
repeat every point five times.

For cross-kernel comparisons, pin the same CPUs, use the same image and
compiler, randomize kernel order, and retain thermal/frequency metadata. Do not
compare runs whose fixture, toolchain, step count, memory size, worker set, or
execution environment differs.

The actual workload is still narrower than a complete software build. It
answers whether a kernel improves dispatch capacity for a shell- and
compiler-heavy runner; it does not predict CPU-bound compile throughput,
long-running services, or container cold-start time. Measure container
lifecycle separately when creation itself is part of the deployment question.
