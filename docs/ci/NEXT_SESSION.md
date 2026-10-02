# Next Session

The original CI sequence through Step 12 is complete. PR #1 was merged into
main, and the original foundation branch was fast-forwarded to the same merge
commit. Do not repeat Step 12 or infer current state from historical CI_STATE
entries.

The user then authorized sequential implementation of laboratory device
telemetry ingestion. Its work is isolated in `feat/device-ingestion-v1`, PR #2.

Read first:

1. `AGENTS.md`
2. `README.md`
3. `docs/device_ingestion/PROTOCOL_V1.md`
4. `docs/device_ingestion/IMPLEMENTATION.md`
5. `docs/device_ingestion/STAND_SETUP.md`

Before any further change, inspect actual Git refs, PR #2, the exact head SHA,
both GitHub Actions jobs and artifacts for that SHA. Report differences rather
than manufacturing a self-referential handoff commit.

The next operational milestone is selecting an explicitly authorized development
Supabase target and API host, applying the reviewed migrations, provisioning
runtime/device credentials, and installing a real sensor adapter. The supplied
agent targets Linux/Python, not ESP32 firmware. Software test data is not proof
of physical-device operation.

Do not merge PR #2, delete either branch, change protection, reset a remote
database, expose credentials, or deploy to an unidentified remote target without
specific user authorization. Keep required CI independent of hardware and
remote Supabase.
