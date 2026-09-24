"""BFF del portal · chat (F2): motores, sesiones en memoria, flujo SSE de un turno (pasos en directo y respuesta),
rechazos con alternativa, 409 por sesión ocupada, caducidad y errores del agente. Sin red: la API de acceso es un
`httpx.MockTransport` y el LLM un falso con respuestas preparadas (`APIFalsa`, `LLMFalso` y `_mensaje` copiados de
tests/test_chatbot.py). El agente de cada sesión se construye con una fábrica falsa sustituida con `monkeypatch`."""
import asyncio
import json
import re
from types import SimpleNamespace

import httpx
import ollama
import pytest

from parte4_frontend.bff import app as APP
from parte4_frontend.bff import configuracion as C
from parte4_frontend.bff import seguridad as S
from parte4_frontend.bff.servicios import chat as SC

import agente as AG  # noqa: E402  (parte3_chatbot, que servicios/chat.py ya ha puesto en sys.path)

ENTORNO = {'PUERTO_ACCESO': '8002', 'PUERTO_OLLAMA': '11435', 'ACCESO_CLAVE_EQUIPO': 'clave-equipo',
           'FRONTEND_CLAVE': 'portal', 'FRONTEND_SECRETO': 'secreto'}
CREAR_AGENTE_REAL = SC.crear_agente        # antes de que la fixture `mundo` la sustituya

# --- fakes (copiados de tests/test_chatbot.py) ------------------------------------------------------------------

ZONAS = [
    {'_id': 132, 'nombre': 'JFK Airport', 'barrio': 'Queens'},
    {'_id': 230, 'nombre': 'Times Sq/Theatre District', 'barrio': 'Manhattan'},
    {'_id': 43, 'nombre': 'Central Park', 'barrio': 'Manhattan'},
    {'_id': 41, 'nombre': 'Central Harlem', 'barrio': 'Manhattan'},
    {'_id': 42, 'nombre': 'Central Harlem North', 'barrio': 'Manhattan'},
    {'_id': 5, 'nombre': 'Arden Heights', 'barrio': 'Staten Island'},
    {'_id': 6, 'nombre': 'Arrochar/Fort Wadsworth', 'barrio': 'Staten Island'},
]


def _fila(zona: int, hora: int, n) -> dict:
    return {'zona_origen': zona, 'zona_origen_nombre': f'zona {zona}', 'barrio_origen': 'Staten Island',
            'hora': f'2020-01-01T{hora:02d}:00:00', 'n_viajes': n, 'suprimido': isinstance(n, str)}


class APIFalsa:
    """La API de acceso en memoria: zonas, consultas (por zona) y registro de peticiones individuales."""

    def __init__(self, filas_por_zona: dict | None = None, rechazar: bool = False):
        self.filas_por_zona = filas_por_zona or {}
        self.rechazar = rechazar
        self.consultas: list[dict] = []
        self.individuales: list[str] = []

    def __call__(self, peticion: httpx.Request) -> httpx.Response:
        if peticion.url.path == '/zonas':
            return httpx.Response(200, json=ZONAS)
        cuerpo = json.loads(peticion.content)
        if peticion.url.path == '/consultas/individual':
            self.individuales.append(cuerpo['descripcion'])
            return httpx.Response(403, json={'resultado': 'rechazada', 'motivos': ['individual'], 'alternativa': None})
        self.consultas.append(cuerpo)
        if self.rechazar:
            return httpx.Response(403, json={'resultado': 'rechazada', 'motivos': ['x'],
                                             'alternativa': {**cuerpo, 'nivel': 'dia_barrio'}})
        filas = self.filas_por_zona.get(cuerpo.get('zona_origen'), [])
        ocultas = sum(1 for f in filas if f['suprimido'])
        return httpx.Response(200, json={'resultado': 'enmascarada' if ocultas else 'permitida', 'consulta': cuerpo,
                                         'filas': filas, 'grupos_enmascarados': ocultas, 'truncada': False})


def _mensaje(contenido: str = '', llamadas: list[tuple[str, dict]] = ()):
    tool_calls = [SimpleNamespace(function=SimpleNamespace(name=n, arguments=a)) for n, a in llamadas]
    return SimpleNamespace(message=SimpleNamespace(content=contenido, tool_calls=tool_calls or None))


