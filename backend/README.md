# Backend — FastAPI (Ringg AI)

Triggers Ringg AI outbound voice calls and ingests post-call webhooks
(transcript, recording, analysis).

## Run locally

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env        # fill in RINGG_API_KEY + RINGG_ASSISTANT_ID
uvicorn app.main:app --reload
```

Open http://localhost:8000/docs for interactive API docs.

## Endpoints

| Method | Path             | Purpose                                            |
|--------|------------------|----------------------------------------------------|
| GET    | `/health`        | Liveness + whether Ringg is configured             |
| GET    | `/calls`         | Call history (newest first)                        |
| POST   | `/calls`         | Trigger one outbound Ringg call                    |
| GET    | `/calls/{id}`    | Single call record                                 |
| POST   | `/webhooks/ringg`| Ringg post-call webhook (transcript/recording/analysis) |

### Trigger a call

```bash
curl -X POST http://localhost:8000/calls \
  -H 'Content-Type: application/json' \
  -d '{"customer_name":"Asha Rao","phone_number":"+919812345678",
       "custom_args_values":{"plan":"Pro","amount":"499"}}'
```

Point your Ringg assistant's webhook at `POST {BACKEND_URL}/webhooks/ringg`
(see https://docs.ringg.ai/webhooks/payloads).

## Test & lint

```bash
pytest
ruff check .
```

## Deploy

Containerized via `Dockerfile`; Render blueprint in repo-root `render.yaml`.
Set `RINGG_API_KEY`, `RINGG_ASSISTANT_ID`, and `CORS_ORIGINS` (your Vercel URL)
as environment variables on the host.
