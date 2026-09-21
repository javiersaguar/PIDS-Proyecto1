"""Routers del BFF. `salud` y `sesion` son públicos; el resto se incluye en `app.py` con `prefix='/api'` y la
dependencia `sesion_requerida`, así que cada router define sus rutas sin `/api` y sin pensar en la sesión."""
