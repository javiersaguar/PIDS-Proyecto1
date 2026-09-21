"""Router vacío que rellena F1 (CONTRATOS.md §5): GET/POST /api/operaciones/airflow/… y GET/POST/DELETE /api/operaciones/simulacion.

`app.py` lo incluye con `prefix='/api'` y `dependencies=[Depends(sesion_requerida)]`: las rutas se definen sin
`/api` y no tienen que comprobar la sesión.
"""
from fastapi import APIRouter

router = APIRouter(tags=['operaciones'])
