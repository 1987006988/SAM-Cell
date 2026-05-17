# SAM-Cell Agent Instructions

This repository uses explicit project memory files. Before starting any non-trivial SAM-Cell task, read:

```text
docs/project_memory.md
```

Use it as the durable source of truth for:

- current scientific objective
- dataset versions and paths
- remote workstation status
- training checkpoints
- evaluation results
- known failure modes
- next-step decision rules

## Memory Update Rules

Update `docs/project_memory.md` after any of these events:

- a training run starts, stops, fails, or completes
- a new dataset version is built
- a benchmark or diagnostic evaluation finishes
- a model/config becomes the new recommended default
- a major conclusion changes
- a path, environment, or remote session name changes

Keep memory concise and decision-oriented. Do not paste long logs. Prefer:

- exact paths
- exact dates/times
- metric tables
- current status
- next action
- caveats and known risks

Do not store passwords, private keys, or unrelated personal information.

## Working Protocol

1. Read `docs/project_memory.md`.
2. Check current filesystem/remote status before assuming old status is still valid.
3. Make code/data/training changes.
4. Verify with tests or metrics where feasible.
5. Update `docs/project_memory.md`.
6. Report only the high-signal result to the user.

For long-running jobs, write scripts and logs to stable paths under `scripts/`, `docs/`, and `outputs/` so future sessions can resume without relying on chat history.
