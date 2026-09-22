"""Cimientos del BFF del portal (parte 4): configuración host/contenedor, sesión por cookie firmada, rutas
públicas y protegidas y la SPA servida desde `dist`. Sin red."""
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from fastapi import APIRouter
from fastapi.testclient import TestClient

from parte4_frontend.bff import app as A
from parte4_frontend.bff import configuracion as C
from parte4_frontend.bff import estaticos as E
from parte4_frontend.bff import seguridad as S
from parte4_frontend.bff.rutas import auditoria, catalogo, chat, consultas, gestos, observabilidad, operaciones, panel, tiempo_real

ENTORNO_ENV = {
    'PUERTO_ACCESO': '8002', 'PUERTO_CAPTURA': '8001', 'PUERTO_PROMETHEUS': '9090', 'PUERTO_AIRFLOW': '8085',
    'PUERTO_MONGO': '27018', 'PUERTO_OLLAMA': '11435',
    'ACCESO_CLAVE_EQUIPO': 'clave-equipo', 'CAPTURA_CLAVE_SIMULADOR': 'clave-sim',
    'MONGO_AUDITOR_PASSWORD': 'p@ss/word', 'AIRFLOW_ADMIN_USER': 'admin', 'AIRFLOW_ADMIN_PASSWORD': 'af',
    'FRONTEND_CLAVE': 'portal', 'FRONTEND_SECRETO': 'secreto',
}
ENTORNO_COMPOSE = {
    'ACCESO_URL': 'http://acceso:8000', 'ACCESO_CLAVE': 'clave-frontend',
    'CAPTURA_URL': 'http://captura:8000', 'CAPTURA_CLAVE': 'clave-sim',
    'PROMETHEUS_URL': 'http://prometheus:9090', 'AIRFLOW_URL': 'http://airflow-apiserver:8080',
    'AIRFLOW_USUARIO': 'admin', 'AIRFLOW_CLAVE': 'af',
    'AUDITORIA_MONGO_URI': 'mongodb://pids_auditor:x@mongo:27017/?authSource=admin',
    'OLLAMA_URL': 'http://ollama:11434', 'OLLAMA_MODELO': 'llama3.2:3b',
    'ENLACES_GRAFANA': 'http://localhost:3300',
    'FRONTEND_CLAVE': 'portal', 'FRONTEND_SECRETO': 'secreto', 'PIDS_CONFIG_DIR': '/app/config',
}


# --- configuración ---------------------------------------------------------------------------------------

def test_en_el_host_deriva_las_url_de_los_puertos_publicados():
    cfg = C.Configuracion.desde_entorno(ENTORNO_ENV, contenedor=False)
    assert cfg.acceso_url == 'http://127.0.0.1:8002'
    assert cfg.captura_url == 'http://127.0.0.1:8001'
    assert cfg.prometheus_url == 'http://127.0.0.1:9090'
    assert cfg.airflow_url == 'http://127.0.0.1:8085'
    assert cfg.ollama_url == 'http://127.0.0.1:11435'
    assert cfg.auditoria_mongo_uri == 'mongodb://pids_auditor:p%40ss%2Fword@127.0.0.1:27018/?authSource=admin'
    assert cfg.acceso_clave == 'clave-equipo'          # sin ACCESO_CLAVE_FRONTEND se usa la del equipo
    assert cfg.captura_clave == 'clave-sim' and cfg.airflow_usuario == 'admin' and cfg.airflow_clave == 'af'
    assert cfg.ollama_modelo == 'llama3.1:8b'
    assert cfg.enlaces == C.ENLACES_POR_DEFECTO and not cfg.en_contenedor


