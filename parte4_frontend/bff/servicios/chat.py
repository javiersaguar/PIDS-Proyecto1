"""Asistente conversacional del portal (CONTRATOS.md §5, «chat»): sesiones en memoria con un agente vivo y los
eventos de cada turno.

El BFF ejecuta el mismo agente que Chainlit (`parte3_chatbot/agente.py`) dentro de su proceso en vez de reenviar
al chatbot: así el navegador nunca ve la clave de la API de acceso ni la URL de Ollama, y las barreras de
privacidad son exactamente las del agente (aquí no se reimplementa ninguna: la respuesta se emite tal cual).

Dos motores:
  - `ollama`: `Agente` con `ollama.AsyncClient` (LLM local; ninguna pregunta sale del equipo).
  - `rag`: `parte3_chatbot_rag/fabrica.py::agente_rag`, solo si ese módulo existe en esta copia del repositorio
    y el grupo `rag` (LangChain) está instalado; si no, el motor aparece con `disponible: false`.

Cada sesión guarda su agente (con el historial de la conversación), un `ClienteAcceso` propio con la clave del
cliente `frontend`, el contador de tokens y la alternativa pendiente tras un rechazo. Las sesiones caducan a las
2 h sin uso y un cerrojo por sesión impide dos turnos a la vez sobre el mismo agente (→ 409).

Los pasos de las herramientas llegan en directo: el `ejecutar` que se pasa al agente encola un evento `paso` por
cada herramienta mientras el agente corre en una tarea aparte; el generador los emite según llegan y al final
emite `respuesta` (o `error` si el agente falla, sin traza ni claves).

Los módulos de `parte3_chatbot` se importan como módulos sueltos (`import agente`), porque entre ellos se importan
así; por eso sus carpetas se añaden a `sys.path` (en la imagen Docker están en `/app/parte3_chatbot`).
"""
from __future__ import annotations

import asyncio
import importlib
import importlib.util
import logging
import secrets
import sys
import time
from collections.abc import AsyncGenerator, Awaitable, Callable
from dataclasses import asdict, dataclass, field
from datetime import timedelta
from functools import lru_cache
from types import ModuleType
from typing import Any, Literal

from ..configuracion import RAIZ, Configuracion

log = logging.getLogger('pids.frontend')

RUTA_CHATBOT = RAIZ / 'parte3_chatbot'
RUTA_RAG = RAIZ / 'parte3_chatbot_rag'
for _ruta in (RUTA_RAG, RUTA_CHATBOT):
    if _ruta.is_dir() and str(_ruta) not in sys.path:
        sys.path.insert(0, str(_ruta))

import agente as AG  # noqa: E402  (parte3_chatbot, módulo suelto)
from herramientas import ClienteAcceso  # noqa: E402

try:
    from ollama import AsyncClient as ClienteOllama  # noqa: E402
except ImportError:                                  # sin el grupo `chatbot` el motor ollama no está disponible
    ClienteOllama = None                             # type: ignore[assignment,misc]

IdMotor = Literal['ollama', 'rag']
TipoEvento = Literal['paso', 'respuesta', 'error']
Ejecutor = Callable[[str, dict], Awaitable[Any]]
# (motor, configuración, cliente de acceso) -> (agente, contador de tokens); los tests la sustituyen
FabricaAgente = Callable[[str, Configuracion, ClienteAcceso], tuple[Any, Any]]

CADUCIDAD = timedelta(hours=2)
LARGO_RESUMEN = 120


# --- tipos del contrato ------------------------------------------------------------------------------------

@dataclass(frozen=True)
class Motor:
    id: IdMotor
    nombre: str
    modelo: str
    disponible: bool
    descripcion: str


@dataclass(frozen=True)
class EventoPaso:
    nombre: str
    argumentos: dict
    resultado: str          # resumen corto, nunca las filas
    segundos: float


@dataclass(frozen=True)
class EventoRespuesta:
    respuesta: str          # Markdown tal cual lo produce el agente
    bloqueo: str | None
    pasos_llm: int
    segundos: float
    tokens: int | None
    alternativa: dict | None
    alternativa_descripcion: str | None
    fuentes: list[dict]     # solo el motor rag


