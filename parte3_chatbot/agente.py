"""El agente, sin interfaz: lo usan la aplicación de Chainlit, comprobar_agente.py y las pruebas.

Flujo de cada mensaje:
  1. Filtro previo: si parece una petición de datos individuales, o pide un destino por zona, se rechaza
     sin pasar por el LLM (queda registrado en la API) y se propone una alternativa agregada.
  2. El LLM decide qué herramienta usar; las herramientas llaman a la API de acceso (nunca a la base).
  3. Barreras sobre la respuesta, que no dependen de que el modelo obedezca:
     - sin datos en el turno no se muestra ninguna cifra (se enseña el rechazo o un aviso);
     - con datos, cada cifra tiene que salir de ellos; si no, se muestran los datos tal cual;
     - si todos los grupos devueltos están enmascarados, la respuesta se da sin el LLM.
"""
from __future__ import annotations

import os
import re
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

from cifras import cifras_no_justificadas, respuesta_con_datos, respuesta_enmascarada, todo_enmascarado
from herramientas import (
    ESQUEMAS, INSTRUCCION_RECHAZO, ClienteAcceso, hay_datos, para_el_modelo, parece_individual, tiene_cifras)
from prompts import SISTEMA

MODELO = os.environ.get('OLLAMA_MODELO', 'llama3.1:8b')
MAX_PASOS = 5
SIN_DATOS = ('No tengo datos publicados para esa consulta, así que no te doy cifras. Prueba con otro día, '
             'barrio o nivel de agregación.')
SIN_TERMINAR = 'No he podido completar la consulta en pocos pasos; ¿puedes concretarla?'

Ejecutor = Callable[[str, dict], Awaitable[Any]]


def opciones_llm() -> dict | None:
    """Temperatura del LLM (OLLAMA_TEMPERATURA). Por defecto 0,2: con la suite de casos de uso acierta igual o
    más que con la del modelo y responde más rápido y de forma más estable. Vacía = la del modelo."""
    temperatura = os.environ.get('OLLAMA_TEMPERATURA', '0.2').strip()
    return {'temperature': float(temperatura)} if temperatura else None


@dataclass
class Llamada:
    nombre: str
    argumentos: dict
    resultado: Any
    segundos: float = 0.0


@dataclass
class Turno:
    pregunta: str
    respuesta: str = ''
    llamadas: list[Llamada] = field(default_factory=list)
    alternativa: dict | None = None      # consulta agregada que se puede lanzar con un botón o un gesto
    # filtro_previo · sin_datos · todo_enmascarado · cifras_no_verificadas · sin_terminar
    bloqueo: str | None = None
    texto_modelo: str | None = None      # respuesta original del LLM cuando no se ha mostrado
    cifras_sueltas: list[str] = field(default_factory=list)
    pasos_llm: int = 0
    segundos: float = 0.0

    @property
    def resultados(self) -> list:
        return [llamada.resultado for llamada in self.llamadas]

    @property
    def con_datos(self) -> bool:
        return any(hay_datos(r) for r in self.resultados)


# --- textos para el usuario ------------------------------------------------------------------------------

NIVELES = {'hora_zona': 'viajes por hora', 'dia_barrio': 'viajes por día', 'od_dia_barrio': 'flujos por día'}


def _fecha(valor: Any) -> datetime | None:
    try:
        return datetime.fromisoformat(str(valor))
    except ValueError:
        return None


def describir(consulta: dict, nombres_zona: dict[int, str] | None = None) -> str:
    """"viajes por hora desde Times Sq/Theatre District el 15/01/2020 de 03:00 a 04:00 (histórico)"."""
    partes = [NIVELES.get(consulta.get('nivel'), 'viajes')]
    zona = consulta.get('zona_origen')
    if zona is not None:
        nombre = (nombres_zona or {}).get(zona)
        partes.append(f'desde {nombre} (zona {zona})' if nombre else f'desde la zona {zona}')
    if consulta.get('barrio_origen'):
        partes.append(f'desde {consulta["barrio_origen"]}')
    if consulta.get('barrio_destino'):
        partes.append(f'hacia {consulta["barrio_destino"]}')
    desde, hasta = _fecha(consulta.get('desde')), _fecha(consulta.get('hasta'))
    if desde and hasta and hasta > desde:
        partes.append(_ventana(desde, hasta))
    metricas = [m for m in consulta.get('metricas') or [] if m != 'n_viajes']
    if metricas:
        partes.append(f'con {", ".join(metricas)}')
    partes.append('(tiempo real)' if consulta.get('fuente') == 'tiempo_real' else '(histórico)')
    return ' '.join(partes)


