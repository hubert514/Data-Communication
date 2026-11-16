# Upstream changes — Engineer B

`001-rr-queue-age-observation.patch` applies to ns-3.49 commit
`418210e8914e9f6bcb5cddbcc94a2cecb7853b68`. It adds observation-only RR
TraceSources, the example-side CSV sink, and a disabled-by-default,
class-agnostic queue-head-age prototype plus its deterministic test fixture.

Setup reads `series` in order. Patches retain upstream licenses and are kept
separate from the project repository so the pinned checkout remains
reconstructable.