class LLMFalso:
    """Como el de tests/test_chatbot.py, con dos añadidos para probar el flujo en directo: una excepción en la
    lista se lanza en vez de devolverse, y `pausas[n]` detiene la llamada n-ésima hasta que el test la suelte."""

    def __init__(self, *respuestas):
        self.respuestas = list(respuestas)
        self.llamadas = 0
        self.dentro = asyncio.Event()                  # se activa al entrar en `chat`
        self.pausas: dict[int, asyncio.Event] = {}

    async def chat(self, **_):
        self.llamadas += 1
        self.dentro.set()
        if pausa := self.pausas.get(self.llamadas):
            await pausa.wait()
        respuesta = self.respuestas.pop(0)
        if isinstance(respuesta, BaseException):
            raise respuesta
        return respuesta


CONSULTA_SI = {'nivel': 'hora_zona', 'zona_origen': 6, 'desde': '2020-01-01T00:00:00', 'hasta': '2020-01-02T00:00:00'}
PREGUNTA_INDIVIDUAL = 'Dame el viaje de las 3:12 del 15 de enero desde Times Square'
ALTERNATIVA_TIMES_SQ = {'nivel': 'hora_zona', 'fuente': 'historico', 'desde': '2020-01-15T03:00:00',
                        'hasta': '2020-01-15T04:00:00', 'metricas': ['n_viajes'], 'zona_origen': 230}


def _acceso_falso(acceso: SC.ClienteAcceso, api: APIFalsa) -> None:
    acceso.http = httpx.AsyncClient(base_url='http://acceso', headers={'X-API-Key': 'k'},
                                    transport=httpx.MockTransport(api))


# --- fixtures ---------------------------------------------------------------------------------------------------

class Mundo:
    """La app con un agente falso por sesión: la API de acceso en memoria y un LLM con respuestas preparadas
    (compartidos por todas las sesiones del test)."""

    def __init__(self, cfg: C.Configuracion, dist) -> None:
        self.app = APP.crear_app(cfg, dist=dist)
        self.api = APIFalsa()
        self.llm = LLMFalso()

    def fabrica(self, motor: str, cfg: C.Configuracion, acceso: SC.ClienteAcceso) -> tuple:
        assert motor == 'ollama'
        _acceso_falso(acceso, self.api)
        contador = SC.OllamaContado(self.llm)
        return AG.Agente(acceso, contador, opciones={}), contador

    @property
    def sesiones(self) -> SC.Sesiones:
        return self.app.state.chat_sesiones


@pytest.fixture
def cfg() -> C.Configuracion:
    return C.Configuracion.desde_entorno(ENTORNO, contenedor=False)


@pytest.fixture
def mundo(cfg, tmp_path, monkeypatch) -> Mundo:
    m = Mundo(cfg, tmp_path / 'sin-dist')
    monkeypatch.setattr(SC, 'crear_agente', m.fabrica)
    return m


@pytest.fixture
async def cliente(mundo, cfg):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=mundo.app), base_url='http://portal') as c:
        c.cookies.set('pids_sesion', S.crear_valor_sesion(cfg.frontend_secreto))
        yield c


def parsear_sse(texto: str) -> list[tuple[str, dict]]:
    """[(event, data)] de un cuerpo text/event-stream (sse-starlette separa con \\r\\n; los comentarios fuera)."""
    eventos = []
    for bloque in re.split(r'(?:\r\n|\n){2}', texto.strip()):
        tipo, datos = None, []
        for linea in bloque.splitlines():
            if linea.startswith('event:'):
                tipo = linea[len('event:'):].strip()
            elif linea.startswith('data:'):
                datos.append(linea[len('data:'):].strip())
        if tipo is not None:
            eventos.append((tipo, json.loads('\n'.join(datos))))
    return eventos


async def _post_sse(cliente: httpx.AsyncClient, url: str, cuerpo: dict | None = None) -> tuple[int, list | dict]:
    """POST leído como flujo: (código, eventos SSE) o, si no es un event-stream, (código, JSON del error)."""
    async with cliente.stream('POST', url, **({'json': cuerpo} if cuerpo is not None else {})) as r:
        texto = (await r.aread()).decode('utf-8')
    if r.headers.get('content-type', '').startswith('text/event-stream'):
        assert r.status_code == 200
        return r.status_code, parsear_sse(texto)
    return r.status_code, json.loads(texto)


async def _sesion(cliente: httpx.AsyncClient, motor: str = 'ollama') -> str:
    r = await cliente.post('/api/chat/sesiones', json={'motor': motor})
    assert r.status_code == 201 and r.json()['motor'] == motor and r.json()['id']
    return r.json()['id']


# --- motores y sesiones -----------------------------------------------------------------------------------------

