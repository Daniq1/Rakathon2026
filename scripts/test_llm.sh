#!/usr/bin/env bash
# Jedno krátké testovací volání podle slajdu Microsoftu.
set -euo pipefail
set -a; source "$(dirname "$0")/../.env"; set +a
curl -sS "$LLM_BASE_URL/chat/completions" \
  -H "api-key: $LLM_API_KEY" \
  -H "Content-Type: application/json" \
  -d "{\"model\": \"$LLM_DEPLOYMENT_EXTRACT\", \"messages\": [{\"role\": \"user\", \"content\": \"Ahoj, odpověz jedním slovem.\"}]}" \
  | python3 -m json.tool
