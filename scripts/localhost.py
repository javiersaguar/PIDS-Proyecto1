"""Todo lo que se puede abrir en el navegador, con su dirección en localhost y si responde ahora mismo.

    make localhost                    # la tabla
    make localhost ARGS=--abrir       # además abre en el navegador todo lo que responde
    make ver                          # abre un rato Prometheus, Spark, Qdrant y el estado de SeaweedFS

Los puertos salen de `.env` (solo se leen las variables `PUERTO_*`; ninguna clave se imprime) y, si no están,
de los valores por defecto de `.env.example`. Cada servicio lleva el nombre de la variable con su usuario o
clave, nunca el valor.

Hay tres grupos:
  - siempre:  lo que se publica en 127.0.0.1 porque pide credencial (docs/seguridad.md).
  - make ver: interfaces sin login, que solo se abren mientras está en marcha el proxy de solo lectura.
  - nunca:    lo que enseña viajes individuales (E3) o no es una web.
"""
from __future__ import annotations

import argparse
import os
import platform
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
TIEMPO_MAXIMO = 2.0


@dataclass(frozen=True)
class Servicio:
    nombre: str
    variable: str            # PUERTO_* de .env
    puerto: int              # el de .env.example
    ruta: str
    que_es: str
    como_se_entra: str
    grupo: str               # 'siempre' · 'ver' · 'no web'

    def url(self, puertos: dict[str, int]) -> str:
        return f'http://localhost:{puertos.get(self.variable, self.puerto)}{self.ruta}'


SERVICIOS = [
    Servicio('Portal web', 'PUERTO_FRONTEND', 8020, '/', 'Panel, explorador, asistente, tiempo real y operaciones',
             'contraseña FRONTEND_CLAVE', 'siempre'),
    Servicio('Grafana', 'PUERTO_GRAFANA', 3000, '/', 'Cuadros y alertas',
             'ver: sin clave · editar: admin / GRAFANA_ADMIN_PASSWORD', 'siempre'),
    Servicio('Airflow', 'PUERTO_AIRFLOW', 8085, '/', 'Cargas históricas (DAG)',
             'AIRFLOW_ADMIN_USER / AIRFLOW_ADMIN_PASSWORD', 'siempre'),
    Servicio('Chatbot (Ollama)', 'PUERTO_CHATBOT', 8010, '/', 'Chainlit con el LLM local',
             'CHATBOT_USUARIO / CHATBOT_CLAVE', 'siempre'),
    Servicio('Chatbot RAG', 'PUERTO_CHATBOT_RAG', 8011, '/', 'Chainlit con LangChain y Qdrant',
             'CHATBOT_USUARIO / CHATBOT_CLAVE', 'siempre'),
    Servicio('API de acceso', 'PUERTO_ACCESO', 8002, '/docs', 'Documentación interactiva (filtro de privacidad)',
             'las consultas piden X-API-Key', 'siempre'),
    Servicio('API de captura', 'PUERTO_CAPTURA', 8001, '/docs', 'Documentación interactiva (entrada de viajes)',
             'los envíos piden X-API-Key', 'siempre'),
    Servicio('SeaweedFS S3 (API)', 'PUERTO_S3', 8333, '/', 'Pasarela S3: sin clave responde «AccessDenied»',
             'claves S3_*_ACCESS_KEY / S3_*_SECRET_KEY', 'siempre'),
    Servicio('Spark', 'PUERTO_SPARK', 8090, '/', 'Máster, workers y trabajos (tiempo real y cargas)',
             'sin login · solo lectura', 'ver'),
    Servicio('Prometheus', 'PUERTO_PROMETHEUS', 9091, '/', 'Métricas y objetivos en bruto',
             'sin login · solo lectura', 'ver'),
    Servicio('SeaweedFS (estado)', 'PUERTO_SEAWEED', 9333, '/', 'Volúmenes, colecciones y tamaños, sin ficheros',
             'sin login · solo la página de estado', 'ver'),
    Servicio('Qdrant', 'PUERTO_QDRANT', 6333, '/dashboard', 'Panel del índice del chatbot RAG',
             'sin login · solo lectura', 'ver'),
    Servicio('MongoDB', 'PUERTO_MONGO', 27018, '', 'No es una web: mongosh o MongoDB Compass',
             'usuario y contraseña MONGO_*', 'no web'),
]

