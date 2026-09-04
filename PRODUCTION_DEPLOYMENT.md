# Production Deployment Guide

This guide covers the recommended deployment pattern for a production instance of the Health Tracker app behind a reverse proxy with HTTPS enabled.

## 1. Runtime requirements

- Python 3.10+
- MongoDB 7.x or a reachable MongoDB service
- Gunicorn as the production WSGI server
- Reverse proxy such as Nginx or Caddy terminating TLS
- A real `SECRET_KEY` in production

## 2. Environment configuration

Create a production environment file from the example:

```powershell
Copy-Item .env.production.example .env.production
```

Then fill in the real values:

```dotenv
APP_ENV=production
SECRET_KEY=replace-with-a-long-random-secret
SESSION_COOKIE_SECURE=True
SESSION_COOKIE_SAMESITE=Lax
SESSION_COOKIE_HTTPONLY=True
SESSION_LIFETIME_MINUTES=30
SESSION_REFRESH=True
CSRF_PROTECTION=True
MONGO_URI=mongodb://health-tracker-mongo:27017/health_tracker
MONGO_DB_NAME=health_tracker
DEBUG=False
DEVELOPER_MODE=False
SHOW_API_OUTPUT=False
USDA_API_KEY=
EXERCISEDB_API_KEY=
GROQ_API_KEY=
```

## 3. Production app startup

The app is meant to run behind Gunicorn and not via Flask's debug server in production.

Example:

```bash
gunicorn --config gunicorn.conf.py wsgi:app
```

The project also includes a containerized path:

```powershell
docker compose --env-file .env.production -f docker-compose.yml -f docker-compose.production.yml up --build -d
```

## 4. Reverse proxy and HTTPS

The app trusts forwarded headers via Werkzeug `ProxyFix` so a reverse proxy can terminate TLS correctly:

```python
from werkzeug.middleware.proxy_fix import ProxyFix
app.wsgi_app = ProxyFix(
    app.wsgi_app,
    x_for=1,
    x_proto=1,
    x_host=1,
    x_port=1,
    x_prefix=1,
)
```

This ensures Flask sees the correct scheme, host, and forwarded client information when running behind Nginx/Caddy.

Example Nginx config:

```nginx
server {
    listen 80;
    server_name app.example.com;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl;
    server_name app.example.com;

    ssl_certificate     /etc/letsencrypt/live/app.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/app.example.com/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:5001;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;
        proxy_set_header X-Forwarded-Host $host;
        proxy_set_header X-Forwarded-Port 443;
    }
}
```

## 5. Health checks

The app exposes these deployment probes:

- `/api/health` — general liveness status
- `/api/health/live` — simple liveness endpoint
- `/api/health/ready` — readiness check for load balancers and orchestration

Expected readiness behavior:

- `200 OK` when the app has a valid secret and is ready to serve traffic
- `503 Service Unavailable` when production is missing required readiness conditions

Example:

```bash
curl -fsS https://app.example.com/api/health/ready
```

## 6. Security checklist

Before exposing the service publicly:

- set a strong `SECRET_KEY`
- enable HTTPS only
- set `SESSION_COOKIE_SECURE=True`
- use a non-default MongoDB connection
- keep `.env` and `.env.production` out of version control
- set `DEBUG=False`
- keep API keys only where needed

## 7. Operational notes

- MongoDB should be reachable from the app container or host.
- If MongoDB is not available in production, the app will not be considered ready.
- Cache and rate-limit settings are configured via env vars in `CONFIGURATION.md`.
- Logs can be checked with Docker or Gunicorn console output.

## 8. Useful commands

Start with Gunicorn:

```bash
gunicorn --config gunicorn.conf.py wsgi:app
```

With Docker:

```powershell
docker compose --env-file .env.production -f docker-compose.yml -f docker-compose.production.yml up --build -d
```

Check the app health:

```bash
curl -i http://localhost:5001/api/health/ready
```
