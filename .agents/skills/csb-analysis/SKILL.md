---
name: csb-analysis
description: "Use when analyzing existing CSB result artifacts under results/ and preparing evidence-backed kernel patch artifacts from benchmark CSVs, saved monitor data, perf/flamegraph/lock evidence, Linux source correlation, and upstream/vendor history."
---

# CSB Analysis

Use this skill for post-run CSB result analysis and the kernel patch artifacts
that follow from that analysis. Do not run new experiments or mutate benchmark
inputs, CSB internals, or host tracing state.

Use CSB documentation as the source of truth for framework facts:

- Runner outputs and workflow: `doc/bm-runner.md`
- Config fields, monitor names, plot fields, and environment variables:
  `doc/bm-config.md`
- Builtin benchmark output format and metric names: `doc/bench.md`
- Development commands and repository discipline: `doc/development.md`

## Guardrails

- Do not modify any existing results, only write to new files.
- Analyze existing artifacts only.
- Write only analysis reports and kernel patch-preparation artifacts under
  `results/`.
- Do not modify applications, configs, generated CSB files, runner code,
  monitor setup, framework files, or host perf/tracefs/sysctl/cgroup/Docker/NIC
  state.
- If artifacts, permissions, symbols are
  missing, state the limitation directly.
- Treat every benchmark as an independent experiment unless the user requests a
  cross-benchmark synthesis.

## Inputs

Start from the CSB repository root unless the user gives another path. A result
set at least includes a result directory plus sibling `.csv`, `.json`, and
`.html` files; consult `doc/bm-runner.md` and `doc/bench.md` for the runner and
benchmark output contracts.

Preserve run dimensions in every conclusion. Evidence from one
`execution_type`, `container_cnt`, `nb_threads`, host,
kernel, or run is not evidence for another unless explicitly aggregated and
stated.

Before analysis, check whether `performance-patterns` is available as a skill
or local reference under `deps/intel-performance-skills/skills/performance-patterns`.
If it is absent, record that classification as unavailable. Use `deps/linux`
for source correlation and local history when present; if absent, clone latest Linux
tree and use branch main as upstream. Add a remote to the git tree for the
distribution specific kernel version. Use a commit or branch that matches the test
machine kernel version. This vendor specific tree and checkout serves as the current
running kernel source.

## Workflow

For each benchmark/run:

1. Verify completeness.
   Identify the result basename and expected sibling artifacts. Report missing
   files and avoid unsupported conclusions.

2. Identify the execution-unit axis.
   Prefer the CSV dimension that actually changes, commonly `container_cnt`.
   Keep all other dimensions separated unless constant.

3. Establish the performance signal.
   Use the benchmark's primary documented metric. For builtin CSB benchmarks
   this is usually `throughput_min`; some external benchmarks use time for a
   fixed amount of work. Track success and latency columns when present.

4. Run the CSB analyzer when practical.
   Use `bm-runner/analyze.py` only on a folder containing the intended
   top-level benchmark result CSVs:

   ```bash
   cd bm-runner
   TMPDIR=/tmp/csb-analyze MPLCONFIGDIR=/tmp/csb-mpl ../venv/bin/python analyze.py <csv-folder> [<csv-folder> ...]
   ```

   Treat its output as aggregate first-pass evidence, not as a replacement for
   per-run monitor, perf, lock, source, and history analysis. The script
   recursively discovers CSVs, so do not point it at an unfiltered `results/`
   tree containing monitor CSVs. Record dependency or input failures directly.

5. Find degradation points.
   Compute performance by comparing each independent dimension group against
   execution-unit count. Identify the peak or plateau and the first material
   drop. State the threshold used; a useful default is at least 10% below peak
   or sustained negative marginal scaling.

6. Correlate saved monitor signals.
   Compare baseline, peak/plateau, first degradation point, and largest count
   when those points exist. Use the monitors documented in `doc/bm-config.md`,
   but interpret collected files from the result directory, not monitor names
   alone. Prefer ratios and percentages over vague movement descriptions.