def test_en_el_host_una_url_de_contenedor_se_sustituye_pero_otra_se_respeta():
    con_nombres = {**ENTORNO_ENV, 'ACCESO_URL': 'http://acceso:8000', 'PROMETHEUS_URL': 'http://mi-servidor:9090',
                   'AUDITORIA_MONGO_URI': 'mongodb://pids_auditor:x@mongo:27017/?authSource=admin',
                   'ACCESO_CLAVE_FRONTEND': 'clave-frontend'}
    cfg = C.Configuracion.desde_entorno(con_nombres, contenedor=False)
    assert cfg.acceso_url == 'http://127.0.0.1:8002'
    assert cfg.prometheus_url == 'http://mi-servidor:9090'
    assert cfg.auditoria_mongo_uri.endswith('@127.0.0.1:27018/?authSource=admin')
    assert cfg.acceso_clave == 'clave-frontend'         # ACCESO_CLAVE_FRONTEND manda sobre la del equipo


def test_en_el_contenedor_se_usa_lo_que_pone_compose():
    cfg = C.Configuracion.desde_entorno(ENTORNO_COMPOSE)          # detecta el contenedor por PIDS_CONFIG_DIR
    assert cfg.en_contenedor
    assert cfg.acceso_url == 'http://acceso:8000' and cfg.acceso_clave == 'clave-frontend'
    assert cfg.captura_url == 'http://captura:8000' and cfg.prometheus_url == 'http://prometheus:9090'
    assert cfg.airflow_url == 'http://airflow-apiserver:8080' and cfg.ollama_url == 'http://ollama:11434'
    assert cfg.auditoria_mongo_uri == 'mongodb://pids_auditor:x@mongo:27017/?authSource=admin'
    assert cfg.ollama_modelo == 'llama3.2:3b'
    assert cfg.enlaces['grafana'] == 'http://localhost:3300' and cfg.enlaces['airflow'] == 'http://localhost:8085'


def test_el_env_de_la_raiz_se_lee_y_el_entorno_del_proceso_manda(tmp_path, monkeypatch):
    env = tmp_path / '.env'
    env.write_text('# comentario\nFRONTEND_CLAVE=del-fichero\nPUERTO_ACCESO="8123"\n\nVACIA=\n', encoding='utf-8')
    monkeypatch.setenv('FRONTEND_CLAVE', 'del-proceso')
    monkeypatch.delenv('PUERTO_ACCESO', raising=False)
    cfg = C.entorno(env)
    assert cfg['FRONTEND_CLAVE'] == 'del-proceso' and cfg['PUERTO_ACCESO'] == '8123' and cfg['VACIA'] == ''
    assert C.leer_env(tmp_path / 'no-existe') == {}


def test_los_avisos_no_revelan_valores():
    cfg = C.Configuracion.desde_entorno({}, contenedor=False)
    avisos = cfg.avisos()
    assert len(avisos) == 3 and all('FRONTEND' in a or 'ACCESO' in a for a in avisos)
    assert C.Configuracion.desde_entorno(ENTORNO_ENV, contenedor=False).avisos() == []


def test_configuracion_cacheada_se_puede_sustituir(monkeypatch):
    monkeypatch.setenv('FRONTEND_CLAVE', 'otra')
    C.configuracion.cache_clear()
    assert C.configuracion().frontend_clave == 'otra'
    C.configuracion.cache_clear()


# --- sesión ----------------------------------------------------------------------------------------------

def test_cookie_firmada_y_caducidad():
    ahora = datetime(2026, 1, 1, tzinfo=timezone.utc)
    valor = S.crear_valor_sesion('secreto', ahora=ahora)
    assert S.sesion_valida(valor, 'secreto', ahora=ahora + timedelta(hours=11, minutes=59))
    assert not S.sesion_valida(valor, 'secreto', ahora=ahora + timedelta(hours=12, seconds=1))
    assert not S.sesion_valida(valor, 'otro-secreto', ahora=ahora)
    caducidad, firma = valor.split('.')
    assert not S.sesion_valida(f'{int(caducidad) + 999999}.{firma}', 'secreto', ahora=ahora)   # caducidad alterada
    assert not S.sesion_valida(None, 'secreto') and not S.sesion_valida('basura', 'secreto')
    assert not S.sesion_valida(valor, '', ahora=ahora)


