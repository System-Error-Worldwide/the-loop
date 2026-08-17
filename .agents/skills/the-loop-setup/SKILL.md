---
name: the-loop-setup
description: Detect supported agent harnesses, preview an exact portable-skill installation, and apply or roll back only approved filesystem operations. Use when a user asks to install, update, inspect an install plan for, or uninstall SYSTEM ERROR'S THE LOOP.
license: MIT
compatibility: Codex, Claude Code, Kimi Code, OpenCode and DeepSeek Harness
metadata:
  the-loop-capability: setup.install
  the-loop-version: "0.1"
---

# THE LOOP Setup

Install the public skill pack into one repository or one selected user scope. Start with a dry run. Never infer approval from a broad request when the plan reports a collision.

## Inputs

- Source root containing canonical packages under `.agents/skills`: either the public checkout or an installed `.the-loop/toolkit`.
- Existing target root.
- One or more installed harnesses, or automatic detection.
- Scope: `project` or `user`.
- Mode: supported `copy`. A requested `link` plan fails closed when portable documentation transformation requires copies; unchanged synthetic packages exercise the lower-level link path only with explicit same-filesystem proof.
- Exact destination approvals for every non-identical collision.

## Procedure

1. Read the four public adapter manifests and detect installed executables independently.
2. Build a read-only operation plan in stable order. Include directory creation, copy, link, skip, collision, rollback action, and digests.
3. Show the plan. A dry run changes nothing.
4. On apply, recheck target identity, source digests, destination digests, selected harnesses, mode, and exact approvals.
5. Apply the transaction. Restore the exact prior filesystem state if any operation or receipt write fails.
6. Write the schema-valid receipt to `.the-loop/installs/<receipt-id>.json`.
7. For rollback, remove only unchanged receipt-owned output. Restore an approved replacement only when the installed result is unchanged and its receipt backup is present.

Apply installs a private, namespaced `.the-loop/toolkit` containing the canonical packages, adapters, protocols, schemas, scripts and standard-library runtime. After the first apply, core execution, Doctor, rollback and a later Setup plan do not require network access or the original source checkout.

From an installed project, use `.the-loop/toolkit/scripts/the_loop_setup.py`. The canonical public source is [`scripts/the_loop_setup.py`](https://github.com/System-Error-Worldwide/the-loop/blob/main/scripts/the_loop_setup.py), and the receipt contract is [`install-receipt.schema.json`](https://github.com/System-Error-Worldwide/the-loop/blob/main/schemas/install-receipt.schema.json).

## Evidence

- Dry-run plan and selected adapter manifests.
- Applied or rolled-back install receipt.
- Setup tests covering collision refusal, exact approval, interruption, changed output, shipping-link rejection, and bounded unchanged-package link proof.

## Halt conditions

Stop with a precise error when no selected harness is installed, an adapter is missing or invalid, a path escapes its root, any path crosses a symlink, a source or destination changed after planning, link support is not proven, or an exact collision approval is absent.

Setup does not read credential files, collect prompts, send telemetry, or publish anything.
