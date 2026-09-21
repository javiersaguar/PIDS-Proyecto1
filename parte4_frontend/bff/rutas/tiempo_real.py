"""Router vacío que rellena F1 (CONTRATOS.md §5): GET /api/tiempo-real?horas=6.

`app.py` lo incluye con `prefix='/api'` y `dependencies=[Depends(sesion_requerida)]`: las rutas se definen sin
`/api` y no tienen que comprobar la sesión.
"""
from fastapi import APIRouter

router = APIRouter(tags=['tiempo real'])
