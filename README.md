# SYSTEM ERROR'S THE LOOP

An autonomous agentic skill pack for Codex, Claude Code, Kimi Code, OpenCode and
DeepSeek Harness.

Created and maintained by Moses Mawila through System Error Worldwide.

THE LOOP gives an agent a complete path from a rough objective to tested work and a
clean handoff. It installs 31 portable skills, detects qualified specialists already
available in the host harness, and keeps a bundled System Error fallback for every
capability in the pack.

## What ships in v0.1

- All 31 portable `SKILL.md` packages.
- Attended, Auto, Parallel, Cloud and Endless operating modes.
- Setup, Doctor, Watch, Control, Autonomy, skill planning and skill creation.
- Strategize, Spec-pack, Build, Test and Resolve lifecycle stages.
- Health-check, Audit and Portfolio Review feeders.
- Grounding, quality, memory, handoff and Close utilities.
- Five thin harness adapters that preserve the host's permission decisions.
- An offline toolkit with the protocols, schemas and Python runtime used by the pack.
- Synthetic code and non-code examples plus a deterministic five-harness contract suite.

The exact package list and provenance class for every skill are recorded in the
[v0.1 shipping manifest](docs/provenance/v0.1-shipping-manifest.md).

## How it works

The attended lifecycle is:

`Strategize -> Spec-pack -> Build -> Test <-> Resolve -> Close`

THE LOOP routes each stage by capability and recorded evidence. If a compatible,
verified specialist is installed, the harness can use it. Otherwise the bundled
fallback executes the same stage contract. Code and non-code work use the same issue,
evidence, authority and close rules.

The modes change how work is supervised:

| Mode | Use it for |
| --- | --- |
| `the-loop` | One attended lifecycle with visible stage gates. |
| `the-loop-auto` | One declared asset driven to green or to a configured gate. |
| `the-loop-parallel` | Independent lanes with explicit ownership and one integration join. |
| `the-loop-cloud` | Planning, drafting and handoff in a restricted or remote environment. |
| `the-loop-endless` | Repeated bounded Auto missions selected from an approved queue. |

Endless never invents work when its queue is empty. Auto and Endless do not weaken
approval, budget, lease, evidence or kill-switch requirements.

## Quickstart

Prerequisites: Python 3.9 or newer and at least one supported harness executable.

```sh
git clone https://github.com/System-Error-Worldwide/the-loop.git
cd the-loop
mkdir -p /path/to/project

# 1. Inspect the installation plan. This does not write to the target.
python3 scripts/the_loop_setup.py \
  --target-root /path/to/project \
  --harness codex \
  --json

# 2. Apply the plan and write a private installation receipt.
python3 scripts/the_loop_setup.py \
  --target-root /path/to/project \
  --harness codex \
  --apply \
  --actor local-user \
  --source-version 0.1.0 \
  --json

# 3. Verify the installed pack from its offline toolkit.
python3 /path/to/project/.the-loop/toolkit/scripts/the_loop_doctor.py \
  --project-root /path/to/project \
  --json
```

Choose `codex`, `claude_code`, `kimi_code`, `opencode` or `deepseek_harness` for
`--harness`. Setup refuses a different file already present at a destination unless
that exact destination is approved with `--approve-destination`. It does not collect
prompts or send telemetry.

The applied installation contains the skills and a namespaced offline toolkit at
`.the-loop/toolkit`. The project does not need the source checkout or a network
connection for core operation after installation.

### Invoke THE LOOP

| Harness | Explicit invocation |
| --- | --- |
| Codex | Select or mention `$the-loop` |
| Claude Code | Run `/the-loop` |
| Kimi Code | Run `/skill:the-loop` |
| OpenCode | Ask the agent to load `skill(the-loop)` |
| DeepSeek Harness | Run `/the-loop` |

Start with the attended mode. Move to Auto after defining the asset, done gate,
budgets, authority and kill switch.

### Roll back an installation

```sh
python3 /path/to/project/.the-loop/toolkit/scripts/the_loop_setup.py \
  --rollback-receipt /path/to/project/.the-loop/installs/RECEIPT_ID.json \
  --target-root /path/to/project \
  --json
```

Rollback removes only unchanged files owned by that receipt. Modified files are kept
and reported instead of being overwritten or deleted.

For a user-level install, use the same dry-run and apply sequence with
`--scope user --target-root "$HOME"`. Setup chooses one documented skill root for the
selected harness and avoids duplicate copies across its search paths.

## Supported harnesses

The repository includes adapters for:

- Codex
- Claude Code
- Kimi Code
- OpenCode
- DeepSeek Harness

Setup detection, installation layout, skill discovery and portable contract behavior
are covered by the repository test and conformance suites for all five adapters.
Provider authentication, model availability and the host's own runtime remain host
concerns; THE LOOP never bypasses their denial or permission settings. Dated probe
reports live under [docs/release](docs/release/README.md).

## Safety model

- Outward actions, strategic expansion and self-modification require approval by
  default.
- Elevated authority names its actor, scope, confirmation time, expiry and reversal
  path.
- Run ownership, leases, evidence, audit history and faithful failure reporting remain
  mandatory.
- A kill switch can halt work without granting a replacement worker authority.
- Repeated missions stay individually bounded by configured duration, token, action,
  attempt and cost gates.

These invariants apply at every autonomy level, including full autonomy.

## Contract conformance

The deterministic conformance runner installs and diagnoses the complete pack in five
synthetic harness projects and validates 12 locked scenarios per adapter:

```sh
mkdir -p /tmp/the-loop-contract-check
python3 scripts/run_conformance.py \
  --project-root /tmp/the-loop-contract-check
```

That is a 60-scenario portable contract check. It verifies installation, discovery,
fallback structure, lifecycle artifacts and safety assertions without spending model
tokens or changing harness configuration.

See the [code example](examples/code/README.md) and
[non-code example](examples/noncode/README.md).

## Repository map

- [Provenance and licensing](PROVENANCE.md)
- [v0.1 shipping manifest](docs/provenance/v0.1-shipping-manifest.md)
- [Product specification](docs/specs/README.md)
- [Shared protocols](protocols/README.md)
- [Schemas](schemas/README.md)
- [Release data](docs/release/README.md)
- [Contributing](CONTRIBUTING.md)
- [Security policy](SECURITY.md)

## Development validation

```sh
python3 scripts/validate_repository.py
python3 scripts/validate_protocols.py
python3 -m unittest discover -s tests -p 'test_*.py'
python3 scripts/run_conformance.py --project-root /tmp/the-loop-contract-check
```

The repository validator scans public files, the Git index, reachable history, commit
metadata and symlink targets for blocked private material and credential patterns.

## Licence and security

System Error original and clean-room rewrite work in this repository is released under
the [MIT License](LICENSE). Provenance classes describe lineage, not different usage
rights. Third-party dependencies remain under their own licences and are not copied
into this repository without an approved record.

Report vulnerabilities through [SECURITY.md](SECURITY.md). Do not publish credentials,
private infrastructure details or exploit material in a public issue.
