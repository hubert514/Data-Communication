# Scheduling — Engineer B

Implemented locally against pinned ns-3.49:

- observation-only RR candidate-age and final-RU TraceSources;
- example-side structured CSV sink;
- automated R0/R1/R2 behavior-equivalence checks;
- a disabled-by-default, class-agnostic queue-head-age prototype;
- a deterministic 8-STA/4-RU functional fixture.

See `docs/SCHEDULER_CHECKPOINT.zh-TW.md`. The upstream changes are exported as
`patches/001-rr-queue-age-observation.patch`; raw evidence stays under
`.local/scheduler-checkpoint/`.

NOT IMPLEMENTED: LL/BE-aware policy or project performance claims. These need
Engineer A's real 4 LL / 4 BE scenario and an agreed AID/TID/flow mapping.