async def test_lista_de_motores(cliente, monkeypatch):
    r = await cliente.get('/api/chat/motores')
    assert r.status_code == 200
    motores = {m['id']: m for m in r.json()}
    assert list(motores) == ['ollama', 'rag']
    assert motores['ollama'] == {'id': 'ollama', 'nombre': 'Ollama', 'modelo': 'llama3.1:8b', 'disponible': True,
                                 'descripcion': 'LLM local; ninguna pregunta sale del equipo'}
    assert motores['rag']['descripcion'] == 'Mistral + Qdrant; barreras heredadas'
    assert motores['rag']['disponible'] is (SC.fabrica_rag() is not None)

    monkeypatch.setattr(SC, 'fabrica_rag', lambda: None)             # sin parte3_chatbot_rag/fabrica.py (esta rama)
    rag = next(m for m in (await cliente.get('/api/chat/motores')).json() if m['id'] == 'rag')
    assert rag == {'id': 'rag', 'nombre': 'RAG', 'modelo': '', 'disponible': False,
                   'descripcion': 'Mistral + Qdrant; barreras heredadas'}
    r = await cliente.post('/api/chat/sesiones', json={'motor': 'rag'})
    assert r.status_code == 409 and r.json() == {'detail': 'El motor rag no está disponible en esta instalación'}


def test_la_fabrica_rag_solo_existe_con_el_modulo_y_langchain(tmp_path, monkeypatch):
    monkeypatch.setattr(SC, 'RUTA_RAG', tmp_path / 'no-existe')        # sin parte3_chatbot_rag (esta rama)
    SC.fabrica_rag.cache_clear()
    assert SC.fabrica_rag() is None

    (tmp_path / 'fabrica.py').write_text('def agente_rag(acceso):\n    return acceso, None\n'
                                         'def modelo_rag():\n    return "modelo-de-prueba"\n', encoding='utf-8')
    monkeypatch.setattr(SC, 'RUTA_RAG', tmp_path)
    monkeypatch.setattr(SC.importlib.util, 'find_spec', lambda nombre: None)   # el módulo está, LangChain no
    SC.fabrica_rag.cache_clear()
    assert SC.fabrica_rag() is None

    monkeypatch.setattr(SC.importlib.util, 'find_spec', lambda nombre: object())
    monkeypatch.syspath_prepend(str(tmp_path))
    monkeypatch.delitem(SC.sys.modules, 'fabrica', raising=False)
    SC.fabrica_rag.cache_clear()
    try:
        assert SC.fabrica_rag().modelo_rag() == 'modelo-de-prueba'
    finally:
        SC.sys.modules.pop('fabrica', None)
        SC.fabrica_rag.cache_clear()


async def test_crear_y_cerrar_sesion(cliente, mundo):
    id_sesion = await _sesion(cliente)
    sesion = mundo.sesiones.sesiones[id_sesion]
    assert sesion.motor == 'ollama' and isinstance(sesion.agente, AG.Agente) and not sesion.ocupada
    assert isinstance(sesion.acceso, SC.ClienteAcceso) and sesion.alternativa_pendiente is None

    r = await cliente.delete(f'/api/chat/sesiones/{id_sesion}')
    assert r.status_code == 204 and id_sesion not in mundo.sesiones.sesiones
    assert sesion.acceso.http.is_closed                               # se cierra el cliente HTTP de la sesión
    r = await cliente.delete(f'/api/chat/sesiones/{id_sesion}')
    assert r.status_code == 404 and r.json() == {'detail': 'La sesión de chat no existe o ha caducado'}

    assert (await cliente.post('/api/chat/sesiones', json={'motor': 'gpt'})).status_code == 422
    assert (await cliente.post('/api/chat/sesiones', json={})).status_code == 422
    codigo, cuerpo = await _post_sse(cliente, '/api/chat/sesiones/no-existe/mensajes', {'texto': 'hola'})
    assert codigo == 404 and cuerpo == {'detail': 'La sesión de chat no existe o ha caducado'}


async def test_sin_cookie_todo_es_401(mundo):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=mundo.app), base_url='http://portal') as c:
        for r in (await c.get('/api/chat/motores'), await c.post('/api/chat/sesiones', json={'motor': 'ollama'}),
                  await c.post('/api/chat/sesiones/x/mensajes', json={'texto': 'hola'}),
                  await c.post('/api/chat/sesiones/x/alternativa'), await c.delete('/api/chat/sesiones/x')):
            assert r.status_code == 401 and r.json() == {'detail': 'Sesión no iniciada'}


