# Upstream changes — Engineer B

Both patches apply to ns-3.49 commit
`418210e8914e9f6bcb5cddbcc94a2cecb7853b68`:

- `001-rr-queue-age-observation.patch` adds observation-only RR TraceSources,
  the official-example CSV sink, and a disabled-by-default class-agnostic
  queue-head-age prototype plus its deterministic test fixture.
- `002-mixed-traffic-checkpoint.patch` adds the project-specific 1 AP / 8 STA,
  4 LL / 4 BE downlink scenario and its application, scheduler, and PHY CSV
  observation points.

Setup reads `series` in order. Patches retain upstream licenses and are kept
separate from the project repository so the pinned checkout remains
reconstructable.
