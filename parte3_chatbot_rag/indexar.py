"""Indexa en Qdrant el conocimiento (corpus.py) y las fichas de agregados gruesos (fichas.py).

    python indexar.py                      # las dos colecciones
    python indexar.py --solo conocimiento  # o --solo fichas
    python indexar.py --recrear            # borra las colecciones antes (si cambia el modelo de embeddings)
    python indexar.py --reanudar           # salta los documentos que ya están en Qdrant (tras un corte)

Idempotente: el id de cada punto es el `_id` estable del documento, así que volver a indexar sustituye, no duplica.
Los embeddings se piden en lotes de 32 (el máximo del endpoint), dos lotes a la vez y con una pausa tras cada uno para
no pasar de las 60 peticiones por minuto de la clave; un fallo se reintenta con espera exponencial. La dimensión del
vector se toma del propio modelo (4096 en qwen3-embedding), no se da por supuesta.

Desde la plataforma: make rag-indexar (servicio `rag-indexar`, que monta docs/ y habla con la API de acceso con la
clave del cliente chatbot_rag). Desde el anfitrión: QDRANT_URL=http://localhost:6333 y ACCESO_URL=http://localhost:8002.
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys
import time
import warnings
from collections.abc import Callable

from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from qdrant_client import AsyncQdrantClient, models

import corpus
import fichas as F
from herramientas import ClienteAcceso
from recuperador import COLECCION_CONOCIMIENTO, COLECCION_FICHAS, a_punto, asincrono

log = logging.getLogger('pids.rag.indexar')

LOTE = 32
PAUSA_SEGUNDOS = 0.5
PARALELO = 2
REINTENTOS = 5
# Campos de metadatos por los que se filtra (recuperador.fichas y filtro_para): un índice de carga por cada uno
INDICES = {COLECCION_FICHAS: ('tipo', 'nivel', 'dia', 'mes', 'barrio_origen', 'barrio_destino', 'suprimido'),
           COLECCION_CONOCIMIENTO: ('tipo', 'zona_id', 'barrio', 'herramienta')}

Avisador = Callable[[str], None]


def avisar_por_defecto(texto: str) -> None:
    print(texto, flush=True)                      # que el progreso se vea también con la salida redirigida


async def dimension(embeddings: Embeddings) -> int:
    return len(await embeddings.aembed_query('dimensión del vector'))


async def preparar_coleccion(cliente: AsyncQdrantClient, nombre: str, dimension_vector: int, recrear: bool = False,
                             avisar: Avisador = avisar_por_defecto) -> None:
    """Crea la colección (coseno) si no existe; si existe con otra dimensión pide --recrear, para no mezclar modelos."""
    cliente = asincrono(cliente)
    if recrear and await cliente.collection_exists(nombre):
        await cliente.delete_collection(nombre)
        avisar(f'[indexar] colección {nombre} borrada')
    if await cliente.collection_exists(nombre):
        info = await cliente.get_collection(nombre)
        actual = info.config.params.vectors.size
        if actual != dimension_vector:
            raise SystemExit(f'La colección {nombre} tiene vectores de {actual} dimensiones y el modelo da '
                             f'{dimension_vector}: ejecuta con --recrear (cambió el modelo de embeddings)')
        return
    await cliente.create_collection(nombre, vectors_config=models.VectorParams(size=dimension_vector,
                                                                                 distance=models.Distance.COSINE))
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')               # el Qdrant en memoria de las pruebas avisa de que no indexa
        for campo in INDICES.get(nombre, ()):
            tipo = models.PayloadSchemaType.BOOL if campo == 'suprimido' else \
                models.PayloadSchemaType.INTEGER if campo in ('mes', 'zona_id') else models.PayloadSchemaType.KEYWORD
            await cliente.create_payload_index(nombre, field_name=f'metadata.{campo}', field_schema=tipo)
    avisar(f'[indexar] colección {nombre} creada ({dimension_vector} dimensiones, coseno)')


async def ya_indexados(cliente: AsyncQdrantClient, coleccion: str, documentos: list[Document]) -> set[str]:
    cliente = asincrono(cliente)
    ids = [d.metadata['_id'] for d in documentos]
    existentes: set[str] = set()
    for i in range(0, len(ids), 256):
        puntos = await cliente.retrieve(coleccion, ids=ids[i:i + 256], with_payload=False, with_vectors=False)
        existentes.update(str(p.id) for p in puntos)
    return existentes


async def _con_reintentos(operacion, descripcion: str, reintentos: int = REINTENTOS,
                          avisar: Avisador = avisar_por_defecto):
    for intento in range(1, reintentos + 1):
        try:
            return await operacion()
        except Exception as e:                       # noqa: BLE001 - red y límites de la clave: se reintenta
            if intento == reintentos:
                raise
            espera = min(2 ** intento, 60)
            avisar(f'[indexar] {descripcion}: {type(e).__name__}: {str(e)[:120]} → reintento '
                   f'{intento}/{reintentos - 1} en {espera} s')
            await asyncio.sleep(espera)


async def subir(cliente: AsyncQdrantClient, coleccion: str, embeddings: Embeddings, documentos: list[Document],
                lote: int = LOTE, pausa: float = PAUSA_SEGUNDOS, reanudar: bool = False, reintentos: int = REINTENTOS,
                paralelo: int = PARALELO, avisar: Avisador = avisar_por_defecto) -> int:
    """Embeddings por lotes y upsert por id, con `paralelo` lotes en vuelo a la vez (la clave admite 10 peticiones
    simultáneas y 60 por minuto; cada lote de 32 textos tarda unos 3 s). Devuelve cuántos documentos se han subido."""
    cliente = asincrono(cliente)
    if reanudar:
        existentes = await ya_indexados(cliente, coleccion, documentos)
        documentos = [d for d in documentos if d.metadata['_id'] not in existentes]
        avisar(f'[indexar] {coleccion}: {len(existentes)} ya estaban; quedan {len(documentos)}')
    inicio, total = time.monotonic(), len(documentos)
    lotes = [documentos[i:i + lote] for i in range(0, total, lote)]
    semaforo, progreso = asyncio.Semaphore(max(1, paralelo)), {'subidos': 0}

    async def un_lote(numero: int, parte: list[Document]) -> None:
        descripcion = f'{coleccion} lote {numero}/{len(lotes)}'
        async with semaforo:
            vectores = await _con_reintentos(lambda: embeddings.aembed_documents([d.page_content for d in parte]),
                                             descripcion + ' (embeddings)', reintentos, avisar)
            puntos = [a_punto(d, v) for d, v in zip(parte, vectores)]
            await _con_reintentos(lambda: cliente.upsert(coleccion, points=puntos, wait=True),
                                  descripcion + ' (upsert)', reintentos, avisar)
            if pausa:
                await asyncio.sleep(pausa)
        progreso['subidos'] += len(parte)
        if progreso['subidos'] % (lote * 10) == 0 or progreso['subidos'] == total:
            avisar(f'[indexar] {coleccion}: {progreso["subidos"]}/{total} ({time.monotonic() - inicio:.0f} s)')

    await asyncio.gather(*(un_lote(n, parte) for n, parte in enumerate(lotes, start=1)))
    return progreso['subidos']


async def indexar_conocimiento(cliente: AsyncQdrantClient, embeddings: Embeddings, documentos: list[Document],
                               recrear: bool = False, avisar: Avisador = avisar_por_defecto, **opciones) -> int:
    cliente = asincrono(cliente)
    corpus.comprobar_ids_unicos(documentos)
    await preparar_coleccion(cliente, COLECCION_CONOCIMIENTO, await dimension(embeddings), recrear, avisar)
    avisar(f'[indexar] conocimiento: {len(documentos)} documentos {corpus.resumen(documentos)}')
    return await subir(cliente, COLECCION_CONOCIMIENTO, embeddings, documentos, avisar=avisar, **opciones)


async def indexar_fichas(cliente: AsyncQdrantClient, embeddings: Embeddings, documentos: list[Document],
                         recrear: bool = False, avisar: Avisador = avisar_por_defecto, **opciones) -> int:
    cliente = asincrono(cliente)
    corpus.comprobar_ids_unicos(documentos)
    await preparar_coleccion(cliente, COLECCION_FICHAS, await dimension(embeddings), recrear, avisar)
    primero, ultimo = F.dias_cubiertos(documentos)
    suprimidas = sum(1 for d in documentos if d.metadata.get('suprimido'))
    avisar(f'[indexar] fichas: {len(documentos)} ({suprimidas} enmascaradas) del {primero} al {ultimo}')
    return await subir(cliente, COLECCION_FICHAS, embeddings, documentos, avisar=avisar, **opciones)


async def estado(cliente: AsyncQdrantClient) -> dict[str, int]:
    cliente = asincrono(cliente)
    salida = {}
    for nombre in (COLECCION_CONOCIMIENTO, COLECCION_FICHAS):
        if await cliente.collection_exists(nombre):
            salida[nombre] = (await cliente.count(nombre, exact=True)).count
    return salida


def argumentos(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--solo', choices=['conocimiento', 'fichas'], default=None)
    p.add_argument('--recrear', action='store_true', help='borrar las colecciones antes de indexar')
    p.add_argument('--reanudar', action='store_true', help='saltar los documentos que ya están en Qdrant')
    p.add_argument('--lote', type=int, default=None,
                   help='textos por petición de embeddings (por defecto y como máximo, el del proveedor: 64 en Mistral)')
    p.add_argument('--pausa', type=float, default=PAUSA_SEGUNDOS, help='segundos de espera tras cada lote')
    p.add_argument('--paralelo', type=int, default=PARALELO, help='lotes en vuelo a la vez (límite de la clave: 10)')
    p.add_argument('--fuente', choices=['historico', 'tiempo_real'], default='historico', help='fuente de las fichas')
    p.add_argument('--qdrant', default=os.environ.get('QDRANT_URL', 'http://qdrant:6333'))
    return p.parse_args(argv)


async def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(level=logging.INFO, format='%(message)s')
    for ruidoso in ('httpx', 'httpcore', 'httpx2', 'httpcore2', 'openai'):      # el cliente de OpenAI trae su httpx
        logging.getLogger(ruidoso).setLevel(logging.WARNING)
    args = argumentos(argv)
    from llm import obtener_embeddings, proveedor
    lote = min(args.lote or proveedor().lote, proveedor().lote)
    embeddings = obtener_embeddings()
    cliente = AsyncQdrantClient(url=args.qdrant, timeout=60)
    acceso = ClienteAcceso()
    inicio = time.monotonic()
    try:
        opciones = {'lote': lote, 'pausa': args.pausa, 'reanudar': args.reanudar, 'paralelo': args.paralelo}
        if args.solo != 'fichas':
            documentos = await corpus.conocimiento_desde_api(acceso)
            await indexar_conocimiento(cliente, embeddings, documentos, args.recrear, **opciones)
        if args.solo != 'conocimiento':
            catalogo = await corpus.catalogo_desde_api(acceso)
            documentos = await F.fichas_desde_api(acceso, catalogo['barrios'], args.fuente)
            await indexar_fichas(cliente, embeddings, documentos, args.recrear, **opciones)
        avisar_por_defecto(f'[indexar] hecho en {time.monotonic() - inicio:.0f} s; puntos por colección: '
                           f'{await estado(cliente)}')
    finally:
        await acceso.cerrar()
        await cliente.close()


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit(130)
