# Output contract and storage policy

TODO / NOT IMPLEMENTED: no empirical CSVs or project result pipeline exists.
Do not create dummy measurements. Local setup/build/example evidence lives in
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
Bootstrap tooling emits an operation-specific metadata schema, with no claim
that the project experiment schema or measured outputs are implemented.