def _ventana(desde: datetime, hasta: datetime) -> str:
    if desde.time() == hasta.time() == datetime.min.time():            # días completos
        ultimo = hasta - timedelta(days=1)
        return f'el {desde:%d/%m/%Y}' if ultimo.date() == desde.date() else f'del {desde:%d/%m/%Y} al {ultimo:%d/%m/%Y}'
    if (hasta - timedelta(seconds=1)).date() == desde.date():
        return f'el {desde:%d/%m/%Y} de {desde:%H:%M} a {hasta:%H:%M}'
    return f'del {desde:%d/%m/%Y %H:%M} al {hasta:%d/%m/%Y %H:%M}'


def pie_de_fuente(resultados: list) -> str:
    """"Datos históricos" o "de tiempo real" al pie: no depende de que el LLM se acuerde de decirlo."""
    fuentes = sorted({'en tiempo real' if (r.get('consulta') or {}).get('fuente') == 'tiempo_real' else 'históricos'
                      for r in resultados if isinstance(r, dict) and r.get('filas')})
    return f'\n\n_Datos {" y ".join(fuentes)}, solo agregados._' if fuentes else ''


def texto_rechazo(rechazo: dict | None, alternativa: dict | None = None, pista: str | None = None,
                  nombres_zona: dict[int, str] | None = None) -> str:
    rechazo = rechazo or {}
    motivos = rechazo.get('motivos') or ['la plataforma solo publica agregados de al menos 10 viajes']
    texto = '🔒 **Consulta rechazada por privacidad**\n' + '\n'.join(f'- {m}' for m in motivos)
    alternativa = alternativa or rechazo.get('alternativa')
    if alternativa:
        texto += f'\n\nPuedo responder esta alternativa agregada: **{describir(alternativa, nombres_zona)}**.'
    elif pista:
        texto += f'\n\n{pista}'
    else:
        texto += '\n\nPrueba con volúmenes por hora y zona, o por día y barrio.'
    return texto


# --- el agente -------------------------------------------------------------------------------------------

