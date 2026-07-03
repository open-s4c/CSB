# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project partially comply with [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.0] - 2026-07-03

### Added

- Add `bpftrace` monitor support, including a pool of BPFTrace programs under `scripts/bpftrace`.
- Add new monitors: `iostat`, `perf stat`, and `perf lock` / `perf lock contention`.
- Add external benchmark support for cgroups and Sysbench/MariaDB workloads.
- Add AI-agent support files and CSB skills for usage, refinement, remote execution, and analysis.

## Changed

- Refactor monitor process handling around `BackgroundProcess`.
- Improve CPU/core assignment with topology detection, core assignment policies, distant CPU assignment, and dynamic default `container_list`.
- Move external benchmark configs under `config/bm-external`.
- Improve generated benchmark templates and update Syzkaller.
- Add kernel, CPU, and cgroup-version metadata to CSV outputs.
- Improve plotting support, including mean plots, min/max/avg latency plots, and plot refactoring.

### Fixed

- Alignment for auto generated write buffer to support O_DIRECT writes in test cases

## [0.2.1] - 2026-03-27

### Changed

- build only required benchmarks instead of
  building all benchmarks

### Fixed

- cleanup of temporary syz* folders
- mysql-aggregated.json benchmark and networking script
- wait for start signal
- plots


## [0.2.0] - 2026-03-17

### Added

- support for unixbench as external benchmark
- environment variable to turn off monitors
- rocksdb auto-generated benchmarks

### Changed

- bm-generator optimized
- bm-generator support networking syscalls
- flamegraph selection added to bm-generator pipeline
- update mySQL benchmarks including networking syscalls

## [0.1.0] - 2026-02-04

### Added

- prototype bm-runner python framework for running benchmarks
- prototype bench set of C benchmarks
- prototype bm-generator experimental tooling for generating syscalls benchmarks
