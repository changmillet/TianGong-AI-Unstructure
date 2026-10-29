# Single SCI PDF integration probe

This is an operator-run test, not a new production mode. It reuses the existing
`kb_parse_queue`, enqueue/claim/heartbeat RPCs, `ParseWorker.process_message`,
HTTP parser adapter, and configured local Unstructure-Serve service. The only
substituted boundary is `write_processed_artifacts_from_parsed`: the test
captures parser output before embedding, publishes three inspection artifacts,
and stops the worker there. It never exercises embedding or cloud handoff.

Run from the repository root with the existing Python environment:

```sh
python -m tests.manual.sci_probe.cli --env-file /absolute/runtime/.env \
  --document-id SCI_UUID --run-id NEW_RUN_UUID --owner-id EXISTING_OPERATOR_UUID \
  --pdf-root /absolute/docs/journals --legacy-root /absolute/docs/processed_docs \
  --output-root /absolute/docs/processed/sci --parser-version VERIFIED_SERVICE_REVISION
```

Default is read-only. Add `--execute` for the single bounded test. It requires
an existing SCI row and readable PDF, no filename-matched historical PKL, and no
existing KB document, input alias or output run. UUID remains `journals.id`.
The test creates a canonical symlink under `NAS_RAW_ROOT/sci_parse_probe/`;
it never renames, edits or deletes the original PDF. The dedicated test
collection retains files (`archive_only`). Its normal database trigger may
assign a search partition; no index job or S3-ready transition is requested.

Registration calls the existing enqueue RPC and reserves **only this job's**
message with real conditional `pgmq.read` before committing; other messages
are not consumed. The existing Worker claims that message and maintains its
lease. `max_attempts=1` bounds failures without automatic retries. Successful
parser output becomes `parsed.pkl` (no vector fields), `fulltext.txt`, and
`manifest.json` under `UUID/run_id`. Manifest identity, sizes and SHA256 are
verified before a test-only receipt transaction marks the parse job succeeded,
document parsed and archives this queue message. No S3-ready job is created.
SCI rows are SELECT-only and compared in full before/after.

The test is deliberately not an unattended ingestion implementation. If it is
interrupted after registration, do not blindly rerun or start background
workers: inspect its job, queue lease and output directory first. If output is
published but the receipt fails, preserve the files and repair only that run's
receipt after checking its ownership. A killed process can leave its message
visible after the lease expires. Keep the original input and generated evidence;
Ordinary caught failures cancel/archive only this test job. SIGKILL or a lost
database connection can still require operator recovery. Cleanup is a separate
operator decision. The test does not establish NAS-to-S3
readiness, complete document fidelity, embedding quality or search availability.

Validation: `python -m unittest tests.test_sci_parse -v`. These tests verify
identity/hashes, no vectors, no overwrite, incomplete writes, DOI paths, and
that the existing Worker reaches the parser then stops before embedding.
Live run evidence belongs in ignored `analysis/`, never in Git.
