# Acceptance tests

Implemented bootstrap safety checks: `python -m unittest discover -s tests -v`
uses temporary Git repositories without network access to check idempotency,
patch additions, exact pins, and preservation of unexpected local work.

TODO / NOT IMPLEMENTED: project behavior/regression tests. The official example
execution helper is `scripts/smoke_ofdma.sh`; it does not itself certify DL MU.

Required later: reproducible build; actual DL MU/STA/RU evidence; RR regression;
crafted P1 urgency ordering; crafted P2 BE intervention without duplicates or
empty/invalid allocations; timestamps/classification/loss denominators; chart
reproduction. Record command, outcome and evidence for each PM acceptance gate.
