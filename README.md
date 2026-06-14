# Growthx-Ringg

A voice-agent app for the **GrowthX × Ringg AI Voice AI Buildathon**. The frontend
triggers Ringg AI outbound calls; the backend places the calls and ingests post-call
webhooks (transcript, recording, analysis).

## Structure

```
.
├── info/        # Full archive of the buildathon handbook + Ringg AI skill reference
├── frontend/    # Next.js dashboard (Voice Agent Console)
├── backend/     # FastAPI service (Ringg calls + webhook ingestion)
└── .github/workflows/   # CI + deploy (Vercel / Render)
```

## Quick start

```bash
# Backend
cd backend && python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env          # add RINGG_API_KEY, RINGG_ASSISTANT_ID, RINGG_FROM_NUMBER_ID
uvicorn app.main:app --reload # http://localhost:8000/docs

# Frontend (new terminal)
cd frontend && npm install
cp .env.example .env.local    # NEXT_PUBLIC_API_URL=http://localhost:8000
npm run dev                   # http://localhost:3000
```

See [`backend/README.md`](backend/README.md) and [`frontend/README.md`](frontend/README.md).

## Architecture

```
Frontend (Next.js/Vercel) ──POST /calls──▶ Backend (FastAPI/Render) ──▶ Ringg AI API
        ▲                                          ▲
        └──────── GET /calls (history) ────────────┘
                                            Ringg ──POST /webhooks/ringg──▶ Backend
                                            (transcript, recording, analysis)
```

## CI/CD

GitHub Actions in [`.github/workflows`](.github/workflows):

| Workflow | Trigger | Action |
|----------|---------|--------|
| `backend-ci.yml`  | PR / push to `backend/**`  | ruff + pytest |
| `frontend-ci.yml` | PR / push to `frontend/**` | eslint + next build |
| `backend-deploy.yml`  | push to `main` | Render deploy hook (gated by `vars.ENABLE_RENDER_DEPLOY`) |
| `frontend-deploy.yml` | push to `main` | Vercel deploy (gated by `vars.ENABLE_VERCEL_DEPLOY`) |

Deploy workflows are **off until you set the secrets/variables** (see each workflow
header). CI (lint/test/build) runs immediately.

### Required secrets / variables

- **Vercel:** secrets `VERCEL_TOKEN`, `VERCEL_ORG_ID`, `VERCEL_PROJECT_ID`; variable `ENABLE_VERCEL_DEPLOY=true`.
- **Render:** secret `RENDER_DEPLOY_HOOK_URL`; variable `ENABLE_RENDER_DEPLOY=true`. Backend env via `render.yaml`.

## Handbook

The complete buildathon handbook (rules, scoring, Ringg AI docs, build stack,
submission/demo guidance, FAQ, terms) plus the Ringg AI skill reference is archived in
[`info/`](info/README.md).

## Status

- [x] Handbook content archived in `info/`
- [x] Backend scaffold (FastAPI) — tests + lint green
- [x] Frontend scaffold (Next.js) — production build green
- [x] CI/CD workflows (Vercel + Render)
