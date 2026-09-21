"""Corpus de conocimiento y fichas de agregados del chatbot RAG: lógica pura y una API de acceso falsa."""
import json
import sys
from datetime import datetime
from pathlib import Path

import httpx
import pytest

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / 'parte3_chatbot'))
sys.path.insert(0, str(RAIZ / 'parte3_chatbot_rag'))

import corpus as C  # noqa: E402
import fichas as F  # noqa: E402
import herramientas as H  # noqa: E402
from parte2_plataforma.comun import privacidad as P  # noqa: E402

ZONAS = [
    {'_id': 1, 'nombre': 'Newark Airport', 'barrio': 'EWR', 'tipo_servicio': 'EWR'},
    {'_id': 5, 'nombre': 'Arden Heights', 'barrio': 'Staten Island', 'tipo_servicio': 'Boro Zone'},
    {'_id': 6, 'nombre': 'Arrochar/Fort Wadsworth', 'barrio': 'Staten Island', 'tipo_servicio': 'Boro Zone'},
    {'_id': 132, 'nombre': 'JFK Airport', 'barrio': 'Queens', 'tipo_servicio': 'Airports'},
    {'_id': 230, 'nombre': 'Times Sq/Theatre District', 'barrio': 'Manhattan', 'tipo_servicio': 'Yellow Zone'},
]
BARRIOS = ['Bronx', 'Brooklyn', 'EWR', 'Manhattan', 'N/A', 'Queens', 'Staten Island', 'Unknown']
CATALOGO = {'k_minimo': 10, 'max_dias_por_consulta': 31, 'metricas': P.config()['metricas'],
            'niveles': {n: {'descripcion': v['descripcion'], 'dimensiones': v['dimensiones']}
                        for n, v in P.config()['niveles'].items()},
            'fuentes': ['historico', 'tiempo_real'], 'barrios': BARRIOS}
HERRAMIENTAS = {e['function']['name'] for e in H.ESQUEMAS}

FILA_DIA = {'dia': '2020-03-03T00:00:00', 'barrio_origen': 'Manhattan', 'n_viajes': 203866, 'distancia_media': 2.9,
            'importe_medio': 18.5, 'propina_media': 2.07, 'pct_pago_tarjeta': 71.2, 'suprimido': False}
FILA_OCULTA = {'dia': '2020-01-01T00:00:00', 'barrio_origen': 'Staten Island', 'n_viajes': '<10',
               'distancia_media': None, 'importe_medio': None, 'propina_media': None, 'pct_pago_tarjeta': None,
               'suprimido': True}
FILA_FLUJO = {'dia': '2020-01-01T00:00:00', 'barrio_origen': 'Manhattan', 'barrio_destino': 'Bronx', 'n_viajes': 1311,
              'distancia_media': 8.23, 'importe_medio': 31.52, 'propina_media': 1.88, 'pct_pago_tarjeta': 37.38,
              'suprimido': False}


# --- corpus ------------------------------------------------------------------------------------------------------

MARKDOWN = """# Escenario E3

Intro corta que no llega a nada.

## Reglas propias

1. Niveles publicados: por hora y zona; por día y barrio; por día y par de barrios.
2. k-anonimato por grupo: k = 10.

```bash
make test   # esto no se indexa
```

### Redondeo

Las medias se redondean a 2 decimales, siempre, en todos los niveles publicados por la plataforma.

## Reglas propias

Segunda sección con la misma cabecera, para comprobar que no chocan los identificadores de los trozos.
"""


def test_trocea_el_markdown_por_cabeceras_con_su_titulo_y_sin_codigo():
    trozos = C.trocear_markdown(MARKDOWN, 'docs/escenario_E3.md')
    titulos = [t.metadata['titulo'] for t in trozos]
    assert titulos == ['Escenario E3 › Reglas propias', 'Escenario E3 › Reglas propias › Redondeo',
                       'Escenario E3 › Reglas propias · 2']
    assert trozos[0].page_content.startswith('Escenario E3 › Reglas propias\n\n1. Niveles')
    assert 'make test' not in trozos[0].page_content
    assert all(t.metadata['tipo'] == 'doc' and t.metadata['fuente'] == 'docs/escenario_E3.md' for t in trozos)
    assert len({t.metadata['_id'] for t in trozos}) == 3
    largo = C.trocear_markdown('# Largo\n\n' + ('palabra ' * 700), 'docs/largo.md', tamano=1000, solape=50)
    assert len(largo) > 1 and largo[0].metadata['titulo'].startswith('Largo (1/')


