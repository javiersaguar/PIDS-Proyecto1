"""El agente RAG con LLM, recuperador y guardia falsos (sin red ni Qdrant): filtro previo, contexto,
herramientas de LangChain, guardia de salida y las barreras sobre las cifras."""
import json
import sys
from pathlib import Path
from typing import Any

import httpx
import pytest
from langchain_core.documents import Document
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.utils.function_calling import convert_to_openai_tool
from langchain_openai import ChatOpenAI
from pydantic import Field

RAIZ = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(RAIZ / 'parte3_chatbot_rag'), str(RAIZ / 'parte3_chatbot')]

import agente_rag as R  # noqa: E402
import herramientas as H  # noqa: E402
import herramientas_lc as HL  # noqa: E402
import prompts  # noqa: E402
import prompts_rag as PR  # noqa: E402

# --- dobles: la API de acceso (copiada de tests/test_chatbot.py), el LLM, el recuperador y la guardia ----------

ZONAS = [
    {'_id': 132, 'nombre': 'JFK Airport', 'barrio': 'Queens'},
    {'_id': 230, 'nombre': 'Times Sq/Theatre District', 'barrio': 'Manhattan'},
    {'_id': 43, 'nombre': 'Central Park', 'barrio': 'Manhattan'},
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


def _cliente(api) -> H.ClienteAcceso:
    cliente = H.ClienteAcceso(url='http://acceso', clave='k')
    cliente.http = httpx.AsyncClient(base_url='http://acceso', headers={'X-API-Key': 'k'},
                                     transport=httpx.MockTransport(api))
    return cliente


class LLMFalso(GenericFakeChatModel):
    """Devuelve las respuestas programadas y guarda lo que recibe (para mirar el sistema y el historial)."""
    recibidos: list = Field(default_factory=list)
    herramientas: Any = None
    fallo: Any = None

    def bind_tools(self, tools, **kwargs):
        self.herramientas = list(tools)
        return self

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        self.recibidos.append(list(messages))
        if self.fallo is not None:
            raise self.fallo
        return super()._generate(messages, stop=stop, run_manager=run_manager, **kwargs)


def _llm(*respuestas, fallo=None) -> LLMFalso:
    return LLMFalso(messages=iter(respuestas), fallo=fallo)


def _texto(contenido: str, tokens: int | None = None) -> AIMessage:
    uso = {'input_tokens': tokens - 5, 'output_tokens': 5, 'total_tokens': tokens} if tokens else None
    return AIMessage(content=contenido, usage_metadata=uso)


def _llamada(nombre: str, argumentos: dict, id_llamada: str = 'c1') -> AIMessage:
    return AIMessage(content='',
                     tool_calls=[{'name': nombre, 'args': argumentos, 'id': id_llamada, 'type': 'tool_call'}])


class RecuperadorFalso:
    def __init__(self, *documentos: Document, fallar: bool = False):
        self.documentos = list(documentos)
        self.fallar = fallar
        self.preguntas: list[tuple[str, int]] = []

    async def recuperar(self, pregunta: str, k: int = 6) -> list[Document]:
        self.preguntas.append((pregunta, k))
        if self.fallar:
            raise ConnectionError('Qdrant no responde')
        return self.documentos[:k]


class GuardiaFalsa:
    def __init__(self, bloquear: bool = False, anadir: SystemMessage | None = None):
        self.bloquear, self.anadir = bloquear, anadir
        self.revisados: list[list] = []
        self.registradas: list[AIMessage] = []

    def revisar(self, mensajes):
        self.revisados.append(list(mensajes))
        if self.bloquear:
            raise R.FugaSalida('el mensaje contiene una clave de API')
        return [*mensajes, self.anadir] if self.anadir else mensajes

    def registrar(self, respuesta):
        self.registradas.append(respuesta)


DOC_E3 = Document(page_content='Los grupos con menos de 10 viajes se publican marcados como suprimidos y sin cifras.',
                  metadata={'tipo': 'doc', 'fuente': 'docs/escenario_E3.md', 'titulo': 'Escenario E3 · Reglas propias'})
FICHA_MANHATTAN = Document(
    page_content='El martes 3 de marzo de 2020 salieron de Manhattan 203 866 viajes, con un importe medio de 18,64 $.',
    metadata={'tipo': 'ficha', 'fuente': 'api:dia_barrio', 'titulo': 'Manhattan · 03/03/2020 · día y barrio',
              'nivel': 'dia_barrio', 'dia': '2020-03-03', 'barrio_origen': 'Manhattan', 'suprimido': False,
              'n_viajes': 203866, 'importe_medio': 18.64})
FICHA_OCULTA = Document(
    page_content='El 3 de marzo de 2020 el grupo de Staten Island está enmascarado por privacidad.',
    metadata={'tipo': 'ficha', 'fuente': 'api:dia_barrio', 'titulo': 'Staten Island · 03/03/2020 · día y barrio',
              'nivel': 'dia_barrio', 'dia': '2020-03-03', 'barrio_origen': 'Staten Island', 'suprimido': True})
CONSULTA_SI = {'nivel': 'hora_zona', 'zona_origen': 6, 'desde': '2020-01-01T00:00:00', 'hasta': '2020-01-02T00:00:00'}
PIE = '\n\n_Datos históricos, solo agregados._'


def _agente(api=None, llm=None, recuperador=None, guardia=None, **kw) -> R.AgenteRAG:
    return R.AgenteRAG(_cliente(api or APIFalsa()), llm or _llm(), recuperador or RecuperadorFalso(), guardia, **kw)


# --- herramientas de LangChain ------------------------------------------------------------------------------

def test_las_herramientas_langchain_tienen_los_mismos_nombres_y_esquemas_que_el_chatbot():
    herramientas = HL.herramientas_langchain(_cliente(APIFalsa()))
    assert [h.name for h in herramientas] == HL.NOMBRES == [e['function']['name'] for e in H.ESQUEMAS]
    for herramienta, esquema in zip(herramientas, H.ESQUEMAS):
        assert convert_to_openai_tool(herramienta)['function'] == esquema['function']


async def test_las_herramientas_delegan_en_ejecutar_y_admiten_la_llamada_del_modelo():
    recibido = []

    async def ejecutar(nombre, argumentos):
        recibido.append((nombre, argumentos))
        return {'resultado': 'permitida', 'filas': []}

    consultar = HL.herramientas_langchain(ejecutar=ejecutar)[0]
    mensaje = await consultar.ainvoke({'name': 'consultar_viajes', 'args': CONSULTA_SI, 'id': 'c1',
                                       'type': 'tool_call'})
    assert recibido == [('consultar_viajes', CONSULTA_SI)]
    assert isinstance(mensaje, ToolMessage) and mensaje.tool_call_id == 'c1'
    with pytest.raises(ValueError):
        HL.herramientas_langchain()


def test_el_agente_vincula_las_cuatro_herramientas_al_modelo():
    llm = _llm()
    _agente(llm=llm)
    assert [h.name for h in llm.herramientas] == HL.NOMBRES


# --- prompt y contexto ---------------------------------------------------------------------------------------

def test_el_prompt_rag_conserva_las_instrucciones_de_privacidad_del_chatbot():
    assert PR.SISTEMA_RAG.startswith(prompts.SISTEMA) and 'Contexto recuperado' in PR.SISTEMA_RAG
    assert PR.BIENVENIDA_RAG.startswith('**Asistente de datos de taxis (NYC, 2020) · versión RAG**')


def test_formatear_contexto_numera_los_fragmentos_y_recorta_los_largos(monkeypatch):
    monkeypatch.setattr(PR, 'MAX_CARACTERES_DOCUMENTO', 30)
    largo = Document(page_content='x' * 100, metadata={'titulo': 'Largo'})
    texto = PR.formatear_contexto([DOC_E3, largo])
    assert texto.startswith(PR.ENCABEZADO_CONTEXTO)
    assert '[1] Escenario E3 · Reglas propias (doc · docs/escenario_E3.md)\nLos grupos' in texto
    assert '[2] Largo\n' + 'x' * 30 + ' […]' in texto
    assert PR.SIN_CONTEXTO in PR.formatear_contexto([])


def test_fuentes_de_no_repite_y_rellena_lo_que_falta():
    sin_titulo = Document(page_content='', metadata={'fuente': 'docs/datos.md'})
    assert R.fuentes_de([DOC_E3, DOC_E3, sin_titulo]) == [
        {'titulo': 'Escenario E3 · Reglas propias', 'fuente': 'docs/escenario_E3.md', 'tipo': 'doc'},
        {'titulo': 'docs/datos.md', 'fuente': 'docs/datos.md', 'tipo': 'doc'},
    ]


def test_una_ficha_se_convierte_en_un_resultado_de_la_api():
    resultado = R.ficha_como_resultado(FICHA_MANHATTAN)
    assert resultado['consulta'] == {'nivel': 'dia_barrio', 'fuente': 'historico', 'desde': '2020-03-03T00:00:00',
                                     'hasta': '2020-03-04T00:00:00', 'metricas': ['n_viajes', 'importe_medio'],
                                     'barrio_origen': 'Manhattan'}
    assert resultado['filas'] == [{'dia': '2020-03-03', 'barrio_origen': 'Manhattan', 'suprimido': False,
                                   'n_viajes': 203866, 'importe_medio': 18.64}]
    assert resultado['resultado'] == 'permitida' and resultado['texto'].startswith('El martes 3 de marzo')
    oculta = R.ficha_como_resultado(FICHA_OCULTA)
    assert oculta['filas'][0]['n_viajes'] == '<10' and oculta['grupos_enmascarados'] == 1
    assert R.ficha_como_resultado(DOC_E3) is None
    mala = Document(page_content='', metadata={'tipo': 'ficha', 'nivel': 'dia_barrio', 'dia': 'ayer'})
    assert R.ficha_como_resultado(mala) is None


def test_cita_fichas_distingue_una_cifra_publicada_del_umbral_de_privacidad():
    fichas = [R.ficha_como_resultado(FICHA_MANHATTAN), R.ficha_como_resultado(FICHA_OCULTA)]
    assert R.cita_fichas('Manhattan tuvo 203.866 viajes', fichas)
    assert R.cita_fichas('El importe medio fue de 18,64 $', fichas)
    assert not R.cita_fichas('Los grupos con menos de 10 viajes se ocultan; el máximo son 31 días', fichas)
    assert not R.cita_fichas('El 3 de marzo de 2020 hubo viajes', fichas) and not R.cita_fichas('203.866', [])


@pytest.mark.parametrize('mensaje, esperado', [
    (AIMessage(content='Hola'), 'Hola'),
    (AIMessage(content='<think>sumo 3 y 4</think>Salieron 7 viajes'), 'Salieron 7 viajes'),
    (AIMessage(content='<think>razonamiento cortado'), ''),
    (AIMessage(content=[{'type': 'reasoning', 'reasoning': 'pensando'}, {'type': 'text', 'text': 'Respuesta'}]),
     'Respuesta'),
])
def test_texto_de_quita_el_razonamiento_del_modelo(mensaje, esperado):
    assert R.texto_de(mensaje) == esperado


# --- filtro previo (sin LLM ni recuperación) -----------------------------------------------------------------

async def test_el_filtro_previo_rechaza_sin_llm_ni_recuperacion_y_propone_la_alternativa():
    api, llm, recuperador = APIFalsa(), _llm(), RecuperadorFalso(DOC_E3)
    agente = _agente(api, llm, recuperador)
    turno = await agente.responder('Dame el viaje de las 3:12 del 15 de enero desde Times Square')
    assert llm.recibidos == [] and recuperador.preguntas == [] and api.individuales
    assert turno.bloqueo == 'filtro_previo' and turno.fuentes == [] and agente.historial == []
    assert turno.alternativa == {'nivel': 'hora_zona', 'fuente': 'historico', 'desde': '2020-01-15T03:00:00',
                                 'hasta': '2020-01-15T04:00:00', 'metricas': ['n_viajes'], 'zona_origen': 230}
    assert '🔒' in turno.respuesta and 'de 03:00 a 04:00' in turno.respuesta


async def test_el_destino_por_zona_se_rechaza_antes_del_llm_con_el_flujo_entre_barrios():
    api, llm = APIFalsa(), _llm()
    turno = await _agente(api, llm).responder('¿Cuántos viajes fueron de JFK a Times Square el 15 de enero?')
    assert llm.recibidos == [] and api.individuales[0].startswith('destino por zona')
    assert turno.bloqueo == 'filtro_previo' and turno.alternativa['nivel'] == 'od_dia_barrio'
    assert (turno.alternativa['barrio_origen'], turno.alternativa['barrio_destino']) == ('Queens', 'Manhattan')


# --- contexto recuperado --------------------------------------------------------------------------------------

async def test_el_contexto_va_en_el_mensaje_de_sistema_y_las_fuentes_en_el_turno():
    llm = _llm(_texto('Los grupos pequeños se ocultan (Escenario E3 · Reglas propias).'))
    recuperador = RecuperadorFalso(DOC_E3)
    agente = _agente(llm=llm, recuperador=recuperador, k=3)
    turno = await agente.responder('¿Por qué algunos grupos aparecen como <10?')
    assert recuperador.preguntas == [('¿Por qué algunos grupos aparecen como <10?', 3)]
    sistema, pregunta = llm.recibidos[0]
    assert isinstance(sistema, SystemMessage) and sistema.content.startswith(PR.SISTEMA_RAG)
    assert '[1] Escenario E3 · Reglas propias (doc · docs/escenario_E3.md)' in sistema.content
    assert DOC_E3.page_content in sistema.content
    assert isinstance(pregunta, HumanMessage) and pregunta.content == turno.pregunta
    assert turno.fuentes == [{'titulo': 'Escenario E3 · Reglas propias', 'fuente': 'docs/escenario_E3.md',
                              'tipo': 'doc'}]
    assert turno.fichas == [] and turno.bloqueo is None
    assert turno.respuesta == 'Los grupos pequeños se ocultan (Escenario E3 · Reglas propias).'
    # el historial no guarda el contexto: solo lo que dijeron el usuario y el modelo
    assert [type(m) for m in agente.historial] == [HumanMessage, AIMessage]


async def test_si_la_recuperacion_falla_se_responde_sin_contexto():
    llm = _llm(_texto('Solo publico agregados.'))
    turno = await _agente(llm=llm, recuperador=RecuperadorFalso(DOC_E3, fallar=True)).responder('¿Qué haces?')
    assert turno.bloqueo is None and turno.fuentes == [] and turno.respuesta == 'Solo publico agregados.'
    assert PR.SIN_CONTEXTO in llm.recibidos[0][0].content


async def test_el_contexto_cambia_en_cada_turno_y_el_historial_se_conserva():
    llm = _llm(_texto('Primera.'), _texto('Segunda.'))
    recuperador = RecuperadorFalso(DOC_E3)
    agente = _agente(llm=llm, recuperador=recuperador)
    await agente.responder('Uno')
    recuperador.documentos = [FICHA_MANHATTAN]
    await agente.responder('Dos')
    assert 'Escenario E3' in llm.recibidos[0][0].content and 'Escenario E3' not in llm.recibidos[1][0].content
    assert 'Manhattan · 03/03/2020' in llm.recibidos[1][0].content
    assert [m.content for m in llm.recibidos[1][1:]] == ['Uno', 'Primera.', 'Dos']


# --- herramientas y barreras ----------------------------------------------------------------------------------

async def test_una_cifra_verificada_por_una_herramienta_se_muestra_con_la_fuente_al_pie():
    api = APIFalsa({6: [_fila(6, 8, 12), _fila(6, 9, 15)]})
    llm = _llm(_llamada('consultar_viajes', CONSULTA_SI), _texto('Salieron 27 viajes', tokens=120))
    agente = _agente(api, llm)
    turno = await agente.responder('¿Cuántos viajes salieron de Arrochar el 1 de enero?')
    assert turno.bloqueo is None and turno.alternativa is None
    assert turno.respuesta == 'Salieron 27 viajes' + PIE
    assert [ll.nombre for ll in turno.llamadas] == ['consultar_viajes'] and api.consultas == [CONSULTA_SI]
    assert turno.pasos_llm == 2 and turno.tokens == 120
    humano, llamada, herramienta, final = agente.historial
    assert llamada.tool_calls[0]['id'] == herramienta.tool_call_id == 'c1' and herramienta.name == 'consultar_viajes'
    assert json.loads(herramienta.content)['filas'][0]['n_viajes'] == 12
    assert final.content == 'Salieron 27 viajes'
    # la segunda llamada al modelo lleva el sistema, la pregunta, la llamada y el resultado de la herramienta
    assert [type(m) for m in llm.recibidos[1]] == [SystemMessage, HumanMessage, AIMessage, ToolMessage]


async def test_una_cifra_que_no_sale_de_los_datos_se_sustituye_por_los_datos():
    api = APIFalsa({6: [_fila(6, 8, 12), _fila(6, 9, 15)]})
    llm = _llm(_llamada('consultar_viajes', CONSULTA_SI), _texto('Salieron 30 viajes'))
    agente = _agente(api, llm)
    turno = await agente.responder('¿Cuántos viajes salieron de Arrochar el 1 de enero?')
    assert turno.bloqueo == 'cifras_no_verificadas' and turno.cifras_sueltas == ['30']
    assert turno.texto_modelo == 'Salieron 30 viajes'
    assert '| 2020-01-01 08:00 | zona 6 | 12 |' in turno.respuesta and 'Total: 27 viajes' in turno.respuesta
    assert agente.historial[-1] == AIMessage(content=turno.respuesta)


async def test_sin_datos_no_se_muestran_cifras_y_se_ofrece_la_alternativa():
    llm = _llm(_llamada('consultar_viajes', CONSULTA_SI), _texto('Hubo 1.234 viajes'))
    turno = await _agente(APIFalsa(rechazar=True), llm).responder('¿Cuántos viajes?')
    assert turno.bloqueo == 'sin_datos' and '1.234' not in turno.respuesta
    assert turno.alternativa['nivel'] == 'dia_barrio' and '🔒' in turno.respuesta
    assert H.INSTRUCCION_RECHAZO in llm.recibidos[1][-1].content


async def test_si_todo_esta_enmascarado_la_respuesta_no_pasa_por_el_llm():
    llm = _llm(_llamada('consultar_viajes', CONSULTA_SI), _texto('Hubo pocos, quizá 3'))
    turno = await _agente(APIFalsa({6: [_fila(6, 8, '<10')]}), llm).responder('¿Cuántos viajes salieron de Arrochar?')
    assert turno.bloqueo == 'todo_enmascarado' and 'quizá' not in turno.respuesta
    assert turno.respuesta.startswith('Todos los grupos de esta consulta están enmascarados')


async def test_el_razonamiento_del_modelo_no_llega_al_usuario():
    api = APIFalsa({6: [_fila(6, 8, 12)]})
    llm = _llm(_llamada('consultar_viajes', CONSULTA_SI), _texto('<think>12 más 0 son 12</think>Salieron 12 viajes'))
    turno = await _agente(api, llm).responder('¿Cuántos viajes salieron de Arrochar el 1 de enero?')
    assert turno.respuesta == 'Salieron 12 viajes' + PIE


async def test_los_argumentos_mal_formados_se_devuelven_al_modelo_como_error():
    invalida = AIMessage(content='', invalid_tool_calls=[
        {'name': 'consultar_viajes', 'args': '{nivel:', 'id': 'c9', 'error': 'JSON inválido',
         'type': 'invalid_tool_call'}])
    llm = _llm(invalida, _texto('No he podido consultar la plataforma.'))
    agente = _agente(llm=llm)
    turno = await agente.responder('¿Cuántos viajes hubo?')
    assert turno.bloqueo is None and turno.respuesta == 'No he podido consultar la plataforma.'
    assert turno.llamadas[0].resultado['error'].startswith('argumentos no válidos para consultar_viajes')
    herramienta = agente.historial[2]
    assert isinstance(herramienta, ToolMessage) and herramienta.tool_call_id == 'c9'
    assert 'argumentos no válidos' in herramienta.content


async def test_si_no_termina_en_pocos_pasos_se_muestran_los_datos():
    api = APIFalsa({6: [_fila(6, 8, 12)]})
    llm = _llm(_llamada('consultar_viajes', CONSULTA_SI), _llamada('consultar_viajes', CONSULTA_SI, 'c2'))
    agente = _agente(api, llm, max_pasos=2)
    turno = await agente.responder('¿Cuántos viajes salieron de Arrochar?')
    assert turno.bloqueo == 'sin_terminar' and turno.pasos_llm == 2
    assert '| 2020-01-01 08:00 | zona 6 | 12 |' in turno.respuesta
    assert agente.historial[-1] == AIMessage(content=turno.respuesta)


# --- fichas recuperadas como datos del turno -----------------------------------------------------------------

async def test_una_ficha_citada_tal_cual_se_permite_sin_llamar_a_ninguna_herramienta():
    llm = _llm(_texto('El 3 de marzo de 2020 salieron de Manhattan 203.866 viajes (ficha Manhattan · 03/03/2020).'))
    turno = await _agente(llm=llm, recuperador=RecuperadorFalso(FICHA_MANHATTAN, DOC_E3)).responder(
        '¿Cuántos viajes salieron de Manhattan el 3 de marzo?')
    assert turno.bloqueo is None and turno.llamadas == []
    assert turno.respuesta.endswith('203.866 viajes (ficha Manhattan · 03/03/2020).' + PIE)
    assert turno.fichas[0]['filas'][0]['n_viajes'] == 203866
    assert [f['tipo'] for f in turno.fuentes] == ['ficha', 'doc']


async def test_una_cifra_que_no_sale_de_las_fichas_se_sustituye_por_las_fichas():
    llm = _llm(_texto('Salieron unos 210.000 viajes de Manhattan.'))
    turno = await _agente(llm=llm, recuperador=RecuperadorFalso(FICHA_MANHATTAN)).responder(
        '¿Cuántos viajes salieron de Manhattan el 3 de marzo?')
    assert turno.bloqueo == 'cifras_no_verificadas' and turno.cifras_sueltas == ['210.000']
    assert turno.respuesta.startswith(R.FICHAS_TAL_CUAL) and FICHA_MANHATTAN.page_content in turno.respuesta


async def test_una_ficha_enmascarada_recuperada_por_parecido_no_manda_sobre_la_respuesta():
    llm = _llm(_texto('Un grupo con menos de 10 viajes se publica sin cifras.'))
    turno = await _agente(llm=llm, recuperador=RecuperadorFalso(DOC_E3, FICHA_OCULTA)).responder(
        '¿Qué pasa con los grupos pequeños?')
    assert turno.bloqueo is None and turno.respuesta == 'Un grupo con menos de 10 viajes se publica sin cifras.'


async def test_las_fichas_no_valen_para_deducir_ni_para_sumar():
    llm = _llm(_texto('Staten Island tuvo 4 viajes y Manhattan 203.866'))
    turno = await _agente(llm=llm, recuperador=RecuperadorFalso(FICHA_MANHATTAN, FICHA_OCULTA)).responder(
        '¿Cuántos viajes hubo el 3 de marzo en cada barrio?')
    assert turno.bloqueo == 'cifras_no_verificadas' and '4 viajes' in turno.cifras_sueltas


async def test_los_datos_de_una_herramienta_mandan_sobre_las_fichas():
    api = APIFalsa({6: [_fila(6, 8, '<10')]})
    llm = _llm(_llamada('consultar_viajes', CONSULTA_SI), _texto('Manhattan tuvo 203.866 viajes'))
    agente = _agente(api, llm, RecuperadorFalso(FICHA_MANHATTAN))
    turno = await agente.responder('¿Cuántos viajes salieron de Arrochar?')
    assert turno.bloqueo == 'todo_enmascarado'


# --- guardia de salida y proveedor -----------------------------------------------------------------------------

async def test_la_guardia_revisa_antes_de_cada_llamada_y_registra_despues():
    api = APIFalsa({6: [_fila(6, 8, 12)]})
    llm = _llm(_llamada('consultar_viajes', CONSULTA_SI), _texto('Salieron 12 viajes'))
    guardia = GuardiaFalsa(anadir=SystemMessage(content='revisado por la guardia'))
    turno = await _agente(api, llm, guardia=guardia).responder('¿Cuántos viajes salieron de Arrochar el 1 de enero?')
    assert turno.bloqueo is None and len(guardia.revisados) == len(guardia.registradas) == 2
    assert isinstance(guardia.revisados[0][0], SystemMessage) and isinstance(guardia.revisados[1][-1], ToolMessage)
    assert guardia.registradas[1].content == 'Salieron 12 viajes'
    # el modelo recibe lo que devuelve la guardia, no lo que se le pasó
    assert all(recibido[-1].content == 'revisado por la guardia' for recibido in llm.recibidos)


async def test_si_la_guardia_bloquea_no_se_llama_al_modelo_y_el_turno_se_deshace():
    llm = _llm(_texto('no debería llegar'))
    agente = _agente(llm=llm, guardia=GuardiaFalsa(bloquear=True))
    await agente.responder('Hola')
    agente.historial.clear()
    turno = await agente.responder('Mi clave es X-API-Key: abc; ¿cuántos viajes hubo el 1 de enero?')
    assert turno.bloqueo == 'guardia_salida' and llm.recibidos == []
    assert turno.respuesta.startswith('🔒') and 'clave de API' in turno.respuesta and 'abc' not in turno.respuesta
    assert agente.historial == []


async def test_si_el_proveedor_falla_se_avisa_sin_romper_la_sesion():
    agente = _agente(llm=_llm(fallo=RuntimeError('502 Bad Gateway')))
    turno = await agente.responder('¿Cuántos viajes hubo?')
    assert turno.bloqueo == 'error_llm' and turno.respuesta == R.ERROR_LLM
    assert [type(m) for m in agente.historial] == [HumanMessage, AIMessage]


# --- con ChatOpenAI de verdad y un proveedor simulado (sin red) --------------------------------------------------

class ProveedorFalso:
    """Un /chat/completions compatible con OpenAI, como el de Helmcode: guarda las peticiones y contesta primero
    con una llamada a herramienta y después con texto y razonamiento aparte (como DeepSeek)."""

    def __init__(self):
        self.peticiones: list[dict] = []

    def __call__(self, peticion: httpx.Request) -> httpx.Response:
        assert peticion.url.path.endswith('/chat/completions')
        assert peticion.headers['authorization'] == 'Bearer clave-falsa'
        cuerpo = json.loads(peticion.content)
        self.peticiones.append(cuerpo)
        if len(self.peticiones) == 1:
            mensaje = {'role': 'assistant', 'content': None, 'tool_calls': [
                {'id': 'call_1', 'type': 'function',
                 'function': {'name': 'consultar_viajes', 'arguments': json.dumps(CONSULTA_SI)}}]}
        else:
            mensaje = {'role': 'assistant', 'content': 'Salieron 12 viajes de Arrochar.',
                       'reasoning_content': 'La fila dice 12, así que son 12.'}
        return httpx.Response(200, json={
            'id': 'x', 'object': 'chat.completion', 'created': 0, 'model': 'deepseek-v4-flash',
            'choices': [{'index': 0, 'message': mensaje, 'finish_reason': 'stop'}],
            'usage': {'prompt_tokens': 100, 'completion_tokens': 20, 'total_tokens': 120}})


async def test_con_chat_openai_el_historial_llega_al_proveedor_como_espera_y_el_razonamiento_no_sale():
    proveedor = ProveedorFalso()
    llm = ChatOpenAI(model='deepseek-v4-flash', base_url='http://helmcode.falso/v1', api_key='clave-falsa',
                     max_retries=0, http_async_client=httpx.AsyncClient(transport=httpx.MockTransport(proveedor)))
    api = APIFalsa({6: [_fila(6, 8, 12)]})
    agente = R.AgenteRAG(_cliente(api), llm, RecuperadorFalso(DOC_E3))
    turno = await agente.responder('¿Cuántos viajes salieron de Arrochar el 1 de enero?')

    assert turno.bloqueo is None and turno.respuesta == 'Salieron 12 viajes de Arrochar.' + PIE
    assert turno.tokens == 240 and turno.pasos_llm == 2 and api.consultas == [CONSULTA_SI]
    primera, segunda = proveedor.peticiones
    assert primera['model'] == 'deepseek-v4-flash'
    assert [h['function']['name'] for h in primera['tools']] == HL.NOMBRES
    assert [m['role'] for m in primera['messages']] == ['system', 'user']
    sistema = primera['messages'][0]['content']
    assert sistema.startswith(PR.SISTEMA_RAG) and DOC_E3.page_content in sistema
    assert [m['role'] for m in segunda['messages']] == ['system', 'user', 'assistant', 'tool']
    assert segunda['messages'][2]['tool_calls'][0]['id'] == segunda['messages'][3]['tool_call_id'] == 'call_1'
    assert json.loads(segunda['messages'][3]['content'])['filas'][0]['n_viajes'] == 12
    assert 'razonamiento' not in turno.respuesta.lower() and 'La fila dice' not in turno.respuesta


# --- la alternativa aceptada ------------------------------------------------------------------------------------

async def test_la_alternativa_aceptada_se_ejecuta_tal_cual():
    api = APIFalsa({6: [_fila(6, 8, 12)]})
    agente = _agente(api, _llm(_texto('Salieron 12 viajes')))
    turno = await agente.responder_alternativa(CONSULTA_SI)
    assert api.consultas == [CONSULTA_SI] and turno.respuesta == 'Salieron 12 viajes' + PIE
    pregunta, llamada, herramienta, _ = agente.historial
    assert pregunta.content == R.PREGUNTA_ALTERNATIVA
    assert llamada.tool_calls[0]['args'] == CONSULTA_SI and llamada.tool_calls[0]['id'] == herramienta.tool_call_id


async def test_si_tras_la_alternativa_el_llm_no_da_la_cifra_se_muestran_los_datos():
    agente = _agente(APIFalsa({6: [_fila(6, 8, 12)]}), _llm(_texto('La consulta es permitida.')))
    turno = await agente.responder_alternativa(CONSULTA_SI)
    assert turno.respuesta.startswith('La consulta es permitida.')
    assert '| 2020-01-01 08:00 | zona 6 | 12 |' in turno.respuesta
