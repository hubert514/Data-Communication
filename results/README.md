# Output contract and storage policy

The official-example scheduler checkpoint now has real local candidate-age and
RU-allocation CSVs under `.local/scheduler-checkpoint/`; its provenance and
verified summary are indexed by `docs/evidence/b-scheduler-01/MANIFEST.md`.
The project 4 LL / 4 BE empirical pipeline is implemented by
`scripts/mixed_traffic_checkpoint.py`. Its first seed-1 E1/E2 summaries and raw
checksums are indexed by `docs/evidence/b-mixed-traffic-01/MANIFEST.md`.
Do not create dummy measurements. Local setup/build evidence lives in
`.local/evidence/`; preserve/share real evidence and add its location to issues.
Results are ignored by default. Explicitly select small real outputs only after
provenance review; use durable external storage for large raw data/PCAPs and
commit the manifest, checksum and accessible location. Never commit binaries or
the full upstream tree. Synthetic fixtures, if ever needed, must say so.

Initial schemas from README (PM-approved migration/PR required for changes):

```text
flows.csv:
run_id,flow_id,traffic_class,src,dst,tx_packets,rx_packets,rx_payload_bytes,throughput_mbps,mean_delay_ms,loss_count

packets.csv:
run_id,flow_id,packet_id,traffic_class,tx_time_s,rx_time_s,delay_ms,status

scheduler_decisions.csv:
run_id,time_s,scheduler,eligible_sta_ids,selected_sta_ids,ru_allocation,urgent_sta_ids,fairness_override
```

Optional queue ages must be marked observed or unavailable. Missing/expired
packets have explicit status and no fabricated RX timestamps. Define metric
layers, units, windows, drain, loss handling and deadline denominator before use.

`run_metadata.json`: exact upstream/project SHA, toolchain/OS, full config,
scheduler, seed/run, exact invocation, timestamps, outcome, file checksums.
Bootstrap tooling emits an operation-specific metadata schema. Project runs
emit `mixed-traffic-run-v1` metadata plus packet-, flow-, class-, queue-age-,
scheduler-, and PHY-layer outputs.
