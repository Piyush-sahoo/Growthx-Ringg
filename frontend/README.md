# Frontend — Next.js (Voice Agent Console)

Dashboard to trigger Ringg AI outbound calls and review call outcomes
(status, transcript, recording) that arrive via the backend webhook.

## Run locally

```bash
cd frontend
npm install
cp .env.example .env.local   # set NEXT_PUBLIC_API_URL to your backend
npm run dev
```

Open http://localhost:3000. The backend must be running (default
`http://localhost:8000`).

## Scripts

- `npm run dev` — dev server
- `npm run build` — production build
- `npm start` — serve the production build
- `npm run lint` — ESLint

## Config

| Env var               | Purpose                          | Example                 |
|-----------------------|----------------------------------|-------------------------|
| `NEXT_PUBLIC_API_URL` | Base URL of the FastAPI backend  | `http://localhost:8000` |

## Deploy

Deploys to Vercel. Set `NEXT_PUBLIC_API_URL` to your Render backend URL in the
Vercel project's Environment Variables. CI/CD workflow:
`.github/workflows/frontend-deploy.yml`.
