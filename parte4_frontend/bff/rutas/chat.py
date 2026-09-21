"""Router vacío que rellena F2 (CONTRATOS.md §5): GET /api/chat/motores y POST/DELETE /api/chat/sesiones… (SSE).

`app.py` lo incluye con `prefix='/api'` y `dependencies=[Depends(sesion_requerida)]`: las rutas se definen sin
`/api` y no tienen que comprobar la sesión.
"""
from fastapi import APIRouter

router = APIRouter(tags=['chat'])
