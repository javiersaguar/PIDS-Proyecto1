"""Los servicios sin credencial no se publican en el anfitrión (T08, docs/seguridad.md)."""
import json
import subprocess
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]

SIN_PUBLICAR = (
    'redpanda', 'spark-master', 'spark-worker-1', 'spark-worker-2',
    'prometheus', 'ollama', 'qdrant', 'redpanda-consola',
)
CON_CREDENCIAL = (
    's3', 'mongo', 'captura', 'acceso', 'airflow-apiserver', 'grafana',
    'chatbot', 'chatbot-rag', 'frontend',
)


def test_compose_no_publica_servicios_sin_credencial():
    resultado = subprocess.run(
        ['docker', 'compose',
         '--profile', 'spark', '--profile', 'airflow', '--profile', 'observabilidad',
         '--profile', 'chatbot', '--profile', 'rag', '--profile', 'frontend',
         '--profile', 'herramientas', '--profile', 'simulador',
         'config', '--format', 'json'],
        cwd=RAIZ, capture_output=True, text=True, check=False)
    assert resultado.returncode == 0, resultado.stderr
    servicios = json.loads(resultado.stdout)['services']
    for nombre in SIN_PUBLICAR:
        assert not servicios[nombre].get('ports'), nombre
    for nombre in CON_CREDENCIAL:
        assert servicios[nombre].get('ports'), nombre
    publicados = json.dumps(servicios['spark-master'])
    assert '6066' not in publicados
