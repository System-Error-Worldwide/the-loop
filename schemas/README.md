# Runtime record schemas

These JSON Schema draft 2020-12 files define the v0.1 local-state records. The
Python helpers in `src/the_loop/` enforce the schemas plus cross-record rules
such as transitions, owner matching, digest chains and safe path resolution.
Mutation helpers require an explicit project root so state paths, symlinks and
owner-only runtime directories can be checked against a concrete boundary.

The package uses only the Python 3.11 standard library.