def test_clave_del_portal_vacia_no_deja_entrar():
    assert S.clave_correcta('portal', 'portal')
    assert not S.clave_correcta('portal', 'otra') and not S.clave_correcta('', '') and not S.clave_correcta('x', '')


@pytest.fixture
def cfg():
    return C.Configuracion.desde_entorno(ENTORNO_ENV, contenedor=False)


@pytest.fixture
def cliente(cfg, tmp_path):
    with TestClient(A.crear_app(cfg, dist=tmp_path / 'sin-dist')) as c:
        yield c


def test_salud_sin_sesion(cliente):
    r = cliente.get('/api/salud')
    assert r.status_code == 200 and r.json() == {'estado': 'ok', 'spa_construida': False}


def test_login_incorrecto_da_401_sin_cookie(cliente, monkeypatch):
    monkeypatch.setattr('parte4_frontend.bff.rutas.sesion.RETARDO_FALLO', 0)
    r = cliente.post('/api/sesion', json={'clave': 'mala'})
    assert r.status_code == 401 and r.json() == {'detail': 'Clave incorrecta'}
    assert 'set-cookie' not in r.headers
    assert cliente.get('/api/sesion').json() == {'autenticado': False}
    assert cliente.post('/api/sesion', json={}).status_code == 422


def test_login_correcto_pone_cookie_httponly_y_cerrar_la_borra(cliente):
    r = cliente.post('/api/sesion', json={'clave': 'portal'})
    assert r.status_code == 204
    cookie = r.headers['set-cookie']
    assert cookie.startswith('pids_sesion=') and 'HttpOnly' in cookie and 'SameSite=lax' in cookie
    assert 'Max-Age=43200' in cookie and 'Path=/' in cookie
    assert cliente.get('/api/sesion').json() == {'autenticado': True}

    r = cliente.delete('/api/sesion')
    assert r.status_code == 204 and 'pids_sesion=' in r.headers['set-cookie']
    assert cliente.get('/api/sesion').json() == {'autenticado': False}


def test_una_cookie_manipulada_no_vale(cliente, cfg):
    valor = S.crear_valor_sesion(cfg.frontend_secreto)
    caducidad, firma = valor.split('.')
    cliente.cookies.set('pids_sesion', f'{int(caducidad) + 3600}.{firma}')
    assert cliente.get('/api/sesion').json() == {'autenticado': False}
    cliente.cookies.set('pids_sesion', S.crear_valor_sesion('otro-secreto'))
    assert cliente.get('/api/sesion').json() == {'autenticado': False}


# --- routers protegidos ------------------------------------------------------------------------------------

def test_los_nueve_routers_estan_incluidos_y_la_app_se_crea():
    modulos = (consultas, catalogo, panel, tiempo_real, auditoria, operaciones, chat, observabilidad, gestos)
    assert all(isinstance(m.router, APIRouter) for m in modulos)
    assert A.ROUTERS_PROTEGIDOS == tuple(m.router for m in modulos)
    app = A.crear_app(C.Configuracion.desde_entorno(ENTORNO_ENV, contenedor=False))
    assert {'/api/salud', '/api/sesion'} <= set(app.openapi()['paths'])
    # Cada router protegido está incluido con la dependencia de sesión (FastAPI guarda la inclusión sin aplanarla).
    incluidos = {id(r.original_router): r.include_context for r in app.routes if hasattr(r, 'original_router')}
    for router in A.ROUTERS_PROTEGIDOS:
        contexto = incluidos[id(router)]
        assert contexto.prefix == '/api'
        assert any(d.dependency is S.sesion_requerida for d in contexto.dependencies)
    for router in A.ROUTERS_PUBLICOS:
        assert not incluidos[id(router)].dependencies
    assert isinstance(A.app.state.configuracion, C.Configuracion)      # el `app` del módulo también se construye


