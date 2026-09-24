"""`scripts/localhost.py`: direcciones de todo lo que se abre en el navegador, sin imprimir ninguna clave."""
from __future__ import annotations

import http.server
import importlib.util
import sys
import threading
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location('localhost_pids', RAIZ / 'scripts' / 'localhost.py')
L = importlib.util.module_from_spec(_spec)
sys.modules['localhost_pids'] = L
_spec.loader.exec_module(L)


def test_solo_lee_los_puertos_del_env(tmp_path):
    env = tmp_path / '.env'
    env.write_text('PUERTO_GRAFANA=3300\nGRAFANA_ADMIN_PASSWORD=secreto\nPUERTO_MALO=abc\n# PUERTO_X=1\n', encoding='utf-8')
    assert L.leer_puertos(env) == {'PUERTO_GRAFANA': 3300}
    assert L.leer_puertos(tmp_path / 'no_existe') == {}


def test_el_env_manda_sobre_el_ejemplo(tmp_path):
    (tmp_path / '.env.example').write_text('PUERTO_CHATBOT_RAG=8011\nPUERTO_SPARK=8090\n', encoding='utf-8')
    (tmp_path / '.env').write_text('PUERTO_CHATBOT_RAG=8012\n', encoding='utf-8')
    assert L.puertos_del_proyecto(tmp_path) == {'PUERTO_CHATBOT_RAG': 8012, 'PUERTO_SPARK': 8090}


def test_los_puertos_por_defecto_coinciden_con_el_env_example():
    ejemplo = L.leer_puertos(RAIZ / '.env.example')
    for s in L.SERVICIOS:
        assert ejemplo.get(s.variable) == s.puerto, s.nombre


def test_la_tabla_no_imprime_valores_de_claves(tmp_path, monkeypatch):
    texto, _ = L.tabla({}, lambda _url: 'sí')
    assert 'FRONTEND_CLAVE' in texto                    # el nombre de la variable sí
    entorno = RAIZ / '.env'
    if entorno.is_file():                                # y ningún valor de .env que no sea un puerto
        for linea in entorno.read_text(encoding='utf-8').splitlines():
            clave, _, valor = linea.partition('=')
            if valor.strip() and len(valor.strip()) >= 12 and not clave.startswith('PUERTO_'):
                assert valor.strip() not in texto, clave


def test_grupos_y_lo_que_nunca_se_abre():
    texto, abiertas = L.tabla({'PUERTO_SPARK': 18090}, lambda url: 'no' if '18090' in url else 'sí')
    assert '| Spark | http://localhost:18090/ | no |' in texto
    assert 'http://localhost:18090/' not in abiertas and 'http://localhost:8020/' in abiertas
    assert 'Consola de Redpanda' in texto and 'Nunca se abren' in texto
    assert 'localhost:27018' in texto and 'http://localhost:27018' not in abiertas        # MongoDB no es web
    for nombre in ('Portal web', 'Grafana', 'Airflow', 'Chatbot (Ollama)', 'Chatbot RAG', 'Prometheus',
                   'Qdrant', 'SeaweedFS S3 (API)', 'SeaweedFS (estado)'):
        assert f'| {nombre} |' in texto


@pytest.fixture
def servidor():
    """Un servidor HTTP de prueba que responde 200 en / y 403 en /privado."""
    class Manejador(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(403 if self.path == '/privado' else 502 if self.path == '/proxy' else 200)
            self.end_headers()

        def log_message(self, *args):
            pass

    srv = http.server.HTTPServer(('127.0.0.1', 0), Manejador)
    hilo = threading.Thread(target=srv.serve_forever, daemon=True)
    hilo.start()
    yield f'http://127.0.0.1:{srv.server_address[1]}'
    srv.shutdown()


def test_responde_distingue_en_marcha_de_parado(servidor):
    assert L.responde(f'{servidor}/') == 'sí'
    assert L.responde(f'{servidor}/privado') == 'sí'          # pide credencial, pero está en marcha
    assert L.responde(f'{servidor}/proxy') == 'no (502)'      # el proxy de `make ver` sin el servicio detrás
    assert L.responde('http://127.0.0.1:1/', tiempo=0.5) == 'no'


def test_abrir_solo_lo_que_responde(monkeypatch, capsys):
    abiertas = []
    monkeypatch.setattr(L, 'abrir', abiertas.append)
    monkeypatch.setattr(L, 'responde', lambda url: 'sí' if ':8020' in url or ':3000' in url else 'no')
    monkeypatch.setattr(L, 'puertos_del_proyecto', lambda: {})
    assert L.main(['--abrir']) == 0
    assert abiertas == ['http://localhost:8020/', 'http://localhost:3000/']
    assert 'Abiertas 2 pestañas' in capsys.readouterr().out
