"""BFF del portal (parte 4), rutas de plataforma (F1): consultas, catálogo, panel, tiempo real, auditoría y
operaciones. Sin red: la API de acceso, la de captura, Prometheus y Airflow son una `Plataforma` falsa detrás de
un `httpx.MockTransport` (la API de acceso falsa aplica el filtro de privacidad real de
`parte2_plataforma.comun.privacidad`, así que los 403 y los `"oculto"` son los de verdad); MongoDB es un fake que
sustituye a `servicios.auditoria.abrir_cliente`."""
from __future__ import annotations

import csv
import gzip
import json
import random
import re
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from pymongo.errors import ServerSelectionTimeoutError

from parte2_plataforma.comun import privacidad as P
from parte2_plataforma.simulador import directo as DIRECTO
from parte4_frontend.bff import app as A
from parte4_frontend.bff import configuracion as C
from parte4_frontend.bff import seguridad as S
from parte4_frontend.bff.rutas import tiempo_real as RTR
from parte4_frontend.bff.servicios import acceso as ACCESO
from parte4_frontend.bff.servicios import airflow as AIR
from parte4_frontend.bff.servicios import auditoria as AUD
from parte4_frontend.bff.servicios import prometheus as PROM
from parte4_frontend.bff.servicios import simulacion as SIM

ENTORNO = {
    'PUERTO_ACCESO': '8002', 'PUERTO_CAPTURA': '8001', 'PUERTO_PROMETHEUS': '9090', 'PUERTO_AIRFLOW': '8085',
    'PUERTO_MONGO': '27018', 'PUERTO_OLLAMA': '11435',
    'ACCESO_CLAVE_EQUIPO': 'clave-equipo', 'CAPTURA_CLAVE_SIMULADOR': 'clave-sim',
    'MONGO_AUDITOR_PASSWORD': 'p@ss', 'AIRFLOW_ADMIN_USER': 'admin', 'AIRFLOW_ADMIN_PASSWORD': 'af',
    'FRONTEND_CLAVE': 'portal', 'FRONTEND_SECRETO': 'secreto',
}
PUERTOS = {8002: 'acceso', 8001: 'captura', 9090: 'prometheus', 8085: 'airflow'}
CATALOGO = {'k_minimo': 10, 'max_dias_por_consulta': 31, 'metricas': P.config()['metricas'],
            'niveles': {n: {'descripcion': v['descripcion'], 'dimensiones': v['dimensiones']}
                        for n, v in P.config()['niveles'].items()},
            'fuentes': ['historico', 'tiempo_real'], 'barrios': ['Bronx', 'Brooklyn', 'Manhattan', 'Queens']}
ZONAS = [{'_id': 132, 'nombre': 'JFK Airport', 'barrio': 'Queens', 'tipo_servicio': 'Airports'},
         {'_id': 138, 'nombre': 'LaGuardia Airport', 'barrio': 'Queens', 'tipo_servicio': 'Airports'},
         {'_id': 161, 'nombre': 'Midtown Center', 'barrio': 'Manhattan', 'tipo_servicio': 'Yellow Zone'}]
RUN = {'dag_run_id': 'manual__2026-09-17T19:20:32+00:00', 'dag_id': 'pids_carga_historica', 'logical_date': None,
       'start_date': '2026-09-17T19:20:32.454527Z', 'end_date': '2026-09-17T19:22:40.584929Z', 'state': 'success',
       'run_type': 'manual', 'conf': {'mes': '2020-01', 'muestra': True}, 'note': None}
DAG_RUNS = '/api/v2/dags/pids_carga_historica/dagRuns'
MUESTRA = ('publico_ultima_actualizacion_timestamp_segundos', 'tiempo_real')


def dia(fecha: str, barrio: str, n: int, suprimido: bool = False) -> dict:
    return {'dia': f'{fecha}T00:00:00', 'barrio_origen': barrio, 'n_viajes': n, 'suprimido': suprimido}


def hora(momento: str, zona: int, n: int, suprimido: bool = False) -> dict:
    return {'hora': momento, 'zona_origen': zona, 'zona_origen_nombre': f'zona {zona}', 'barrio_origen': 'Manhattan',
            'n_viajes': n, 'suprimido': suprimido}


def muestra(metric: dict, valor, evaluado: float = 1_600_000_100.0) -> dict:
    return {'metric': metric, 'value': [evaluado, str(valor)]}


