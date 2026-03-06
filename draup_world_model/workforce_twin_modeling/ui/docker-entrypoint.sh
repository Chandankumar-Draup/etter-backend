#!/bin/sh
set -e

# Generate runtime config from environment variable.
# Set API_BASE_URL to the backend endpoint, e.g.:
#   API_BASE_URL=https://api.example.com/api/v1/workforce-twin
cat > /app/config.js <<EOF
window.__WORKFORCE_TWIN_API_BASE__ = '${API_BASE_URL:-/api}';
EOF

echo "Config: API_BASE_URL=${API_BASE_URL:-/api}"

exec serve -s /app -l 3000