class Agente:
    def __init__(self, acceso: ClienteAcceso, llm, modelo: str = MODELO, opciones: dict | None = None,
                 max_pasos: int = MAX_PASOS):
        self.acceso = acceso
        self.llm = llm
        self.modelo = modelo
        self.opciones = opciones if opciones is not None else opciones_llm()
        self.max_pasos = max_pasos
        self.mensajes: list = [{'role': 'system', 'content': SISTEMA}]

    async def responder(self, texto: str, ejecutar: Ejecutor | None = None) -> Turno:
        inicio = time.monotonic()
        turno = Turno(pregunta=texto)
        try:
            if parece_individual(texto):
                await self._rechazo_previo(turno)
            elif (destino := await self.acceso.rechazo_destino(texto)) is not None:
                rechazo, alternativa, pista = destino
                turno.llamadas.append(Llamada('solicitud_individual', {'descripcion': f'destino por zona: {texto}'},
                                              rechazo))
                turno.bloqueo, turno.alternativa = 'filtro_previo', alternativa
                turno.respuesta = texto_rechazo(rechazo, alternativa, pista, self.acceso.nombres_zona())
            else:
                self.mensajes.append({'role': 'user', 'content': texto})
                await self._bucle(turno, ejecutar or self.acceso.ejecutar)
        finally:
            turno.segundos = time.monotonic() - inicio
        return turno

    async def responder_alternativa(self, alternativa: dict, ejecutar: Ejecutor | None = None) -> Turno:
        """Lanza la alternativa tal cual, sin que el LLM la reescriba, y deja que el modelo la resuma."""
        inicio = time.monotonic()
        ejecutar = ejecutar or self.acceso.ejecutar
        turno = Turno(pregunta='Consulta la alternativa propuesta y dime el resultado con su cifra.')
        self.mensajes.append({'role': 'user', 'content': turno.pregunta})
        self.mensajes.append({'role': 'assistant', 'content': '',
                              'tool_calls': [{'function': {'name': 'consultar_viajes', 'arguments': alternativa}}]})
        try:
            await self._ejecutar(turno, 'consultar_viajes', dict(alternativa), ejecutar)
            await self._bucle(turno, ejecutar, exigir_cifra=True)
        finally:
            turno.segundos = time.monotonic() - inicio
        return turno

    async def _rechazo_previo(self, turno: Turno) -> None:
        rechazo = await self.acceso.solicitud_individual(turno.pregunta)
        alternativa, pista = await self.acceso.alternativa_individual(turno.pregunta)
        turno.llamadas.append(Llamada('solicitud_individual', {'descripcion': turno.pregunta}, rechazo))
        turno.bloqueo = 'filtro_previo'
        turno.alternativa = alternativa
        turno.respuesta = texto_rechazo(rechazo, alternativa, pista, self.acceso.nombres_zona())

    async def _ejecutar(self, turno: Turno, nombre: str, argumentos: dict, ejecutar: Ejecutor) -> None:
        inicio = time.monotonic()
        resultado = await ejecutar(nombre, argumentos)
        turno.llamadas.append(Llamada(nombre, argumentos, resultado, time.monotonic() - inicio))
        aviso = ''
        if isinstance(resultado, dict) and resultado.get('resultado') == 'rechazada':
            aviso = INSTRUCCION_RECHAZO
            if resultado.get('alternativa'):
                turno.alternativa = resultado['alternativa']
        self.mensajes.append({'role': 'tool', 'tool_name': nombre, 'content': para_el_modelo(resultado) + aviso})

    async def _bucle(self, turno: Turno, ejecutar: Ejecutor, exigir_cifra: bool = False) -> None:
        for _ in range(self.max_pasos):
            respuesta = await self.llm.chat(model=self.modelo, messages=self.mensajes, tools=ESQUEMAS,
                                            options=self.opciones)
            turno.pasos_llm += 1
            self.mensajes.append(respuesta.message)
            llamadas = respuesta.message.tool_calls or []
            if not llamadas:
                self._cerrar(turno, (respuesta.message.content or '').strip() or '(sin respuesta)', exigir_cifra)
                return
            for llamada in llamadas:
                await self._ejecutar(turno, llamada.function.name, dict(llamada.function.arguments or {}), ejecutar)
        turno.bloqueo = 'sin_terminar'
        turno.respuesta = respuesta_con_datos(turno.resultados) or SIN_TERMINAR
        self.mensajes.append({'role': 'assistant', 'content': turno.respuesta})

    def _ultimo_rechazo(self, turno: Turno) -> dict | None:
        return next((r for r in reversed(turno.resultados)
                     if isinstance(r, dict) and r.get('resultado') == 'rechazada'), None)

    def _cerrar(self, turno: Turno, contenido: str, exigir_cifra: bool = False) -> None:
        rechazo = self._ultimo_rechazo(turno)
        if not turno.con_datos and tiene_cifras(contenido):
            # Barrera: sin datos no se dejan pasar cifras (los modelos pequeños se las inventan)
            turno.bloqueo, turno.texto_modelo = 'sin_datos', contenido
            turno.respuesta = texto_rechazo(rechazo, nombres_zona=self.acceso.nombres_zona()) if rechazo else SIN_DATOS
        elif todo_enmascarado(turno.resultados):
            # Sin ninguna cifra visible el LLM no tiene nada que contar y tiende a enredarse
            turno.bloqueo, turno.texto_modelo = 'todo_enmascarado', contenido
            turno.respuesta = respuesta_enmascarada(turno.resultados)
        elif sueltas := cifras_no_justificadas(contenido, turno.resultados, turno.pregunta):
            # Barrera: cada cifra tiene que salir de los datos devueltos (ni inventadas ni deducidas)
            turno.bloqueo, turno.texto_modelo, turno.cifras_sueltas = 'cifras_no_verificadas', contenido, sueltas
            turno.respuesta = (respuesta_con_datos(turno.resultados)
                               or (texto_rechazo(rechazo, nombres_zona=self.acceso.nombres_zona()) if rechazo
                                   else SIN_DATOS))
        elif exigir_cifra and not re.search(r'\d', contenido) and (tablas := respuesta_con_datos(turno.resultados)):
            # tras aceptar una alternativa el LLM a veces solo dice «la consulta es permitida»
            turno.respuesta = f'{contenido}\n\n{tablas}'
        else:
            turno.respuesta = contenido
        if turno.respuesta != contenido:           # que el modelo no construya sobre lo que no se ha mostrado
            self.mensajes[-1] = {'role': 'assistant', 'content': turno.respuesta}
        if turno.con_datos:
            turno.alternativa = None
            if turno.bloqueo is None:
                turno.respuesta += pie_de_fuente(turno.resultados)