class Plataforma:
    """La API de acceso (con el filtro de privacidad real), la de captura, Prometheus y Airflow, en memoria."""

    def __init__(self):
        self.filas: dict[tuple[str, str], list[dict]] = {}          # (fuente, nivel) -> filas publicadas
        self.consultas: list[dict] = []                              # cuerpos recibidos en POST /consultas
        self.peticiones: list[tuple[str, str]] = []                  # (servicio, ruta) de todo lo recibido
        self.claves_vistas: set[str | None] = set()
        self.textos_zonas: list[str] = []                            # `texto` recibido en GET /zonas
        self.acceso_caida = False
        self.acceso_codigo: int | None = None                        # fuerza un código inesperado (500…)
        self.prometheus: dict[str, list[dict]] | None = {}           # expresión -> vector; None = caído
        self.airflow_caido = False
        self.airflow_tokens = ['jwt-1']                              # los que emite /auth/token, en orden
        self.airflow_valido = 'jwt-1'                                # el único que acepta
        self.airflow_runs = [dict(RUN)]
        self.airflow_lanzar_codigo: int | None = None                # fuerza un 4xx al crear la ejecución
        self.captura_lotes: list[dict] = []
        self.captura_codigo = 202

    def __call__(self, peticion: httpx.Request) -> httpx.Response:
        servicio = PUERTOS.get(peticion.url.port or 0)
        self.peticiones.append((servicio or '?', peticion.url.path))
        if servicio is None:
            return httpx.Response(404, json={'detail': 'servicio desconocido'})
        return getattr(self, f'_{servicio}')(peticion)

    # --- API de acceso ---
    def _acceso(self, r: httpx.Request) -> httpx.Response:
        if self.acceso_caida:
            raise httpx.ConnectError('caída', request=r)
        if r.url.path == '/salud':
            return httpx.Response(200, json={'estado': 'ok'})
        clave = r.headers.get('X-API-Key')
        self.claves_vistas.add(clave)
        if clave != 'clave-equipo':
            return httpx.Response(401, json={'detail': 'Falta la cabecera X-API-Key o no es válida'})
        if self.acceso_codigo:
            return httpx.Response(self.acceso_codigo, text='error interno')
        if r.url.path == '/catalogo':
            return httpx.Response(200, json=CATALOGO)
        if r.url.path == '/zonas':
            texto = r.url.params.get('texto', '').lower()
            self.textos_zonas.append(texto)
            return httpx.Response(200, json=[z for z in ZONAS if texto in z['nombre'].lower()])
        if r.url.path == '/consultas':
            return self._consultar(json.loads(r.content))
        return httpx.Response(404, json={'detail': 'Not Found'})

    def _consultar(self, cuerpo: dict) -> httpx.Response:
        self.consultas.append(cuerpo)
        try:
            consulta = P.Consulta.model_validate(cuerpo)
        except ValidationError as error:
            return httpx.Response(422, json={'detail': json.loads(error.json())})
        decision = P.evaluar(consulta)
        if decision.resultado == P.Resultado.RECHAZADA:
            return httpx.Response(403, json=decision.model_dump(mode='json'))
        campo = 'hora' if consulta.nivel == 'hora_zona' else 'dia'
        filas = [f for f in self.filas.get((consulta.fuente, consulta.nivel), [])
                 if consulta.desde <= datetime.fromisoformat(f[campo]) < consulta.hasta
                 and (consulta.zona_origen is None or f.get('zona_origen') == consulta.zona_origen)
                 and (consulta.barrio_origen is None or f.get('barrio_origen') == consulta.barrio_origen)]
        filas.sort(key=lambda f: f[campo])
        maximo = P.config()['max_filas_por_respuesta']
        truncada = len(filas) > maximo
        filas, ocultas = P.enmascarar(filas[:maximo], [m for m in consulta.metricas if m != 'n_viajes'])
        return httpx.Response(200, json={
            'resultado': P.resultado_final(ocultas).value, 'consulta': consulta.model_dump(mode='json'),
            'filas': filas, 'grupos_enmascarados': ocultas, 'truncada': truncada,
            'nota': 'Los grupos enmascarados no se suman a ningún total.'})

    # --- API de captura ---
    def _captura(self, r: httpx.Request) -> httpx.Response:
        if r.url.path == '/salud':
            return httpx.Response(200, json={'estado': 'ok'})
        if r.headers.get('X-API-Key') != 'clave-sim':
            return httpx.Response(401, json={'detail': 'Falta la cabecera X-API-Key o no es válida'})
        cuerpo = json.loads(r.content)
        self.captura_lotes.append(cuerpo)
        if self.captura_codigo != 202:
            return httpx.Response(self.captura_codigo, json={'detail': 'error'})
        return httpx.Response(202, json={'aceptados': len(cuerpo['viajes']), 'lote': cuerpo['lote']})

    # --- Prometheus ---
    def _prometheus(self, r: httpx.Request) -> httpx.Response:
        if self.prometheus is None:
            raise httpx.ConnectError('caído', request=r)
        vector = self.prometheus.get(r.url.params.get('query', ''), [])
        return httpx.Response(200, json={'status': 'success', 'data': {'resultType': 'vector', 'result': vector}})

    # --- Airflow ---
    def _airflow(self, r: httpx.Request) -> httpx.Response:
        if self.airflow_caido:
            raise httpx.ConnectError('caído', request=r)
        if r.url.path == '/auth/token':
            if json.loads(r.content) != {'username': 'admin', 'password': 'af'}:
                return httpx.Response(401, json={'detail': 'Invalid credentials'})
            token = self.airflow_tokens.pop(0) if len(self.airflow_tokens) > 1 else self.airflow_tokens[0]
            return httpx.Response(201, json={'access_token': token})
        if r.headers.get('Authorization') != f'Bearer {self.airflow_valido}':
            return httpx.Response(403, json={'detail': 'Invalid JWT token'})
        if r.url.path == DAG_RUNS and r.method == 'GET':
            return httpx.Response(200, json={'dag_runs': self.airflow_runs, 'total_entries': len(self.airflow_runs)})
        if r.url.path == DAG_RUNS and r.method == 'POST':
            if self.airflow_lanzar_codigo:
                return httpx.Response(self.airflow_lanzar_codigo, json={'detail': 'ya existe una ejecución igual'})
            cuerpo = json.loads(r.content)
            run = {**RUN, 'dag_run_id': 'manual__nueva', 'state': 'queued', 'conf': cuerpo['conf'],
                   'start_date': None, 'end_date': None}
            self.airflow_runs.insert(0, run)
            return httpx.Response(200, json=run)
        return httpx.Response(404, json={'detail': 'Not Found'})


# --- MongoDB falso -----------------------------------------------------------------------------------------

def _cumple(doc: dict, filtro: dict) -> bool:
    for campo, condicion in filtro.items():
        valor = doc.get(campo)
        if isinstance(condicion, dict):
            if '$gte' in condicion and (valor is None or valor < condicion['$gte']):
                return False
            if '$lt' in condicion and (valor is None or valor >= condicion['$lt']):
                return False
        elif valor != condicion:
            return False
    return True


class CursorFalso:
    def __init__(self, docs: list[dict], proyeccion: dict | None):
        self.docs, self.proyeccion = docs, proyeccion or {}

    def sort(self, campo: str, direccion: int = 1) -> CursorFalso:
        self.docs = sorted(self.docs, key=lambda d: d.get(campo), reverse=direccion == -1)
        return self

    def limit(self, n: int) -> CursorFalso:
        self.docs = self.docs[:n]
        return self

    def __iter__(self):
        incluidos = [k for k, v in self.proyeccion.items() if v]
        for d in self.docs:
            if incluidos:
                yield {k: v for k, v in d.items() if k in incluidos or (k == '_id' and self.proyeccion.get('_id', 1))}
            else:
                yield {k: v for k, v in d.items() if self.proyeccion.get(k, 1)}


class ColeccionFalsa:
    def __init__(self, docs: list[dict], rota: bool):
        self.docs, self.rota = docs, rota

    def find(self, filtro: dict | None = None, proyeccion: dict | None = None) -> CursorFalso:
        if self.rota:
            raise ServerSelectionTimeoutError('mongo caído')
        return CursorFalso([d for d in self.docs if _cumple(d, filtro or {})], proyeccion)


class MongoFalso:
    def __init__(self, decisiones: list[dict], cargas: list[dict], roto: bool = False):
        self.bases = {'auditoria': {'decisiones': ColeccionFalsa(decisiones, roto), 'cargas': ColeccionFalsa(cargas, roto)}}
        self.cerrado = False

    def __getitem__(self, nombre: str) -> dict:
        return self.bases[nombre]

    def close(self) -> None:
        self.cerrado = True


AHORA = datetime.now(timezone.utc).replace(microsecond=0)
INDIVIDUAL = 'la plataforma solo publica agregados de al menos 10 viajes'
DECISIONES = [
    {'_id': 1, 'instante': AHORA - timedelta(minutes=5), 'componente': 'acceso', 'cliente': 'chatbot',
     'consulta': {'individual': 'Dame el viaje de las 3:12'}, 'resultado': 'rechazada',
     'motivos': ['petición de datos individuales: Dame el viaje de las 3:12', INDIVIDUAL], 'alternativa': None,
     'version_reglas': 1},
    {'_id': 2, 'instante': AHORA - timedelta(hours=1), 'componente': 'acceso', 'cliente': 'frontend',
     'consulta': {'nivel': 'dia_barrio', 'desde': '2020-12-31T00:00:00', 'hasta': '2021-01-01T00:00:00'},
     'resultado': 'permitida', 'motivos': [], 'alternativa': None, 'version_reglas': 1,
     'filas_devueltas': 8, 'grupos_enmascarados': 0},
    {'_id': 3, 'instante': AHORA - timedelta(hours=2), 'componente': 'acceso', 'cliente': 'chatbot',
     'consulta': {'individual': '¿quién cogió el taxi?'}, 'resultado': 'rechazada',
     'motivos': ['petición de datos individuales: ¿quién cogió el taxi?', INDIVIDUAL], 'alternativa': None,
     'version_reglas': 1},
    {'_id': 4, 'instante': AHORA - timedelta(hours=30), 'componente': 'acceso', 'cliente': 'equipo',
     'consulta': {'nivel': 'hora_zona'}, 'resultado': 'enmascarada', 'motivos': ['3 grupos con menos de 10 viajes'],
     'alternativa': None, 'version_reglas': 1, 'filas_devueltas': 40, 'grupos_enmascarados': 3},
]
CARGAS = [
    {'_id': 'a', 'lote': 'muestra', 'entrada': 's3a://crudo/muestra/yellow_tripdata_2020_muestra.csv', 'origen': 'historico',
     'filas': 1000, 'validos': 991, 'rechazados': 9, 'motivos': {'fecha_fuera_de_rango': 3}, 'grupos_publicados': {'dia_barrio': 4},
     'grupos_suprimidos': {'dia_barrio': 2}, 'version_reglas': 1, 'instante': AHORA - timedelta(days=3)},
    {'_id': 'b', 'lote': 'anio-2020', 'entrada': 's3a://crudo/historico/2020.csv', 'origen': 'historico',
     'filas': 24648499, 'validos': 23684852, 'rechazados': 963647, 'motivos': {}, 'grupos_publicados': {'dia_barrio': 2813},
     'grupos_suprimidos': {'dia_barrio': 604}, 'grupos_complementarios': {'dia_barrio': 564}, 'version_reglas': 1,
     'instante': AHORA - timedelta(days=1)},
]


