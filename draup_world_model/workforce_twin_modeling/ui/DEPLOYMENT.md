# Workforce Twin UI — Deployment Guide

## Architecture

The UI is a React SPA (Vite + TypeScript) deployed as a **separate EKS pod**.
It connects to the Etter backend API which serves workforce twin routes at:

```
<backend-host>/api/v1/workforce-twin/*
```

The API base URL is injected at container startup via the `API_BASE_URL` environment variable.

---

## Local Development

```bash
cd draup_world_model/workforce_twin_modeling/ui
npm install
npm run dev
```

- Vite dev server runs on `http://localhost:5173`
- Proxies `/api/*` → `http://localhost:8000` (configured in `vite.config.ts`)
- Requires the backend running locally (`uvicorn settings.server:etter_app --port 8000`)

> `node_modules/` is gitignored. `npm install` fetches dependencies from `package.json`.

---

## Docker Build & Local Test

```bash
cd draup_world_model/workforce_twin_modeling/ui

# Build
docker build -t workforce-twin-ui .

# Run (point to your local or remote backend)
docker run -p 3000:80 \
  -e API_BASE_URL=http://localhost:7071/api/v1/workforce-twin \
  workforce-twin-ui
```

Open `http://localhost:3000`.

---

## EKS Deployment

### Container

| Item       | Value                                           |
|------------|--------------------------------------------------|
| Image      | `workforce-twin-ui:<tag>`                        |
| Port       | `3000`                                           |
| Entrypoint | `/docker-entrypoint.sh` (generates `config.js`)  |

### Environment Variable

| Variable       | Required | Description                              | Example                                                  |
|----------------|----------|------------------------------------------|----------------------------------------------------------|
| `API_BASE_URL` | Yes      | Full URL to workforce twin API base path | `https://api.draup.com/api/v1/workforce-twin`            |

### Pod Spec Example

```yaml
containers:
  - name: workforce-twin-ui
    image: workforce-twin-ui:latest
    ports:
      - containerPort: 3000
    env:
      - name: API_BASE_URL
        value: "https://api.draup.com/api/v1/workforce-twin"
```

### Health Check

```yaml
livenessProbe:
  httpGet:
    path: /
    port: 3000
  initialDelaySeconds: 5
readinessProbe:
  httpGet:
    path: /
    port: 3000
  initialDelaySeconds: 3
```

---

## API Endpoints Used by the UI

All paths are relative to `API_BASE_URL`:

| Method | Path                              | Description              |
|--------|-----------------------------------|--------------------------|
| GET    | `/health`                         | Health check             |
| GET    | `/org`                            | Full org data            |
| GET    | `/org/hierarchy`                  | Org tree                 |
| GET    | `/org/functions`                  | Functions list           |
| GET    | `/org/roles/{role_id}`            | Role details             |
| GET    | `/org/tools`                      | Tech stack               |
| GET    | `/snapshot`                       | Gap analysis             |
| GET    | `/snapshot/function/{name}`       | Function gap             |
| GET    | `/snapshot/role/{role_id}`        | Role gap                 |
| GET    | `/snapshot/opportunities`         | Top opportunities        |
| POST   | `/cascade`                        | Run cascade              |
| POST   | `/simulate`                       | Run simulation           |
| POST   | `/simulate/preset/{id}`           | Run preset scenario      |
| GET    | `/simulate/presets`               | List presets             |
| GET    | `/scenarios/catalog`              | Scenario catalog         |
| POST   | `/scenarios/run`                  | Batch run scenarios      |
| POST   | `/scenarios/run-single/{id}`      | Run single scenario      |
| POST   | `/compare`                        | Compare scenarios        |

---

## How Runtime Config Works

1. `docker-entrypoint.sh` writes `API_BASE_URL` into `/app/config.js` at startup
2. `index.html` loads `config.js` before the React bundle
3. `config.js` sets `window.__WORKFORCE_TWIN_API_BASE__`
4. `src/api/client.ts` reads from `window.__WORKFORCE_TWIN_API_BASE__` (falls back to `/api`)

This means: **one Docker image works for all environments** — just change the env var.

---

## Authentication

All API endpoints require a Bearer token (`Authorization: Bearer <token>` header).
The backend uses the same `verify_token` mechanism as the rest of the Etter app.

### How token flows

1. User receives a link: `https://<workforce-twin-host>/<token>`
2. UI extracts the token from the URL path on load (`src/auth.ts`)
3. Token is saved to `localStorage` (key: `workforce_twin_token`)
4. URL is cleaned to `/` (via `history.replaceState`)
5. All subsequent API calls include `Authorization: Bearer <token>` header

### Token in the URL

The token is the **first path segment** that doesn't match a known route
(`/`, `/explorer`, `/simulation`, `/nova`, `/deep-dive`).

Example:
```
https://workforce-twin.draup.com/eyJhbGciOiJIUzI1NiIsInR5cCI6...
                                  ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
                                  this gets extracted and stored
```

After extraction, the URL becomes `https://workforce-twin.draup.com/`.

### Backend protection

The workforce twin router has `dependencies=[Depends(verify_token)]` at the
router level in `api/app.py`, so **all endpoints** are protected without needing
to add the dependency to each individual route handler.

---

## CORS

The backend must allow requests from the UI's origin. The etter backend already has CORS middleware configured in `middleware/cors_middleware.py`. Ensure the UI's domain is allowed.
