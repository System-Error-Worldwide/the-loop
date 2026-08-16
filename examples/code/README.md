# Synthetic code example

This example asks THE LOOP to: **Add a deterministic slug validator to a synthetic Python utility.**

It demonstrates the code track without identifying a real repository, customer, or
incident. The attended run first records live repository state and an approved
single-function slice. Build works on an isolated branch, Test captures a failing
focused test before the implementation and passing focused and full suites after it,
and Close reviews the final diff before reporting green.

The run halts instead of widening scope when it encounters an overlapping dirty file,
an outward action, a data-model change, or a failing full suite. The machine-readable
fixture is at
[`tests/fixtures/conformance/assets/code.json`](../../tests/fixtures/conformance/assets/code.json).