# --- fixtures ----------------------------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def sin_estado_entre_tests():
    def limpiar():
        ACCESO.limpiar_caches()
        RTR.limpiar_cache()
        AIR.olvidar_tokens()
        AUD.olvidar_clientes()
    limpiar()
    yield
    limpiar()


@pytest.fixture
def plataforma() -> Plataforma:
    return Plataforma()


@pytest.fixture
def cfg() -> C.Configuracion:
    return C.Configuracion.desde_entorno(ENTORNO, contenedor=False)


@pytest.fixture
def cliente(cfg, plataforma, tmp_path, monkeypatch):
    """La app con sesión iniciada y su `httpx.AsyncClient` compartido hablando con la `Plataforma` falsa."""
    original = httpx.AsyncClient
    monkeypatch.setattr(httpx, 'AsyncClient',
                        lambda **kw: original(transport=httpx.MockTransport(plataforma), **kw))
    with TestClient(A.crear_app(cfg, dist=tmp_path / 'sin-dist')) as c:
        c.cookies.set('pids_sesion', S.crear_valor_sesion(cfg.frontend_secreto))
        yield c


@pytest.fixture
def mongo(monkeypatch) -> MongoFalso:
    falso = MongoFalso(DECISIONES, CARGAS)
    monkeypatch.setattr(AUD, 'abrir_cliente', lambda uri: falso)
    return falso


def con_datos_de_diciembre(plataforma: Plataforma) -> None:
    plataforma.filas[('historico', 'dia_barrio')] = [
        dia('2020-12-30', 'Manhattan', 100), dia('2020-12-30', 'Queens', 50),
        dia('2020-12-31', 'Manhattan', 200), dia('2020-12-31', 'Queens', 30), dia('2020-12-31', 'Bronx', 5, suprimido=True),
    ]


def prometheus_sano(plataforma: Plataforma) -> None:
    def up(job, instancia, valor):
        return muestra({'__name__': 'up', 'job': job, 'instance': instancia}, valor)
    plataforma.prometheus = {
        PROM.CONSULTA_UP: [up('acceso', 'acceso:8000', 1), up('captura', 'captura:8000', 1), up('redpanda', 'redpanda:9644', 0),
                           up('spark-workers', 'spark-worker-1:8081', 1), up('spark-workers', 'spark-worker-2:8081', 0),
                           up('prometheus', 'localhost:9090', 1), up('grafana', 'grafana:3000', 1)],
        PROM.CONSULTA_FRESCURA: [muestra({'fuente': 'tiempo_real'}, 1_600_000_000)],
        PROM.CONSULTA_24H: [muestra({'resultado': 'enmascarada'}, 21893.59), muestra({'resultado': 'permitida'}, 9621.91),
                            muestra({'resultado': 'rechazada'}, 766.07)],
    }


# --- consultas, catálogo y zonas ---------------------------------------------------------------------------

def test_sin_sesion_las_rutas_de_plataforma_dan_401(cliente):
    cliente.cookies.clear()
    for ruta in ('/api/catalogo', '/api/panel', '/api/tiempo-real', '/api/auditoria/resumen', '/api/operaciones/simulacion'):
        r = cliente.get(ruta)
        assert r.status_code == 401 and r.json() == {'detail': 'Sesión no iniciada'}, ruta


def test_consulta_permitida_o_enmascarada_pasa_tal_cual_con_la_clave_del_portal(cliente, plataforma):
    con_datos_de_diciembre(plataforma)
    r = cliente.post('/api/consultas', json={'nivel': 'dia_barrio', 'desde': '2020-12-31T00:00:00', 'hasta': '2021-01-01T00:00:00'})
    assert r.status_code == 200
    cuerpo = r.json()
    assert cuerpo['resultado'] == 'enmascarada' and cuerpo['grupos_enmascarados'] == 1 and cuerpo['truncada'] is False
    assert [f['n_viajes'] for f in cuerpo['filas']] == [200, 30, 'oculto']
    assert cuerpo['filas'][2]['suprimido'] is True and 'nota' in cuerpo
    assert cuerpo['consulta']['fuente'] == 'historico' and cuerpo['consulta']['metricas'] == ['n_viajes']
    assert plataforma.claves_vistas == {'clave-equipo'}


def test_consulta_rechazada_devuelve_el_403_con_la_alternativa(cliente, plataforma):
    r = cliente.post('/api/consultas', json={'nivel': 'dia_barrio', 'desde': '2020-01-01T03:12:00', 'hasta': '2020-01-02T00:00:00'})
    assert r.status_code == 403
    decision = r.json()
    assert decision['resultado'] == 'rechazada'
    assert decision['motivos'] == ['la granularidad mínima es de un día completo']
    assert decision['alternativa']['desde'] == '2020-01-01T00:00:00' and decision['alternativa']['nivel'] == 'dia_barrio'
    assert len(plataforma.consultas) == 1                    # la decisión la tomó la API, no el BFF


def test_consulta_invalida_da_422_antes_de_llegar_a_la_api(cliente, plataforma):
    r = cliente.post('/api/consultas', json={'nivel': 'viajes_individuales', 'desde': '2020-01-01T00:00:00',
                                             'hasta': '2020-01-02T00:00:00'})
    assert r.status_code == 422 and r.json()['detail'][0]['loc'] == ['body', 'nivel']
    assert plataforma.consultas == []
    r = cliente.post('/api/consultas', json={'nivel': 'dia_barrio', 'desde': 'ayer', 'hasta': 'hoy'})
    assert r.status_code == 422


def test_api_de_acceso_caida_o_rota_es_un_503_con_detalle_y_nunca_un_500(cliente, plataforma):
    consulta = {'nivel': 'dia_barrio', 'desde': '2020-12-31T00:00:00', 'hasta': '2021-01-01T00:00:00'}
    plataforma.acceso_caida = True
    for llamada in (lambda: cliente.post('/api/consultas', json=consulta), lambda: cliente.get('/api/catalogo'),
                    lambda: cliente.get('/api/zonas?texto=jfk')):
        r = llamada()
        assert r.status_code == 503 and r.json()['detail'].startswith('La API de acceso no está disponible')
    plataforma.acceso_caida = False
    plataforma.acceso_codigo = 500
    r = cliente.post('/api/consultas', json=consulta)
    assert r.status_code == 503 and 'HTTP 500' in r.json()['detail']