def test_los_docs_del_repositorio_se_trocean_en_tamanos_razonables():
    trozos = C.documentos_markdown(RAIZ / 'docs', 'docs', C.DOCS_EXCLUIDOS)
    assert len(trozos) > 20
    assert not any(t.metadata['fuente'].endswith(('plan.md', 'herramientas.md')) for t in trozos)
    assert all(len(t.page_content) <= C.TAMANO_TROZO + 200 for t in trozos)
    C.comprobar_ids_unicos(trozos)


def test_la_configuracion_de_privacidad_se_cuenta_en_prosa():
    texto = C.documento_privacidad().page_content
    assert 'menos de 10 viajes' in texto and 'hora_zona' in texto and 'zona_destino' in texto
    assert '31 días' in texto and 'tiempo_real' in texto


def test_el_calendario_de_2020_da_el_dia_de_la_semana():
    meses = C.documentos_calendario()
    assert len(meses) == 12 and meses[1].page_content.startswith('Calendario de febrero de 2020: 29 días')
    marzo = meses[2].page_content
    assert '- Martes: 3, 10, 17, 24, 31' in marzo and '3 martes' in marzo
    assert 'desde 2020-03-01T00:00:00 hasta 2020-04-01T00:00:00' in marzo
    assert meses[11].page_content.endswith('hasta 2021-01-01T00:00:00 (31 días).')


def test_las_zonas_llevan_sinonimos_y_hay_un_resumen_por_barrio():
    docs = C.documentos_zonas(ZONAS)
    por_titulo = {d.metadata['titulo']: d for d in docs}
    jfk = por_titulo['Zona 132 · JFK Airport'].page_content
    assert 'JFK' in jfk and 'Kennedy' in jfk and 'aeropuerto' in jfk and 'zona_origen=132' in jfk and 'Queens' in jfk
    assert 'Times Square' in por_titulo['Zona 230 · Times Sq/Theatre District'].page_content
    assert 'Newark' in por_titulo['Zona 1 · Newark Airport'].page_content and 'Nueva Jersey' in \
        por_titulo['Zona 1 · Newark Airport'].page_content
    staten = por_titulo['Zonas del barrio Staten Island'].page_content
    assert 'tiene 2 zonas' in staten and 'Arden Heights (5)' in staten
    assert all(d.metadata['tipo'] == 'zona' for d in docs) and len(docs) == len(ZONAS) + 4
    C.comprobar_ids_unicos(docs)


def _consulta_evaluable(argumentos: dict) -> P.Consulta:
    """Lo que llega a la API tras pasar por el cliente del chatbot: la zona por nombre se resuelve a su id y «por
    horas desde un barrio» se convierte en una consulta por cada zona del barrio."""
    limpio = dict(argumentos)
    if isinstance(limpio.get('zona_origen'), str) and not limpio['zona_origen'].isdigit():
        limpio['zona_origen'] = 132
    if limpio.get('nivel') == 'hora_zona' and limpio.pop('barrio_origen', None) and 'zona_origen' not in limpio:
        limpio['zona_origen'] = 5
    return P.Consulta(**limpio)


def test_los_ejemplos_del_corpus_pasan_el_filtro_de_privacidad_de_la_api():
    datos = json.loads((RAIZ / 'parte3_chatbot_rag' / 'corpus' / 'ejemplos.json').read_text(encoding='utf-8'))
    ejemplos = datos['ejemplos']
    assert len(ejemplos) >= 20 and len({e['pregunta'] for e in ejemplos}) == len(ejemplos)
    for ejemplo in ejemplos:
        assert not H.parece_individual(ejemplo['pregunta']) or \
            ejemplo['llamadas'][0]['herramienta'] == 'solicitud_individual', ejemplo['pregunta']
        for llamada in ejemplo['llamadas']:
            assert llamada['herramienta'] in HERRAMIENTAS
            if llamada['herramienta'] != 'consultar_viajes':
                continue
            argumentos = llamada['argumentos']
            assert set(argumentos) <= H.PARAMETROS - {'campos_extra'}, ejemplo['pregunta']
            decision = P.evaluar(_consulta_evaluable(argumentos))
            assert decision.resultado == P.Resultado.PERMITIDA, (ejemplo['pregunta'], decision.motivos)
            for barrio in ('barrio_origen', 'barrio_destino'):
                assert argumentos.get(barrio) in (None, *P.BARRIOS), ejemplo['pregunta']
    docs = C.documentos_ejemplos(RAIZ / 'parte3_chatbot_rag' / 'corpus' / 'ejemplos.json')
    assert len(docs) == len(ejemplos) and all(d.metadata['tipo'] == 'ejemplo' for d in docs)
    assert docs[0].page_content.startswith('Pregunta: ') and 'Llamada: consultar_viajes(nivel="hora_zona"' in \
        docs[0].page_content
    dos = next(d for d in docs if 'Llamada 2:' in d.page_content)
    assert dos.metadata['herramienta'] == 'consultar_viajes'


