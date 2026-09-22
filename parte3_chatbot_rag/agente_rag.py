"""El agente RAG, sin interfaz: lo usan la aplicación de Chainlit (app.py), las suites y las pruebas.

Es el mismo flujo que parte3_chatbot/agente.py con dos cambios: el LLM es un modelo de LangChain (Helmcode,
compatible con OpenAI) y antes de llamarlo se recupera contexto de Qdrant. Todo lo demás se reutiliza tal
cual del chatbot de Ollama: el filtro previo, el cliente de la API (herramientas.py) y las barreras sobre
las cifras (cifras.py).

Flujo de cada mensaje:
  1. Filtro previo: una petición individual o un destino por zona se rechaza sin LLM, queda registrada en la
     API y se propone una alternativa agregada.
  2. Recuperación: `recuperador.recuperar(pregunta, k)` -> bloque «Contexto recuperado» al final del mensaje
     de sistema, solo para el turno actual (el historial guarda lo que dijeron usuario, modelo y
     herramientas, no el contexto). Las fichas de agregados recuperadas se guardan además como
     pseudo-resultados (`TurnoRAG.fichas`), para que sus cifras cuenten como datos del turno.
  3. Guardia de salida: `guardia.revisar(mensajes)` antes de cada llamada al proveedor (lanza `FugaSalida`
     si algún mensaje lleva campos individuales o claves) y `guardia.registrar(respuesta)` después (tokens).
  4. Bucle de herramientas (`llm.bind_tools`) hasta `max_pasos`; cada herramienta pasa por
     `ClienteAcceso.ejecutar`, nunca por la base de datos.
  5. Barreras sobre la respuesta, las mismas que en el chatbot de Ollama, que no dependen de que el modelo
     obedezca:
     - sin datos en el turno (ni de herramientas ni de fichas) no se muestra ninguna cifra;
     - si todo lo devuelto por las herramientas está enmascarado, la respuesta se da sin el LLM;
     - cada cifra tiene que salir de los datos del turno (herramientas o fichas); si no, se muestran los
       datos tal cual.
"""
from __future__ import annotations

import json
import logging
import os
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any, Protocol
from uuid import uuid4

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage

from agente import MAX_PASOS, SIN_DATOS, SIN_TERMINAR, Ejecutor, Llamada, Turno, pie_de_fuente, texto_rechazo
from cifras import (
    CONSTANTES, cifras_no_justificadas, numeros_en, respuesta_con_datos, respuesta_enmascarada, todo_enmascarado,
    valores_permitidos)
from herramientas import INSTRUCCION_RECHAZO, ClienteAcceso, para_el_modelo, parece_individual, tiene_cifras
from herramientas_lc import herramientas_langchain
from prompts_rag import SISTEMA_RAG, formatear_contexto

if TYPE_CHECKING:  # recuperador.py: `async def recuperar(self, pregunta: str, k: int = 6) -> list[Document]`
    from recuperador import Recuperador

try:
    from salida import FugaSalida             # la define salida.py (guardia de salida); aquí solo se captura
except ModuleNotFoundError as _error:
    if _error.name != 'salida':
        raise

    class FugaSalida(RuntimeError):  # type: ignore[no-redef]
        """La guardia ha encontrado algo que no debe salir del equipo (campos individuales, claves…).

        Sustituto con la misma firma mientras no exista salida.py (pruebas y ramas en paralelo)."""

log = logging.getLogger('pids.chatbot_rag')

K_POR_DEFECTO = int(os.environ.get('RAG_K', '6'))
PREGUNTA_ALTERNATIVA = 'Consulta la alternativa propuesta y dime el resultado con su cifra.'
BLOQUEO_GUARDIA = ('🔒 **Mensaje no enviado al modelo**: {motivo}.\n\n'
                   'Reformula la pregunta sin datos personales, identificadores ni claves.')
ERROR_LLM = ('El modelo de lenguaje no ha respondido (fallo del proveedor). Vuelve a intentarlo en unos '
             'segundos; si sigue fallando, el chatbot local sigue disponible.')
