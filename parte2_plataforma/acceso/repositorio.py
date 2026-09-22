"""Acceso a MongoDB con el usuario `pids_acceso`: lectura de `publico` e inserción en `auditoria`.

Ese usuario no puede leer nada individual (no existe en MongoDB) ni modificar la auditoría: los
permisos los crea parte2_plataforma/mongodb/init/01_usuarios.js.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Protocol

from ..comun import privacidad as P


class Repositorio(Protocol):
    async def buscar(self, consulta: P.Consulta, limite: int) -> list[dict]: ...
    async def zonas(self, texto: str | None) -> list[dict]: ...
    async def barrios(self) -> list[str]: ...
    async def ultimo_dia_por_barrio(self, fuente: str) -> tuple[datetime | None, dict[str, int]]: ...
    async def ultima_actualizacion_tiempo_real(self) -> datetime | None: ...
    async def inventario(self) -> list[dict[str, Any]]: ...
    async def auditar(self, decision: dict[str, Any]) -> None: ...
    async def cerrar(self) -> None: ...


def filtro_mongo(consulta: P.Consulta) -> dict:
    tiempo = 'hora' if consulta.nivel == 'hora_zona' else 'dia'
    filtro: dict[str, Any] = {tiempo: {'$gte': consulta.desde, '$lt': consulta.hasta}}
    for campo in ('zona_origen', 'barrio_origen', 'barrio_destino'):
        valor = getattr(consulta, campo)
        if valor is not None:
            filtro[campo] = valor
    return filtro


def proyeccion(consulta: P.Consulta) -> dict:
    dims = P.config()['niveles'][consulta.nivel]['dimensiones']
    extra = ['zona_origen_nombre', 'barrio_origen'] if consulta.nivel == 'hora_zona' else []
    campos = dims + extra + consulta.metricas + ['n_viajes', 'suprimido']
    return {'_id': 0, **{c: 1 for c in campos}}


class RepositorioMongo:
    def __init__(self, uri: str):
        from pymongo import AsyncMongoClient
        self.cliente = AsyncMongoClient(uri, tz_aware=False, serverSelectionTimeoutMS=5000)
        self.publico = self.cliente['publico']
        self.auditoria = self.cliente['auditoria']

    async def buscar(self, consulta: P.Consulta, limite: int) -> list[dict]:
        tiempo = 'hora' if consulta.nivel == 'hora_zona' else 'dia'
        cursor = (self.publico[P.coleccion(consulta)]
                  .find(filtro_mongo(consulta), proyeccion(consulta))
                  .sort([(tiempo, 1)])
                  .limit(limite))
        return await cursor.to_list()

    async def zonas(self, texto: str | None) -> list[dict]:
        filtro = {'nombre': {'$regex': texto, '$options': 'i'}} if texto else {}
        return await self.publico['zonas'].find(filtro).sort('_id').limit(300).to_list()

    async def barrios(self) -> list[str]:
        return sorted(b for b in await self.publico['zonas'].distinct('barrio') if b)

    async def ultimo_dia_por_barrio(self, fuente: str) -> tuple[datetime | None, dict[str, int]]:
        coleccion = self.publico[P.config()['fuentes'][fuente] + 'viajes_dia_barrio']
        ultimo = await coleccion.find_one({}, {'dia': 1}, sort=[('dia', -1)])
        if not ultimo:
            return None, {}
        filas = await coleccion.find({'dia': ultimo['dia'], 'suprimido': False},
                                     {'barrio_origen': 1, 'n_viajes': 1}).to_list()
        return ultimo['dia'], {f.get('barrio_origen') or 'desconocido': f['n_viajes'] for f in filas}

    async def auditar(self, decision: dict[str, Any]) -> None:
        await self.auditoria['decisiones'].insert_one(decision)

    async def inventario(self) -> list[dict[str, Any]]:
        """Documentos y bytes de cada colección de agregados. Los viajes sueltos no están en MongoDB."""
        filas = [await self._coleccion(prefijo + nivel['coleccion'], fuente)
                 for fuente, prefijo in P.config()['fuentes'].items()
                 for nivel in P.config()['niveles'].values()]
        filas.append(await self._coleccion('zonas', 'catalogo'))
        return filas

    async def _coleccion(self, nombre: str, fuente: str) -> dict[str, Any]:
        stats = await self.publico.command('collStats', nombre)
        return {'coleccion': nombre, 'fuente': fuente,
                'documentos': int(stats.get('count') or 0), 'bytes': int(stats.get('size') or 0)}

    async def ultima_actualizacion_tiempo_real(self) -> datetime | None:
        # Solo streaming: evita ordenar los cientos de miles de documentos del histórico.
        ultimo = await self.publico['tr_viajes_hora_zona'].find_one(
            {'actualizado_en': {'$type': 'date'}}, {'_id': 0, 'actualizado_en': 1},
            sort=[('actualizado_en', -1)], max_time_ms=5000)
        return ultimo['actualizado_en'] if ultimo else None

    async def cerrar(self) -> None:
        await self.cliente.close()