def test_las_rutas_protegidas_exigen_la_cookie(cfg, tmp_path, monkeypatch):
    protegido = APIRouter()

    @protegido.get('/protegida')
    async def protegida() -> dict:
        return {'ok': True}

    monkeypatch.setattr(A, 'ROUTERS_PROTEGIDOS', A.ROUTERS_PROTEGIDOS + (protegido,))
    with TestClient(A.crear_app(cfg, dist=tmp_path)) as c:
        r = c.get('/api/protegida')
        assert r.status_code == 401 and r.json() == {'detail': 'Sesión no iniciada'}
        c.cookies.set('pids_sesion', S.crear_valor_sesion('otro-secreto'))
        assert c.get('/api/protegida').status_code == 401
        c.cookies.set('pids_sesion', S.crear_valor_sesion(cfg.frontend_secreto))
        assert c.get('/api/protegida').json() == {'ok': True}


def test_el_ciclo_de_vida_crea_y_cierra_el_cliente_http(cfg, tmp_path):
    app = A.crear_app(cfg, dist=tmp_path)
    assert app.state.http is None                                          # lo crea el ciclo de vida
    with TestClient(app):
        assert app.state.http is not None and not app.state.http.is_closed
    assert app.state.http.is_closed


# --- estáticos --------------------------------------------------------------------------------------------

@pytest.fixture
def dist(tmp_path) -> Path:
    d = tmp_path / 'dist'
    (d / 'assets').mkdir(parents=True)
    (d / 'index.html').write_text('<!doctype html><title>PIDS</title><div id="root"></div>', encoding='utf-8')
    (d / 'favicon.svg').write_text('<svg/>', encoding='utf-8')
    (d / 'assets' / 'index-abc123.js').write_text('console.log(1)', encoding='utf-8')
    return d


def test_sirve_la_spa_con_fallback_a_index(cfg, dist):
    with TestClient(A.crear_app(cfg, dist=dist)) as c:
        assert c.get('/api/salud').json()['spa_construida'] is True
        for ruta in ('/', '/explorador', '/privacidad/decisiones', '/acceso?desde=x'):
            r = c.get(ruta)
            assert r.status_code == 200 and 'id="root"' in r.text, ruta
            assert r.headers['content-type'].startswith('text/html') and r.headers['cache-control'] == 'no-cache'
        r = c.get('/assets/index-abc123.js')
        assert r.status_code == 200 and r.text == 'console.log(1)'
        assert r.headers['cache-control'] == 'public, max-age=31536000, immutable'
        assert c.get('/favicon.svg').text == '<svg/>'
        assert c.get('/assets/no-existe.js').status_code == 404


def test_la_spa_no_tapa_la_api_ni_deja_salir_de_dist(cfg, dist):
    (dist.parent / 'secreto.txt').write_text('CONTENIDO-FUERA-DE-DIST', encoding='utf-8')
    with TestClient(A.crear_app(cfg, dist=dist)) as c:
        r = c.get('/api/no-existe')
        assert r.status_code == 404 and r.json() == {'detail': 'Recurso no encontrado'}
        assert c.get('/api').status_code == 404
        for intento in ('/..%2Fsecreto.txt', '/%2e%2e/secreto.txt', '/assets/..%2F..%2Fsecreto.txt'):
            r = c.get(intento)
            assert 'CONTENIDO-FUERA-DE-DIST' not in r.text, intento
            assert r.status_code == 404 or 'id="root"' in r.text, intento
    assert E.fichero_de_dist(dist, '../secreto.txt') is None
    assert E.fichero_de_dist(dist, 'favicon.svg') == (dist / 'favicon.svg').resolve()
    assert E.fichero_de_dist(dist, '') is None and E.fichero_de_dist(dist, 'assets/') is None


def test_sin_dist_la_raiz_explica_como_construir_la_spa(cliente):
    r = cliente.get('/')
    assert r.status_code == 200
    assert 'npm run build' in r.json()['como_construirla']
    assert cliente.get('/explorador').status_code == 404
