"""Herramientas del agente: la única forma que tiene el LLM de ver datos es la API de acceso.

El LLM nunca toca la base de datos: si pide algo que viola la privacidad, la API lo rechaza y
devuelve una alternativa. Además, `parece_individual` detecta antes del LLM las peticiones de
viajes concretos, para no depender de que el modelo obedezca las instrucciones.
"""
from __future__ import annotations

import os
import re
from typing import Any

import httpx

ACCESO_URL = os.environ.get('ACCESO_URL', 'http://acceso:8000')
ACCESO_CLAVE = os.environ.get('ACCESO_CLAVE', '')

PATRONES_INDIVIDUALES = [
    r'\bmatr[ií]cula',
    r'\b(conductor|taxista|chófer|chofer)\b',
    r'\b(nombre|tel[eé]fono|direcci[oó]n) del (pasajero|cliente)',
    r'\bviaje (concreto|exacto|espec[ií]fico|individual)',
    r'\b(qui[eé]n|qu[eé] persona)\b.*\b(cogi[oó]|tom[oó]|subi[oó]|viaj[oó])',
    r'\blos viajes? de (un|una|el|la) (pasajer|client|usuari)',
    r'\b\d{1,2}:(?!00\b)\d{2}\b',            # una hora con minutos: apunta a un viaje concreto
    r'\b(id|identificador) del viaje',
]


def parece_individual(texto: str) -> bool:
    t = texto.lower()
    return any(re.search(p, t) for p in PATRONES_INDIVIDUALES)


ESQUEMAS: list[dict[str, Any]] = [
    {
        'type': 'function',
        'function': {
            'name': 'consultar_viajes',
            'description': (
                'Consulta agregados de viajes de taxi de Nueva York en 2020. Niveles: hora_zona (por hora y '
                'zona de origen), dia_barrio (por día y barrio de origen), od_dia_barrio (flujos entre barrios '
                'por día). Las fechas van en formato ISO 2020-MM-DDTHH:00:00 y el rango máximo es de 31 días.'),
            'parameters': {
                'type': 'object',
                'properties': {
                    'nivel': {'type': 'string', 'enum': ['hora_zona', 'dia_barrio', 'od_dia_barrio']},
                    'desde': {'type': 'string', 'description': 'inicio incluido, ISO'},
                    'hasta': {'type': 'string', 'description': 'fin excluido, ISO'},
                    'metricas': {'type': 'array', 'items': {'type': 'string', 'enum': [
                        'n_viajes', 'distancia_media', 'importe_medio', 'propina_media', 'pct_pago_tarjeta']}},
                    'zona_origen': {'type': 'integer', 'description': 'id de zona (solo hora_zona); usa buscar_zona'},
                    'barrio_origen': {'type': 'string', 'enum': ['Manhattan', 'Brooklyn', 'Queens', 'Bronx',
                                                                  'Staten Island', 'EWR']},
                    'barrio_destino': {'type': 'string', 'description': 'solo nivel od_dia_barrio'},
                    'fuente': {'type': 'string', 'enum': ['historico', 'tiempo_real']},
                },
                'required': ['nivel', 'desde', 'hasta'],
            },
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'buscar_zona',
            'description': 'Busca zonas de taxi por nombre (por ejemplo "JFK", "Times Sq") y devuelve su id y barrio.',
            'parameters': {'type': 'object', 'properties': {'texto': {'type': 'string'}}, 'required': ['texto']},
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'solicitud_individual',
            'description': ('Úsala SIEMPRE que el usuario pida datos de un viaje, persona, conductor o vehículo '
                            'concretos. La plataforma lo rechazará y quedará registrado.'),
            'parameters': {'type': 'object', 'properties': {'descripcion': {'type': 'string'}},
                           'required': ['descripcion']},
        },
    },
]


class ClienteAcceso:
    def __init__(self, url: str = ACCESO_URL, clave: str = ACCESO_CLAVE):
        self.http = httpx.AsyncClient(base_url=url, headers={'X-API-Key': clave}, timeout=30)

    async def _llamar(self, metodo: str, ruta: str, **kwargs) -> dict | list:
        r = await self.http.request(metodo, ruta, **kwargs)
        if r.status_code in (200, 403):          # 403 = rechazo de privacidad, con motivos y alternativa
            return r.json()
        return {'error': f'HTTP {r.status_code}', 'detalle': r.text[:300]}

    async def consultar_viajes(self, **consulta) -> dict:
        consulta = {k: v for k, v in consulta.items() if v not in (None, '', [])}
        return await self._llamar('POST', '/consultas', json=consulta)

    async def buscar_zona(self, texto: str) -> list:
        return await self._llamar('GET', '/zonas', params={'texto': texto})

    async def solicitud_individual(self, descripcion: str) -> dict:
        return await self._llamar('POST', '/consultas/individual', json={'descripcion': descripcion})

    async def ejecutar(self, nombre: str, argumentos: dict) -> Any:
        if nombre not in {e['function']['name'] for e in ESQUEMAS}:
            return {'error': f'herramienta desconocida: {nombre}'}
        return await getattr(self, nombre)(**argumentos)

    async def cerrar(self) -> None:
        await self.http.aclose()
