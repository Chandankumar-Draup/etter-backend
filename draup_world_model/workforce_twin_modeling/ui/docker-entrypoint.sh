#!/bin/sh
set -e

# Generate runtime config from environment variables.
#
# API_BASE_URL     — workforce twin API (e.g. https://api.draup.com/api/v1/workforce-twin)
# ETTER_API_BASE   — etter backend root for auth (e.g. https://api.draup.com/api)
cat > /app/config.js <<EOF
window.__WORKFORCE_TWIN_API_BASE__ = '${API_BASE_URL:-/api}';
window.__ETTER_API_BASE__ = '${ETTER_API_BASE:-/etter-api}';
EOF

echo "Config: API_BASE_URL=${API_BASE_URL:-/api}, ETTER_API_BASE=${ETTER_API_BASE:-/etter-api}"

exec serve -s /app -l 3000