async def test_el_texto_es_obligatorio_y_acotado(cliente):
    id_sesion = await _sesion(cliente)
    url = f'/api/chat/sesiones/{id_sesion}/mensajes'
    for cuerpo in ({}, {'texto': ''}, {'texto': '   '}, {'texto': 'x' * 2001}, {'texto': 5}):
        codigo, respuesta = await _post_sse(cliente, url, cuerpo)
        assert codigo == 422, cuerpo
    assert (await cliente.post(url, content=b'no es json', headers={'Content-Type': 'application/json'})).status_code == 422


# --- el flujo SSE -----------------------------------------------------------------------------------------------

async def test_un_mensaje_con_tool_call_emite_el_paso_y_luego_la_respuesta(cliente, mundo):
    mundo.api.filas_por_zona = {6: [_fila(6, 8, 12), _fila(6, 9, 15)]}
    primera, segunda = _mensaje(llamadas=[('consultar_viajes', CONSULTA_SI)]), _mensaje('Salieron 27 viajes')
    primera.prompt_eval_count, primera.eval_count = 300, 20
    segunda.prompt_eval_count, segunda.eval_count = 400, 10
    mundo.llm.respuestas += [primera, segunda]
    id_sesion = await _sesion(cliente)

    async with cliente.stream('POST', f'/api/chat/sesiones/{id_sesion}/mensajes',
                              json={'texto': '¿Cuántos viajes salieron de Arrochar el 1 de enero?'}) as r:
        assert r.status_code == 200 and r.headers['content-type'].startswith('text/event-stream')
        assert r.headers['cache-control'] in ('no-cache', 'no-store')    # sin caché intermedia para el flujo
        eventos = parsear_sse((await r.aread()).decode('utf-8'))

    assert [tipo for tipo, _ in eventos] == ['paso', 'respuesta']
    paso = eventos[0][1]
    assert paso['nombre'] == 'consultar_viajes' and paso['argumentos'] == CONSULTA_SI
    assert paso['resultado'] == 'permitida (2 filas)' and isinstance(paso['segundos'], float) and paso['segundos'] >= 0
    respuesta = eventos[1][1]
    assert isinstance(respuesta.pop('segundos'), float)
    assert respuesta == {'respuesta': 'Salieron 27 viajes\n\n_Datos históricos, solo agregados._', 'bloqueo': None,
                         'pasos_llm': 2, 'tokens': 730, 'alternativa': None, 'alternativa_descripcion': None,
                         'fuentes': []}
    assert mundo.api.consultas == [CONSULTA_SI] and mundo.llm.llamadas == 2
    assert not mundo.sesiones.sesiones[id_sesion].ocupada and mundo.sesiones.sesiones[id_sesion].alternativa_pendiente is None


async def test_los_tokens_son_los_del_turno_no_los_de_la_sesion(cliente, mundo):
    respuestas = [_mensaje('Hola, dime qué quieres saber'), _mensaje('Sin cifras, claro')]
    for r, tokens in zip(respuestas, (100, 30)):
        r.prompt_eval_count, r.eval_count = tokens, 0
    mundo.llm.respuestas += respuestas
    id_sesion = await _sesion(cliente)
    url = f'/api/chat/sesiones/{id_sesion}/mensajes'
    _, eventos = await _post_sse(cliente, url, {'texto': 'Hola'})
    assert eventos[-1][1]['tokens'] == 100 and eventos[-1][1]['respuesta'] == 'Hola, dime qué quieres saber'
    _, eventos = await _post_sse(cliente, url, {'texto': '¿Qué barrio tuvo más viajes el 3 de marzo?'})
    assert eventos[-1][1]['tokens'] == 30 and mundo.sesiones.sesiones[id_sesion].contador.tokens == 130


async def test_los_pasos_se_emiten_en_directo_antes_de_que_termine_el_turno(cfg, mundo):
    mundo.api.filas_por_zona = {6: [_fila(6, 8, 12)]}
    mundo.llm.respuestas += [_mensaje(llamadas=[('consultar_viajes', CONSULTA_SI)]), _mensaje('Salieron 12 viajes')]
    seguir = asyncio.Event()
    mundo.llm.pausas[2] = seguir                  # la segunda llamada al LLM (la respuesta final) queda a la espera
    sesiones = SC.Sesiones(cfg)                   # la fábrica sustituida se resuelve al llamar
    sesion = await sesiones.crear('ollama')
    await sesiones.reservar(sesion)

    eventos = sesiones.responder(sesion, '¿Cuántos viajes salieron de Arrochar?')
    primero = await asyncio.wait_for(anext(eventos), 5)
    assert primero.tipo == 'paso' and primero.datos['nombre'] == 'consultar_viajes'
    assert sesion.ocupada and not seguir.is_set()             # el turno sigue en marcha: el paso ha llegado antes
    seguir.set()
    resto = [evento async for evento in eventos]
    assert [evento.tipo for evento in resto] == ['respuesta']
    assert resto[0].datos['respuesta'].startswith('Salieron 12 viajes') and not sesion.ocupada
    await sesiones.cerrar(sesion.id)


