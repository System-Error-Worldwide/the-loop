---
name: the-loop-setup
description: Detect supported agent harnesses, preview an exact portable-skill installation, and apply or roll back only approved filesystem operations.
license: MIT
compatibility: Codex, Claude Code, Kimi Code and OpenCode
metadata:
  the-loop-capability: setup.install
  the-loop-version: "0.1"
---

# THE LOOP Setup

Install the public skill pack into one repository or one selected user scope. Start with a dry run. Never infer approval from a broad request when the plan reports a collision.

## Inputs

- Source repository containing canonical packages under `.agents/skills`.
- Existing target root.
- One or more installed harnesses, or automatic detection.
- Scope: `project` or `user`.
- Mode: universal `copy`, or `link` only with explicit filesystem and harness proof.
- Exact destination approvals for every non-identical collision.

## Procedure

1. Read the four public adapter manifests and detect installed executables independently.
2. Build a read-only operation plan in stable order. Include directory creation, copy, link, skip, collision, rollback action, and digests.
3. Show the plan. A dry run changes nothing.
4. On apply, recheck target identity, source digests, destination digests, selected harnesses, mode, and exact approvals.
5. Apply the transaction. Restore the exact prior filesystem state if any operation or receipt write fails.
6. Write the schema-valid receipt to `.the-loop/installs/<receipt-id>.json`.
7. For rollback, remove only unchanged receipt-owned output. Restore an approved replacement only when the installed result is unchanged and its receipt backup is present.

Use [`scripts/the_loop_setup.py`](../../../scripts/the_loop_setup.py) for the CLI and [`install-receipt.schema.json`](../../../schemas/install-receipt.schema.json) for the receipt contract.

## Evidence

- Dry-run plan and selected adapter manifests.
- Applied or rolled-back install receipt.
- Setup tests covering collision refusal, exact approval, interruption, changed output, and link proof.

## Halt conditions

Stop with a precise error when no selected harness is installed, an adapter is missing or invalid, a path escapes its root, any path crosses a symlink, a source or destination changed after planning, link support is not proven, or an exact collision approval is absent.

Setup does not read credential files, collect prompts, send telemetry, or publish anything.