def test_el_401_de_la_api_no_se_reenvia_como_401_del_portal():
    error = ACCESO.ClienteAcceso._inesperada(httpx.Response(401))
    assert isinstance(error, ACCESO.ServicioNoDisponible) and 'clave' in error.detalle and 'ACCESO_CLAVE' in error.detalle


def test_catalogo_y_zonas_se_cachean_diez_minutos(cliente, plataforma):
    assert cliente.get('/api/catalogo').json() == CATALOGO
    assert cliente.get('/api/catalogo').json()['k_minimo'] == 10
    assert cliente.get('/api/zonas?texto=jfk').json() == [ZONAS[0]]
    assert cliente.get('/api/zonas?texto=JFK').json() == [ZONAS[0]]          # misma clave de caché
    assert len(cliente.get('/api/zonas').json()) == 3
    assert plataforma.peticiones.count(('acceso', '/catalogo')) == 1
    assert plataforma.peticiones.count(('acceso', '/zonas')) == 2
    assert cliente.get('/api/zonas?texto=' + 'x' * 80).json() == []
    assert max(len(texto) for texto in plataforma.textos_zonas) == 50            # se recorta a 50, como hace la API


# --- panel -------------------------------------------------------------------------------------------------

def test_panel_suma_solo_los_grupos_visibles_y_busca_el_ultimo_dia_desde_diciembre(cliente, plataforma):
    con_datos_de_diciembre(plataforma)
    prometheus_sano(plataforma)
    r = cliente.get('/api/panel')
    assert r.status_code == 200
    panel = r.json()
    assert panel['ultimo_dia']['historico'] == {'dia': '2020-12-31T00:00:00', 'por_barrio': {'Manhattan': 200, 'Queens': 30},
                                                'total': 230, 'grupos_enmascarados': 1}
    assert panel['ultimo_dia']['tiempo_real'] is None
    assert panel['acceso_disponible'] is True and panel['prometheus_disponible'] is True
    assert panel['enlaces'] == C.ENLACES_POR_DEFECTO
    # histórico: un mes bastó; tiempo real: los doce meses de 2020, de diciembre a enero, siempre `dia_barrio`
    historico = [c for c in plataforma.consultas if c['fuente'] == 'historico']
    tiempo_real = [c for c in plataforma.consultas if c['fuente'] == 'tiempo_real']
    assert [c['desde'] for c in historico] == ['2020-12-01T00:00:00']
    assert [c['desde'][:7] for c in tiempo_real] == [f'2020-{m:02d}' for m in range(12, 0, -1)]
    assert {c['nivel'] for c in plataforma.consultas} == {'dia_barrio'}
    assert all(c['hasta'] <= '2021-01-01T00:00:00' for c in plataforma.consultas)


def test_panel_toma_de_prometheus_estado_frescura_y_consultas(cliente, plataforma):
    prometheus_sano(plataforma)
    panel = cliente.get('/api/panel').json()
    assert panel['consultas_24h'] == {'permitida': 9622, 'enmascarada': 21894, 'rechazada': 766}
    assert panel['frescura_tiempo_real'] == {'instante': '2020-09-13T12:26:40+00:00', 'segundos': 100}
    estados = {s['job']: s['estado'] for s in panel['servicios']}
    assert estados['acceso'] == 'ok' and estados['captura'] == 'ok' and estados['prometheus'] == 'ok'
    assert estados['redpanda'] == 'caido' and estados['spark-workers'] == 'caido'      # una instancia caída basta
    assert estados['s3'] == 'desconocido' and estados['grafana'] == 'ok'                # ausente / job no previsto
    assert [s['job'] for s in panel['servicios']][:2] == ['acceso', 'captura']
    acceso = next(s for s in panel['servicios'] if s['job'] == 'acceso')
    assert acceso['nombre'] == 'API de acceso' and acceso['enlace'] == 'http://localhost:8002/docs'
    assert 'enlace' not in next(s for s in panel['servicios'] if s['job'] == 'redpanda')


def test_panel_sin_prometheus_marca_no_disponible_y_comprueba_las_apis_directamente(cliente, plataforma):
    plataforma.prometheus = None
    panel = cliente.get('/api/panel').json()
    assert panel['prometheus_disponible'] is False and panel['consultas_24h'] is None
    assert panel['frescura_tiempo_real'] == {'instante': None, 'segundos': None}
    estados = {s['job']: s['estado'] for s in panel['servicios']}
    assert estados['acceso'] == 'ok' and estados['captura'] == 'ok' and estados['prometheus'] == 'caido'
    assert {estados[j] for j in ('redpanda', 's3', 'spark-master', 'spark-workers')} == {'desconocido'}
    assert ('acceso', '/salud') in plataforma.peticiones and ('captura', '/salud') in plataforma.peticiones


def test_panel_sin_api_de_acceso_responde_200_con_nulos(cliente, plataforma):
    plataforma.acceso_caida = True
    prometheus_sano(plataforma)
    r = cliente.get('/api/panel')
    assert r.status_code == 200
    panel = r.json()
    assert panel['ultimo_dia'] == {'historico': None, 'tiempo_real': None} and panel['acceso_disponible'] is False
    assert {s['job']: s['estado'] for s in panel['servicios']}['acceso'] == 'caido'


def test_panel_reutiliza_las_respuestas_de_la_api_un_rato(cliente, plataforma):
    con_datos_de_diciembre(plataforma)
    cliente.get('/api/panel')
    consultas = len(plataforma.consultas)
    assert cliente.get('/api/panel').json()['ultimo_dia']['historico']['total'] == 230
    assert len(plataforma.consultas) == consultas


def test_frescura_sin_datos_o_nan_es_nula():
    assert PROM.frescura([muestra(MUESTRA, 0)]) == {'instante': None, 'segundos': None}
    assert PROM.frescura([muestra(MUESTRA, 'NaN')]) == {'instante': None, 'segundos': None}
    assert PROM.frescura([]) == {'instante': None, 'segundos': None}
    assert PROM.frescura([muestra(MUESTRA, 1_600_000_000, evaluado=1_600_000_030.5)])['segundos'] == 30
    assert PROM.consultas_24h([]) == {'permitida': 0, 'enmascarada': 0, 'rechazada': 0}


# --- tiempo real -------------------------------------------------------------------------------------------

def con_tiempo_real(plataforma: Plataforma) -> None:
    plataforma.filas[('tiempo_real', 'dia_barrio')] = [dia('2020-12-30', 'Manhattan', 40), dia('2020-12-31', 'Manhattan', 60)]
    plataforma.filas[('tiempo_real', 'hora_zona')] = [
        hora('2020-12-30T22:00:00', 1, 15), hora('2020-12-30T22:00:00', 2, 11),
        hora('2020-12-30T23:00:00', 1, 14),
        hora('2020-12-31T05:00:00', 1, 20), hora('2020-12-31T05:00:00', 2, 4, suprimido=True), hora('2020-12-31T05:00:00', 3, 10),
        hora('2020-12-31T06:00:00', 1, 13),
        hora('2020-12-31T07:00:00', 4, 12), hora('2020-12-31T07:00:00', 5, 3, suprimido=True),
    ]