FICHAS_TAL_CUAL = ('No he podido verificar las cifras de la respuesta. Estas son las fichas publicadas que he '
                   'consultado:')
# Los campos de una fila de la API que puede traer la ficha (metadatos del documento)
CAMPOS_FICHA = ('dia', 'barrio_origen', 'barrio_destino', 'suprimido', 'n_viajes', 'distancia_media',
                'importe_medio', 'propina_media', 'pct_pago_tarjeta')
MARCA_ENMASCARADO = 'oculto'       # lo que devuelve la API para un grupo suprimido (privacidad.enmascarar)
RAZONAMIENTO = re.compile(r'<think>.*?(?:</think>|$)', re.DOTALL)


class Guardia(Protocol):
    """Revisa lo que va a salir hacia el proveedor y lleva la cuenta de tokens (salida.py)."""

    def revisar(self, mensajes: list[BaseMessage]) -> list[BaseMessage]:
        """Devuelve los mensajes que se pueden enviar; lanza FugaSalida si alguno no puede salir."""
        ...

    def registrar(self, respuesta: AIMessage) -> None:
        """Anota el consumo (`usage_metadata`) de una respuesta del proveedor."""
        ...


@dataclass
class TurnoRAG(Turno):
    """Un turno del agente RAG. A los campos de `Turno` añade el contexto usado.

    `bloqueo` admite, además de los del chatbot de Ollama, `guardia_salida` (la guardia no dejó salir el
    mensaje) y `error_llm` (el proveedor no respondió).
    """
    fuentes: list[dict] = field(default_factory=list)   # [{'titulo', 'fuente', 'tipo'}] de lo recuperado
    fichas: list[dict] = field(default_factory=list)    # fichas de agregados recuperadas, como resultados de la API
    tokens: int = 0                                      # tokens del proveedor en el turno (usage_metadata)


# --- contexto recuperado --------------------------------------------------------------------------------

def texto_de(mensaje: BaseMessage) -> str:
    """El texto de una respuesta del modelo, sin bloques de razonamiento ni etiquetas <think>.

    Un modelo que razona no debe colar su razonamiento en la respuesta: rompería la barrera de cifras.
    """
    texto = getattr(mensaje, 'text', None)
    if not isinstance(texto, str) and callable(texto):   # langchain-core < 1 lo tenía como método
        texto = texto()
    if not isinstance(texto, str):
        texto = mensaje.content if isinstance(mensaje.content, str) else ''
    return RAZONAMIENTO.sub('', texto).strip()


def fuentes_de(documentos: list[Any]) -> list[dict]:
    """[{'titulo', 'fuente', 'tipo'}] de los fragmentos recuperados, en orden y sin repetir."""
    salida, vistas = [], set()
    for documento in documentos:
        meta = documento.metadata or {}
        fuente = {'titulo': meta.get('titulo') or meta.get('fuente') or 'fragmento',
                  'fuente': meta.get('fuente') or '', 'tipo': meta.get('tipo') or 'doc'}
        clave = tuple(fuente.values())
        if clave not in vistas:
            vistas.add(clave)
            salida.append(fuente)
    return salida


