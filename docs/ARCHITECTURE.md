# Architecture

## Purpose

Job-App Helix is a small, inspectable example of a larger systems principle: components become valuable when their outputs are explicit, their verification is independent, and their composition produces a decision a human can understand.

## Runtime flow

```text
scenario evidence
      |
      v
flight piston ----\
propulsion piston ----> initial campaign decision
 ground piston ----/
      |
      | only when declared contingency evidence exists
      v
one transparent refinement stroke
      |
      v
final verification -> GO or NO-GO -> JSON proof receipt
```

## Design decisions

### Immutable evidence

Scenario inputs and results use frozen dataclasses. Assessments do not mutate their inputs, which keeps the causal record inspectable.

### Fail-closed decisions

A campaign can proceed only when every final stage is acceptable. An unhandled failure remains a `NO-GO` rather than being converted into a warning.

### Declared contingencies only

The refinement layer cannot invent capacity, telemetry, or a better propulsion profile. It may consume only backup evidence explicitly supplied with the scenario.

### Human and machine surfaces

The CLI explains findings in plain language. The same report serializes to JSON for automation, CI artifacts, or downstream analysis.

## Extension points

A new piston should provide:

1. A typed input model.
2. A deterministic assessment function returning `StageResult`.
3. Stable finding codes.
4. Documented metrics and limits.
5. An optional refinement function that consumes declared contingency evidence.
6. Tests covering nominal, warning, failure, and invalid input behavior.

## Public versus local orchestration

The public package is the reproducibility boundary. Larger private or local workspaces may connect additional repositories and tools, but those integrations must remain optional adapters. A clean clone of this repository must always install, test, and execute without them.