async def test_si_el_navegador_se_va_a_mitad_se_cancela_el_agente_y_se_libera_la_sesion(cfg, mundo):
    mundo.api.filas_por_zona = {6: [_fila(6, 8, 12)]}
    mundo.llm.respuestas += [_mensaje(llamadas=[('consultar_viajes', CONSULTA_SI)]), _mensaje('Salieron 12 viajes')]
    mundo.llm.pausas[2] = asyncio.Event()         # el LLM se queda colgado en la segunda llamada (nadie lo suelta)
    sesiones = SC.Sesiones(cfg)
    sesion = await sesiones.crear('ollama')
    await sesiones.reservar(sesion)

    eventos = sesiones.responder(sesion, '¿Cuántos viajes salieron de Arrochar?')
    assert (await asyncio.wait_for(anext(eventos), 5)).tipo == 'paso'
    await eventos.aclose()                        # sse-starlette cierra el generador cuando el cliente desconecta
    await asyncio.sleep(0)                        # la cancelación llega a la tarea del agente
    assert not sesion.ocupada
    assert all(t.done() for t in asyncio.all_tasks() if t is not asyncio.current_task())
    mundo.llm.respuestas[:] = [_mensaje('Sigo aquí')]       # (la respuesta del turno cancelado quedó sin consumir)
    await sesiones.reservar(sesion)                          # y la sesión sigue sirviendo
    assert [e.datos['respuesta'] async for e in sesiones.responder(sesion, 'hola')] == ['Sigo aquí']
    await sesiones.cerrar(sesion.id)


async def test_un_rechazo_del_filtro_previo_trae_la_alternativa_y_su_descripcion(cliente, mundo):
    id_sesion = await _sesion(cliente)
    codigo, eventos = await _post_sse(cliente, f'/api/chat/sesiones/{id_sesion}/mensajes',
                                      {'texto': PREGUNTA_INDIVIDUAL})
    assert codigo == 200 and [tipo for tipo, _ in eventos] == ['paso', 'respuesta']
    paso, respuesta = eventos[0][1], eventos[1][1]
    # la petición rechazada queda registrada en la API (auditoría) y se muestra como paso aunque no pase por el LLM
    assert paso['nombre'] == 'solicitud_individual' and paso['resultado'] == 'rechazada'
    assert paso['argumentos'] == {'descripcion': PREGUNTA_INDIVIDUAL}
    assert mundo.api.individuales == [PREGUNTA_INDIVIDUAL] and mundo.llm.llamadas == 0
    assert respuesta['bloqueo'] == 'filtro_previo' and respuesta['pasos_llm'] == 0 and respuesta['tokens'] == 0
    assert respuesta['respuesta'].startswith('🔒 **Consulta rechazada por privacidad**')
    assert respuesta['alternativa'] == ALTERNATIVA_TIMES_SQ
    assert respuesta['alternativa_descripcion'] == ('viajes por hora desde Times Sq/Theatre District (zona 230) '
                                                    'el 15/01/2020 de 03:00 a 04:00 (histórico)')
    assert respuesta['fuentes'] == []
    assert mundo.sesiones.sesiones[id_sesion].alternativa_pendiente == ALTERNATIVA_TIMES_SQ


async def test_la_alternativa_se_ejecuta_tal_cual_y_se_consume(cliente, mundo):
    id_sesion = await _sesion(cliente)
    url = f'/api/chat/sesiones/{id_sesion}/alternativa'
    codigo, cuerpo = await _post_sse(cliente, url)
    assert codigo == 400 and cuerpo == {'detail': 'No hay ninguna alternativa pendiente en esta sesión'}

    await _post_sse(cliente, f'/api/chat/sesiones/{id_sesion}/mensajes', {'texto': PREGUNTA_INDIVIDUAL})
    mundo.api.filas_por_zona = {230: [_fila(230, 3, 54)]}
    mundo.llm.respuestas.append(_mensaje('Salieron 54 viajes'))
    codigo, eventos = await _post_sse(cliente, url)
    assert codigo == 200 and [tipo for tipo, _ in eventos] == ['paso', 'respuesta']
    assert eventos[0][1]['nombre'] == 'consultar_viajes' and eventos[0][1]['argumentos'] == ALTERNATIVA_TIMES_SQ
    assert eventos[0][1]['resultado'] == 'permitida (1 fila)'
    assert mundo.api.consultas == [ALTERNATIVA_TIMES_SQ]                  # sin que el LLM la reescriba
    respuesta = eventos[1][1]
    assert respuesta['respuesta'].startswith('Salieron 54 viajes') and respuesta['bloqueo'] is None
    assert respuesta['alternativa'] is None and respuesta['alternativa_descripcion'] is None
    assert mundo.sesiones.sesiones[id_sesion].alternativa_pendiente is None

    codigo, cuerpo = await _post_sse(cliente, url)                         # consumida: ya no hay ninguna
    assert codigo == 400 and cuerpo == {'detail': 'No hay ninguna alternativa pendiente en esta sesión'}