NUNCA = [
    ('Consola de Redpanda y Kafka', 'enseñan los mensajes de viajes-crudos, viajes individuales (E3)'),
    ('Filer y volúmenes de SeaweedFS', 'sirven los ficheros de la zona restringida, con viajes individuales (E3)'),
    ('Ollama', 'es una API para el chatbot, sin interfaz; el modelo se usa desde el chatbot'),
]

GRUPOS = {
    'siempre': 'Publicados (piden credencial)',
    'ver': 'Sin login: solo con `make ver` (se cierran con `make ver-cerrar`)',
    'no web': 'No son una web',
}


def leer_puertos(ruta: Path) -> dict[str, int]:
    """Solo las variables `PUERTO_*` de un .env: el resto (claves) ni se guarda."""
    puertos: dict[str, int] = {}
    if not ruta.is_file():
        return puertos
    for linea in ruta.read_text(encoding='utf-8').splitlines():
        clave, _, valor = linea.strip().partition('=')
        if clave.startswith('PUERTO_') and valor.strip().isdigit():
            puertos[clave] = int(valor.strip())
    return puertos


def puertos_del_proyecto(raiz: Path = RAIZ) -> dict[str, int]:
    """Los de `.env.example`, y encima los de `.env`, que son los que usa Docker Compose."""
    return {**leer_puertos(raiz / '.env.example'), **leer_puertos(raiz / '.env')}


def responde(url: str, tiempo: float = TIEMPO_MAXIMO) -> str:
    """'sí' si contesta algo por HTTP (aunque sea 401 o 403: está en marcha y pide credencial), si no 'no'."""
    try:
        with urllib.request.urlopen(url, timeout=tiempo):
            return 'sí'
    except urllib.error.HTTPError as error:
        return 'no (502)' if error.code in (502, 503, 504) else 'sí'     # 502: el proxy de `make ver` sin destino
    except (urllib.error.URLError, OSError, ValueError):
        return 'no'


def abrir(url: str) -> None:
    """En WSL abre el navegador de Windows; si no, el del sistema."""
    if 'microsoft' in platform.release().lower() and shutil.which('cmd.exe'):
        subprocess.run(['cmd.exe', '/c', 'start', '', url], check=False,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, cwd='/mnt/c' if os.path.isdir('/mnt/c') else None)
        return
    import webbrowser
    webbrowser.open(url)


def tabla(puertos: dict[str, int], comprobar=responde) -> tuple[str, list[str]]:
    """El texto de la tabla y las URL que responden (para `--abrir`)."""
    lineas, abiertas = [], []
    for grupo, titulo in GRUPOS.items():
        lineas += ['', f'## {titulo}', '', '| Servicio | Dirección | Responde | Qué es | Cómo se entra |', '|---|---|---|---|---|']
        for s in (s for s in SERVICIOS if s.grupo == grupo):
            if grupo == 'no web':
                direccion, estado = f'localhost:{puertos.get(s.variable, s.puerto)}', '—'
            else:
                direccion = s.url(puertos)
                estado = comprobar(direccion)
                if estado == 'sí':
                    abiertas.append(direccion)
            lineas.append(f'| {s.nombre} | {direccion} | {estado} | {s.que_es} | {s.como_se_entra} |')
    lineas += ['', '## Nunca se abren', '']
    lineas += [f'- **{nombre}**: {motivo}.' for nombre, motivo in NUNCA]
    return '\n'.join(lineas).lstrip(), abiertas


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--abrir', action='store_true', help='abre en el navegador todo lo que responde')
    p.add_argument('--sin-comprobar', action='store_true', help='no prueba si responden (más rápido)')
    a = p.parse_args(argv)
    texto, abiertas = tabla(puertos_del_proyecto(), (lambda _url: '?') if a.sin_comprobar else responde)
    print(texto)
    if a.abrir:
        for url in abiertas:
            abrir(url)
        print(f'\nAbiertas {len(abiertas)} pestañas.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
