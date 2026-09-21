"""Lectura de la auditoría de privacidad (`auditoria.decisiones` y `auditoria.cargas`) con `pids_auditor`.

Es la única conexión del portal a MongoDB y va con el usuario de solo lectura de `auditoria` (no puede leer
`publico` ni nada individual: los permisos los crea parte2_plataforma/mongodb/init/01_usuarios.js). Las
decisiones no contienen viajes, solo qué se preguntó, quién y qué decidió el filtro (E3).

- Un `MongoClient` por proceso y URI (`tz_aware=True`, 3 s de selección de servidor), abierto en `abrir_cliente`,
  que los tests sustituyen por un fake con `monkeypatch`.
- pymongo es síncrono: las lecturas van en un hilo (`asyncio.to_thread`) para no bloquear el BFF.
- `resumen(horas)` agrupa los motivos por su tipo (el texto antes de `': '`), igual que `scripts/informe_auditoria.py`
  (`resumir` y `tipo_de_motivo` están copiados aquí porque `scripts/` no va en la imagen).
- `_id` nunca sale; `instante` sale en ISO 8601 (UTC).
- MongoDB caído -> `disponible: false` / listas vacías con 200, sin registrar la URI (lleva la contraseña).
"""
from __future__ import annotations

import asyncio
import logging
from collections import Counter
from collections.abc import Iterable
from datetime import datetime, timedelta, timezone
from typing import Any

from pymongo import DESCENDING, MongoClient
from pymongo.errors import PyMongoError

log = logging.getLogger('pids.frontend')

TIEMPO_SELECCION_MS = 3000
BASE = 'auditoria'
MAX_CARGAS = 200
CAMPOS_RESUMEN = {'_id': 0, 'resultado': 1, 'cliente': 1, 'motivos': 1}
SIN_ID = {'_id': 0}

_clientes: dict[str, MongoClient] = {}


def abrir_cliente(uri: str) -> MongoClient:
    """El cliente de MongoDB del auditor. Solo se abre uno por URI; los tests lo sustituyen con `monkeypatch`."""
    return MongoClient(uri, tz_aware=True, serverSelectionTimeoutMS=TIEMPO_SELECCION_MS,
                       connectTimeoutMS=TIEMPO_SELECCION_MS, socketTimeoutMS=10000)


def cliente_mongo(uri: str) -> MongoClient:
    if uri not in _clientes:
        _clientes[uri] = abrir_cliente(uri)
    return _clientes[uri]


def olvidar_clientes() -> None:
    """Para los tests: cierra y olvida los clientes abiertos."""
    for cliente in _clientes.values():
        try:
            cliente.close()
        except Exception:      # noqa: BLE001 - un fake puede no tener close(); cerrar es cortesía
            pass
    _clientes.clear()


# --- lógica pura (copiada de scripts/informe_auditoria.py) -------------------------------------------------

def tipo_de_motivo(motivo: str) -> str:
    """'petición de datos individuales: <texto de la pregunta>' -> 'petición de datos individuales'.

    Los motivos llevan detrás de ': ' el detalle de cada consulta; sin quitarlo, cada pregunta distinta sería
    un motivo distinto y la tabla de los más frecuentes no diría nada.
    """
    return motivo.split(': ', 1)[0]


def resumir(decisiones: Iterable[dict]) -> dict:
    """Una pasada sobre las decisiones: totales por resultado y cliente, y motivos de rechazo por tipo."""
    resultados: Counter[str] = Counter()
    clientes: Counter[str] = Counter()
    motivos: Counter[str] = Counter()
    total = 0
    for d in decisiones:
        total += 1
        resultados[d.get('resultado', 'sin resultado')] += 1
        clientes[d.get('cliente', 'sin cliente')] += 1
        if d.get('resultado') == 'rechazada':
            motivos.update(tipo_de_motivo(m) for m in d.get('motivos', []))
    return {'total': total, 'resultados': resultados, 'clientes': clientes, 'motivos': motivos}


