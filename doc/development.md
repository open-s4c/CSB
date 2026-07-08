# CSB Development Notes

CSB is a prototype codebase. Keep changes scoped to the behavior under change,
prefer existing helper scripts and local patterns over new tooling, and update
the public documentation whenever behavior, configuration, workflows, or
supported commands change.

## Repository Layout for Development

The main runner implementation lives in `bm-runner/`. The runner entry point is
`bm-runner/main.py`; configuration parsing is in `bm-runner/bm_config.py` and
`bm-runner/config/`; benchmark orchestration is in `bm-runner/benchmark.py` and
`bm-runner/bm_executer.py`; native and container execution live in
`bm-runner/bm_native.py` and `bm-runner/bm_container.py`; monitors live under
`bm-runner/monitors/`; plotting is implemented in `bm-runner/bm_visualize.py`.

Builtin benchmark targets live under `bench/targets/` and external benchmark
helpers live under `scripts/adapters/` and `scripts/bm-external/`. Plugin
scripts referenced from JSON configs live under `scripts/plugins/`.

`deps/syzkaller` is a nested repository/submodule. Check its status and history
with `git -C deps/syzkaller ...` and keep its changes separate from the CSB root
repository.

## Development Commands

Prepare the Python and benchkit environment from the repository root:

```bash
scripts/prepare.sh
```

Run the Python test suite from the repository root:

```bash
helpers/python-tests.sh
```

or directly from `bm-runner/`:

```bash
cd bm-runner
../venv/bin/pytest tests
```

Run focused runner tests:

```bash
cd bm-runner
../venv/bin/pytest tests/test_env_config.py tests/test_container_config.py tests/test_topology.py
../venv/bin/pytest tests/test_with_plugins.py tests/test_perf_monitor.py
```

Run Python checks and formatting:

```bash
helpers/python-checks.sh
```

Validate and format JSON configs:

```bash
helpers/json-format.sh
```

Run a single benchmark config:

```bash
scripts/run-single.sh config/bm_empty.json
```

Replot existing results:

```bash
scripts/bm-run replot-all
```

alternatively

```bash
cd bm-runner
../venv/bin/python main.py --replot --title '<title>' --config ../config/<file>.json ../results/<run-dir>
```

Some commands require Docker, perf, sysstat, cgroups, NIC privileges, or network
access. If they fail because host permissions or services are unavailable,
report the missing requirement rather than changing code to hide the failure.

## Common Change Patterns

- New runner config field: update the matching class and Docstrings under
  `bm-runner/config/`, parsing/defaults, and tests under `bm-runner/tests/`.
- Run the following script to update doc/bm-config.md `helpers/update-doc.sh`
- New monitor: implement the monitor under `bm-runner/monitors/`, wire the
  monitor type and factory, document the config in `doc/bm-config.md`, and test
  empty/failing output handling.
- New plot type: update `bm-runner/config/plot.py`, implement plotting behavior
  in `bm-runner/bm_visualize.py`, document the plot type, and add tests when the
  behavior is non-trivial.
- New external benchmark: add or update scripts under `scripts/adapters/` or
  `scripts/bm-external/`, keep adapter output in CSB's semicolon-separated
  key/value format, and add config/docs.
- CPU/topology behavior: inspect `bm-runner/config/container.py`,
  `bm-runner/config/policy.py`, and `bm-runner/utils/topology.py`.
- Docker/container behavior: inspect `bm-runner/bm_container.py`,
  `bm-runner/config/nics.py`, and `scripts/add-nic-to-container.sh`.
- Plugin workflow: add scripts under `scripts/plugins/` and reference them in
  the JSON `plugins` section.
- Parser/proggen changes in syzkaller: update Go tests and regenerate parser
  artifacts if required.
- Extraction changes: test deterministic ordering, dependency preservation,
  poll filtering, minimum-size filtering, and network split behavior.
- `prog2c`/`csource` changes: inspect generated headers for sanitized paths,
  sockets, buffers, file descriptor cleanup/leak handling, metadata, and trace
  output.
- Always inline document new code.

## Style

Python code uses type hints, straightforward dataclass-like config classes, and
`bm_log(..., LogType...)` for user-visible runner messages.

Shell scripts are Bash and generally use repository-relative paths from the
documented working directory. Keep staged generator scripts explicit and easy to
debug.

Preserve license headers when editing existing source files. Add the same
MIT/Huawei header to new project source files when consistent with nearby files.

License to new files will be added with:

```bash
helpers/license-check.sh
```
