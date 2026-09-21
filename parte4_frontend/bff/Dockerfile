# Portal web (parte 4): un solo contenedor con el BFF de FastAPI y la SPA de React ya construida.
# Contexto de construcción: la raíz del repositorio.
#
#   docker compose --profile frontend up -d --build frontend      (o: make frontend)
#
# GRUPOS: grupos de dependencias de pyproject.toml que instala la imagen (uv sync --group … por cada uno).
# Por defecto `frontend chatbot`; cuando el grupo `rag` exista en main, Compose lo puede ampliar sin tocar la imagen.

# --- 1. La SPA -----------------------------------------------------------------------------------------------
FROM node:22-alpine AS spa
WORKDIR /app/web
COPY parte4_frontend/web/package.json parte4_frontend/web/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY parte4_frontend/web ./
RUN npm run build

# --- 2. El BFF -----------------------------------------------------------------------------------------------
FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.12.15 /uv /bin/uv

ARG GRUPOS="frontend chatbot"
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:${PATH}" \
    PYTHONUNBUFFERED=1 \
    PIDS_CONFIG_DIR=/app/config

WORKDIR /app
COPY pyproject.toml uv.lock .python-version ./
RUN test -n "${GRUPOS}" \
 && uv sync --frozen --no-default-groups $(for g in ${GRUPOS}; do printf -- '--group %s ' "$g"; done)

COPY config ./config
COPY data/muestra ./data/muestra
COPY parte2_plataforma ./parte2_plataforma
COPY parte3_chatbot ./parte3_chatbot
COPY parte4_frontend/__init__.py ./parte4_frontend/__init__.py
COPY parte4_frontend/bff ./parte4_frontend/bff
COPY --from=spa /app/web/dist ./parte4_frontend/web/dist

RUN useradd --system --create-home --uid 10001 app \
 && chown -R app /app/parte3_chatbot
USER app

EXPOSE 8000
CMD ["uvicorn", "parte4_frontend.bff.app:app", "--host", "0.0.0.0", "--port", "8000"]
