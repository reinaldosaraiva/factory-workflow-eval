# factory-workflow-eval

Pilot repo for Dify software factory workflow validation

Validation marker: 2026-02-24T21:08:14Z

## Health Endpoint (Pilot)

Run server:

```bash
python3 scripts/apply_migrations.py
python3 app/health_server.py
```

Smoke tests:

```bash
curl -sS http://127.0.0.1:8000/health
curl -sS http://127.0.0.1:8000/health/details
curl -sS http://127.0.0.1:8000/health/ready
curl -sS http://127.0.0.1:8000/metrics
```

Notes API:

```bash
curl -sS -X POST http://127.0.0.1:8000/notes \
  -H 'Content-Type: application/json' \
  -d '{"title":"First note","content":"Created in pilot 3"}'
curl -sS http://127.0.0.1:8000/notes
```

Persistence config:

```bash
export NOTES_DB_PATH=/tmp/factory-pilot-notes.db
python3 scripts/apply_migrations.py
```

Observability:

```bash
# endpoint de contadores internos
curl -sS http://127.0.0.1:8000/metrics
# logs estruturados JSON aparecem no stdout do servidor (event=http_request)
```

Not-ready simulation:

```bash
READY_DB=false curl -sS http://127.0.0.1:8000/health/ready
```

Run tests:

```bash
python3 -m unittest discover -s tests -v
```

Run quality/security baseline (local, same as CI gate):

```bash
scripts/quality/run_quality_security_checks.sh
```

Run coverage gate (local, same threshold as CI):

```bash
python3 -m pip install coverage
scripts/quality/run_coverage_gate.sh 70
```

PR body evidence template (required for factory PRs):

```md
## Execution Evidence
- Command: `scripts/quality/run_quality_security_checks.sh`
- Result: `PASS (all checks passed)`
- Command: `scripts/quality/run_coverage_gate.sh 70`
- Result: `PASS (TOTAL >= 70%)`
```

PR traceability template (required for factory PRs):

```md
## Traceability
- Issue URL: https://github.com/<org>/<repo>/issues/<number>
- PR URL: https://github.com/<org>/<repo>/pull/<number>
- Run URL: https://github.com/<org>/<repo>/actions/runs/<run_id>
```

PR agent plan template (required for factory PRs):

```md
## Agent Plan
- AGENT_BACKEND_STATUS: PLANNED
- AGENT_FRONTEND_STATUS: N/A
- AGENT_QA_STATUS: PLANNED
- AGENT_FRONTEND_JUSTIFICATION: repository has no frontend tree in pilot scope
```

When `factory` PR checks run, these values drive the execution of CI jobs: `agent_backend`, `agent_frontend`, and `agent_qa`.
If any agent status is `N/A`, include the corresponding `AGENT_<NAME>_JUSTIFICATION` with a non-placeholder reason.
`N/A` justification must have at least 15 non-space characters and mention scope context (`backend/api`, `frontend/web`, or `qa/test`).

PR evidence records template (required for factory PRs):

```md
## Evidence Records
- EVIDENCE_SCHEMA_VERSION: v1
- EVIDENCE_COMMAND_1: scripts/quality/run_quality_security_checks.sh
- EVIDENCE_RESULT_1: PASS (all checks passed)
- EVIDENCE_ARTIFACT_1: local-terminal-output
- EVIDENCE_COMMAND_2: scripts/quality/run_coverage_gate.sh 70
- EVIDENCE_RESULT_2: PASS (TOTAL 90% >= 70%)
- EVIDENCE_ARTIFACT_2: local-terminal-output
```

`EVIDENCE_RESULT_n` format: `PASS|FAIL|WARN|SKIP` with optional details in parentheses.
If `EVIDENCE_RESULT_n` is `FAIL` or `WARN`, `EVIDENCE_ARTIFACT_n` must be a concrete artifact (not `local-terminal-output`, `none`, `n/a`, or `na`).
For `FAIL|WARN`, use artifact as `http(s)://...` or file path with extension (for example: `reports/error-log.txt`).
Within the same PR, `EVIDENCE_COMMAND_n` and `EVIDENCE_ARTIFACT_n` values must be unique across indexes.

Policy validation marker: 2026-02-24T22:59:33Z

Auto-merge validation marker: 2026-02-24T23:06:04Z

Merge API validation marker: 2026-02-24T23:14:39Z

Operational update marker: 2026-02-24T23:17:41Z
