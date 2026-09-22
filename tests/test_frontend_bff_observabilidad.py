"""BFF del portal (parte 4), Observabilidad: los cuadros de Grafana descritos desde sus JSON y con los datos de
Prometheus. Sin red: Prometheus y Grafana son un `httpx.MockTransport` que apunta qué consultas le llegan, para
comprobar que el BFF solo ejecuta las de los ficheros de los cuadros."""
from __future__ import annotations

import json

import httpx
import pytest
from fastapi.testclient import TestClient

from parte4_frontend.bff import app as A
from parte4_frontend.bff import configuracion as C
from parte4_frontend.bff import seguridad as S
from parte4_frontend.bff.servicios import observabilidad as OBS

ENTORNO = {'PUERTO_PROMETHEUS': '9090', 'PUERTO_GRAFANA': '3000', 'FRONTEND_CLAVE': 'portal',
           'FRONTEND_SECRETO': 'secreto'}
REGLAS = {'status': 'success', 'data': {'groups': [{'name': 'pids', 'rules': [
    {'name': 'PIDS · Servicio caído', 'state': 'inactive', 'type': 'alerting', 'annotations': {'summary': 'Un job no responde'}},
    {'name': 'PIDS · Tiempo real antiguo', 'state': 'firing', 'type': 'alerting', 'annotations': {'summary': 'Hace 20 min'}},
    {'name': 'grabada', 'type': 'recording'},
]}]}}


class Observatorio:
    """Prometheus (instantáneas y rangos) y la API de reglas de Grafana, en memoria."""

    def __init__(self):
        self.consultas: list[str] = []
        self.prometheus_caido = False

    def __call__(self, peticion: httpx.Request) -> httpx.Response:
        if peticion.url.port == 3000:
            return httpx.Response(200, json=REGLAS)
        if self.prometheus_caido:
            raise httpx.ConnectError('caído', request=peticion)
        consulta = peticion.url.params['query']
        self.consultas.append(consulta)
        metrica = {'__name__': 'x', 'job': 'acceso', 'resultado': 'permitida'}
        if peticion.url.path.endswith('query_range'):
            inicio = float(peticion.url.params['start'])
            paso = float(peticion.url.params['step'])
            valores = [[inicio + i * paso, str(i)] for i in range(5)] + [[inicio + 5 * paso, 'NaN']]
            return httpx.Response(200, json={'status': 'success', 'data': {'resultType': 'matrix',
                                                                           'result': [{'metric': metrica, 'values': valores}]}})
        return httpx.Response(200, json={'status': 'success', 'data': {'resultType': 'vector',
                                                                       'result': [{'metric': metrica, 'value': [0, '3']}]}})


@pytest.fixture(autouse=True)
def sin_cache():
    OBS.CACHE.limpiar()
    yield
    OBS.CACHE.limpiar()


@pytest.fixture
def observatorio() -> Observatorio:
    return Observatorio()


@pytest.fixture
def cliente(observatorio, tmp_path, monkeypatch):
    cfg = C.Configuracion.desde_entorno(ENTORNO, contenedor=False)
    original = httpx.AsyncClient
    monkeypatch.setattr(httpx, 'AsyncClient', lambda **kw: original(transport=httpx.MockTransport(observatorio), **kw))
    with TestClient(A.crear_app(cfg, dist=tmp_path / 'sin-dist')) as c:
        c.cookies.set('pids_sesion', S.crear_valor_sesion(cfg.frontend_secreto))
        yield c


# --- lógica pura -------------------------------------------------------------------------------------------

def test_periodos_leyendas_y_variable_de_grafana():
    assert OBS.segundos('6h') == 21_600 and OBS.segundos('24h') == 86_400 and OBS.segundos('15m') == 900
    assert OBS.expresion('sum(increase(x[$__range]))', '24h') == 'sum(increase(x[24h]))'
    assert OBS.leyenda('{{cliente}} · {{resultado}}', {'cliente': 'portal', 'resultado': 'permitida'}) == 'portal · permitida'
    assert OBS.leyenda('{{falta}}', {'__name__': 'up', 'job': 'acceso'}) == 'acceso'
    assert OBS.leyenda('', {'__name__': 'up'}) == 'valor'
    workers = [{'job': 'spark-workers', 'instance': 'w1:8081'}, {'job': 'spark-workers', 'instance': 'w2:8081'},
               {'job': 'acceso'}]
    assert OBS.nombres(workers, '{{job}}') == ['spark-workers · w1:8081', 'spark-workers · w2:8081', 'acceso']
    assert OBS.nombres([{'job': 'a'}, {'job': 'a'}], '{{job}}') == ['a (1)', 'a (2)']
    cubos = [{'bucket': 'crudo', 'instance': 's3:9327', 'type': 'GET'}, {'bucket': 'crudo', 'instance': 's3:9327', 'type': 'PUT'}]
    assert OBS.nombres(cubos, '{{bucket}}') == ['crudo · GET', 'crudo · PUT']