async def test_dos_mensajes_a_la_vez_sobre_la_misma_sesion_dan_409(cliente, mundo):
    mundo.llm.respuestas += [_mensaje('Manhattan, sin cifras'), _mensaje('Y ahora otra cosa')]
    seguir = asyncio.Event()
    mundo.llm.pausas[1] = seguir
    id_sesion = await _sesion(cliente)
    url = f'/api/chat/sesiones/{id_sesion}/mensajes'

    primero = asyncio.create_task(_post_sse(cliente, url, {'texto': '¿Qué barrio tuvo más viajes el 3 de marzo?'}))
    await asyncio.wait_for(mundo.llm.dentro.wait(), 5)                 # el primer turno está dentro del LLM
    assert mundo.sesiones.sesiones[id_sesion].ocupada
    codigo, cuerpo = await _post_sse(cliente, url, {'texto': 'Propina media en Manhattan en febrero'})
    assert codigo == 409 and cuerpo == {'detail': 'Ya hay un mensaje en curso en esta sesión'}
    codigo, cuerpo = await _post_sse(cliente, f'/api/chat/sesiones/{id_sesion}/alternativa')
    assert codigo == 409                                                 # ocupada manda sobre «sin alternativa»
    otra = await _sesion(cliente)                                        # otra sesión no se ve afectada
    assert not mundo.sesiones.sesiones[otra].ocupada

    seguir.set()
    codigo, eventos = await primero
    assert codigo == 200 and eventos == [('respuesta', eventos[0][1])]
    assert eventos[0][1]['respuesta'] == 'Manhattan, sin cifras'
    assert not mundo.sesiones.sesiones[id_sesion].ocupada               # el cerrojo se libera al terminar
    _, eventos = await _post_sse(cliente, url, {'texto': 'Otra pregunta sin cifras'})
    assert eventos[-1][1]['respuesta'] == 'Y ahora otra cosa'


async def test_las_sesiones_caducan_a_las_dos_horas_sin_uso(cliente, mundo):
    id_sesion = await _sesion(cliente)
    sesion = mundo.sesiones.sesiones[id_sesion]
    sesion.ultimo_uso -= SC.CADUCIDAD.total_seconds() - 60                # 1 h 59: sigue viva
    codigo, cuerpo = await _post_sse(cliente, f'/api/chat/sesiones/{id_sesion}/alternativa')
    assert codigo == 400                                                  # existe (pero no tiene alternativa)
    sesion.ultimo_uso -= 120                                              # más de 2 h: caducada
    codigo, cuerpo = await _post_sse(cliente, f'/api/chat/sesiones/{id_sesion}/mensajes', {'texto': 'hola'})
    assert codigo == 404 and cuerpo == {'detail': 'La sesión de chat no existe o ha caducado'}
    assert id_sesion not in mundo.sesiones.sesiones and sesion.acceso.http.is_closed

    vieja = await _sesion(cliente)                                        # crear una sesión también purga
    mundo.sesiones.sesiones[vieja].ultimo_uso -= SC.CADUCIDAD.total_seconds() + 1
    nueva = await _sesion(cliente)
    assert set(mundo.sesiones.sesiones) == {nueva}

    ocupada = mundo.sesiones.sesiones[nueva]                              # una sesión con un turno en curso no caduca
    await ocupada.cerrojo.acquire()
    ocupada.ultimo_uso -= SC.CADUCIDAD.total_seconds() + 1
    await mundo.sesiones.purgar()
    assert nueva in mundo.sesiones.sesiones
    ocupada.cerrojo.release()


