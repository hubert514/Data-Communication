# Scheduler design and interface gate

**TODO / NOT IMPLEMENTED:** B1 project scenario, P1, P2, instrumentation,
approved extension strategy, and frozen engineer-to-engineer contract.
README Sections 2–7 are authoritative; PM decides requirement changes.

- B1: preserve upstream `RrMultiUserScheduler` airtime-priority behavior.
- P1: actual oldest eligible LL packet queue age / deadline; trial urgency 0.5;
  deterministic ties, eligible nonempty stations only, upstream RR fill, same RU rules.
- P2: deterministic overdue-BE service guard; pending traffic required; log
  interventions; distinguish scheduled service from ACK/delivery.
- Both classes use the same AC initially. Mixed AC and adaptive RU are separate
  PM-approved stretch experiments. No hard-deadline guarantee is claimed.
- If enqueue timestamps cannot be observed safely, document the limitation and
  obtain PM approval for an explicitly named service-age-aware fallback.

## A/B contract checklist — PM approval required before parallel implementation

- [ ] Exact tag/SHA, compiler and patch/overlay installation method.
- [ ] One simulation entry point (TODO) and canonical config schema (proposed
  `configs/checkpoint.json`; no reader is implemented).
- [ ] Selectors `rr`, `latency`, `fairness`; reject unimplemented selectors.
- [ ] LL/BE flow, STA, recipient, UDP-port mapping; proposed values await review.
- [ ] Warm-up, measurement window, application stop and drain definitions.
- [ ] README output schemas and layer/loss/deadline denominator definitions.
- [ ] Versioned fields distinguish implemented, planned, and unavailable values.
- [ ] Precise decision function, eligible queue metadata, extension strategy:
  supported subclass hooks or maintained upstream patch; preserve licenses.

Evidence/decision log: TODO — source paths + line references in pinned commit,
probe command/output, selected strategy, PM review URL and date.

The pending decision register and written Nov 10 feasibility gate are tracked in
[PM_DECISIONS.zh-TW.md](PM_DECISIONS.zh-TW.md). D02–D08 identify evidence owners,
dependencies and the items needed to freeze this contract. The register is not
an approval of any currently unresolved technical choice.
