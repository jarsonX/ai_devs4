# L3 Proxy Tests

This directory groups L3_proxy verification by scenario.

## local_mvp

`local_mvp/test_local_mvp.py` runs repeatable local tests without real external services.

It does not call:

- OpenAI,
- the real packages API,
- the hub verification endpoint.

Run it with:

```powershell
.\venv\Scripts\python.exe tests/L3_proxy/local_mvp/test_local_mvp.py
```

Reports for this scenario are stored in:

```text
tests/L3_proxy/local_mvp/reports/
```

## openai_agent

`openai_agent/run_openai_agent_verification.py` uses the real OpenAI API with a fake packages API.

It does not call:

- the real packages API,
- the hub verification endpoint,
- any public tunnel.

It does use:

- `OPENAI_API_KEY` from `.env`,
- the configured OpenAI model,
- a hard `max_model_requests` guard.

Run it with:

```powershell
.\venv\Scripts\python.exe tests/L3_proxy/openai_agent/run_openai_agent_verification.py
```

Reports for this scenario are stored in:

```text
tests/L3_proxy/openai_agent/reports/
```
