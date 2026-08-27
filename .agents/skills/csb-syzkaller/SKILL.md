---
name: csb-syzkaller
description: "Use for operating CSB's syzkaller-based benchmark generation workflow: preparing bm-generator, parsing strace logs, extracting syz programs, generating or refreshing CSB C headers and JSON configs, selecting generated benchmarks, and adapting generated configs for runs."
---

# CSB Syzkaller Usage

Use this skill to operate the CSB `bm-generator/` pipeline and adopt generated
benchmark artifacts. Keep stable workflow details in the docs instead of
repeating them here.

## Compose With

- Project docs first: `doc/bm-generator.md` for generator requirements,
  numbered scripts, syzkaller fork notes, selection, excluded syscalls, and Go
  test commands; `doc/bench.md` for generated benchmark layout and builtin
  benchmark contracts; `doc/bm-runner.md` for running generated configs.
- `csb` after generation when validating configs, running benchmark campaigns,
  replotting, or setting up monitors.
- `csb-remote` when trace collection, generation, selection, or benchmark runs
  must happen on an SSH benchmark host.
- `csb-dev` for implementation changes in CSB framework code when that skill is
  available. For `deps/syzkaller` changes, follow `doc/bm-generator.md` and keep
  the nested repository status/history separate.

## First Checks

From the CSB root:

```bash
git status --short
git -C deps/syzkaller status --short
sed -n '1,260p' doc/bm-generator.md
```

Then inspect only task-relevant inputs, outputs, and scripts:

```bash
rg '<term>' bm-generator config bench/targets doc deps/syzkaller
```

Respect the dirty-tree rules in `AGENTS.md`: generated headers, generated
configs, deserialized/extracted program directories, result folders, and
`deps/syzkaller` changes are common here. Do not clean, delete, or regenerate
them unless the user asks.

## Operating Guardrails

- Run the numbered `bm-generator/` pipeline documented in
  `doc/bm-generator.md`; rerun only the smallest needed suffix when refreshing
  artifacts.
- Generator scripts intentionally fail on non-empty output directories. Move or
  clean only the specific generated group/output path the user asked to refresh.
- Keep generated configs and headers aligned with their `CSB_RESULTS_GROUP`.
  Prefer copying a generated config to a named experiment file before adapting
  duration, repeats, containers, execution type, monitors, or plots.
- Do not hand-edit generated headers/configs as the durable fix unless the user
  explicitly asks for a temporary experiment; update the trace, `.prog`,
  template, metadata, or generator code and regenerate instead.
- When Go, syzkaller tool builds, Docker, perf, flamegraph selection, or host
  permissions fail, report the exact missing requirement. Do not redirect caches
  or disable analysis in a way that hides the environment issue.

## Validation

Use the generator and syzkaller validation commands in `doc/bm-generator.md`.
For generated benchmark runs, switch to `csb`. For network traces, verify
split-aware metadata and selected programs before treating generated configs as
ready for benchmark campaigns.