async def test_el_uso_refresca_la_caducidad(cfg, mundo):
    reloj = SimpleNamespace(ahora=1000.0)
    sesiones = SC.Sesiones(cfg, reloj=lambda: reloj.ahora)
    sesion = await sesiones.crear('ollama')
    mundo.llm.respuestas.append(_mensaje('Sin cifras'))
    reloj.ahora += 7000                                                   # casi dos horas después se usa
    await sesiones.reservar(await sesiones.obtener(sesion.id))
    assert [e.tipo async for e in sesiones.responder(sesion, 'hola')] == ['respuesta']
    reloj.ahora += 7000                                                   # y desde ese uso aún no han pasado 2 h
    assert await sesiones.obtener(sesion.id) is sesion
    reloj.ahora += 300
    with pytest.raises(SC.SesionNoEncontrada):
        await sesiones.obtener(sesion.id)
    with pytest.raises(SC.MotorDesconocido):
        await sesiones.crear('gpt')


async def test_un_error_del_agente_produce_el_evento_error_sin_traza_y_libera_la_sesion(cliente, mundo):
    mundo.llm.respuestas += [RuntimeError('Ollama no responde\n  File "x.py", line 1'), _mensaje('Ahora sí')]
    id_sesion = await _sesion(cliente)
    url = f'/api/chat/sesiones/{id_sesion}/mensajes'
    codigo, eventos = await _post_sse(cliente, url, {'texto': '¿Qué barrio tuvo más viajes el 3 de marzo?'})
    assert codigo == 200
    assert eventos == [('error', {'detail': 'El asistente no ha podido responder (RuntimeError: Ollama no responde)'})]
    assert 'File' not in eventos[0][1]['detail'] and 'clave-equipo' not in eventos[0][1]['detail']
    assert not mundo.sesiones.sesiones[id_sesion].ocupada
    codigo, eventos = await _post_sse(cliente, url, {'texto': '¿Y el 4 de marzo?'})
    assert [tipo for tipo, _ in eventos] == ['respuesta'] and eventos[0][1]['respuesta'] == 'Ahora sí'


# --- el motor rag, con una fábrica falsa ------------------------------------------------------------------------

class AgenteRAGFalso:
    """Lo mínimo que el BFF usa de `AgenteRAG`: `responder` con `ejecutar` y un turno con `fuentes` y `tokens`."""

    def __init__(self, acceso: SC.ClienteAcceso) -> None:
        self.acceso = acceso

    async def responder(self, texto: str, ejecutar=None) -> AG.Turno:
        zonas = await ejecutar('buscar_zona', {'texto': 'JFK'})
        turno = AG.Turno(pregunta=texto, respuesta='JFK es la zona 132 (Queens).', pasos_llm=1, segundos=0.25)
        turno.llamadas.append(AG.Llamada('buscar_zona', {'texto': 'JFK'}, zonas, 0.1))
        turno.fuentes = [{'titulo': 'Catálogo de zonas', 'fuente': 'docs/zonas.md', 'tipo': 'doc'}]
        turno.tokens = 321
        return turno


async def test_el_motor_rag_funciona_si_su_fabrica_existe(cliente, mundo, monkeypatch):
    def agente_rag(acceso):
        _acceso_falso(acceso, mundo.api)
        return AgenteRAGFalso(acceso), None            # sin contador: los tokens salen del propio turno

    monkeypatch.setattr(SC, 'fabrica_rag', lambda: SimpleNamespace(agente_rag=agente_rag,
                                                                    modelo_rag=lambda: 'deepseek-v4-flash'))
    monkeypatch.setattr(SC, 'crear_agente', CREAR_AGENTE_REAL)
    rag = next(m for m in (await cliente.get('/api/chat/motores')).json() if m['id'] == 'rag')
    assert rag['disponible'] is True and rag['modelo'] == 'deepseek-v4-flash'

    id_sesion = await _sesion(cliente, 'rag')
    codigo, eventos = await _post_sse(cliente, f'/api/chat/sesiones/{id_sesion}/mensajes', {'texto': '¿Qué es JFK?'})
    assert codigo == 200 and [tipo for tipo, _ in eventos] == ['paso', 'respuesta']
    assert eventos[0][1]['nombre'] == 'buscar_zona' and eventos[0][1]['resultado'] == '1 zona'
    respuesta = eventos[1][1]
    assert respuesta['respuesta'] == 'JFK es la zona 132 (Queens).' and respuesta['tokens'] == 321
    assert respuesta['fuentes'] == [{'titulo': 'Catálogo de zonas', 'fuente': 'docs/zonas.md', 'tipo': 'doc'}]


