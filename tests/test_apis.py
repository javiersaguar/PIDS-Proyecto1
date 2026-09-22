"""APIs de captura y de acceso con dobles de Redpanda y MongoDB (sin servicios reales)."""
import asyncio
from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from parte2_plataforma.acceso import app as acceso
from parte2_plataforma.captura import app as captura


class ProductorFalso:
    def __init__(self):
        self.enviados = []

    async def send(self, topic, valor, key=None):
        self.enviados.append((topic, valor, key))
        futuro = asyncio.get_running_loop().create_future()
        futuro.set_result(None)
        return futuro


class RepoFalso:
    def __init__(self, filas):
        self.filas = filas
        self.auditoria = []
        self.consultas = []

    async def buscar(self, consulta, limite):
        self.consultas.append(consulta)
        return self.filas[:limite]

    async def zonas(self, texto):
        return [{'_id': 138, 'nombre': 'LaGuardia Airport', 'barrio': 'Queens'}]

    async def barrios(self):
        return ['Manhattan', 'Queens']

    async def ultimo_dia_por_barrio(self, fuente):
        return None, {}

    async def ultima_actualizacion_tiempo_real(self):
        return None

    async def inventario(self):
        return []

    async def auditar(self, decision):
        self.auditoria.append(decision)

    async def cerrar(self):
        pass


@pytest.fixture
def cliente_captura(monkeypatch):
    monkeypatch.setenv('CAPTURA_CLAVES', 'simulador=clave-sim,gestos=clave-ges')
    captura.app.state.productor = ProductorFalso()
    with TestClient(captura.app) as c:
        yield c, captura.app.state.productor
    captura.app.state.productor = None


@pytest.fixture
def cliente_acceso(monkeypatch):
    monkeypatch.setenv('ACCESO_CLAVES', 'chatbot=clave-bot')
    filas = [
        {'hora': datetime(2020, 1, 15, 8), 'zona_origen': 138, 'n_viajes': 40, 'importe_medio': 31.5, 'suprimido': False},
        {'hora': datetime(2020, 1, 15, 9), 'zona_origen': 138, 'n_viajes': None, 'importe_medio': None, 'suprimido': True},
    ]
    acceso.app.state.repo = RepoFalso(filas)
    with TestClient(acceso.app) as c:
        yield c, acceso.app.state.repo
    acceso.app.state.repo = None


CABECERA_BOT = {'X-API-Key': 'clave-bot'}
CONSULTA = {'nivel': 'hora_zona', 'desde': '2020-01-15T08:00:00', 'hasta': '2020-01-15T10:00:00',
            'metricas': ['n_viajes', 'importe_medio'], 'zona_origen': 138}


# --- captura ---------------------------------------------------------------------------------

def test_captura_exige_clave(cliente_captura):
    c, _ = cliente_captura
    assert c.post('/viajes', json={'viajes': [{'VendorID': 1}]}).status_code == 401
    assert c.post('/viajes', json={'viajes': [{'VendorID': 1}]}, headers={'X-API-Key': 'mala'}).status_code == 401


def test_captura_encola_viajes_con_procedencia(cliente_captura):
    c, productor = cliente_captura
    r = c.post('/viajes', json={'lote': 'l1', 'viajes': [{'VendorID': 1}, {'VendorID': 2}]},
               headers={'X-API-Key': 'clave-sim'})
    assert r.status_code == 202 and r.json() == {'aceptados': 2, 'lote': 'l1'}
    topic, valor, _ = productor.enviados[0]
    assert topic == 'viajes-crudos'
    assert valor['registro'] == {'VendorID': 1}
    assert valor['cliente'] == 'simulador' and valor['origen'] == 'tiempo_real'


def test_captura_limita_el_lote(cliente_captura):
    c, _ = cliente_captura
    r = c.post('/viajes', json={'viajes': [{}] * 1001}, headers={'X-API-Key': 'clave-sim'})
    assert r.status_code == 422


def test_captura_valida_gestos(cliente_captura):
    c, productor = cliente_captura
    cab = {'X-API-Key': 'clave-ges'}
    ok = c.post('/gestos', json={'gesto': 'thumbsup', 'confianza': 0.97, 'modelo': 'mlp', 'dispositivo': 'portatil'},
                headers=cab)
    assert ok.status_code == 202
    assert productor.enviados[-1][0] == 'gestos' and productor.enviados[-1][2] == b'portatil'
    assert c.post('/gestos', json={'gesto': 'saludo', 'confianza': 0.9, 'modelo': 'm', 'dispositivo': 'd'},
                  headers=cab).status_code == 422
    assert c.post('/gestos', json={'gesto': 'ok', 'confianza': 1.5, 'modelo': 'm', 'dispositivo': 'd'},
                  headers=cab).status_code == 422


# --- acceso ----------------------------------------------------------------------------------

def test_acceso_exige_clave(cliente_acceso):
    c, _ = cliente_acceso
    assert c.post('/consultas', json=CONSULTA).status_code == 401


def test_acceso_enmascara_y_audita(cliente_acceso):
    c, repo = cliente_acceso
    r = c.post('/consultas', json=CONSULTA, headers=CABECERA_BOT)
    assert r.status_code == 200
    cuerpo = r.json()
    assert cuerpo['resultado'] == 'enmascarada'
    assert cuerpo['grupos_enmascarados'] == 1
    assert cuerpo['filas'][1]['n_viajes'] == 'oculto'           # nunca «<10»: puede ser un complementario
    assert cuerpo['filas'][1]['importe_medio'] is None
    assert repo.auditoria[-1]['resultado'] == 'enmascarada'
    assert repo.auditoria[-1]['cliente'] == 'chatbot'


def test_acceso_rechaza_con_alternativa_y_no_consulta_la_base(cliente_acceso):
    c, repo = cliente_acceso
    peligrosa = {**CONSULTA, 'desde': '2020-01-15T03:12:00', 'hasta': '2020-01-15T03:13:00',
                 'campos_extra': ['recogida']}
    r = c.post('/consultas', json=peligrosa, headers=CABECERA_BOT)
    assert r.status_code == 403
    cuerpo = r.json()
    assert cuerpo['resultado'] == 'rechazada'
    assert cuerpo['alternativa']['desde'] == '2020-01-15T03:00:00'
    assert cuerpo['alternativa']['campos_extra'] == []
    assert repo.consultas == []
    assert repo.auditoria[-1]['resultado'] == 'rechazada'


@pytest.mark.parametrize('metodo, ruta, cuerpo', [
    ('post', '/consultas/individual', {'descripcion': 'el viaje de las 3:12 desde JFK'}),
    ('get', '/viajes/12345', None),
    ('get', '/viajes/por-matricula/5ABC123', None),
])
def test_acceso_individual_siempre_rechazado(cliente_acceso, metodo, ruta, cuerpo):
    c, repo = cliente_acceso
    r = getattr(c, metodo)(ruta, headers=CABECERA_BOT, **({'json': cuerpo} if cuerpo else {}))
    assert r.status_code == 403
    assert r.json()['resultado'] == 'rechazada'
    assert repo.auditoria[-1]['resultado'] == 'rechazada'


def test_acceso_catalogo(cliente_acceso):
    c, _ = cliente_acceso
    r = c.get('/catalogo', headers=CABECERA_BOT)
    assert r.status_code == 200
    assert r.json()['barrios'] == ['Manhattan', 'Queens']
    assert 'hora_zona' in r.json()['niveles']