7. Extract hot kernel functions.
   Use saved `perf.data`, perf reports/scripts, flamegraphs, lock-contention
   outputs, bpftrace outputs, Arm SPE captures, and similar artifacts when
   present. Compare stacks/functions across the same execution-unit points used
   for monitor correlation. Report unreadable perf data, unresolved symbols, or
   permission-limited captures.

8. Map hot paths to source.
   Use already available local trees, usually `deps/linux`. Search exact symbols
   first, then wrappers/callers from stacks. Record the tree path, current
   commit, dirty status, and whether the source appears to match the tested
   kernel. Cite fymbol-to-file mapping lookup evidence in the report.

9. Inspect local history.
   Compare candidate hot paths against already available vendor or upstream refs
   in `deps/linux`. Include only commits plausibly related to the measured path,
   lock, syscall, filesystem, memory-management, scheduler, network, block,
   cgroup, or architecture behavior. Treat history as possibly relevant unless
   it clearly changes the measured path in a matching way.

10. Classify bottleneck.
    Use evidence to suggest prime source of main performance bottleneck.
    A classification might be lock contention or CPU/IO bound.

11. Write reports.
    Produce one Markdown report per complete run unless cross-run synthesis was
    requested. Use `results/<base>_csb-analysis.md` as the filename and follow
    `template-csb-analysis-report.md`. Generate HTML only when requested.

12. Prepare kernel patch artifacts when evidence supports a concrete change.
    Create a per-run `results/<base>_patch-series-<theme>/` directory containing
    the patch, `README.md`, and `SAFETY_IMPLICATIONS_AND_DESCRIPTION.md`. Use
    an RFC patch when the change is hypothesis-driven and not rerun-validated.
    Add or update `results/<base>_kernel_patch_preparation_summary.md` as an index.

13. Validate local links.
    Resolve Markdown links from the file that contains them. Link existing
    result HTML, generated analysis, source paths, and patch artifacts. Mark
    missing optional artifacts as `missing` rather than linking them.

## Evidence Rules

- Benchmark output is the primary performance signal; monitor data explains it.
- Keep native and container execution types separate unless explicitly
  comparing them.
- Recompute baselines and degradation independently for each complete run.
- Do not claim a kernel root cause from one signal alone. Require a benchmark
  inflection plus matching monitor movement plus plausible stack/function/source
  evidence.
- In cross-run summaries, rank evidence strength separately from degradation
  severity.

## Reports

Write the reports under the result directory or user-specified location, using the related benchmark basename as a prefix:

- `<base>_csb-analysis.md`: should be generated according to point #11 of the Workflow section.
- `<base>_kernel_patch_preparation_summary.md`: should be generated according to point #12 of the Workflow section.

## Patch Artifact Requirements

To create a patch series, consider the evidence in detail:
- For CPU-bound benchmarks, study the perf annotation of the source code. Try to reduce the overheads of hot instructions and code path in the patch.
- For benchmarks bound on lock contention, study the relevant critical sections. Try to reduce the duration of critical sections, use lock-free data structure, or RCU protection if possible.
- For disk and network bound benchmarks, suggest further experiments on faster hardware.

Patch proposals must state:

- affected files/functions and whether the patch is novel RFC work, a backport,
  an adaptation, or a combination;
- measured degradation and evidence confidence;
- expected benefit and why the selected path should be profitable;
- semantic, latency, performance, memory, fairness, crash-consistency,
  permissions, LSM/fsnotify/accounting, cgroup, and architecture implications
  as applicable;
- validation checklist and minimal benchmark rerun matrix.

Before reporting patch preparation complete, count expected patch-series
directories and patch files, ensure each patch-series directory has `README.md`
and `SAFETY_IMPLICATIONS_AND_DESCRIPTION.md`, and check for stale or broken
source links.
