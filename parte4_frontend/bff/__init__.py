"""BFF («backend for frontend») del portal: FastAPI que guarda todas las claves, gestiona la sesión por cookie
firmada, reenvía las consultas a la API de acceso y sirve la SPA construida (`web/dist`).

    uv run uvicorn parte4_frontend.bff.app:app --port 8020 --reload
"""