async def test_si_la_fabrica_rag_falla_al_arrancar_no_hay_500(cliente, mundo, monkeypatch):
    def agente_rag(acceso):
        raise ConnectionError('Qdrant no responde')

    monkeypatch.setattr(SC, 'fabrica_rag', lambda: SimpleNamespace(agente_rag=agente_rag, modelo_rag=lambda: 'm'))
    monkeypatch.setattr(SC, 'crear_agente', CREAR_AGENTE_REAL)
    r = await cliente.post('/api/chat/sesiones', json={'motor': 'rag'})
    assert r.status_code == 503 and r.json() == {'detail': 'No se ha podido iniciar el motor rag (ConnectionError)'}
    assert mundo.sesiones.sesiones == {}


# --- piezas sueltas ---------------------------------------------------------------------------------------------

async def test_crear_agente_ollama_usa_la_configuracion_del_bff(cfg):
    acceso = SC.ClienteAcceso(url='http://acceso', clave='k')
    agente, contador = CREAR_AGENTE_REAL('ollama', cfg, acceso)
    assert isinstance(agente, AG.Agente) and agente.acceso is acceso and agente.modelo == 'llama3.1:8b'
    assert isinstance(contador, SC.OllamaContado) and agente.llm is contador
    assert isinstance(contador.cliente, ollama.AsyncClient)
    with pytest.raises(SC.MotorDesconocido):
        CREAR_AGENTE_REAL('gpt', cfg, acceso)
    await acceso.cerrar()


async def test_el_contador_suma_los_tokens_de_cada_chat():
    llm = LLMFalso(SimpleNamespace(prompt_eval_count=100, eval_count=20),
                   SimpleNamespace(prompt_eval_count=None, eval_count=5), SimpleNamespace())
    contador = SC.OllamaContado(llm)
    assert await contador.chat(model='x', messages=[]) is not None and contador.tokens == 120
    await contador.chat()
    await contador.chat()
    assert contador.tokens == 125 and contador.llamadas == 3


@pytest.mark.parametrize('resultado, esperado', [
    ({'resultado': 'permitida', 'filas': [1, 2], 'grupos_enmascarados': 0}, 'permitida (2 filas)'),
    ({'resultado': 'enmascarada', 'filas': [1, 2, 3], 'grupos_enmascarados': 1}, 'enmascarada (3 filas, 1 enmascarada)'),
    ({'resultado': 'enmascarada', 'filas': [1, 2, 3], 'grupos_enmascarados': 2}, 'enmascarada (3 filas, 2 enmascaradas)'),
    ({'resultado': 'rechazada', 'motivos': ['x'], 'alternativa': None}, 'rechazada'),
    ({'resultado': 'sin_datos', 'filas': []}, 'sin_datos'),
    ({'error': 'zona ambigua: Harlem', 'zonas_posibles': []}, 'error: zona ambigua: Harlem'),
    ([{'_id': 132}], '1 zona'), ([], '0 zonas'), (ZONAS, '7 zonas'),
    ('x' * 500, 'x' * 120), (None, 'None'),
])
def test_el_resumen_del_paso_es_corto_y_sin_filas(resultado, esperado):
    assert SC.resumir_resultado(resultado) == esperado


def test_el_detalle_del_error_no_lleva_traza():
    assert SC.detalle_error(RuntimeError('boom\n  traza')) == 'El asistente no ha podido responder (RuntimeError: boom)'
    assert SC.detalle_error(ValueError()) == 'El asistente no ha podido responder (ValueError)'
    assert SC.detalle_error(SC.SinAlternativa('nada pendiente')) == 'nada pendiente'
    assert SC.detalle_error(httpx.ConnectError('x' * 300)).endswith('x)') and len(SC.detalle_error(httpx.ConnectError('x' * 300))) < 260


def test_evento_respuesta_describe_la_alternativa_y_tolera_turnos_sin_fuentes():
    turno = AG.Turno(pregunta='p', respuesta='r', bloqueo='sin_datos', pasos_llm=2, segundos=1.23456,
                     alternativa={'nivel': 'dia_barrio', 'barrio_origen': 'Queens', 'desde': '2020-01-10T00:00:00',
                                  'hasta': '2020-01-11T00:00:00'})
    evento = SC.evento_respuesta(turno, tokens=None, nombres_zona={})
    assert evento.tipo == 'respuesta'
    assert evento.datos == {'respuesta': 'r', 'bloqueo': 'sin_datos', 'pasos_llm': 2, 'segundos': 1.235, 'tokens': None,
                            'alternativa': turno.alternativa,
                            'alternativa_descripcion': 'viajes por día desde Queens el 10/01/2020 (histórico)',
                            'fuentes': []}
    assert SC.tokens_del_turno(SimpleNamespace(tokens=50), 20, turno) == 30
    assert SC.tokens_del_turno(None, None, turno) is None
    turno.tokens = 7
    assert SC.tokens_del_turno(None, None, turno) == 7