def test_tiempo_real_devuelve_las_ultimas_horas_con_datos_ordenadas_y_solo_suma_lo_visible(cliente, plataforma):
    con_tiempo_real(plataforma)
    prometheus_sano(plataforma)
    r = cliente.get('/api/tiempo-real?horas=4')
    assert r.status_code == 200
    tr = r.json()
    assert tr['ultimo_dia'] == '2020-12-31T00:00:00' and tr['acceso_disponible'] is True
    assert tr['frescura']['segundos'] == 100
    assert [h['hora'] for h in tr['por_hora']] == ['2020-12-30T23:00:00', '2020-12-31T05:00:00', '2020-12-31T06:00:00',
                                                   '2020-12-31T07:00:00']
    assert tr['por_hora'][1] == {'hora': '2020-12-31T05:00:00', 'n_viajes': 30, 'grupos': 3, 'grupos_enmascarados': 1}
    assert tr['por_hora'][3] == {'hora': '2020-12-31T07:00:00', 'n_viajes': 12, 'grupos': 2, 'grupos_enmascarados': 1}
    assert [f['n_viajes'] for f in tr['por_zona_ultima_hora']] == [12, 'oculto']    # tal cual las da la API
    assert tr['por_zona_ultima_hora'][1]['suprimido'] is True and tr['por_zona_ultima_hora'][1]['zona_origen'] == 5
    assert all(c['fuente'] == 'tiempo_real' for c in plataforma.consultas)


def test_tiempo_real_limita_las_horas_y_valida_el_parametro(cliente, plataforma):
    con_tiempo_real(plataforma)
    assert [h['hora'][11:13] for h in cliente.get('/api/tiempo-real?horas=2').json()['por_hora']] == ['06', '07']
    assert len(cliente.get('/api/tiempo-real').json()['por_hora']) == 5          # 6 por defecto; solo hay 5 con datos
    assert cliente.get('/api/tiempo-real?horas=0').status_code == 422
    assert cliente.get('/api/tiempo-real?horas=49').status_code == 422


def test_tiempo_real_pide_hora_a_hora_cuando_el_dia_entero_viene_truncado(cliente, plataforma):
    plataforma.filas[('tiempo_real', 'dia_barrio')] = [dia('2020-12-31', 'Manhattan', 5000)]
    plataforma.filas[('tiempo_real', 'hora_zona')] = [hora(f'2020-12-31T{h:02d}:00:00', z, 10 + h)
                                                      for h in range(24) for z in range(1, 26)]     # 600 > 500 filas
    tr = cliente.get('/api/tiempo-real?horas=3').json()
    assert [h['hora'][11:13] for h in tr['por_hora']] == ['21', '22', '23']
    assert tr['por_hora'][-1] == {'hora': '2020-12-31T23:00:00', 'n_viajes': 25 * 33, 'grupos': 25, 'grupos_enmascarados': 0}
    assert len(tr['por_zona_ultima_hora']) == 25
    horarias = [c for c in plataforma.consultas if c['nivel'] == 'hora_zona']
    assert horarias[0]['desde'] == '2020-12-31T00:00:00' and horarias[0]['hasta'] == '2021-01-01T00:00:00'   # el día entero
    assert [(c['desde'][11:13], c['hasta'][11:13]) for c in horarias[1:]] == [('23', '00'), ('22', '23'), ('21', '22')]


def test_tiempo_real_sin_datos_ni_api(cliente, plataforma):
    prometheus_sano(plataforma)
    tr = cliente.get('/api/tiempo-real').json()
    assert tr['ultimo_dia'] is None and tr['por_hora'] == [] and tr['por_zona_ultima_hora'] == []
    assert tr['acceso_disponible'] is True and tr['frescura']['segundos'] == 100
    RTR.limpiar_cache()
    ACCESO.limpiar_caches()                       # los meses vacíos también se recuerdan
    plataforma.acceso_caida = True
    plataforma.prometheus = None
    r = cliente.get('/api/tiempo-real')
    assert r.status_code == 200
    assert r.json()['acceso_disponible'] is False and r.json()['frescura'] == {'instante': None, 'segundos': None}


# --- lógica pura del cliente de acceso -----------------------------------------------------------------------

def test_trocear_respeta_el_maximo_de_31_dias():
    ventanas = ACCESO.trocear(datetime(2020, 1, 1), datetime(2020, 3, 15))
    assert [(a.isoformat(), b.isoformat()) for a, b in ventanas] == [
        ('2020-01-01T00:00:00', '2020-02-01T00:00:00'), ('2020-02-01T00:00:00', '2020-03-03T00:00:00'),
        ('2020-03-03T00:00:00', '2020-03-15T00:00:00')]
    assert ACCESO.trocear(datetime(2020, 1, 1), datetime(2020, 1, 1)) == []
    assert all((b - a).days <= 31 for a, b in ACCESO.meses_del_anio(2020)) and len(ACCESO.meses_del_anio(2020)) == 12


def test_resumenes_no_suman_lo_enmascarado():
    filas = [dia('2020-12-31', 'Manhattan', 200), {**dia('2020-12-31', 'Bronx', 'oculto'), 'suprimido': True},
             dia('2020-12-31', 'Manhattan', 5), {**dia('2020-12-31', 'Queens', 40), 'suprimido': True}]
    assert ACCESO.resumir_dia('2020-12-31T00:00:00', filas) == {
        'dia': '2020-12-31T00:00:00', 'por_barrio': {'Manhattan': 205}, 'total': 205, 'grupos_enmascarados': 2}
    assert ACCESO.sumar_visibles(filas) == (205, 2)
    assert ACCESO.resumir_hora('2020-12-31T23:00:00', filas) == {'hora': '2020-12-31T23:00:00', 'n_viajes': 205,
                                                               'grupos': 4, 'grupos_enmascarados': 2}


def test_cache_ttl_caduca():
    cache = ACCESO.CacheTTL(0.05)
    assert cache.obtener('x') is ACCESO.SIN_VALOR
    assert cache.guardar('x', 1) == 1 and cache.obtener('x') == 1
    time.sleep(0.06)
    assert cache.obtener('x') is ACCESO.SIN_VALOR
    cache.guardar('y', 2, segundos=10)
    cache.limpiar()
    assert cache.obtener('y') is ACCESO.SIN_VALOR


# --- auditoría ---------------------------------------------------------------------------------------------

def test_resumen_de_auditoria_agrupa_los_motivos_por_tipo(cliente, mongo):
    r = cliente.get('/api/auditoria/resumen')
    assert r.status_code == 200
    resumen = r.json()
    assert resumen['disponible'] is True and resumen['total'] == 3
    assert resumen['resultados'] == {'rechazada': 2, 'permitida': 1}
    assert resumen['clientes'] == {'chatbot': 2, 'frontend': 1}
    assert resumen['motivos'] == [{'motivo': 'petición de datos individuales', 'cantidad': 2},
                                  {'motivo': INDIVIDUAL, 'cantidad': 2}]
    desde, hasta = datetime.fromisoformat(resumen['desde']), datetime.fromisoformat(resumen['hasta'])
    assert hasta - desde == timedelta(hours=24) and hasta.tzinfo is not None
    assert cliente.get('/api/auditoria/resumen?horas=48').json()['total'] == 4
    assert cliente.get('/api/auditoria/resumen?horas=0').status_code == 422