@dataclass(frozen=True)
class Evento:
    """Un evento SSE: `tipo` va en el campo `event` y `datos` en `data` (como JSON)."""
    tipo: TipoEvento
    datos: dict


class ErrorChat(Exception):
    """Error del servicio que el router traduce a HTTP (`codigo`, `detail`)."""
    codigo = 400

    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


class MotorDesconocido(ErrorChat):
    codigo = 422


class MotorNoDisponible(ErrorChat):
    codigo = 409


class MotorNoArranca(ErrorChat):
    codigo = 503


class SesionNoEncontrada(ErrorChat):
    codigo = 404


class SesionOcupada(ErrorChat):
    codigo = 409


class SinAlternativa(ErrorChat):
    codigo = 400


# --- lógica pura -------------------------------------------------------------------------------------------

@lru_cache(maxsize=1)
def fabrica_rag() -> ModuleType | None:
    """`parte3_chatbot_rag/fabrica.py` si existe en esta copia del repositorio y el grupo `rag` está instalado.

    El módulo importa sin LangChain (lo tolera él mismo), pero `agente_rag` no funcionaría: por eso se comprueba
    también `langchain_core`. Sin cualquiera de las dos cosas el motor `rag` aparece como no disponible.
    """
    if not (RUTA_RAG / 'fabrica.py').is_file() or importlib.util.find_spec('langchain_core') is None:
        return None
    try:
        return importlib.import_module('fabrica')
    except ImportError as e:
        log.warning('El módulo del chatbot RAG existe pero no se puede importar (%s): motor rag no disponible',
                    type(e).__name__)
        return None


def motores(cfg: Configuracion) -> list[Motor]:
    """Los dos motores del contrato, con `disponible` según lo que hay instalado."""
    rag = fabrica_rag()
    return [
        Motor(id='ollama', nombre='Ollama', modelo=cfg.ollama_modelo,
              disponible=bool(cfg.ollama_url) and ClienteOllama is not None,
              descripcion='LLM local; ninguna pregunta sale del equipo'),
        Motor(id='rag', nombre='RAG', modelo=rag.modelo_rag() if rag is not None else '',
              disponible=rag is not None, descripcion='Mistral + Qdrant; barreras heredadas'),
    ]


def motor_disponible(cfg: Configuracion, id_motor: str) -> Motor:
    """El motor pedido, si existe y está disponible; si no, `MotorDesconocido` (422) o `MotorNoDisponible` (409)."""
    motor = next((m for m in motores(cfg) if m.id == id_motor), None)
    if motor is None:
        raise MotorDesconocido(f'Motor desconocido: {id_motor!r}')
    if not motor.disponible:
        raise MotorNoDisponible(f'El motor {motor.id} no está disponible en esta instalación')
    return motor


def _plural(n: int, singular: str, plural: str) -> str:
    return f'{n} {singular if n == 1 else plural}'


def resumir_resultado(resultado: Any) -> str:
    """Texto corto para el evento `paso`: el veredicto de la API («permitida», «rechazada», …) con el número de
    filas, las zonas encontradas por una búsqueda o el error. Nunca las filas: la respuesta ya las lleva."""
    if isinstance(resultado, dict):
        if 'resultado' in resultado:
            texto = str(resultado['resultado'])
            filas = resultado.get('filas')
            if isinstance(filas, list) and filas:
                detalle = _plural(len(filas), 'fila', 'filas')
                if ocultas := resultado.get('grupos_enmascarados') or 0:
                    detalle += f', {_plural(int(ocultas), "enmascarada", "enmascaradas")}'
                texto += f' ({detalle})'
            return texto[:LARGO_RESUMEN]
        if 'error' in resultado:
            return f'error: {resultado["error"]}'[:LARGO_RESUMEN]
    if isinstance(resultado, list):
        return _plural(len(resultado), 'zona', 'zonas')
    return str(resultado)[:LARGO_RESUMEN]


def evento_paso(nombre: str, argumentos: dict, resultado: Any, segundos: float) -> Evento:
    return Evento('paso', asdict(EventoPaso(nombre=nombre, argumentos=dict(argumentos or {}),
                                            resultado=resumir_resultado(resultado), segundos=round(segundos, 3))))