def test_el_conocimiento_completo_junta_todas_las_fuentes_sin_red():
    docs = C.conocimiento(ZONAS, CATALOGO)
    tipos = C.resumen(docs)
    assert set(tipos) == {'doc', 'catalogo', 'zona', 'ejemplo'} and tipos['catalogo'] == 1
    assert tipos['zona'] == len(ZONAS) + 4 and tipos['doc'] > 30
    fuentes = {d.metadata['fuente'] for d in docs}
    assert {'config/privacidad.json', 'calendario', 'api:/catalogo', 'api:/zonas', 'corpus/ejemplos.json',
            'corpus/guia_consultas.md', 'corpus/preguntas_frecuentes.md', 'corpus/contexto_2020.md'} <= fuentes
    assert any(f.startswith('docs/') for f in fuentes)
    catalogo = next(d for d in docs if d.metadata['tipo'] == 'catalogo').page_content
    assert 'Staten Island' in catalogo and 'EWR (aeropuerto de Newark' in catalogo
    assert all(d.metadata['titulo'] and d.page_content for d in docs)


# --- fichas ------------------------------------------------------------------------------------------------------

def test_las_consultas_de_fichas_cubren_el_anio_y_pasan_el_filtro_de_la_api():
    consultas = F.consultas(BARRIOS)
    assert len(consultas) == 12 + 12 * len(BARRIOS)
    assert consultas[0] == {'fuente': 'historico', 'desde': '2020-01-01T00:00:00', 'hasta': '2020-02-01T00:00:00',
                            'metricas': F.METRICAS, 'nivel': 'dia_barrio'}
    assert consultas[-1]['hasta'] == '2021-01-01T00:00:00' and consultas[-1]['barrio_origen'] == 'Unknown'
    for consulta in consultas:
        assert P.evaluar(P.Consulta(**consulta)).resultado == P.Resultado.PERMITIDA
        dias = (datetime.fromisoformat(consulta['hasta']) - datetime.fromisoformat(consulta['desde'])).days
        assert 28 <= dias <= 31


def test_el_texto_de_una_ficha_es_espanol_natural_y_no_inventa_cifras_ocultas():
    visible = F.texto_ficha(FILA_DIA, 'dia_barrio')
    assert visible.startswith('El martes 3 de marzo de 2020 salieron de Manhattan 203.866 viajes de taxi')
    assert 'Distancia media 2,90 millas' in visible and 'propina media 2,07 $' in visible and '71,20 %' in visible
    flujo = F.texto_ficha(FILA_FLUJO, 'od_dia_barrio')
    assert 'hubo 1.311 viajes de taxi de Manhattan a Bronx (flujo entre barrios por día, histórico)' in flujo
    oculta = F.texto_ficha(FILA_OCULTA, 'dia_barrio')
    assert 'Staten Island están enmascarados por privacidad' in oculta and 'menos de 10 viajes' in oculta
    assert not any(c.isdigit() for c in oculta.replace('1 de enero de 2020', '').replace('10 viajes', ''))
    assert 'tiempo real' in F.texto_ficha(FILA_DIA, 'dia_barrio', 'tiempo_real')


