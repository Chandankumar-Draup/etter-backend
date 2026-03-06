# Workforce Twin UI — Deployment Guide

## Architecture

The UI is a React SPA (Vite + TypeScript) deployed as a **separate EKS pod**.
It connects to two backend services on the same Etter backend:

| Service | Route prefix | Purpose |
|---|---|---|
| Workforce Twin API | `/api/v1/workforce-twin/*` | Simulation, cascade, snapshot, etc. |
| Etter Auth API | `/api/auth/*` | Token validation (`check_auth`) |

Both are configured via environment variables injected at container startup.

---

## Local Development

```bash
# Terminal 1: backend
uvicorn settings.server:etter_app --port 7071 --reload

# Terminal 2: UI
cd draup_world_model/workforce_twin_modeling/ui
npm install
npm run dev
```

- Vite dev server runs on `http://localhost:5173`
- Proxies `/api/*` → `http://localhost:7071/api/v1/workforce-twin/*`
- Proxies `/etter-api/*` → `http://localhost:7071/api/*` (for `check_auth`)
- No token required for local dev — works without auth when no token is in the URL

> `node_modules/` is gitignored. `npm install` fetches dependencies from `package.json`.

---

## Docker Build & Local Test

```bash
cd draup_world_model/workforce_twin_modeling/ui

# Build
docker build -t workforce-twin-ui .

# Run (point to local backend)
docker run -p 3000:3000 \
  -e API_BASE_URL=http://localhost:7071/api/v1/workforce-twin \
  -e ETTER_API_BASE=http://localhost:7071/api \
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

### Environment Variables

| Variable         | Required | Description                                  | Example                                       |
|------------------|----------|----------------------------------------------|-----------------------------------------------|
| `API_BASE_URL`   | Yes      | Full URL to workforce twin API base path     | `https://api.draup.com/api/v1/workforce-twin` |
| `ETTER_API_BASE` | Yes      | Full URL to etter backend root (for auth)    | `https://api.draup.com/api`                   |

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
      - name: ETTER_API_BASE
        value: "https://api.draup.com/api"
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

## Authentication

### Flow (Prod/QA)

1. User is redirected from `etter.draup.com` with token in URL: `https://<workforce-twin-host>/<token>`
2. `main.tsx` calls `extractTokenFromURL()` — saves token to `localStorage`, cleans URL to `/`
3. App calls `POST /auth/check_auth` (on etter backend) with `Bearer <token>` header
4. Backend validates token against Draup API, returns user info:
   ```json
   { "status": "Success", "data": { "email": "...", "company_name": "...", "company_id": 1, ... } }
   ```
5. User info cached in `localStorage` (key: `workforce_twin_user`)
6. All workforce twin API calls include `Authorization: Bearer <token>` header

### Flow (Local Dev)

- No token in URL → `getToken()` returns null → no `Authorization` header sent
- Backend `verify_token` dependency needs to be satisfied. Two options:
  - Run backend without the `Depends(verify_token)` (comment it out for local testing)
  - Manually set a token: open browser console → `localStorage.setItem('workforce_twin_token', '<your-token>')`

### Token in the URL

The token is the **first path segment** that doesn't match a known route
(`/`, `/explorer`, `/simulation`, `/nova`, `/deep-dive`).

```
https://workforce-twin.draup.com/eyJhbGciOiJIUzI1NiIsInR5cCI6...
                                 ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
                                 extracted → localStorage → URL cleaned to /
```

### Backend protection

The workforce twin router has `dependencies=[Depends(verify_token)]` at the
router level in `api/app.py`, so all endpoints are protected without needing
to add the dependency to each individual route handler.

---

## How Runtime Config Works

1. `docker-entrypoint.sh` writes env vars into `/app/config.js` at container startup
2. `index.html` loads `config.js` before the React bundle
3. `config.js` sets `window.__WORKFORCE_TWIN_API_BASE__` and `window.__ETTER_API_BASE__`
4. `src/api/client.ts` reads `__WORKFORCE_TWIN_API_BASE__` for workforce twin API calls
5. `src/auth.ts` reads `__ETTER_API_BASE__` for `check_auth` calls

One Docker image works for all environments — just change the env vars.

---

## API Endpoints Used by the UI

### Workforce Twin API (relative to `API_BASE_URL`)

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

### Etter Auth API (relative to `ETTER_API_BASE`)

| Method | Path               | Description                              |
|--------|--------------------|------------------------------------------|
| POST   | `/auth/check_auth` | Validate token, returns user/company info |

---

## CORS

The backend must allow requests from the UI's origin. The etter backend already has CORS middleware configured in `middleware/cors_middleware.py`. Ensure the UI's domain is allowed.
