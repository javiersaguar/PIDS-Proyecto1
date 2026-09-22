"""Reglas propias de privacidad (E3) para las consultas: qué se permite, qué se enmascara y qué se rechaza.

La protección tiene dos capas:
  1. Spark solo publica agregados y deja marcados como `suprimido` los grupos con menos de
     `k_minimo` viajes (sin cifras). Los datos individuales no salen nunca de la zona restringida.
  2. Este módulo filtra cada consulta antes de ir a MongoDB: solo niveles de agregación
     publicados, ventanas alineadas a su granularidad, rango máximo, y ningún campo individual.
     Si rechaza, propone una alternativa agregada que sí se puede responder.

Todo es lógica pura (sin base de datos) para poder probarla a fondo. Las reglas están en
`config/privacidad.json`.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timedelta
from enum import StrEnum
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, field_validator

RUTA_CONFIG = Path(os.environ.get('PIDS_CONFIG_DIR', Path(__file__).resolve().parents[2] / 'config'))


@lru_cache(maxsize=1)
def config() -> dict:
    return json.loads((RUTA_CONFIG / 'privacidad.json').read_text(encoding='utf-8'))


class Resultado(StrEnum):
    PERMITIDA = 'permitida'
    ENMASCARADA = 'enmascarada'
    RECHAZADA = 'rechazada'


BARRIOS = ['Manhattan', 'Brooklyn', 'Queens', 'Bronx', 'Staten Island', 'EWR', 'N/A', 'Unknown']


class Consulta(BaseModel):
    """Consulta agregada. Es lo único que acepta la API de acceso."""
    nivel: Literal['hora_zona', 'dia_barrio', 'od_dia_barrio']
    fuente: Literal['historico', 'tiempo_real'] = 'historico'
    desde: datetime
    hasta: datetime
    metricas: list[str] = Field(default_factory=lambda: ['n_viajes'])
    zona_origen: int | None = None
    barrio_origen: str | None = None
    barrio_destino: str | None = None
    campos_extra: list[str] = Field(default_factory=list,
                                    description='Campos adicionales pedidos; si alguno es individual, se rechaza')

    @field_validator('barrio_origen', 'barrio_destino', mode='before')
    @classmethod
    def _limpiar_barrio(cls, valor):
        """Un LLM manda a veces "" o una lista en texto: se trata como "sin filtro"."""
        if valor is None:
            return None
        texto = str(valor).strip()
        return texto or None

    @field_validator('zona_origen', mode='before')
    @classmethod
    def _limpiar_zona(cls, valor):
        return None if valor in (None, '', 'null', 'None') else valor

    @field_validator('metricas', 'campos_extra', mode='before')
    @classmethod
    def _lista_tolerante(cls, valor, info):
        """Un LLM manda a veces la lista como texto ('["n_viajes"]' o 'n_viajes, propina_media').

        Se acepta la forma chapucera y se normaliza: ser tolerante con el formato no relaja ninguna
        regla de privacidad, porque después se valida contra las métricas publicadas.
        """
        if valor is None or valor == '':
            valor = []
        elif isinstance(valor, str):
            try:
                cargado = json.loads(valor)
            except ValueError:
                cargado = valor.strip().strip('[]').split(',')
            valor = cargado if isinstance(cargado, list) else [cargado]
        elif not isinstance(valor, (list, tuple, set)):
            valor = [valor]
        limpio = [str(v).strip().strip('\'"') for v in valor]
        limpio = [v for v in limpio if v]
        if info.field_name == 'metricas' and not limpio:
            return ['n_viajes']
        return limpio


class Decision(BaseModel):
    resultado: Resultado
    motivos: list[str] = Field(default_factory=list)
    alternativa: Consulta | None = None

    @property
    def permitida(self) -> bool:
        return self.resultado != Resultado.RECHAZADA


def coleccion(consulta: Consulta) -> str:
    cfg = config()
    return cfg['fuentes'][consulta.fuente] + cfg['niveles'][consulta.nivel]['coleccion']


def _paso(nivel: str) -> timedelta:
    return timedelta(hours=1) if config()['niveles'][nivel]['tiempo'] == 'hora' else timedelta(days=1)


def _alinear(momento: datetime, paso: timedelta, arriba: bool) -> datetime:
    base = momento.replace(minute=0, second=0, microsecond=0)
    if paso >= timedelta(days=1):
        base = base.replace(hour=0)
    if arriba and base < momento:
        base += paso
    return base


def evaluar(consulta: Consulta) -> Decision:
    """Decide si la consulta se puede responder. `enmascarada` se decide después, al ver los datos."""
    cfg = config()
    motivos: list[str] = []
    alt = consulta.model_copy(deep=True)

    individuales = sorted(set(consulta.campos_extra) & set(cfg['campos_individuales']))
    if individuales:
        motivos.append(f'pide campos individuales: {", ".join(individuales)}')
    desconocidos = sorted(set(consulta.campos_extra) - set(cfg['campos_individuales']))
    if desconocidos:
        motivos.append(f'campos no publicados: {", ".join(desconocidos)}')
    alt.campos_extra = []

    no_publicadas = [m for m in consulta.metricas if m not in cfg['metricas']]
    if no_publicadas:
        motivos.append(f'métricas no publicadas: {", ".join(no_publicadas)}')
        alt.metricas = [m for m in consulta.metricas if m in cfg['metricas']] or ['n_viajes']

    # primero el nivel al que hay que subir; después, los filtros que ese nivel no admite
    dims = cfg['niveles'][consulta.nivel]['dimensiones']
    if consulta.barrio_destino is not None and 'barrio_destino' not in dims:
        motivos.append('el destino solo se publica por barrio y día (nivel od_dia_barrio)')
        alt.nivel = 'od_dia_barrio'
    elif consulta.barrio_origen is not None and 'barrio_origen' not in dims:
        motivos.append(f'el nivel {consulta.nivel} no filtra por barrio; se usa dia_barrio')
        alt.nivel = 'dia_barrio'
    for campo in ('barrio_origen', 'barrio_destino'):
        valor = getattr(consulta, campo)
        if valor is not None and valor not in BARRIOS:
            barrios = ', '.join(BARRIOS[:6])
            motivos.append(f'{campo} desconocido: {valor!r} (los barrios son: {barrios})')
            setattr(alt, campo, None)

    dims_alt = cfg['niveles'][alt.nivel]['dimensiones']
    if consulta.zona_origen is not None and 'zona_origen' not in dims_alt:
        motivos.append(f'el nivel {alt.nivel} no tiene zona; se agrega por barrio')
        alt.zona_origen = None

    paso = _paso(alt.nivel)
    if consulta.hasta <= consulta.desde:
        motivos.append('la ventana temporal está vacía')
        alt.hasta = alt.desde + paso
    desde = _alinear(alt.desde, paso, arriba=False)
    hasta = _alinear(alt.hasta, paso, arriba=True)
    if hasta - desde < paso:
        hasta = desde + paso
    if (desde, hasta) != (consulta.desde, consulta.hasta):
        unidad = 'una hora completa' if paso == timedelta(hours=1) else 'un día completo'
        motivos.append(f'la granularidad mínima es de {unidad}')
    maximo = timedelta(days=cfg['max_dias_por_consulta'])
    if hasta - desde > maximo:
        motivos.append(f'el rango máximo por consulta es de {cfg["max_dias_por_consulta"]} días')
        hasta = desde + maximo
    alt.desde, alt.hasta = desde, hasta

    if motivos:
        return Decision(resultado=Resultado.RECHAZADA, motivos=motivos, alternativa=alt)
    return Decision(resultado=Resultado.PERMITIDA)


def rechazo_individual(descripcion: str) -> Decision:
    """Respuesta fija para cualquier intento de obtener viajes concretos."""
    return Decision(
        resultado=Resultado.RECHAZADA,
        motivos=[f'petición de datos individuales: {descripcion}'[:300],
                 'la plataforma solo publica agregados de al menos '
                 f'{config()["k_minimo"]} viajes'],
    )


def enmascarar(filas: list[dict], metricas: list[str]) -> tuple[list[dict], int]:
    """Oculta las cifras de los grupos suprimidos. Devuelve las filas y cuántas se han enmascarado.

    La etiqueta es ``oculto`` para todos: un grupo suprimido puede tener menos de k viajes o ser
    el complementario (10 o más), y esa marca no se publica, así que ``<10`` sería falso. Nunca se
    suman a ningún total: el total menos lo visible revelaría justo lo oculto (ataque por diferencia).
    """
    salida, ocultas = [], 0
    for fila in filas:
        fila = {c: v for c, v in fila.items() if c != '_id'}
        if fila.get('suprimido'):
            ocultas += 1
            for m in metricas:
                fila[m] = None
            fila['n_viajes'] = 'oculto'
        salida.append(fila)
    return salida, ocultas


def resultado_final(ocultas: int) -> Resultado:
    return Resultado.ENMASCARADA if ocultas else Resultado.PERMITIDA
