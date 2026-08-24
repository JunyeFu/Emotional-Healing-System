# ADR-0025: Freeze the V-04 design tree before production

- Status: Accepted
- Date: 2026-08-24 +08:00
- Decision owner: Team director

## Context

V-04 was decomposed through 25 confirmed design nodes covering timeline, storyboard, conditions, preview inputs, visual assets, audio, rendering, distribution, review, and effort. Production without one aggregate baseline would force implementers to reconstruct the design from many discussion records and could introduce incompatible local interpretations.

## Decision

Close the current V-04 design decision tree and freeze `V-04_设计冻结与执行基线_v1.0.md` as the aggregate execution baseline.

The baseline is added to the independent V-04 task package. V-04 remains `READY`; design freeze does not claim that implementation, media generation, Unity runtime, formal build, or real-input integration has started.

Any later change to a frozen decision requires a new ADR, explicit impact analysis, and regeneration of the V-04 task package before implementation continues.

## Consequences

- Implementers receive one ordered execution contract plus the detailed node files.
- Conflicts are resolved against the declared authority order instead of conversation memory.
- The next state change is tied to real task claim and production start, not to design confirmation.
