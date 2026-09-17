# Imagen común de los servicios Python (captura, acceso, chatbot y trabajos auxiliares).
# Cada servicio instala solo su grupo de dependencias de pyproject.toml.
# Contexto de construcción: la raíz del repositorio.
FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.12.15 /uv /bin/uv

ARG GRUPO
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:${PATH}" \
    PYTHONUNBUFFERED=1 \
    PIDS_CONFIG_DIR=/app/config

WORKDIR /app
COPY pyproject.toml uv.lock .python-version ./
RUN test -n "${GRUPO}" && uv sync --frozen --no-default-groups --group "${GRUPO}"

COPY config ./config
COPY data/muestra ./data/muestra
COPY parte2_plataforma ./parte2_plataforma
COPY parte3_chatbot ./parte3_chatbot

RUN useradd --system --create-home --uid 10001 app \
 && chown -R app /app/parte3_chatbot
USER app