def evento_respuesta(turno: Any, tokens: int | None, nombres_zona: dict[int, str] | None = None) -> Evento:
    """El `EventoRespuesta` de un `Turno` (o `TurnoRAG`, que añade `fuentes`). La respuesta va tal cual."""
    alternativa = turno.alternativa if isinstance(turno.alternativa, dict) else None
    fuentes = [dict(f) for f in getattr(turno, 'fuentes', None) or [] if isinstance(f, dict)]
    return Evento('respuesta', asdict(EventoRespuesta(
        respuesta=turno.respuesta,
        bloqueo=turno.bloqueo,
        pasos_llm=turno.pasos_llm,
        segundos=round(turno.segundos, 3),
        tokens=tokens,
        alternativa=alternativa,
        alternativa_descripcion=AG.describir(alternativa, nombres_zona) if alternativa else None,
        fuentes=fuentes,
    )))


def detalle_error(error: BaseException) -> str:
    """Texto para el evento `error`: tipo y primera línea del mensaje, sin traza. Las claves nunca aparecen en
    los mensajes de los clientes HTTP (van en cabeceras) ni en los del agente."""
    if isinstance(error, ErrorChat):
        return error.detail
    mensaje = str(error).strip().splitlines()[0][:200] if str(error).strip() else ''
    detalle = f'{type(error).__name__}: {mensaje}' if mensaje else type(error).__name__
    return f'El asistente no ha podido responder ({detalle})'


def tokens_de(contador: Any) -> int | None:
    tokens = getattr(contador, 'tokens', None)
    return int(tokens) if isinstance(tokens, (int, float)) and not isinstance(tokens, bool) else None


def tokens_del_turno(contador: Any, antes: int | None, turno: Any) -> int | None:
    """Tokens consumidos en el turno: la diferencia del contador o, si no hay contador, los que declara el turno
    (`TurnoRAG.tokens`); `None` si no se puede saber."""
    despues = tokens_de(contador)
    if antes is not None and despues is not None:
        return despues - antes
    propios = getattr(turno, 'tokens', None)
    return int(propios) if isinstance(propios, int) and not isinstance(propios, bool) else None


class OllamaContado:
    """Envuelve al cliente de Ollama para sumar los tokens (entrada + salida) de cada `chat`, lo único que usa el
    agente. Es lo mismo que hace `fabrica.OllamaContado` del chatbot RAG; copiado para no depender de ese módulo."""

    def __init__(self, cliente: Any) -> None:
        self.cliente = cliente
        self.tokens = 0
        self.llamadas = 0

    async def chat(self, **argumentos: Any) -> Any:
        respuesta = await self.cliente.chat(**argumentos)
        self.llamadas += 1
        self.tokens += (int(getattr(respuesta, 'prompt_eval_count', 0) or 0)
                        + int(getattr(respuesta, 'eval_count', 0) or 0))
        return respuesta


def crear_agente(motor: str, cfg: Configuracion, acceso: ClienteAcceso) -> tuple[Any, Any]:
    """El agente vivo de una sesión y su contador de tokens. Los tests sustituyen esta función (`monkeypatch`)
    por una que devuelva un agente con un LLM falso y una API en memoria."""
    if motor == 'ollama':
        if ClienteOllama is None:
            raise MotorNoDisponible('El motor ollama no está disponible: falta la biblioteca `ollama`')
        contador = OllamaContado(ClienteOllama(host=cfg.ollama_url))
        return AG.Agente(acceso, contador, modelo=cfg.ollama_modelo), contador
    if motor == 'rag':
        rag = fabrica_rag()
        if rag is None:
            raise MotorNoDisponible('El motor rag no está disponible en esta instalación')
        return rag.agente_rag(acceso)
    raise MotorDesconocido(f'Motor desconocido: {motor!r}')


# --- sesiones ----------------------------------------------------------------------------------------------