def test_la_ficha_lleva_en_los_metadatos_la_fila_de_la_api_y_se_reconstruye():
    ficha = F.ficha(FILA_DIA, 'dia_barrio')
    m = ficha.metadata
    assert m['tipo'] == 'ficha' and m['nivel'] == 'dia_barrio' and m['dia'] == '2020-03-03' and m['mes'] == 3
    assert m['barrio_origen'] == 'Manhattan' and m['barrio_destino'] is None and m['suprimido'] is False
    assert m['n_viajes'] == 203866 and m['propina_media'] == 2.07 and m['titulo'] == 'Manhattan · 2020-03-03'
    assert F.fila_desde_metadatos(m) == {k: v for k, v in FILA_DIA.items()}
    flujo = F.ficha(FILA_FLUJO, 'od_dia_barrio')
    assert flujo.metadata['titulo'] == 'Manhattan → Bronx · 2020-01-01'
    assert F.fila_desde_metadatos(flujo.metadata) == FILA_FLUJO
    oculta = F.ficha({**FILA_OCULTA, 'nivel': 'dia_barrio'})
    assert oculta.metadata['suprimido'] is True and oculta.metadata['n_viajes'] == '<10'
    assert oculta.metadata['propina_media'] is None and H.enmascarada(F.fila_desde_metadatos(oculta.metadata))
    assert F.ficha(FILA_DIA, 'dia_barrio').metadata['_id'] == ficha.metadata['_id']       # estable
    assert F.ficha(FILA_DIA, 'dia_barrio', 'tiempo_real').metadata['_id'] != ficha.metadata['_id']
    C.comprobar_ids_unicos([ficha, flujo, oculta])


class APIFalsa:
    """La API de acceso en memoria: zonas, catálogo y consultas de los niveles gruesos (dos filas por mes)."""

    def __init__(self, truncar: bool = False, rechazar: bool = False):
        self.truncar, self.rechazar = truncar, rechazar
        self.consultas: list[dict] = []

    def __call__(self, peticion: httpx.Request) -> httpx.Response:
        if peticion.url.path == '/zonas':
            return httpx.Response(200, json=ZONAS)
        if peticion.url.path == '/catalogo':
            return httpx.Response(200, json=CATALOGO)
        cuerpo = json.loads(peticion.content)
        self.consultas.append(cuerpo)
        if self.rechazar:
            return httpx.Response(403, json={'resultado': 'rechazada', 'motivos': ['prueba'], 'alternativa': None})
        dia = cuerpo['desde'][:8] + '15T00:00:00'
        if cuerpo['nivel'] == 'dia_barrio':
            filas = [{**FILA_DIA, 'dia': dia}, {**FILA_OCULTA, 'dia': dia}]
        else:
            filas = [{**FILA_FLUJO, 'dia': dia, 'barrio_origen': cuerpo['barrio_origen']}]
        return httpx.Response(200, json={'resultado': 'enmascarada', 'consulta': cuerpo, 'filas': filas,
                                         'grupos_enmascarados': 1, 'truncada': self.truncar})


def _cliente(api) -> H.ClienteAcceso:
    cliente = H.ClienteAcceso(url='http://acceso', clave='k')
    cliente.http = httpx.AsyncClient(base_url='http://acceso', headers={'X-API-Key': 'k'},
                                     transport=httpx.MockTransport(api))
    return cliente


async def test_descarga_las_fichas_mes_a_mes_y_barrio_a_barrio():
    api = APIFalsa()
    cliente = _cliente(api)
    docs = await F.fichas_desde_api(cliente, BARRIOS, avisar=lambda _: None)
    assert len(api.consultas) == 12 + 12 * len(BARRIOS)
    assert all(c['metricas'] == F.METRICAS for c in api.consultas)
    assert len(docs) == 12 * 2 + 12 * len(BARRIOS)
    assert C.resumen(docs) == {'ficha': len(docs)} and F.dias_cubiertos(docs) == ('2020-01-15', '2020-12-15')
    assert {d.metadata['nivel'] for d in docs} == {'dia_barrio', 'od_dia_barrio'}
    C.comprobar_ids_unicos(docs)
    conocimiento = await C.conocimiento_desde_api(cliente)
    assert C.resumen(conocimiento)['zona'] == len(ZONAS) + 4
    await cliente.cerrar()


async def test_una_respuesta_truncada_o_rechazada_detiene_la_descarga():
    for api in (APIFalsa(truncar=True), APIFalsa(rechazar=True)):
        cliente = _cliente(api)
        with pytest.raises(F.ErrorDescarga):
            await F.descargar(cliente, ['Manhattan'], avisar=lambda _: None)
        await cliente.cerrar()
