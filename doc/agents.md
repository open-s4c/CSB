# CSB AI agent skills

CSB ships with a number of AI agent skills that simplify the use of
the CSB functionality. These skills contain information
about common workflows for CSB usage:
- running a benchmark locally and on remote server;
- analyzing the benchmark results;
- finding the root causes of performance degradation using an
  iterative improvement of the benchmark monitors and configurations.

CSB also contains general information for AI agents about the
development process of CSB, such that they can effectively modify the
configurations and develop new functionality (e.g. monitors) for CSB.

## Installation

Install `node`, `nvm` and `npm`:

```bash
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.5/install.sh | bash
. "$HOME/.nvm/nvm.sh"
node install --lts
```

After that, install Codex:

```bash
npm install -g @openai/codex
```

## Skills

The following skills are available:

- `csb`: instructs the agent about how to perform the experiments.
  - Example: "$csb run config/bm-external/cgroups/runc.json"
  - Example: "run benchmark using config/bm-external/cgroups/runc.json config"
- `csb-analysis`: performs automatic analysis of the benchmark run,
  trying to extract as much information as possible for identification
  and classification of the application performance bottleneck.
  - Example: "Analyze results of the last benchmarking run".
  - Example: "Benchmark the modified config, and analyze the results".
- `csb-refine`: an interactive refinement skill that changes the
  benchmark runtime configuration and the monitors in order to better
  pinpoint the bottleneck and establish causal relationships with the
  measured system metrics.
  - Example: "$csb-refine the latest results."
- `csb-remote`: allows execution of the previous skills on a remote
  machine.
  - Example "Use $csb-remote to run experiment
    config/rocksdb/bm_min_rocks_write_fcntl_5_0.json on host
    remote-server, and analyze the results."

## Demo

As a demo, you can run the following command:

```
Run $csb benchmark of ../config/rocksdb/bm_min_rocks_write_fcntl_5_0.json, then $csb-analyze the results.
```
