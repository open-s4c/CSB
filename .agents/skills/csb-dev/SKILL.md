---
name: csb-dev
description: "Use when developing or debugging CSB framework internals: bm-runner Python code, configuration parser classes, execution units, monitors, plots, plugins, adapters, Docker/native process orchestration, tests, or framework documentation. For SSH/remote-only behavior, use csb-remote alongside this skill. Use csb for running/adapting benchmark campaigns without changing framework code."
---

# CSB Development

Use this skill for implementation work in CSB framework internals. Keep it as a
routing and guardrail layer; stable project facts belong in the documentation,
not here.

## Compose With

- Project docs first: `doc/development.md` for layout, commands, common change
  patterns, and style; `doc/bm-runner.md` for runner behavior and output
  contracts; `doc/bm-config.md` for public JSON fields, monitors, plugins,
  plots, and environment variables.
- `csb` for ordinary benchmark setup, running, replotting, monitor setup, and
  permission-sensitive runtime work.
## First Checks

From the CSB root:

```bash
git status --short
git -C deps/syzkaller status --short
sed -n '1,220p' doc/development.md
```

Then read only the task-relevant docs and source. Prefer `rg` for discovery:

```bash
rg '<term>' bm-runner scripts helpers doc config bench
```

Respect the dirty-tree rules in `AGENTS.md`: Do not clean or
regenerate out-of-tree files unless the user asks.

## Development Guardrails

- Keep edits scoped. Reuse existing functionality and follow established
  runner, config, monitor, plugin, adapter, helper-script, style, and naming
  patterns before adding new abstractions.
- Inline-document new code, and add focused unit tests whenever practical.
- When behavior, public configuration, workflows, or supported commands change,
  update the relevant project doc instead of adding facts to this skill.
- Preserve public contracts from `doc/bm-runner.md` and `doc/bm-config.md`
  unless the task intentionally changes them, then update code, docs, and tests
  together.
- For host-dependent failures involving Docker, perf, sysstat, cgroups, NICs, or
  network access, report the exact missing capability. Do not hide permission or
  environment failures with unrelated code changes.

## Validation

Use the validation commands in `doc/development.md`. Run the smallest relevant
tests first, then require both `helpers/python-checks.sh` and
`helpers/python-tests.sh` to pass before handoff. Run a tiny real benchmark only
when the changed behavior needs runtime validation and the host has the required
permissions.
