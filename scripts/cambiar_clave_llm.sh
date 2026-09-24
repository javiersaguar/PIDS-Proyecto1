#!/usr/bin/env bash
# Sustituye LLM_API_KEY en .env por una clave nueva del proveedor del LLM (Mistral: console.mistral.ai) y reinicia
# lo que la usa.
#
#   make rag-clave
#
# La clave se pide sin mostrarla, se prueba contra el proveedor antes de guardarla y no se imprime nunca.
set -euo pipefail
cd "$(dirname "$0")/.."

[[ -f .env ]] || { echo "Falta .env: ejecuta 'make entorno'"; exit 1; }
base=$(grep -E '^LLM_BASE_URL=' .env | cut -d= -f2- || true)
base=${base:-https://api.mistral.ai/v1}

read -rsp "Pega la clave nueva del proveedor del LLM (no se verá) y pulsa Intro: " clave
echo
clave=$(printf '%s' "$clave" | tr -d '[:space:]')
[[ -n "$clave" ]] || { echo "No se ha pegado nada; .env no cambia."; exit 1; }

codigo=$(curl -s -o /dev/null -w '%{http_code}' --max-time 15 -H "Authorization: Bearer ${clave}" "${base}/models")
if [[ "$codigo" != 200 ]]; then
    echo "El proveedor no acepta esa clave (HTTP ${codigo}); .env no cambia."
    exit 1
fi

# Se reescribe solo la línea LLM_API_KEY, conservando el resto y los permisos del fichero
CLAVE_NUEVA="$clave" python3 - <<'EOF'
import os
from pathlib import Path

ruta = Path('.env')
lineas = ruta.read_text(encoding='utf-8').splitlines()
nueva = f"LLM_API_KEY={os.environ['CLAVE_NUEVA']}"
if any(l.startswith('LLM_API_KEY=') for l in lineas):
    lineas = [nueva if l.startswith('LLM_API_KEY=') else l for l in lineas]
else:
    lineas.append(nueva)
ruta.write_text('\n'.join(lineas) + '\n', encoding='utf-8')
EOF
echo "Clave aceptada por el proveedor y guardada en .env."

# Compose recrea los contenedores cuyo entorno ha cambiado: el chatbot RAG y el portal (motor RAG de TAXI AI)
docker compose --profile rag --profile frontend up -d chatbot-rag frontend
echo "Chatbot RAG y portal reiniciados con la clave nueva."
