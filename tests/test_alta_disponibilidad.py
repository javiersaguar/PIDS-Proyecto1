"""Alta disponibilidad de la API de acceso (T09): dos réplicas iguales detrás de un proxy con el nombre de siempre.

La prueba en vivo (parar y tirar réplicas con carga) es scripts/probar_alta_disponibilidad.py; aquí se comprueba
la configuración que la hace posible.
"""
import json
import subprocess
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
REPLICAS = ('acceso-a', 'acceso-b')


@pytest.fixture(scope='module')
def servicios() -> dict:
    resultado = subprocess.run(['docker', 'compose', '--profile', 'chatbot', '--profile', 'frontend',
                                'config', '--format', 'json'],
                               cwd=RAIZ, capture_output=True, text=True, check=False)
    assert resultado.returncode == 0, resultado.stderr
    return json.loads(resultado.stdout)['services']


def test_las_dos_replicas_son_iguales_y_no_se_publican(servicios):
    a, b = (servicios[r] for r in REPLICAS)
    for campo in ('image', 'command', 'environment', 'networks', 'healthcheck'):
        assert a[campo] == b[campo], campo
    assert 'parte2_plataforma.acceso.app:app' in a['command']
    assert 'ACCESO_CLAVES' in a['environment']
    assert not a.get('ports') and not b.get('ports')


def test_el_proxy_conserva_el_nombre_y_el_puerto_de_la_api(servicios):
    proxy = servicios['acceso']
    assert proxy['image'].startswith('caddy:')
    assert [p['target'] for p in proxy['ports']] == [8000]
    assert all(p['host_ip'] == '127.0.0.1' for p in proxy['ports'])
    assert any(v['target'] == '/etc/caddy/Caddyfile' and v.get('read_only') for v in proxy['volumes'])
    assert set(proxy['networks']) == {'servicios'}          # no necesita la red de datos
    # arranca aunque una réplica no esté sana: Caddy la deja fuera del reparto
    assert {r: proxy['depends_on'][r]['condition'] for r in REPLICAS} == dict.fromkeys(REPLICAS, 'service_started')
    # los clientes siguen usando acceso:8000
    for cliente in ('chatbot', 'frontend'):
        assert servicios[cliente]['environment']['ACCESO_URL'] == 'http://acceso:8000'


def test_caddy_reparte_reintenta_y_comprueba_la_salud():
    caddyfile = (RAIZ / 'parte2_plataforma/acceso/Caddyfile').read_text(encoding='utf-8')
    assert 'reverse_proxy acceso-a:8000 acceso-b:8000' in caddyfile
    for directiva in ('lb_policy round_robin', 'lb_try_duration', 'health_uri /salud', 'X-Replica'):
        assert directiva in caddyfile, directiva


def test_prometheus_mide_cada_replica_por_separado():
    config = (RAIZ / 'parte2_plataforma/observabilidad/prometheus/prometheus.yml').read_text(encoding='utf-8')
    for replica in REPLICAS:
        assert f'"{replica}:8000"' in config
    assert '"acceso:8000"' not in config                     # el proxy alternaría entre dos contadores distintos


def test_las_metricas_repetidas_en_las_replicas_no_se_duplican():
    """publico_* lo publican las dos réplicas con el mismo valor: Grafana, las alertas y el portal usan max()."""
    cuadros = sorted((RAIZ / 'parte2_plataforma/observabilidad/grafana/dashboards').glob('*.json'))
    assert cuadros
    alertas = (RAIZ / 'parte2_plataforma/observabilidad/grafana/provisioning/alerting/reglas.json').read_text()
    expresiones = [e for ruta in cuadros for e in _exprs(json.loads(ruta.read_text(encoding='utf-8')))]
    expresiones += list(_exprs(json.loads(alertas)))
    for expr in expresiones:
        if 'publico_' in expr:
            assert 'max(' in expr or 'max by' in expr, expr
    from parte4_frontend.bff.servicios import prometheus
    assert prometheus.CONSULTA_FRESCURA.startswith('max(')


def _exprs(nodo):
    if isinstance(nodo, dict):
        for clave, valor in nodo.items():
            if clave == 'expr':
                yield valor
            else:
                yield from _exprs(valor)
    elif isinstance(nodo, list):
        for valor in nodo:
            yield from _exprs(valor)