@dataclass
class Sesion:
    id: str
    motor: IdMotor
    agente: Any                                 # Agente (ollama) o AgenteRAG (rag), con su historial
    contador: Any                               # objeto con `.tokens` acumulados (o None)
    acceso: ClienteAcceso                       # un cliente HTTP por sesión, con la clave del cliente `frontend`
    alternativa_pendiente: dict | None = None   # consulta agregada propuesta tras el último rechazo
    ultimo_uso: float = 0.0                     # reloj monotónico
    cerrojo: asyncio.Lock = field(default_factory=asyncio.Lock)

    @property
    def ocupada(self) -> bool:
        return self.cerrojo.locked()


class Sesiones:
    """Las sesiones de chat de un proceso del BFF: diccionario en memoria `id -> Sesion` con caducidad.

    `fabrica` construye el agente de cada sesión (por defecto `crear_agente`, resuelta al llamar para que los
    tests puedan sustituirla en el módulo); `reloj` permite probar la caducidad sin esperar.
    """

    def __init__(self, cfg: Configuracion, fabrica: FabricaAgente | None = None,
                 caducidad: timedelta = CADUCIDAD, reloj: Callable[[], float] = time.monotonic) -> None:
        self.cfg = cfg
        self._fabrica = fabrica
        self.caducidad = caducidad.total_seconds()
        self.reloj = reloj
        self.sesiones: dict[str, Sesion] = {}

    def motores(self) -> list[Motor]:
        return motores(self.cfg)

    async def crear(self, id_motor: str) -> Sesion:
        """Una sesión nueva con su agente. 422 si el motor no existe, 409 si no está disponible, 503 si no arranca."""
        await self.purgar()
        motor = motor_disponible(self.cfg, id_motor)
        acceso = ClienteAcceso(url=self.cfg.acceso_url, clave=self.cfg.acceso_clave)
        fabrica = self._fabrica or crear_agente
        try:
            # En un hilo: construir el agente RAG carga modelos y abre clientes, y no debe parar el bucle de eventos
            agente, contador = await asyncio.to_thread(fabrica, motor.id, self.cfg, acceso)
        except ErrorChat:
            await acceso.cerrar()
            raise
        except ImportError as e:
            await acceso.cerrar()
            falta = e.name or 'una dependencia'
            raise MotorNoDisponible(f'El motor {motor.id} no está disponible: falta {falta}') from e
        except Exception as e:  # noqa: BLE001 - Qdrant o el proveedor pueden no responder: no es un 500 del portal
            await acceso.cerrar()
            log.warning('No se ha podido iniciar el motor %s: %s', motor.id, type(e).__name__)
            raise MotorNoArranca(f'No se ha podido iniciar el motor {motor.id} ({type(e).__name__})') from e
        sesion = Sesion(id=secrets.token_urlsafe(16), motor=motor.id, agente=agente, contador=contador,
                        acceso=acceso, ultimo_uso=self.reloj())
        self.sesiones[sesion.id] = sesion
        log.info('Sesión de chat %s creada (motor %s)', sesion.id, motor.id)
        return sesion

    async def obtener(self, id_sesion: str) -> Sesion:
        """La sesión, si existe y no ha caducado (404 si no)."""
        await self.purgar()
        sesion = self.sesiones.get(id_sesion)
        if sesion is None:
            raise SesionNoEncontrada('La sesión de chat no existe o ha caducado')
        return sesion

    async def cerrar(self, id_sesion: str) -> None:
        sesion = self.sesiones.pop(id_sesion, None)
        if sesion is None:
            raise SesionNoEncontrada('La sesión de chat no existe o ha caducado')
        await sesion.acceso.cerrar()
        log.info('Sesión de chat %s cerrada', sesion.id)

    async def purgar(self) -> None:
        """Cierra las sesiones sin uso desde hace más de `caducidad` (una con un turno en curso se respeta)."""
        ahora = self.reloj()
        caducadas = [s for s in self.sesiones.values() if not s.ocupada and ahora - s.ultimo_uso > self.caducidad]
        for sesion in caducadas:
            del self.sesiones[sesion.id]
            await sesion.acceso.cerrar()
            log.info('Sesión de chat %s caducada', sesion.id)

    # --- turnos ---

    async def reservar(self, sesion: Sesion, alternativa: bool = False) -> None:
        """Reserva la sesión para un turno antes de empezar a emitir (así el 409 y el 400 llegan como códigos
        HTTP y no como un evento dentro de un 200). La libera el generador del turno al terminar."""
        if sesion.ocupada:
            raise SesionOcupada('Ya hay un mensaje en curso en esta sesión')
        if alternativa and sesion.alternativa_pendiente is None:
            raise SinAlternativa('No hay ninguna alternativa pendiente en esta sesión')
        await sesion.cerrojo.acquire()
        sesion.ultimo_uso = self.reloj()

    def liberar(self, sesion: Sesion) -> None:
        if sesion.ocupada:
            sesion.cerrojo.release()
        sesion.ultimo_uso = self.reloj()

    def responder(self, sesion: Sesion, texto: str) -> AsyncGenerator[Evento, None]:
        """Eventos del turno para `texto`: un `paso` por herramienta, en directo, y al final `respuesta` o
        `error`. La sesión tiene que estar reservada (`reservar`); se libera al terminar."""
        return self._turno(sesion, lambda ejecutar: sesion.agente.responder(texto, ejecutar=ejecutar))

    def responder_alternativa(self, sesion: Sesion) -> AsyncGenerator[Evento, None]:
        """El mismo flujo lanzando la alternativa pendiente tal cual, que se consume al usarla."""
        async def iniciar(ejecutar: Ejecutor) -> Any:
            alternativa, sesion.alternativa_pendiente = sesion.alternativa_pendiente, None
            if alternativa is None:
                raise SinAlternativa('No hay ninguna alternativa pendiente en esta sesión')
            return await sesion.agente.responder_alternativa(alternativa, ejecutar=ejecutar)

        return self._turno(sesion, iniciar)

    async def _turno(self, sesion: Sesion,
                     iniciar: Callable[[Ejecutor], Awaitable[Any]]) -> AsyncGenerator[Evento, None]:
        """El agente corre en una tarea; su `ejecutar` encola un `paso` por herramienta y el generador los emite
        según llegan. `None` en la cola marca el final: entonces se recoge el turno (o su excepción)."""
        cola: asyncio.Queue[Evento | None] = asyncio.Queue()
        emitidos: list[int] = []            # id() de los resultados ya emitidos como paso

        async def ejecutar(nombre: str, argumentos: dict) -> Any:
            inicio = time.monotonic()
            resultado = await sesion.acceso.ejecutar(nombre, argumentos)
            emitidos.append(id(resultado))
            cola.put_nowait(evento_paso(nombre, argumentos, resultado, time.monotonic() - inicio))
            return resultado

        async def correr() -> Any:
            try:
                return await iniciar(ejecutar)
            finally:
                cola.put_nowait(None)

        antes = tokens_de(sesion.contador)
        tarea = asyncio.create_task(correr())
        try:
            while (evento := await cola.get()) is not None:
                yield evento
            try:
                turno = await tarea
            except Exception as e:  # noqa: BLE001 - cualquier fallo del agente se cuenta al usuario, sin traza
                log.warning('Fallo del agente en la sesión %s: %s', sesion.id, type(e).__name__)
                yield Evento('error', {'detail': detalle_error(e)})
                return
            for llamada in turno.llamadas:          # las del filtro previo no pasan por `ejecutar`
                if id(llamada.resultado) not in emitidos:
                    yield evento_paso(llamada.nombre, llamada.argumentos, llamada.resultado, llamada.segundos)
            sesion.alternativa_pendiente = turno.alternativa if isinstance(turno.alternativa, dict) else None
            log.info('Sesión de chat %s: turno de %.1f s, %d pasos del LLM, bloqueo=%s',
                     sesion.id, turno.segundos, turno.pasos_llm, turno.bloqueo)
            yield evento_respuesta(turno, tokens_del_turno(sesion.contador, antes, turno),
                                   sesion.acceso.nombres_zona())
        finally:
            if not tarea.done():                    # el navegador se ha ido a mitad: no seguir gastando LLM
                tarea.cancel()
            self.liberar(sesion)
