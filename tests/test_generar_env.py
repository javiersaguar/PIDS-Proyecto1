"""scripts/generar_env.py: relleno aleatorio, claves que se dejan vacías y --completar sobre un .env existente."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))

import generar_env as G  # noqa: E402

PLANTILLA = [
    '# --- S3 ---',
    'S3_ADMIN_ACCESS_KEY=',
    'MONGO_ROOT_USER=pids_admin',
    'MONGO_ROOT_PASSWORD=',
    '# --- Chatbot RAG ---',
    'LLM_BASE_URL=https://api.helmcode.com/v1',
    'LLM_API_KEY=',
    'ACCESO_CLAVE_CHATBOT_RAG=',
    'PUERTO_QDRANT=6333',
]


def test_generar_rellena_solo_los_vacios():
    lineas = G.generar(PLANTILLA)
    valores = G.variables(lineas)
    assert lineas[0] == '# --- S3 ---'
    assert valores['MONGO_ROOT_USER'] == 'pids_admin'
    assert valores['LLM_BASE_URL'] == 'https://api.helmcode.com/v1'
    assert len(valores['MONGO_ROOT_PASSWORD']) >= 24
    assert valores['S3_ADMIN_ACCESS_KEY'].isupper() and len(valores['S3_ADMIN_ACCESS_KEY']) == 20


def test_la_clave_del_proveedor_externo_se_deja_vacia():
    assert G.variables(G.generar(PLANTILLA))['LLM_API_KEY'] == ''
    assert G.valor_para('LLM_API_KEY') == ''


def test_completar_anade_solo_lo_que_falta():
    actual = ['# mi .env', 'S3_ADMIN_ACCESS_KEY=ABC', 'MONGO_ROOT_USER=pids_admin', 'MONGO_ROOT_PASSWORD=secreta', '']
    lineas, anadidas = G.completar(actual, PLANTILLA)
    assert anadidas == ['LLM_BASE_URL', 'LLM_API_KEY', 'ACCESO_CLAVE_CHATBOT_RAG', 'PUERTO_QDRANT']
    valores = G.variables(lineas)
    assert valores['MONGO_ROOT_PASSWORD'] == 'secreta'          # lo existente no se toca
    assert valores['S3_ADMIN_ACCESS_KEY'] == 'ABC'
    assert valores['LLM_API_KEY'] == ''
    assert len(valores['ACCESO_CLAVE_CHATBOT_RAG']) >= 24
    assert lineas[:4] == actual[:4]


def test_forzar_sustituye_las_claves_y_sin_el_no_toca_el_env(tmp_path, monkeypatch):
    (tmp_path / '.env.example').write_text('MONGO_ROOT_PASSWORD=\nAIRFLOW_FERNET_KEY=\n', encoding='utf-8')
    destino = tmp_path / '.env'
    destino.write_text('MONGO_ROOT_PASSWORD=vieja\nAIRFLOW_FERNET_KEY=vieja\n', encoding='utf-8')
    monkeypatch.setattr(G, 'RAIZ', tmp_path)
    monkeypatch.setattr(sys, 'argv', ['generar_env.py'])
    assert G.main() == 0
    assert destino.read_text(encoding='utf-8') == 'MONGO_ROOT_PASSWORD=vieja\nAIRFLOW_FERNET_KEY=vieja\n'
    monkeypatch.setattr(sys, 'argv', ['generar_env.py', '--forzar'])
    assert G.main() == 0
    valores = G.variables(destino.read_text(encoding='utf-8').splitlines())
    assert valores['MONGO_ROOT_PASSWORD'] != 'vieja' and len(valores['MONGO_ROOT_PASSWORD']) >= 24
    assert valores['AIRFLOW_FERNET_KEY'] != 'vieja'


def test_completar_sin_novedades_no_cambia_nada():
    completo = G.generar(PLANTILLA)
    assert G.completar(completo, PLANTILLA) == (completo, [])