def ficha_como_resultado(documento: Any) -> dict | None:
    """Una ficha de agregados recuperada, con el formato de una respuesta de la API (una consulta, una fila).

    Así `cifras.cifras_no_justificadas` acepta sus cifras y el agente no bloquea al modelo por citarla. Solo
    se convierten las fichas con nivel y día; el resto del contexto (documentación, zonas, ejemplos) no son
    datos. Los grupos suprimidos llevan la misma marca que en la API, sin cifra.
    """
    meta = documento.metadata or {}
    if meta.get('tipo') != 'ficha' or not meta.get('nivel') or not meta.get('dia'):
        return None
    try:
        dia = datetime.fromisoformat(str(meta['dia'])[:10])
    except ValueError:
        return None
    fila = {c: meta[c] for c in CAMPOS_FICHA if meta.get(c) is not None}
    fila['suprimido'] = bool(fila.get('suprimido'))
    if fila['suprimido'] and not isinstance(fila.get('n_viajes'), str):
        fila['n_viajes'] = MARCA_ENMASCARADO
    consulta = {'nivel': meta['nivel'], 'fuente': 'historico', 'desde': dia.strftime('%Y-%m-%dT%H:%M:%S'),
                'hasta': (dia + timedelta(days=1)).strftime('%Y-%m-%dT%H:%M:%S'),
                'metricas': ['n_viajes'] + [m for m in CAMPOS_FICHA[5:] if m in fila]}
    for campo in ('barrio_origen', 'barrio_destino'):
        if meta.get(campo):
            consulta[campo] = meta[campo]
    return {'resultado': 'enmascarada' if fila['suprimido'] else 'permitida', 'consulta': consulta, 'filas': [fila],
            'grupos_enmascarados': int(fila['suprimido']), 'truncada': False, 'origen': 'ficha',
            'titulo': meta.get('titulo'), 'texto': (documento.page_content or '').strip()}


def fichas_como_texto(fichas: list[dict]) -> str | None:
    """Las fichas recuperadas tal cual (su texto publicado), cuando la respuesta del modelo no es fiable."""
    textos = [ficha['texto'] for ficha in fichas if ficha.get('texto')]
    if not textos:
        return None
    return FICHAS_TAL_CUAL + '\n\n' + '\n'.join(f'- {texto}' for texto in textos)


def cita_fichas(contenido: str, fichas: list[dict]) -> bool:
    """¿Alguna cifra de la respuesta sale de las fichas recuperadas? Las constantes de las reglas (el umbral
    de 10 viajes, los 31 días) no cuentan: mencionarlas no es citar un dato."""
    if not fichas:
        return False
    citadas = numeros_en(contenido) - CONSTANTES
    return bool(citadas & (valores_permitidos(fichas) - CONSTANTES))


# --- el agente -------------------------------------------------------------------------------------------