def test_los_ocho_cuadros_se_describen_desde_los_json_de_grafana():
    cuadros = OBS.cuadros()
    assert list(cuadros)[:2] == ['pids-plataforma', 'pids-privacidad'] and len(cuadros) == 8
    for uid, cuadro in cuadros.items():
        fichero = json.loads((OBS.CARPETA / f'{uid}.json').read_text(encoding='utf-8'))
        assert cuadro['titulo'] == fichero['title'].removeprefix('PIDS · ')
        assert len(cuadro['paneles']) == len(fichero['panels'])          # ningún tipo de panel se queda fuera
        for panel in cuadro['paneles']:
            assert 0 <= panel['x'] and panel['x'] + panel['ancho'] <= 24
            if panel['tipo'] not in ('fila', 'texto', 'alertas'):
                assert panel['_consultas'], panel['titulo']


def test_describir_panel_saca_umbrales_mapeos_y_colores():
    panel = OBS.describir_panel({
        'id': 7, 'type': 'bargauge', 'title': 'Estado', 'gridPos': {'x': 12, 'y': 5, 'w': 12, 'h': 8},
        'fieldConfig': {'defaults': {'unit': 'short', 'thresholds': {'steps': [{'color': 'red', 'value': None},
                                                                              {'color': 'green', 'value': 1}]},
                                     'mappings': [{'type': 'value', 'options': {'0': {'text': 'Caído', 'color': 'red'}}}]},
                        'overrides': [{'matcher': {'id': 'byName', 'options': 'rechazada'},
                                       'properties': [{'id': 'color', 'value': {'fixedColor': 'red'}}]}]},
        'targets': [{'expr': 'up', 'legendFormat': '{{job}}'}],
    })
    assert panel['tipo'] == 'barras' and (panel['x'], panel['ancho'], panel['alto']) == (12, 12, 8)
    assert panel['umbrales'] == [{'color': 'red', 'desde': None}, {'color': 'green', 'desde': 1}]
    assert panel['mapeos'] == {'0': {'texto': 'Caído', 'color': 'red'}} and panel['colores'] == {'rechazada': 'red'}
    assert OBS.describir_panel({'type': 'news'}) is None


def test_alertas_primero_las_disparadas_y_sin_reglas_de_grabacion():
    alertas = OBS.alertas_de_reglas(REGLAS)
    assert [a['nombre'] for a in alertas] == ['Tiempo real antiguo', 'Servicio caído']
    assert alertas[0] == {'nombre': 'Tiempo real antiguo', 'estado': 'firing', 'resumen': 'Hace 20 min'}


# --- rutas -------------------------------------------------------------------------------------------------

def test_sin_sesion_da_401(tmp_path):
    cfg = C.Configuracion.desde_entorno(ENTORNO, contenedor=False)
    with TestClient(A.crear_app(cfg, dist=tmp_path / 'sin-dist')) as c:
        assert c.get('/api/observabilidad/cuadros').status_code == 401


def test_lista_y_cuadro_desconocido(cliente, observatorio):
    lista = cliente.get('/api/observabilidad/cuadros').json()
    assert lista[0] == {'uid': 'pids-plataforma', 'titulo': 'Plataforma', 'periodo': '6h'}
    respuesta = cliente.get('/api/observabilidad/cuadros/up')
    assert respuesta.status_code == 404 and observatorio.consultas == []


def test_el_cuadro_trae_datos_de_cada_panel_y_solo_ejecuta_sus_consultas(cliente, observatorio):
    cuadro = cliente.get('/api/observabilidad/cuadros/pids-plataforma').json()
    assert cuadro['uid'] == 'pids-plataforma' and cuadro['disponible'] is True
    paneles = {p['titulo']: p for p in cuadro['paneles']}
    assert all('_consultas' not in p for p in cuadro['paneles'])          # las consultas no salen del BFF
    serie = next(p for p in cuadro['paneles'] if p['tipo'] == 'serie')
    assert serie['series'][0]['puntos'][-1][1] is None                    # NaN de Prometheus → null
    stat = next(p for p in cuadro['paneles'] if p['tipo'] == 'stat')
    assert stat['valores'][0]['valor'] == 3
    alertas = next(p for p in paneles.values() if p['tipo'] == 'alertas')
    assert alertas['alertas'][0]['estado'] == 'firing'
    permitidas = {OBS.expresion(c['expr'], '6h') for p in OBS.cuadros()['pids-plataforma']['paneles'] for c in p['_consultas']}
    assert set(observatorio.consultas) <= permitidas and observatorio.consultas
    # unos segundos después, sale de la caché sin volver a preguntar a Prometheus
    antes = len(observatorio.consultas)
    cliente.get('/api/observabilidad/cuadros/pids-plataforma')
    assert len(observatorio.consultas) == antes


def test_prometheus_caido_deja_los_paneles_con_error_y_no_da_500(cliente, observatorio):
    observatorio.prometheus_caido = True
    respuesta = cliente.get('/api/observabilidad/cuadros/pids-spark')
    assert respuesta.status_code == 200
    cuadro = respuesta.json()
    assert cuadro['disponible'] is False
    assert all(p.get('error') == 'Prometheus no responde' for p in cuadro['paneles'] if p['tipo'] not in ('fila', 'texto'))