def test_decisiones_filtradas_ordenadas_y_sin_id(cliente, mongo):
    decisiones = cliente.get('/api/auditoria/decisiones').json()
    assert [d['cliente'] for d in decisiones] == ['chatbot', 'frontend', 'chatbot']          # instante descendente
    assert all('_id' not in d for d in decisiones)
    assert decisiones[0]['instante'] == (AHORA - timedelta(minutes=5)).isoformat()
    assert decisiones[1]['filas_devueltas'] == 8 and decisiones[1]['consulta']['nivel'] == 'dia_barrio'
    rechazadas = cliente.get('/api/auditoria/decisiones?resultado=rechazada&cliente=&limite=1').json()
    assert len(rechazadas) == 1 and rechazadas[0]['motivos'][1] == INDIVIDUAL
    assert [d['cliente'] for d in cliente.get('/api/auditoria/decisiones?cliente=frontend').json()] == ['frontend']
    assert len(cliente.get('/api/auditoria/decisiones?horas=48').json()) == 4
    assert cliente.get('/api/auditoria/decisiones?limite=501').status_code == 422
    assert cliente.get('/api/auditoria/decisiones?limite=0').status_code == 422


def test_cargas_mas_reciente_primero_y_sin_id(cliente, mongo):
    cargas = cliente.get('/api/auditoria/cargas').json()
    assert [c['lote'] for c in cargas] == ['anio-2020', 'muestra']
    assert all('_id' not in c for c in cargas) and cargas[0]['grupos_complementarios'] == {'dia_barrio': 564}
    assert cargas[0]['instante'] == (AHORA - timedelta(days=1)).isoformat()


def test_mongo_caido_da_200_con_disponible_false_o_listas_vacias(cliente, monkeypatch):
    monkeypatch.setattr(AUD, 'abrir_cliente', lambda uri: MongoFalso([], [], roto=True))
    resumen = cliente.get('/api/auditoria/resumen').json()
    assert resumen['disponible'] is False and resumen['total'] == 0 and resumen['motivos'] == []
    assert cliente.get('/api/auditoria/decisiones').json() == []
    assert cliente.get('/api/auditoria/cargas').json() == []


def test_el_cliente_de_mongo_se_abre_una_vez_por_uri(monkeypatch):
    abiertos = []
    monkeypatch.setattr(AUD, 'abrir_cliente', lambda uri: abiertos.append(uri) or MongoFalso([], []))
    AUD.cliente_mongo('mongodb://a')
    AUD.cliente_mongo('mongodb://a')
    AUD.cliente_mongo('mongodb://b')
    assert abiertos == ['mongodb://a', 'mongodb://b']
    AUD.olvidar_clientes()
    assert AUD._clientes == {}


def test_logica_pura_del_resumen():
    assert AUD.tipo_de_motivo('petición de datos individuales: ¿quién cogió el taxi a las 3:12?') == 'petición de datos individuales'
    assert AUD.tipo_de_motivo('la ventana temporal está vacía') == 'la ventana temporal está vacía'
    resumen = AUD.resumir(DECISIONES)
    assert resumen['total'] == 4 and resumen['resultados']['rechazada'] == 2 and resumen['clientes']['chatbot'] == 2
    assert resumen['motivos']['petición de datos individuales'] == 2 and '3 grupos' not in str(resumen['motivos'])
    assert AUD.a_json({'_id': 1, 'instante': datetime(2026, 1, 1), 'lista': [datetime(2026, 1, 2, tzinfo=timezone.utc)]}) == {
        'instante': '2026-01-01T00:00:00+00:00', 'lista': ['2026-01-02T00:00:00+00:00']}


# --- operaciones: Airflow ----------------------------------------------------------------------------------

def test_ejecuciones_de_airflow_con_bearer_y_forma_del_contrato(cliente, plataforma):
    r = cliente.get('/api/operaciones/airflow/ejecuciones')
    assert r.status_code == 200
    assert r.json() == [{'dag_run_id': RUN['dag_run_id'], 'estado': 'success', 'conf': {'mes': '2020-01', 'muestra': True},
                         'inicio': RUN['start_date'], 'fin': RUN['end_date']}]
    assert plataforma.peticiones.count(('airflow', '/auth/token')) == 1
    cliente.get('/api/operaciones/airflow/ejecuciones')
    assert plataforma.peticiones.count(('airflow', '/auth/token')) == 1          # el token se reutiliza


def test_airflow_renueva_el_token_cuando_lo_rechaza(cliente, plataforma):
    plataforma.airflow_tokens = ['jwt-1', 'jwt-2']
    plataforma.airflow_valido = 'jwt-2'
    assert len(cliente.get('/api/operaciones/airflow/ejecuciones').json()) == 1
    assert plataforma.peticiones.count(('airflow', '/auth/token')) == 2
    assert plataforma.peticiones.count(('airflow', DAG_RUNS)) == 2


def test_lanzar_carga_valida_el_mes_y_manda_conf_con_bearer(cliente, plataforma):
    for mes in ('2020-13', '2020-1', '2021-01', '2020-00', 'enero'):
        assert cliente.post('/api/operaciones/airflow/cargas', json={'mes': mes}).status_code == 422, mes
    assert plataforma.peticiones == []
    r = cliente.post('/api/operaciones/airflow/cargas', json={'mes': '2020-03', 'muestra': True})
    assert r.status_code == 202
    assert r.json() == {'dag_run_id': 'manual__nueva', 'estado': 'queued', 'conf': {'mes': '2020-03', 'muestra': True},
                        'inicio': None, 'fin': None}
    assert plataforma.airflow_runs[0]['conf'] == {'mes': '2020-03', 'muestra': True}
    assert cliente.post('/api/operaciones/airflow/cargas', json={'mes': '2020-12'}).json()['conf'] == {'mes': '2020-12', 'muestra': False}


async def test_el_cliente_de_airflow_manda_logical_date_nulo_y_el_bearer(plataforma):
    visto = {}

    def espia(r: httpx.Request) -> httpx.Response:
        if r.url.path == DAG_RUNS:
            visto['cabecera'] = r.headers.get('Authorization')
            visto['cuerpo'] = json.loads(r.content)
        return plataforma(r)

    async with httpx.AsyncClient(transport=httpx.MockTransport(espia)) as http:
        creada = await AIR.ClienteAirflow(http, 'http://127.0.0.1:8085', 'admin', 'af').lanzar('2020-05', False)
        assert creada['estado'] == 'queued'
        assert visto['cabecera'] == 'Bearer jwt-1'
        assert visto['cuerpo'] == {'logical_date': None, 'conf': {'mes': '2020-05', 'muestra': False}}


def test_airflow_caido_o_que_rechaza_no_es_un_500(cliente, plataforma):
    plataforma.airflow_lanzar_codigo = 409
    r = cliente.post('/api/operaciones/airflow/cargas', json={'mes': '2020-01'})
    assert r.status_code == 409 and 'ya existe' in r.json()['detail']
    plataforma.airflow_caido = True
    for r in (cliente.get('/api/operaciones/airflow/ejecuciones'),
              cliente.post('/api/operaciones/airflow/cargas', json={'mes': '2020-01'})):
        assert r.status_code == 503 and r.json()['detail'].startswith('Airflow no está disponible')


async def test_credenciales_malas_de_airflow_no_se_registran_ni_rompen(plataforma):
    async with httpx.AsyncClient(transport=httpx.MockTransport(plataforma)) as http:
        with pytest.raises(ACCESO.ServicioNoDisponible) as error:
            await AIR.ClienteAirflow(http, 'http://127.0.0.1:8085', 'admin', 'mala').ejecuciones()
    assert 'credenciales' in str(error.value) and 'mala' not in str(error.value)