def resumen_json(resumen: dict, desde: datetime, hasta: datetime, disponible: bool = True) -> dict:
    """`AuditoriaResumen` del contrato: los contadores como diccionarios y los motivos de más a menos frecuentes."""
    return {
        'desde': desde.isoformat(), 'hasta': hasta.isoformat(), 'total': resumen['total'],
        'resultados': dict(resumen['resultados'].most_common()),
        'clientes': dict(resumen['clientes'].most_common()),
        'motivos': [{'motivo': motivo, 'cantidad': cantidad} for motivo, cantidad in resumen['motivos'].most_common()],
        'disponible': disponible,
    }


def a_json(valor: Any) -> Any:
    """Documentos de MongoDB listos para JSON: fechas en ISO (UTC) y cualquier otro tipo raro como texto."""
    if isinstance(valor, dict):
        return {str(k): a_json(v) for k, v in valor.items() if k != '_id'}
    if isinstance(valor, (list, tuple)):
        return [a_json(v) for v in valor]
    if isinstance(valor, datetime):
        return (valor if valor.tzinfo else valor.replace(tzinfo=timezone.utc)).isoformat()
    if valor is None or isinstance(valor, (str, int, float, bool)):
        return valor
    return str(valor)


def periodo(horas: float, ahora: datetime | None = None) -> tuple[datetime, datetime]:
    hasta = ahora or datetime.now(timezone.utc)
    return hasta - timedelta(hours=horas), hasta


def filtro_decisiones(desde: datetime, hasta: datetime, resultado: str | None = None,
                      cliente: str | None = None) -> dict:
    filtro: dict[str, Any] = {'instante': {'$gte': desde, '$lt': hasta}}
    if resultado:
        filtro['resultado'] = resultado
    if cliente:
        filtro['cliente'] = cliente
    return filtro


# --- servicio ----------------------------------------------------------------------------------------------

class Auditoria:
    """Lecturas de `auditoria` con `pids_auditor`. Cada método devuelve algo aunque MongoDB no responda."""

    def __init__(self, uri: str):
        self.uri = uri

    def _coleccion(self, nombre: str):
        return cliente_mongo(self.uri)[BASE][nombre]

    def _resumen(self, desde: datetime, hasta: datetime) -> dict:
        cursor = self._coleccion('decisiones').find(filtro_decisiones(desde, hasta), CAMPOS_RESUMEN)
        return resumir(cursor)

    def _decisiones(self, desde: datetime, hasta: datetime, resultado: str | None, cliente: str | None,
                    limite: int) -> list[dict]:
        cursor = (self._coleccion('decisiones')
                  .find(filtro_decisiones(desde, hasta, resultado, cliente), SIN_ID)
                  .sort('instante', DESCENDING)
                  .limit(limite))
        return [a_json(d) for d in cursor]

    def _cargas(self) -> list[dict]:
        cursor = self._coleccion('cargas').find({}, SIN_ID).sort('instante', DESCENDING).limit(MAX_CARGAS)
        return [a_json(d) for d in cursor]

    @staticmethod
    def _aviso(que: str, error: Exception) -> None:
        # La excepción puede llevar la URI con la contraseña: solo se registra su tipo.
        log.warning('La auditoría no responde al pedir %s (%s)', que, type(error).__name__)

    async def resumen(self, horas: float) -> dict:
        desde, hasta = periodo(horas)
        try:
            resumen = await asyncio.to_thread(self._resumen, desde, hasta)
        except PyMongoError as error:
            self._aviso('el resumen', error)
            return resumen_json(resumir([]), desde, hasta, disponible=False)
        return resumen_json(resumen, desde, hasta)

    async def decisiones(self, horas: float, resultado: str | None, cliente: str | None, limite: int) -> list[dict]:
        desde, hasta = periodo(horas)
        try:
            return await asyncio.to_thread(self._decisiones, desde, hasta, resultado or None, cliente or None, limite)
        except PyMongoError as error:
            self._aviso('las decisiones', error)
            return []

    async def cargas(self) -> list[dict]:
        try:
            return await asyncio.to_thread(self._cargas)
        except PyMongoError as error:
            self._aviso('las cargas', error)
            return []
