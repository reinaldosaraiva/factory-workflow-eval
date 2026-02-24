# factory-workflow-eval

Pilot repository for Dify software factory workflow validation.

Validation marker: 2026-02-24T21:08:16Z

## Health Endpoint (Pilot)

Run server:

```bash
python3 app/health_server.py
```

Smoke test:

```bash
curl -sS http://127.0.0.1:8000/health
```

Run tests:

```bash
python3 -m unittest discover -s tests -v
```