class AgenteRAG:
    def __init__(self, acceso: ClienteAcceso, llm: BaseChatModel, recuperador: Recuperador,
                 guardia: Guardia | None = None, k: int | None = None, max_pasos: int = MAX_PASOS):
        self.acceso = acceso
        self.recuperador = recuperador
        self.guardia = guardia
        self.k = k if k is not None else K_POR_DEFECTO      # None: el valor de RAG_K (6 si no está)
        self.max_pasos = max_pasos
        self.llm = llm.bind_tools(herramientas_langchain(acceso))
        # Sin el mensaje de sistema: se construye en cada llamada con el contexto del turno
        self.historial: list[BaseMessage] = []

    async def responder(self, texto: str, ejecutar: Ejecutor | None = None) -> TurnoRAG:
        inicio = time.monotonic()
        turno = TurnoRAG(pregunta=texto)
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
                contexto = await self._recuperar(turno)
                desde = len(self.historial)
                self.historial.append(HumanMessage(content=texto))
                await self._bucle(turno, ejecutar or self.acceso.ejecutar, contexto, desde)
        finally:
            turno.segundos = time.monotonic() - inicio
        return turno

    async def responder_alternativa(self, alternativa: dict, ejecutar: Ejecutor | None = None) -> TurnoRAG:
        """Lanza la alternativa tal cual, sin que el LLM la reescriba, y deja que el modelo la resuma."""
        inicio = time.monotonic()
        ejecutar = ejecutar or self.acceso.ejecutar
        turno = TurnoRAG(pregunta=PREGUNTA_ALTERNATIVA)
        desde = len(self.historial)
        id_llamada = f'alternativa-{uuid4().hex[:8]}'
        self.historial.append(HumanMessage(content=turno.pregunta))
        self.historial.append(AIMessage(content='', tool_calls=[
            {'name': 'consultar_viajes', 'args': dict(alternativa), 'id': id_llamada, 'type': 'tool_call'}]))
        try:
            await self._ejecutar(turno, 'consultar_viajes', dict(alternativa), id_llamada, ejecutar)
            await self._bucle(turno, ejecutar, formatear_contexto([]), desde, exigir_cifra=True)
        finally:
            turno.segundos = time.monotonic() - inicio
        return turno

    async def _rechazo_previo(self, turno: TurnoRAG) -> None:
        rechazo = await self.acceso.solicitud_individual(turno.pregunta)
        alternativa, pista = await self.acceso.alternativa_individual(turno.pregunta)
        turno.llamadas.append(Llamada('solicitud_individual', {'descripcion': turno.pregunta}, rechazo))
        turno.bloqueo = 'filtro_previo'
        turno.alternativa = alternativa
        turno.respuesta = texto_rechazo(rechazo, alternativa, pista, self.acceso.nombres_zona())

    async def _recuperar(self, turno: TurnoRAG) -> str:
        """El bloque de contexto del turno; si Qdrant falla, el agente sigue solo con las herramientas."""
        try:
            documentos = list(await self.recuperador.recuperar(turno.pregunta, k=self.k))
        except Exception as e:  # noqa: BLE001 - sin contexto se puede responder; sin agente, no
            log.warning('recuperación fallida (%s): se responde sin contexto', type(e).__name__)
            documentos = []
        turno.fuentes = fuentes_de(documentos)
        turno.fichas = [ficha for d in documentos if (ficha := ficha_como_resultado(d)) is not None]
        return formatear_contexto(documentos)

    async def _llamar_llm(self, turno: TurnoRAG, contexto: str) -> AIMessage:
        mensajes: list[BaseMessage] = [SystemMessage(content=f'{SISTEMA_RAG}\n\n{contexto}'), *self.historial]
        if self.guardia is not None:
            mensajes = self.guardia.revisar(mensajes)
        respuesta = await self.llm.ainvoke(mensajes)
        turno.pasos_llm += 1
        turno.tokens += int((respuesta.usage_metadata or {}).get('total_tokens') or 0)
        if self.guardia is not None:
            self.guardia.registrar(respuesta)
        return respuesta

    async def _ejecutar(self, turno: TurnoRAG, nombre: str, argumentos: dict, id_llamada: str,
                        ejecutar: Ejecutor) -> None:
        inicio = time.monotonic()
        resultado = await ejecutar(nombre, argumentos)
        turno.llamadas.append(Llamada(nombre, argumentos, resultado, time.monotonic() - inicio))
        aviso = ''
        if isinstance(resultado, dict) and resultado.get('resultado') == 'rechazada':
            aviso = INSTRUCCION_RECHAZO
            if resultado.get('alternativa'):
                turno.alternativa = resultado['alternativa']
        self.historial.append(ToolMessage(content=para_el_modelo(resultado) + aviso, tool_call_id=id_llamada,
                                          name=nombre))

    def _llamada_invalida(self, turno: TurnoRAG, invalida: dict) -> None:
        """El modelo ha escrito mal los argumentos (JSON inválido): se le devuelve el error para que repita."""
        nombre = invalida.get('name') or 'desconocida'
        error = {'error': f'argumentos no válidos para {nombre}: {invalida.get("error") or "JSON mal formado"}'}
        turno.llamadas.append(Llamada(nombre, {'argumentos_texto': invalida.get('args')}, error))
        self.historial.append(ToolMessage(content=json.dumps(error, ensure_ascii=False),
                                          tool_call_id=invalida.get('id') or f'invalida-{uuid4().hex[:8]}',
                                          name=nombre))

    async def _bucle(self, turno: TurnoRAG, ejecutar: Ejecutor, contexto: str, desde: int,
                     exigir_cifra: bool = False) -> None:
        for _ in range(self.max_pasos):
            try:
                respuesta = await self._llamar_llm(turno, contexto)
            except FugaSalida as e:
                del self.historial[desde:]        # lo que no ha salido del equipo tampoco se queda en el historial
                turno.bloqueo = 'guardia_salida'
                turno.respuesta = BLOQUEO_GUARDIA.format(motivo=str(e) or 'contenido que no puede salir del equipo')
                return
            except Exception as e:  # noqa: BLE001 - proveedor externo: se avisa al usuario en vez de romper la sesión
                log.warning('la llamada al LLM ha fallado: %s: %s', type(e).__name__, str(e)[:200])
                turno.bloqueo, turno.respuesta = 'error_llm', ERROR_LLM
                self.historial.append(AIMessage(content=ERROR_LLM))
                return
            self.historial.append(respuesta)
            if not respuesta.tool_calls and not respuesta.invalid_tool_calls:
                self._cerrar(turno, texto_de(respuesta) or '(sin respuesta)', exigir_cifra)
                return
            for llamada in respuesta.tool_calls:
                if not llamada.get('id'):             # el id tiene que coincidir con el del mensaje de la herramienta
                    llamada['id'] = f'llamada-{uuid4().hex[:8]}'
                await self._ejecutar(turno, llamada['name'], dict(llamada.get('args') or {}), llamada['id'], ejecutar)
            for invalida in respuesta.invalid_tool_calls:
                self._llamada_invalida(turno, invalida)
        turno.bloqueo = 'sin_terminar'
        turno.respuesta = respuesta_con_datos(turno.resultados) or SIN_TERMINAR
        self.historial.append(AIMessage(content=turno.respuesta))

    def _ultimo_rechazo(self, turno: TurnoRAG) -> dict | None:
        return next((r for r in reversed(turno.resultados)
                     if isinstance(r, dict) and r.get('resultado') == 'rechazada'), None)

    def _cerrar(self, turno: TurnoRAG, contenido: str, exigir_cifra: bool = False) -> None:
        rechazo = self._ultimo_rechazo(turno)
        datos = turno.resultados + turno.fichas          # las cifras pueden salir de una herramienta o de una ficha
        if not turno.con_datos and not turno.fichas and tiene_cifras(contenido):
            # Barrera: sin datos no se dejan pasar cifras
            turno.bloqueo, turno.texto_modelo = 'sin_datos', contenido
            turno.respuesta = texto_rechazo(rechazo, nombres_zona=self.acceso.nombres_zona()) if rechazo else SIN_DATOS
        elif todo_enmascarado(turno.resultados):
            # Solo lo devuelto por las herramientas: una ficha oculta recuperada por parecido no manda en la respuesta
            turno.bloqueo, turno.texto_modelo = 'todo_enmascarado', contenido
            turno.respuesta = respuesta_enmascarada(turno.resultados)
        elif sueltas := cifras_no_justificadas(contenido, datos, turno.pregunta):
            # Barrera: cada cifra tiene que salir de los datos del turno (ni inventadas ni deducidas)
            turno.bloqueo, turno.texto_modelo, turno.cifras_sueltas = 'cifras_no_verificadas', contenido, sueltas
            turno.respuesta = (respuesta_con_datos(turno.resultados) or fichas_como_texto(turno.fichas)
                               or (texto_rechazo(rechazo, nombres_zona=self.acceso.nombres_zona()) if rechazo
                                   else SIN_DATOS))
        elif exigir_cifra and not re.search(r'\d', contenido) and (tablas := respuesta_con_datos(turno.resultados)):
            # tras aceptar una alternativa el LLM a veces solo dice «la consulta es permitida»
            turno.respuesta = f'{contenido}\n\n{tablas}'
        else:
            turno.respuesta = contenido
        if turno.respuesta != contenido:           # que el modelo no construya sobre lo que no se ha mostrado
            self.historial[-1] = AIMessage(content=turno.respuesta)
        if turno.con_datos:
            turno.alternativa = None
        if turno.bloqueo is None:
            # el pie cuenta las fichas solo si la respuesta cita alguna de sus cifras: explicar no es dar datos
            turno.respuesta += pie_de_fuente(turno.resultados + (turno.fichas if cita_fichas(contenido, turno.fichas)
                                                                 else []))
