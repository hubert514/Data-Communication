# Technical PM status

**TODO / NOT IMPLEMENTED:** simulator baseline, P1/P2, empirical results,
checkpoint acceptance. Bootstrap assets are preparatory tooling only.

Technical PM has final authority over requirements, priorities, integration,
scope, schema changes, and acceptance. A/B own simulator C++; Report Lead owns
analysis and English presentation consistency. GitHub role-to-handle assignments
are TODO; issue bodies record role ownership without inventing identities.

| Window (Asia/Taipei) | Owner | Deliverable | State | Evidence |
|---|---|---|---|---|
| Nov 7–10 | Engineer A | Pin/build, official HE DL MU proof | TODO | TODO |
| Nov 7–10 | Engineer B | Queue metadata + extension feasibility | TODO | TODO |
| Nov 7–10 | Technical PM | Version/extension/interface decision | TODO | TODO |
| Nov 7–10 | Report Lead | Research questions, diagram, slide outline | TODO | TODO |
| Nov 11–13 | Engineer A | Mixed LL/BE B1 + authentic metrics | TODO | TODO |
| Nov 11–13 | Engineer B | Focused selection/instrumentation probe | TODO | TODO |
| Nov 11–13 | Technical PM | Baseline, classification and metrics QA | TODO | TODO |
| Nov 11–13 | Report Lead | Preliminary real-data plot/table | TODO | TODO |
| Nov 14–15 | Engineers A/B | Integration and recorded canonical command | TODO | TODO |
| Nov 14–15 | Technical PM | Smoke test, Nov 14 fallback decision | TODO | TODO |
| Nov 14–15 | Report Lead | 7–8 English slides and evidence audit | TODO | TODO |
| Nov 16–22 (date TBD) | Technical PM | Checkpoint sign-off and presentation readiness | TODO | TODO |

After checkpoint: M2 P1; M3 P2; M4 paired-seed E1–E4; M5 E5 and reproducible
figures; M6 source/manifest/English presentation/final report. Dates remain TODO
for PM, rather than invented semester deadlines.

## Active risks / decisions

- Candidate ns-3.49 build and DL MU runtime remain unverified; see ENVIRONMENT.
- Queue-age visibility and scheduler API extension remain unverified.
- Toolchain readiness, project license, handles, schema/timing/load values need review.
- **Nov 14:** freeze P1 features if B1 is unreliable; repair baseline/measurement.
- Service-age substitution, AC/RU changes and scientific claims require PM review.
- Branch protection and enforced reviews: TODO PM/admin configuration. Templates
  describe policy; they do not enforce approval technically.

Issue register: [ISSUES.md](ISSUES.md). Executed bootstrap validation and pending
gates: [BOOTSTRAP.md](BOOTSTRAP.md).

## Development handoff and version rules

- [Engineer A task handoff (Traditional Chinese)](ENGINEER_A_TASKS.zh-TW.md)
- [Engineer B task handoff (Traditional Chinese)](ENGINEER_B_TASKS.zh-TW.md)
- [Shared version control, ownership and delivery rules](DEVELOPMENT_WORKFLOW.zh-TW.md)

Bootstrap PR #13 was merged on 2026-11-07 under the user's explicit publication
instruction. Handoff/document review does not complete any scientific acceptance
gate or close the 12 checkpoint tasks; unknown toolchain, schema, runtime and
role-account decisions remain TODO.
