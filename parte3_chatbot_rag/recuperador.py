"""Recuperación: qué documentos de Qdrant acompañan a cada pregunta.

Dos colecciones con el mismo modelo de embeddings, así que sus puntuaciones (similitud coseno) son comparables:
  - `conocimiento`: documentación, reglas, catálogo, zonas y ejemplos de consultas (corpus.py);
  - `agregados_gruesos`: fichas de día-barrio y flujos, ya protegidas por la API de acceso (fichas.py).

`recuperar` busca en las dos, fusiona por puntuación y devuelve los `k` mejores; se garantiza un mínimo por colección
para que una pregunta con muchas fichas parecidas (fechas cercanas) no deje fuera la documentación. Opcionalmente
filtra por metadatos (por ejemplo `{'dia': '2020-03-03'}`) y reordena con el modelo `rerank` del proveedor
(`RAG_RERANK=true`), pidiendo primero más candidatos. Sin red en las pruebas: `AsyncQdrantClient(':memory:')` y
embeddings falsos.

Uso a mano, contra el Qdrant de la plataforma:  python recuperador.py "¿qué zonas hay en el aeropuerto?" [--k 6]
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import os
import re
from collections.abc import Awaitable, Callable, Sequence
from typing import Any, Protocol

from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from qdrant_client import AsyncQdrantClient, QdrantClient, models

from herramientas import BARRIOS, MESES, NUMERO_MES, fecha_en_texto, normalizar

log = logging.getLogger('pids.rag.recuperador')

COLECCION_CONOCIMIENTO = 'conocimiento'
COLECCION_FICHAS = 'agregados_gruesos'
COLECCIONES = (COLECCION_CONOCIMIENTO, COLECCION_FICHAS)
K_POR_DEFECTO = 6
CANDIDATOS_RERANK = 4                    # se piden k × 4 candidatos y el rerank se queda con k
CAMPOS_FILTRABLES = ('tipo', 'nivel', 'dia', 'mes', 'barrio_origen', 'barrio_destino', 'suprimido', 'fuente', 'zona_id',
                     'barrio', 'herramienta')

Reordenador = Callable[[str, list[str], int], Awaitable[list[tuple[int, float]]]]


class Recuperador(Protocol):
    async def recuperar(self, pregunta: str, k: int = K_POR_DEFECTO) -> list[Document]: ...


class ClienteAsincrono:
    """Un `QdrantClient` síncrono (el de las pruebas, `QdrantClient(':memory:')`) usado con `await`: cada llamada va a
    un hilo. Así el recuperador y el indexador solo tratan con la interfaz asíncrona."""

    def __init__(self, cliente: QdrantClient):
        self.cliente = cliente

    def __getattr__(self, nombre: str):
        metodo = getattr(self.cliente, nombre)

        async def envoltorio(*args, **kwargs):
            return await asyncio.to_thread(metodo, *args, **kwargs)
        return envoltorio


def asincrono(cliente: AsyncQdrantClient | QdrantClient | ClienteAsincrono) -> AsyncQdrantClient:
    """Idempotente: un cliente ya asíncrono (o ya envuelto) se devuelve tal cual."""
    if isinstance(cliente, (AsyncQdrantClient, ClienteAsincrono)):
        return cliente  # type: ignore[return-value]
    return ClienteAsincrono(cliente)  # type: ignore[return-value]


# --- conversión entre Qdrant y Document ------------------------------------------------------------------------

def a_punto(documento: Document, vector: list[float]) -> models.PointStruct:
    """El mismo formato de carga que usa langchain-qdrant (page_content + metadata), por si algún día se lee con él."""
    return models.PointStruct(id=documento.metadata['_id'], vector=vector,
                              payload={'page_content': documento.page_content, 'metadata': dict(documento.metadata)})


def a_documento(punto: Any, coleccion: str) -> Document:
    carga = punto.payload or {}
    metadatos = dict(carga.get('metadata') or {})
    metadatos.setdefault('_id', str(punto.id))
    metadatos['coleccion'] = coleccion
    if getattr(punto, 'score', None) is not None:
        metadatos['puntuacion'] = round(float(punto.score), 4)
    return Document(page_content=carga.get('page_content', ''), metadata=metadatos)


def filtro_qdrant(filtro: dict[str, Any] | None) -> models.Filter | None:
    """{'dia': '2020-03-03', 'barrio_origen': 'Manhattan'} -> igualdad sobre metadata.*; una lista = «uno de»."""
    if not filtro:
        return None
    condiciones: list[models.Condition] = []
    for campo, valor in filtro.items():
        if campo not in CAMPOS_FILTRABLES:
            raise ValueError(f'no se puede filtrar por {campo!r}; campos: {", ".join(CAMPOS_FILTRABLES)}')
        if valor is None:
            continue
        coincidencia = models.MatchAny(any=list(valor)) if isinstance(valor, (list, tuple, set)) \
            else models.MatchValue(value=valor)
        condiciones.append(models.FieldCondition(key=f'metadata.{campo}', match=coincidencia))
    return models.Filter(must=condiciones) if condiciones else None


def limitar_tipo(documentos: list[Document], tipo: str, maximo: int) -> list[Document]:
    """Deja como mucho `maximo` documentos de un tipo (los ejemplos se parecen entre sí y coparían el contexto)."""
    salida, vistos = [], 0
    for d in documentos:
        if d.metadata.get('tipo') == tipo:
            vistos += 1
            if vistos > maximo:
                continue
        salida.append(d)
    return salida


def fusionar(por_coleccion: dict[str, list[Document]], k: int,
             minimo_por_coleccion: int | dict[str, int] = 1) -> list[Document]:
    """Los k mejores por puntuación, garantizando un mínimo de cada colección que tenga resultados (el mismo para
    todas, o uno por colección). Cada lista viene ordenada de mayor a menor; el resultado final, también."""
    puntuacion = lambda d: d.metadata.get('puntuacion', 0)  # noqa: E731
    minimos = minimo_por_coleccion if isinstance(minimo_por_coleccion, dict) else \
        {c: minimo_por_coleccion for c in por_coleccion}
    elegidos: list[Document] = []
    for coleccion, documentos in por_coleccion.items():
        elegidos += documentos[:minimos.get(coleccion, 0)]
    ids = {d.metadata['_id'] for d in elegidos}
    resto = sorted((d for docs in por_coleccion.values() for d in docs if d.metadata['_id'] not in ids),
                   key=puntuacion, reverse=True)
    elegidos = sorted(elegidos, key=puntuacion, reverse=True)[:k]
    return sorted(elegidos + resto[:k - len(elegidos)], key=puntuacion, reverse=True)


# --- el recuperador ------------------------------------------------------------------------------------------------

class RecuperadorQdrant:
    def __init__(self, cliente: AsyncQdrantClient | QdrantClient, embeddings: Embeddings,
                 colecciones: tuple[str, ...] = COLECCIONES, k: int = K_POR_DEFECTO, rerank: bool = False,
                 minimo_por_coleccion: int = 1, reordenador: Reordenador | None = None):
        self.cliente = asincrono(cliente)
        self.embeddings = embeddings
        self.colecciones = tuple(colecciones)
        self.k = k
        self.rerank = rerank
        self.minimo_por_coleccion = minimo_por_coleccion
        self._reordenador = reordenador

    async def recuperar(self, pregunta: str, k: int | None = None,
                        filtro: dict[str, Any] | None = None) -> list[Document]:
        """Los k documentos más parecidos a la pregunta, de todas las colecciones.

        `filtro` explícito: se aplica a todas las colecciones. Sin él, las fichas se acotan con lo que la pregunta
        dice (`filtro_para`: nivel, día o mes, barrio) y, si nombra un día o un mes, se les reserva la mitad de los
        huecos: la similitud semántica distingue mal las fechas y, sin esto, salen fichas parecidas de otros días.
        El conocimiento no se filtra, pero los ejemplos de consultas, que se parecen mucho entre sí, se limitan a un
        tercio de k. Para todas las fichas de un día está `fichas()`.
        """
        k = k or self.k
        vector = await self.embeddings.aembed_query(pregunta)
        candidatos = k * CANDIDATOS_RERANK if self.rerank else k
        deducido = filtro_para(pregunta) if filtro is None else {}
        existentes = [c for c in self.colecciones if await self.cliente.collection_exists(c)]

        def condicion(coleccion: str) -> models.Filter | None:
            if filtro is not None:
                return filtro_qdrant(filtro)
            return filtro_qdrant(deducido) if coleccion == COLECCION_FICHAS else None

        def limite(coleccion: str) -> int:
            return candidatos * 2 if coleccion == COLECCION_CONOCIMIENTO else candidatos

        resultados = await asyncio.gather(*(self._buscar(c, vector, limite(c), condicion(c)) for c in existentes))
        por_coleccion = {c: docs for c, docs in zip(existentes, resultados) if docs}
        if COLECCION_CONOCIMIENTO in por_coleccion:
            por_coleccion[COLECCION_CONOCIMIENTO] = limitar_tipo(por_coleccion[COLECCION_CONOCIMIENTO], 'ejemplo',
                                                                 max(1, k // 3))
        if not por_coleccion:
            return []
        minimos = {c: self.minimo_por_coleccion for c in por_coleccion}
        if ('dia' in deducido or 'mes' in deducido) and COLECCION_FICHAS in por_coleccion:
            minimos[COLECCION_FICHAS] = max(self.minimo_por_coleccion, k // 2)
        if self.rerank:
            return await self._reordenar(pregunta, fusionar(por_coleccion, candidatos, minimos), k)
        return fusionar(por_coleccion, k, minimos)

    async def _buscar(self, coleccion: str, vector: list[float], limite: int,
                      condicion: models.Filter | None) -> list[Document]:
        respuesta = await self.cliente.query_points(collection_name=coleccion, query=vector, limit=limite,
                                                    query_filter=condicion, with_payload=True)
        return [a_documento(p, coleccion) for p in respuesta.points]

    async def _reordenar(self, pregunta: str, candidatos: list[Document], k: int) -> list[Document]:
        reordenar = self._reordenador or _reordenador_del_proveedor()
        try:
            orden = await reordenar(pregunta, [d.page_content for d in candidatos], k)
        except Exception as e:                        # noqa: BLE001 - el rerank es una mejora, no un requisito
            log.warning('rerank no disponible (%s); se usa el orden por similitud', e)
            return candidatos[:k]
        salida = []
        for indice, puntuacion in orden[:k]:
            documento = candidatos[indice]
            documento.metadata['puntuacion_rerank'] = round(float(puntuacion), 4)
            salida.append(documento)
        return salida

    async def fichas(self, dia: str | None = None, barrio_origen: str | None = None, barrio_destino: str | None = None,
                     nivel: str | None = None, limite: int = 128) -> list[Document]:
        """Fichas por metadatos exactos, sin embeddings: «todas las de Manhattan el 3 de marzo». Un día completo
        son como mucho 8 fichas de día-barrio y 64 de flujos."""
        if COLECCION_FICHAS not in self.colecciones or not await self.cliente.collection_exists(COLECCION_FICHAS):
            return []
        condicion = filtro_qdrant({'dia': dia, 'barrio_origen': barrio_origen, 'barrio_destino': barrio_destino,
                                   'nivel': nivel})
        puntos, _ = await self.cliente.scroll(collection_name=COLECCION_FICHAS, scroll_filter=condicion, limit=limite,
                                              with_payload=True, with_vectors=False)
        documentos = [a_documento(p, COLECCION_FICHAS) for p in puntos]
        return sorted(documentos, key=lambda d: tuple(d.metadata.get(c) or ''
                                                      for c in ('dia', 'nivel', 'barrio_origen', 'barrio_destino')))


HABLA_DE_DESTINO = re.compile(r'\b(flujos?|destinos?|hacia|hasta|lleg(?:aron|an|[oó]|ada)|con destino|a d[oó]nde|'
                              r'ad[oó]nde|entre barrios|a qu[eé] (?:barrios?|zonas?))\b|'
                              r'\bde\s+\w[\w ]*\s+a\s+(?:manhattan|brooklyn|queens|bronx|staten island|ewr|newark)\b',
                              re.IGNORECASE)


def nivel_para(pregunta: str) -> str:
    """Qué nivel grueso responde mejor a la pregunta: los flujos si habla de destino («de Queens a Manhattan»,
    «hacia», «llegaron»); si no, el día y barrio de origen."""
    return 'od_dia_barrio' if HABLA_DE_DESTINO.search(pregunta) else 'dia_barrio'


def filtro_para(pregunta: str) -> dict[str, Any]:
    """Filtro de fichas que se deduce de la pregunta, porque la similitud semántica distingue mal fechas y barrios:
    el nivel (`nivel_para`); el día («el 3 de marzo» -> 2020-03-03) o, si solo nombra un mes, el mes; el barrio de
    origen, si nombra uno solo y el nivel es día-barrio; y, sin un día concreto, solo fichas con cifras (una ficha
    enmascarada de un día cualquiera no aporta nada y su texto se parece a todas las preguntas)."""
    texto = normalizar(pregunta)
    filtro: dict[str, Any] = {'nivel': nivel_para(pregunta)}
    dia = fecha_en_texto(pregunta)
    if dia:
        filtro['dia'] = dia.date().isoformat()
    else:
        meses = {NUMERO_MES[m] for m in re.findall(rf'\b({MESES})\b', texto)}
        if len(meses) == 1:
            filtro['mes'] = meses.pop()
        filtro['suprimido'] = False
    if filtro['nivel'] == 'dia_barrio':
        barrios = [b for b in BARRIOS if re.search(rf'\b{normalizar(b)}\b', texto)]
        if len(barrios) == 1:
            filtro['barrio_origen'] = barrios[0]
    return filtro


def _reordenador_del_proveedor() -> Reordenador:
    from llm import reordenar                     # el proveedor externo solo se importa si hace falta

    async def reordenador(pregunta: str, documentos: list[str], top_n: int) -> list[tuple[int, float]]:
        return await reordenar(pregunta, documentos, top_n=top_n)
    return reordenador


def _entero(nombre: str, por_defecto: int) -> int:
    valor = os.environ.get(nombre, '').strip()
    return int(valor) if valor else por_defecto


def _booleano(nombre: str, por_defecto: bool) -> bool:
    valor = os.environ.get(nombre, '').strip().lower()
    return valor in ('1', 'true', 'si', 'sí', 'yes') if valor else por_defecto


def obtener_recuperador(colecciones: Sequence[str] = COLECCIONES, k: int | None = None, rerank: bool | None = None,
                        cliente: AsyncQdrantClient | QdrantClient | None = None,
                        embeddings: Embeddings | None = None) -> Recuperador:
    """El recuperador de la plataforma. Sin argumentos lee QDRANT_URL, RAG_K y RAG_RERANK y usa los embeddings del
    proveedor (llm.obtener_embeddings); `cliente` (síncrono o asíncrono) y `embeddings` se inyectan en las pruebas."""
    if cliente is None:
        cliente = AsyncQdrantClient(url=os.environ.get('QDRANT_URL', 'http://qdrant:6333'), timeout=30)
    if embeddings is None:
        from llm import obtener_embeddings
        embeddings = obtener_embeddings()
    return RecuperadorQdrant(cliente, embeddings, tuple(colecciones),
                             k=k if k is not None else _entero('RAG_K', K_POR_DEFECTO),
                             rerank=rerank if rerank is not None else _booleano('RAG_RERANK', False))


# --- prueba manual ------------------------------------------------------------------------------------------------

async def _main() -> None:
    p = argparse.ArgumentParser(description='Recupera documentos de Qdrant para una pregunta (prueba manual)')
    p.add_argument('pregunta')
    p.add_argument('--k', type=int, default=None)
    p.add_argument('--rerank', action='store_true')
    p.add_argument('--dia', default=None, help='filtrar por día ISO (2020-03-03); por defecto, el de la pregunta')
    args = p.parse_args()
    recuperador = obtener_recuperador(k=args.k, rerank=args.rerank or None)
    filtro = {'dia': args.dia} if args.dia else None
    documentos = await recuperador.recuperar(args.pregunta, filtro=filtro)
    for d in documentos:
        m = d.metadata
        print(f'[{m.get("puntuacion")}] {m.get("coleccion")} · {m.get("tipo")} · {m.get("titulo")} · {m.get("fuente")}')
        print('   ' + d.page_content[:240].replace('\n', ' ') + ('…' if len(d.page_content) > 240 else ''))
    deducido = filtro_para(args.pregunta)
    if not filtro:
        exactas = await recuperador.fichas(dia=deducido['dia']) if 'dia' in deducido else []
        print(f'\nFiltro deducido: {deducido}' + (f'; fichas exactas de ese día: {len(exactas)}' if exactas else ''))


if __name__ == '__main__':
    asyncio.run(_main())