# --- operaciones: simulador --------------------------------------------------------------------------------

FORMATO_TLC = '%m/%d/%Y %I:%M:%S %p'


def csv_muestra(carpeta: Path, nombre: str = 'viajes.csv', n: int = 250, con_fecha_rota: bool = True) -> Path:
    """`n` viajes del 1 de enero de 2020 en orden barajado (y uno sin fecha, que debe ir al final)."""
    carpeta.mkdir(parents=True, exist_ok=True)
    filas = [{'VendorID': str(i), 'tpep_pickup_datetime': (datetime(2020, 1, 1) + timedelta(seconds=37 * i)).strftime(FORMATO_TLC),
              'PULocationID': '132', 'trip_distance': '1.5' if i % 2 else ''} for i in range(n)]
    random.Random(7).shuffle(filas)
    if con_fecha_rota:
        filas.insert(3, {'VendorID': 'rota', 'tpep_pickup_datetime': '', 'PULocationID': '1', 'trip_distance': '2'})
    ruta = carpeta / nombre
    with ruta.open('w', newline='', encoding='utf-8') as f:
        escritor = csv.DictWriter(f, fieldnames=list(filas[0]))
        escritor.writeheader()
        escritor.writerows(filas)
    return ruta


@pytest.fixture
def simulador(tmp_path, monkeypatch) -> SIM.Simulador:
    carpeta = tmp_path / 'muestra'
    csv_muestra(carpeta)
    (carpeta / 'notas.txt').write_text('no es un csv', encoding='utf-8')
    (tmp_path / 'fuera.csv').write_text('VendorID,tpep_pickup_datetime\n1,01/01/2020 12:00:00 AM\n', encoding='utf-8')
    nuevo = SIM.Simulador(carpeta=carpeta)
    monkeypatch.setattr(SIM, 'SIMULADOR', nuevo)
    return nuevo


def esperar_fin(cliente, segundos: float = 5.0) -> dict:
    limite = time.monotonic() + segundos
    while time.monotonic() < limite:
        estado = cliente.get('/api/operaciones/simulacion').json()
        if not estado['activa']:
            return estado
        time.sleep(0.02)
    raise AssertionError('la simulación no terminó a tiempo')


def test_leer_viajes_ordena_por_recogida_y_manda_lo_ilegible_al_final(tmp_path):
    ruta = csv_muestra(tmp_path, n=20)
    viajes = SIM.leer_viajes(ruta)
    assert [v['VendorID'] for v in viajes] == [str(i) for i in range(20)] + ['rota']
    assert viajes[1]['trip_distance'] == '1.5' and viajes[0]['trip_distance'] is None      # texto tal cual; vacío -> null
    assert [v['VendorID'] for v in SIM.leer_viajes(ruta, maximo=3)] == ['0', '1', '2']
    assert SIM.fecha_recogida('2020 Jan 01 12:28:15 AM') == datetime(2020, 1, 1, 0, 28, 15)
    assert SIM.fecha_recogida('01/01/2020 12:28:15 AM') == datetime(2020, 1, 1, 0, 28, 15)
    assert SIM.fecha_recogida('ayer') == SIM.FECHA_MAXIMA and SIM.fecha_recogida(None) == SIM.FECHA_MAXIMA
    assert [len(lote) for lote in SIM.lotes(viajes, 8)] == [8, 8, 5]


def test_la_muestra_real_del_repositorio_se_lee_ordenada():
    viajes = SIM.leer_viajes(SIM.CARPETA_MUESTRA / 'yellow_tripdata_2020_muestra.csv')
    fechas = [SIM.fecha_recogida(v['tpep_pickup_datetime']) for v in viajes]
    assert len(viajes) == 999 and fechas == sorted(fechas)            # 1000 líneas con la cabecera
    assert set(SIM.SIMULADOR.ficheros()) >= {'yellow_tripdata_2020_muestra.csv', 'exportacion_formato_europeo.csv'}


def test_nombre_de_lote_con_fecha_y_como_mucho_100_caracteres():
    assert SIM.nombre_lote('yellow_tripdata_2020_muestra.csv', datetime(2026, 9, 21, 18, 30, 5)) == \
        'portal-yellow_tripdata_2020_muestra-20260921183005'
    largo = SIM.nombre_lote('x' * 200 + '.csv', datetime(2026, 9, 21, 18, 30, 5))
    assert len(largo) == 100 and largo.endswith('-20260921183005') and largo.startswith('portal-xxx')
    assert SIM.espera_para_ritmo(100, 50, 0.5) == 1.5 and SIM.espera_para_ritmo(100, 50, 3) == 0


def test_solo_se_admiten_ficheros_de_data_muestra(cliente, simulador, tmp_path):
    assert cliente.get('/api/operaciones/simulacion/ficheros').json() == ['viajes.csv']
    for fichero in ('../fuera.csv', str(tmp_path / 'fuera.csv'), 'no_existe.csv', 'notas.txt', '.viajes.csv', 'muestra/viajes.csv'):
        r = cliente.post('/api/operaciones/simulacion', json={'fichero': fichero})
        assert r.status_code == 400, fichero
    assert cliente.post('/api/operaciones/simulacion', json={'fichero': ''}).status_code == 422
    assert cliente.post('/api/operaciones/simulacion', json={'fichero': 'viajes.csv', 'ritmo': 0}).status_code == 422
    assert cliente.get('/api/operaciones/simulacion').json()['activa'] is False
    assert plataforma_sin_lotes(cliente)


def plataforma_sin_lotes(cliente) -> bool:
    return cliente.get('/api/operaciones/simulacion').json()['enviados'] == 0


def test_simulacion_ordena_por_fecha_y_envia_lotes_de_100_con_el_lote_correcto(cliente, plataforma, simulador):
    r = cliente.post('/api/operaciones/simulacion', json={'fichero': 'viajes.csv', 'ritmo': 5000})
    assert r.status_code == 202
    inicial = r.json()
    assert inicial['fichero'] == 'viajes.csv' and inicial['total'] == 251 and inicial['ritmo'] == 5000
    assert re.fullmatch(r'portal-viajes-\d{14}', inicial['lote']) and inicial['inicio'] and inicial['error'] is None
    final = esperar_fin(cliente)
    assert final['enviados'] == 251 and final['total'] == 251 and final['error'] is None and final['fin']
    assert [len(lote['viajes']) for lote in plataforma.captura_lotes] == [100, 100, 51]
    assert {lote['lote'] for lote in plataforma.captura_lotes} == {inicial['lote']}
    enviados = [v for lote in plataforma.captura_lotes for v in lote['viajes']]
    assert [v['VendorID'] for v in enviados] == [str(i) for i in range(250)] + ['rota']
    assert enviados[0] == {'VendorID': '0', 'tpep_pickup_datetime': '01/01/2020 12:00:00 AM', 'PULocationID': '132',
                           'trip_distance': None}                                          # texto tal cual
    assert all(ruta == '/viajes' for servicio, ruta in plataforma.peticiones if servicio == 'captura')


