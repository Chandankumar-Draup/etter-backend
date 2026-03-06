#!/bin/sh
set -e

# Generate runtime config.js from environment variables.
# In EKS, set API_BASE_URL to the backend service URL, e.g.:
#   API_BASE_URL=https://api.example.com/api/v1/workforce-twin
cat > /usr/share/nginx/html/config.js <<EOF
window.__WORKFORCE_TWIN_API_BASE__ = '${API_BASE_URL:-/api}';
EOF

echo "Config injected: API_BASE_URL=${API_BASE_URL:-/api}"

exec nginx -g 'daemon off;'
