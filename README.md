# factory-workflow-eval

Pilot repo for Dify software factory workflow validation

Validation marker: 2026-02-24T21:08:14Z

## Health Endpoint (Pilot)

Run server:

```bash
python3 app/health_server.py
```

Smoke tests:

```bash
curl -sS http://127.0.0.1:8000/health
curl -sS http://127.0.0.1:8000/health/details
```

Run tests:

```bash
python3 -m unittest discover -s tests -v
```