def test_simulacion_respeta_maximo_y_la_clave_de_captura(cliente, plataforma, simulador):
    plataforma.captura_codigo = 401                      # la API rechaza la clave: la simulación termina con error
    r = cliente.post('/api/operaciones/simulacion', json={'fichero': 'viajes.csv', 'ritmo': 5000, 'maximo': 150})
    assert r.status_code == 202 and r.json()['total'] == 150
    final = esperar_fin(cliente)
    assert final['enviados'] == 0 and 'HTTP 401' in final['error'] and final['activa'] is False
    plataforma.captura_codigo = 202
    plataforma.captura_lotes.clear()
    cliente.post('/api/operaciones/simulacion', json={'fichero': 'viajes.csv', 'ritmo': 5000, 'maximo': 150})
    assert esperar_fin(cliente)['enviados'] == 150
    assert [len(lote['viajes']) for lote in plataforma.captura_lotes] == [100, 50]


def test_una_sola_simulacion_activa_y_delete_la_para(cliente, plataforma, simulador):
    r = cliente.post('/api/operaciones/simulacion', json={'fichero': 'viajes.csv', 'ritmo': 1})
    assert r.status_code == 202
    limite = time.monotonic() + 5
    while cliente.get('/api/operaciones/simulacion').json()['enviados'] < 100 and time.monotonic() < limite:
        time.sleep(0.02)
    estado = cliente.get('/api/operaciones/simulacion').json()
    assert estado['activa'] is True and estado['enviados'] == 100 and estado['fin'] is None   # a 1 viaje/s toca esperar
    r = cliente.post('/api/operaciones/simulacion', json={'fichero': 'viajes.csv'})
    assert r.status_code == 409 and 'simulación en marcha' in r.json()['detail']
    parada = cliente.delete('/api/operaciones/simulacion').json()
    assert parada['activa'] is False and parada['enviados'] == 100 and parada['error'] is None and parada['fin']
    assert cliente.get('/api/operaciones/simulacion').json()['activa'] is False
    assert len(plataforma.captura_lotes) == 1
    assert cliente.delete('/api/operaciones/simulacion').status_code == 200                 # parar sin nada activo no falla
    assert cliente.post('/api/operaciones/simulacion', json={'fichero': 'viajes.csv', 'ritmo': 5000}).status_code == 202
    assert esperar_fin(cliente)['enviados'] == 251


# --- captura en directo (botón «Capturar datos» del grafo) ----------------------------------------------------

def dia_directo(carpeta: Path, dia: str, recogidas: list[str]) -> None:
    carpeta.mkdir(parents=True, exist_ok=True)
    with gzip.open(carpeta / f'{dia}.csv.gz', 'wt', newline='', encoding='utf-8') as f:
        escritor = csv.writer(f)
        escritor.writerow(['VendorID', 'tpep_pickup_datetime', 'PULocationID'])
        for i, texto in enumerate(recogidas):
            escritor.writerow([i, texto, 132])


@pytest.fixture
def captura(tmp_path, monkeypatch) -> SIM.Simulador:
    """Dos días preparados: el 1 de diciembre a las 00:00-00:04 y a las 06:00-06:02; el 2, a las 00:00."""
    carpeta = tmp_path / 'directo'
    dia_directo(carpeta, '2020-12-01', [f'12/01/2020 12:0{m}:00 AM' for m in range(5)]
                + [f'12/01/2020 06:0{m}:00 AM' for m in range(3)])
    dia_directo(carpeta, '2020-12-02', ['12/02/2020 12:00:00 AM'])
    nuevo = SIM.Simulador(carpeta=tmp_path / 'muestra', carpeta_directo=carpeta)
    csv_muestra(tmp_path / 'muestra')
    monkeypatch.setattr(SIM, 'SIMULADOR', nuevo)
    return nuevo


def test_captura_informa_de_lo_preparado(cliente, captura, tmp_path):
    info = cliente.get('/api/operaciones/captura').json()
    assert info['disponible'] is True and (info['primer_dia'], info['ultimo_dia']) == ('2020-12-01', '2020-12-02')
    assert info['reloj'] is None and info['velocidad_maxima'] == DIRECTO.VELOCIDAD_MAXIMA
    captura.carpeta_directo = tmp_path / 'vacia'
    assert cliente.get('/api/operaciones/captura').json()['disponible'] is False
    r = cliente.post('/api/operaciones/captura', json={})
    assert r.status_code == 409 and 'captura-preparar' in r.json()['detail']


def test_captura_sigue_tras_la_ultima_hora_publicada_y_comparte_estado_con_la_simulacion(cliente, plataforma, captura):
    plataforma.filas[('tiempo_real', 'dia_barrio')] = [dia('2020-12-01', 'Manhattan', 40)]
    plataforma.filas[('tiempo_real', 'hora_zona')] = [hora('2020-12-01T00:00:00', 132, 40)]
    r = cliente.post('/api/operaciones/captura', json={'velocidad': 600})
    assert r.status_code == 202
    inicial = r.json()
    assert inicial['modo'] == 'directo' and inicial['activa'] is True and inicial['velocidad'] == 600
    assert inicial['reloj'] == '2020-12-01T01:00:00'                    # la hora siguiente a la última publicada
    assert re.fullmatch(r'directo-\d{14}', inicial['lote']) and inicial['total'] == 0
    # la simulación de ficheros ve la misma: una sola a la vez
    assert cliente.get('/api/operaciones/simulacion').json()['modo'] == 'directo'
    r = cliente.post('/api/operaciones/simulacion', json={'fichero': 'viajes.csv'})
    assert r.status_code == 409
    # a ×600, las 06:00 llegan en unos 30 s reales: se para antes y quedan sin enviar
    parada = cliente.delete('/api/operaciones/captura').json()
    assert parada['activa'] is False and parada['enviados'] == 0 and parada['fin']
    assert plataforma.captura_lotes == []
    assert any(c['fuente'] == 'tiempo_real' for c in plataforma.consultas)   # lo preguntó a la API de acceso


def test_captura_envia_en_orden_y_no_vuelve_atras(cliente, plataforma, captura):
    r = cliente.post('/api/operaciones/captura', json={'velocidad': 600, 'desde': '2020-12-01T05:59:00'})
    assert r.status_code == 202 and r.json()['reloj'] == '2020-12-01T05:59:00'
    limite = time.monotonic() + 5
    while cliente.get('/api/operaciones/simulacion').json()['enviados'] < 3 and time.monotonic() < limite:
        time.sleep(0.05)
    estado = cliente.delete('/api/operaciones/captura').json()
    assert estado['enviados'] == 3 and estado['error'] is None
    enviados = [v['tpep_pickup_datetime'] for lote in plataforma.captura_lotes for v in lote['viajes']]
    assert enviados == [f'12/01/2020 06:0{m}:00 AM' for m in range(3)]
    assert {lote['lote'] for lote in plataforma.captura_lotes} == {estado['lote']}
    # Spark ya ha publicado la hora de las 06:00: la siguiente sigue en el minuto donde se quedó esta
    plataforma.filas[('tiempo_real', 'dia_barrio')] = [dia('2020-12-01', 'Manhattan', 3)]
    plataforma.filas[('tiempo_real', 'hora_zona')] = [hora('2020-12-01T06:00:00', 132, 3)]
    siguiente = cliente.post('/api/operaciones/captura', json={'velocidad': 600}).json()
    assert siguiente['reloj'] >= estado['reloj'] > '2020-12-01T06:02:00'
    cliente.delete('/api/operaciones/captura')
    # con el tiempo real vacío (recién reiniciado) vuelve a empezar por el primer día
    plataforma.filas.clear()
    assert cliente.post('/api/operaciones/captura', json={'velocidad': 600}).json()['reloj'] == '2020-12-01T00:00:00'
    cliente.delete('/api/operaciones/captura')
