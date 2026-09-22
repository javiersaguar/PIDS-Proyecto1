"""La muestra de 999 viajes no puede sustituir un histórico ya publicado.

Los agregados se guardan por sus dimensiones, sin el lote. Cargar la muestra cuando ya hay
una carga que no es la muestra reescribe los grupos del 1 de enero. Esta regla la usan el
portal (HTTP 409) y la primera tarea del DAG, antes de Spark.
"""
from __future__ import annotations

MENSAJE_MUESTRA = (
    'Ya hay una carga del histórico que no es la muestra. '
    'Los 999 viajes de prueba sustituirían los grupos del 1 de enero, así que no se cargan.'
)
MENSAJE_SIN_COMPROBAR = (
    'No se ha podido comprobar si el histórico ya está cargado. '
    'La muestra no se lanza para no sustituir los grupos del 1 de enero.'
)


def es_muestra(carga: dict) -> bool:
    """Una carga de la muestra: el lote `muestra` o el CSV de `crudo/muestra/`."""
    lote = str(carga.get('lote') or '')
    entrada = str(carga.get('entrada') or '')
    return lote == 'muestra' or '/muestra/' in entrada


def motivo_si_bloqueada(cargas: list[dict]) -> str | None:
    """El mensaje de rechazo si alguna carga no es la muestra; None si se puede lanzar."""
    if any(not es_muestra(carga) for carga in cargas):
        return MENSAJE_MUESTRA
    return None


def leer_cargas(uri: str) -> list[dict]:
    """`lote` y `entrada` de `auditoria.cargas`. La URI no se registra: lleva la contraseña."""
    from pymongo import MongoClient

    cliente = MongoClient(uri, serverSelectionTimeoutMS=3000, connectTimeoutMS=3000, socketTimeoutMS=10000)
    try:
        return list(cliente['auditoria']['cargas'].find({}, {'lote': 1, 'entrada': 1}))
    finally:
        cliente.close()
