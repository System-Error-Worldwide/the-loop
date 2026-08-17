# Public and private boundary

## Public product

The repository may contain:

- Harness-neutral workflow contracts and schemas.
- Clean System Error skill implementations.
- Thin installation and invocation adapters for the five named harnesses.
- Synthetic examples that do not identify a person, customer, private project or incident.
- Local run state, lease, issue, evidence and audit formats.
- Tests, fixtures and release documentation.
- Creator attribution to Moses Mawila through System Error Worldwide.

## Private material

The repository must not contain:

- Personal or customer memory, portfolio state or internal project registries.
- Private source-vault paths, absolute home paths or machine-specific configuration.
- Private orchestration, monitoring, mirroring or liveness implementations.
- Private incident timelines, identifiers, postmortems or operational metrics.
- Private funding-source data, application material or vertical intelligence.
- Credentials, connectors, tokens, host aliases, addresses or private repository URLs.
- Hooks and scheduled jobs copied from the private operating environment.
- Vendor or community skill text without an explicit compatible licence and attribution path.

## Translation rule

Private experience may establish a requirement, such as “a run needs an expiring lease.” It may not supply public implementation text, private defaults, identifiers or examples. Public behavior is written from the specification and tested with synthetic fixtures.

## Repository hygiene

Automated release checks must scan tracked content and Git history for forbidden path fragments, credential patterns, private host data and known internal identifiers. Any match blocks release until reviewed.
