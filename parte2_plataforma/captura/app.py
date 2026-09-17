"""API de captura: puerta de entrada de los eventos en tiempo real.

- POST /viajes          lotes de viajes del proveedor (o del simulador) -> topic `viajes-crudos`
- POST /gestos          gestos reconocidos por la parte 1                -> topic `gestos`
- GET  /gestos/stream   los gestos, en directo, por SSE (lo usa el chatbot)
- GET  /metrics         métricas para Prometheus

Privacidad (E3): esta API no valida ni guarda viajes, solo los encola en un topic con retención
corta al que solo accede Spark. Nunca escribe el contenido de un viaje en los logs.
Todas las rutas de escritura y lectura exigen una clave (cabecera X-API-Key).
"""
from __future__ import annotations

import json
import os
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Annotated, Any, Literal

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from prometheus_client import Counter, make_asgi_app
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

BROKERS = os.environ.get('KAFKA_BROKERS', 'redpanda:9092')
TOPIC_VIAJES = os.environ.get('TOPIC_VIAJES', 'viajes-crudos')
TOPIC_GESTOS = os.environ.get('TOPIC_GESTOS', 'gestos')
MAX_VIAJES_POR_LOTE = 1000
GESTOS = ('ok', 'paper', 'rock', 'rockandroll', 'scissors', 'thumbsup', 'None')

EVENTOS = Counter('captura_eventos_total', 'Eventos aceptados', ['tipo', 'cliente'])
RECHAZOS = Counter('captura_peticiones_rechazadas_total', 'Peticiones rechazadas', ['motivo'])


def claves() -> dict[str, str]:
    """CAPTURA_CLAVES="cliente1=clave1,cliente2=clave2" -> {clave: cliente}."""
    pares = (p.split('=', 1) for p in os.environ.get('CAPTURA_CLAVES', '').split(',') if '=' in p)
    return {clave.strip(): cliente.strip() for cliente, clave in pares if clave.strip()}


async def cliente(x_api_key: Annotated[str | None, Header()] = None) -> str:
    nombre = claves().get(x_api_key or '')
    if nombre is None:
        RECHAZOS.labels('sin_autenticar').inc()
        raise HTTPException(status_code=401, detail='Falta la cabecera X-API-Key o no es válida')
    return nombre


class LoteViajes(BaseModel):
    lote: str | None = Field(default=None, max_length=100)
    viajes: list[dict[str, Any]] = Field(min_length=1, max_length=MAX_VIAJES_POR_LOTE)


class Gesto(BaseModel):
    gesto: Literal[GESTOS]
    confianza: float = Field(ge=0, le=1)
    modelo: str = Field(max_length=100)
    dispositivo: str = Field(max_length=100)
    instante: datetime | None = None


def _json(valor: Any) -> bytes:
    return json.dumps(valor, default=str, ensure_ascii=False).encode('utf-8')


@asynccontextmanager
async def ciclo_de_vida(app: FastAPI):
    if getattr(app.state, 'productor', None) is not None:     # los tests inyectan uno falso
        yield
        return
    from aiokafka import AIOKafkaProducer
    productor = AIOKafkaProducer(bootstrap_servers=BROKERS, value_serializer=_json,
                                 acks='all', enable_idempotence=True, linger_ms=20)
    await productor.start()
    app.state.productor = productor
    try:
        yield
    finally:
        await productor.stop()


app = FastAPI(title='PIDS · API de captura', version='0.1.0', lifespan=ciclo_de_vida)
app.mount('/metrics', make_asgi_app())


@app.get('/salud')
async def salud() -> dict:
    return {'estado': 'ok'}


@app.post('/viajes', status_code=202)
async def recibir_viajes(peticion: LoteViajes, request: Request,
                         quien: Annotated[str, Depends(cliente)]) -> dict:
    lote = peticion.lote or f'{quien}-{uuid.uuid4().hex[:12]}'
    recibido = datetime.now(timezone.utc).isoformat()
    productor = request.app.state.productor
    envios = [await productor.send(TOPIC_VIAJES, {'registro': viaje, 'origen': 'tiempo_real', 'lote': lote,
                                                  'cliente': quien, 'recibido_en': recibido})
              for viaje in peticion.viajes]
    for envio in envios:
        await envio                      # confirmación del broker
    EVENTOS.labels('viaje', quien).inc(len(envios))
    return {'aceptados': len(envios), 'lote': lote}


@app.post('/gestos', status_code=202)
async def recibir_gesto(gesto: Gesto, request: Request, quien: Annotated[str, Depends(cliente)]) -> dict:
    evento = gesto.model_dump(mode='json')
    evento['instante'] = evento['instante'] or datetime.now(timezone.utc).isoformat()
    evento['cliente'] = quien
    envio = await request.app.state.productor.send(TOPIC_GESTOS, evento, key=gesto.dispositivo.encode())
    await envio
    EVENTOS.labels('gesto', quien).inc()
    return {'aceptado': True}


@app.get('/gestos/stream')
async def flujo_gestos(request: Request, quien: Annotated[str, Depends(cliente)]) -> EventSourceResponse:
    """Gestos en directo. Cada conexión lee desde el final del topic (solo gestos nuevos)."""
    from aiokafka import AIOKafkaConsumer

    async def eventos():
        consumidor = AIOKafkaConsumer(TOPIC_GESTOS, bootstrap_servers=BROKERS, group_id=None,
                                      auto_offset_reset='latest', enable_auto_commit=False)
        await consumidor.start()
        try:
            async for mensaje in consumidor:
                if await request.is_disconnected():
                    break
                yield {'event': 'gesto', 'data': mensaje.value.decode('utf-8')}
        finally:
            await consumidor.stop()

    return EventSourceResponse(eventos(), ping=15)
