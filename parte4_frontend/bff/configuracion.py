"""Configuración del BFF (CONTRATOS.md §3).

En el contenedor las variables las pone Compose (`ACCESO_URL=http://acceso:8000`, `AUDITORIA_MONGO_URI=…@mongo`).
En el host se lee `.env` de la raíz del repositorio (el entorno del proceso tiene prioridad) y las URL se derivan
de los puertos publicados en 127.0.0.1, porque los nombres de los contenedores no resuelven fuera de Docker.
Misma técnica que `parte3_chatbot_rag/fabrica.py`.

    from parte4_frontend.bff.configuracion import configuracion
    cfg = configuracion()          # una por proceso (lru_cache); los tests construyen la suya con
                                   # Configuracion.desde_entorno({...}, contenedor=False) y se la pasan a crear_app()

Este módulo no importa FastAPI: es lógica pura y se prueba sin red.
"""
from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import timedelta
from functools import lru_cache
from pathlib import Path
from urllib.parse import quote_plus, urlparse

RAIZ = Path(__file__).resolve().parents[2]
DIST_SPA = RAIZ / 'parte4_frontend' / 'web' / 'dist'

# variable de la URL -> (anfitrión en Compose, variable del puerto publicado, puerto por defecto)
SERVICIOS: dict[str, tuple[str, str, str]] = {
    'ACCESO_URL': ('acceso', 'PUERTO_ACCESO', '8002'),
    'CAPTURA_URL': ('captura', 'PUERTO_CAPTURA', '8001'),
    'PROMETHEUS_URL': ('prometheus', 'PUERTO_PROMETHEUS', '9090'),
    'AIRFLOW_URL': ('airflow-apiserver', 'PUERTO_AIRFLOW', '8085'),
    'OLLAMA_URL': ('ollama', 'PUERTO_OLLAMA', '11435'),
    'GRAFANA_URL': ('grafana', 'PUERTO_GRAFANA', '3000'),     # estado de las alertas (Observabilidad)
}
MONGO = ('mongo', 'PUERTO_MONGO', '27018')

# Enlaces del menú: son URL del navegador del usuario, no del contenedor, así que valen igual en los dos casos.
ENLACES_POR_DEFECTO: dict[str, str] = {
    'grafana': 'http://localhost:3000',
    'airflow': 'http://localhost:8085',
    'spark': '',   # la interfaz no se publica: no tiene autenticación (docs/seguridad.md)
    'chatbot': 'http://localhost:8010',
    'chatbot_rag': 'http://localhost:8011',
    'api_acceso': 'http://localhost:8002/docs',
    'api_captura': 'http://localhost:8001/docs',
}
OLLAMA_MODELO_POR_DEFECTO = 'llama3.1:8b'
DURACION_SESION = timedelta(hours=12)


# --- entorno -----------------------------------------------------------------------------------------------

def en_contenedor(entorno: Mapping[str, str] | None = None) -> bool:
    """Dentro de Docker hay `/.dockerenv` y `PIDS_CONFIG_DIR` apunta a `/app/config` (imagen común)."""
    entorno = os.environ if entorno is None else entorno
    return Path('/.dockerenv').exists() or entorno.get('PIDS_CONFIG_DIR', '').startswith('/app')


def leer_env(ruta: Path) -> dict[str, str]:
    """Pares CLAVE=valor de un fichero .env (líneas vacías y comentarios fuera; comillas simples o dobles fuera)."""
    valores: dict[str, str] = {}
    if not ruta.is_file():
        return valores
    for linea in ruta.read_text(encoding='utf-8').splitlines():
        if linea.strip() and not linea.lstrip().startswith('#') and '=' in linea:
            clave, valor = linea.split('=', 1)
            valores[clave.strip()] = valor.strip().strip('"\'')
    return valores


def entorno(ruta: Path = RAIZ / '.env') -> dict[str, str]:
    """El .env de la raíz (si existe) con el entorno del proceso por encima."""
    return {**leer_env(ruta), **os.environ}


def _anfitrion(url: str) -> str | None:
    try:
        return urlparse(url).hostname
    except ValueError:
        return None


def url_servicio(variable: str, cfg: Mapping[str, str], contenedor: bool) -> str:
    """URL de un servicio: la del entorno en el contenedor; en el host, la del puerto publicado en 127.0.0.1.

    Fuera de Docker, una URL cuyo anfitrión es el nombre del contenedor (`http://acceso:8000`) no sirve y se
    sustituye por el puerto publicado. Una URL con otro anfitrión (localhost, una IP, un dominio) se respeta.
    """
    servicio, variable_puerto, puerto = SERVICIOS[variable]
    url = cfg.get(variable, '').strip()
    if url and (contenedor or _anfitrion(url) != servicio):
        return url.rstrip('/')
    return f'http://127.0.0.1:{cfg.get(variable_puerto) or puerto}'


def uri_auditoria(cfg: Mapping[str, str], contenedor: bool) -> str:
    """URI de MongoDB del usuario `pids_auditor` (solo lectura de `auditoria`); en el host, por el puerto publicado."""
    servicio, variable_puerto, puerto = MONGO
    uri = cfg.get('AUDITORIA_MONGO_URI', '').strip()
    if uri and (contenedor or _anfitrion(uri) != servicio):
        return uri
    clave = quote_plus(cfg.get('MONGO_AUDITOR_PASSWORD', ''))
    return f'mongodb://pids_auditor:{clave}@127.0.0.1:{cfg.get(variable_puerto) or puerto}/?authSource=admin'


def clave_acceso(cfg: Mapping[str, str]) -> str:
    """ACCESO_CLAVE (Compose) o, en el host, la del cliente `frontend` de .env; si no existe, la del equipo."""
    return cfg.get('ACCESO_CLAVE') or cfg.get('ACCESO_CLAVE_FRONTEND') or cfg.get('ACCESO_CLAVE_EQUIPO') or ''


def enlaces(cfg: Mapping[str, str]) -> dict[str, str]:
    """`ENLACES_GRAFANA`, `ENLACES_AIRFLOW`, … con los valores por defecto del §3 para los que falten."""
    return {nombre: cfg.get(f'ENLACES_{nombre.upper()}') or url for nombre, url in ENLACES_POR_DEFECTO.items()}


# --- configuración -----------------------------------------------------------------------------------------

@dataclass(frozen=True)
class Configuracion:
    en_contenedor: bool
    frontend_clave: str                 # contraseña única del portal (vacía => nadie puede entrar)
    frontend_secreto: str               # firma HMAC de la cookie de sesión
    acceso_url: str
    acceso_clave: str
    captura_url: str
    captura_clave: str
    prometheus_url: str
    airflow_url: str
    airflow_usuario: str
    airflow_clave: str
    auditoria_mongo_uri: str
    ollama_url: str
    ollama_modelo: str
    grafana_url: str = 'http://127.0.0.1:3000'
    enlaces: dict[str, str] = field(default_factory=lambda: dict(ENLACES_POR_DEFECTO))
    duracion_sesion: timedelta = DURACION_SESION
    dist_spa: Path = DIST_SPA

    @classmethod
    def desde_entorno(cls, cfg: Mapping[str, str] | None = None, contenedor: bool | None = None) -> Configuracion:
        """Construye la configuración a partir de un diccionario de variables (por defecto, `entorno()`)."""
        cfg = entorno() if cfg is None else cfg
        contenedor = en_contenedor(cfg) if contenedor is None else contenedor
        return cls(
            en_contenedor=contenedor,
            frontend_clave=cfg.get('FRONTEND_CLAVE', ''),
            frontend_secreto=cfg.get('FRONTEND_SECRETO', ''),
            acceso_url=url_servicio('ACCESO_URL', cfg, contenedor),
            acceso_clave=clave_acceso(cfg),
            captura_url=url_servicio('CAPTURA_URL', cfg, contenedor),
            captura_clave=cfg.get('CAPTURA_CLAVE') or cfg.get('CAPTURA_CLAVE_SIMULADOR') or '',
            prometheus_url=url_servicio('PROMETHEUS_URL', cfg, contenedor),
            airflow_url=url_servicio('AIRFLOW_URL', cfg, contenedor),
            airflow_usuario=cfg.get('AIRFLOW_USUARIO') or cfg.get('AIRFLOW_ADMIN_USER') or 'admin',
            airflow_clave=cfg.get('AIRFLOW_CLAVE') or cfg.get('AIRFLOW_ADMIN_PASSWORD') or '',
            auditoria_mongo_uri=uri_auditoria(cfg, contenedor),
            ollama_url=url_servicio('OLLAMA_URL', cfg, contenedor),
            ollama_modelo=cfg.get('OLLAMA_MODELO') or OLLAMA_MODELO_POR_DEFECTO,
            grafana_url=url_servicio('GRAFANA_URL', cfg, contenedor),
            enlaces=enlaces(cfg),
        )

    def avisos(self) -> list[str]:
        """Carencias que conviene avisar al arrancar (sin revelar ningún valor)."""
        faltan = []
        if not self.frontend_clave:
            faltan.append('FRONTEND_CLAVE no está definida: nadie podrá iniciar sesión en el portal')
        if not self.frontend_secreto:
            faltan.append('FRONTEND_SECRETO no está definido: se usará uno aleatorio y las sesiones no sobrevivirán '
                          'a un reinicio')
        if not self.acceso_clave:
            faltan.append('No hay clave para la API de acceso (ACCESO_CLAVE, ACCESO_CLAVE_FRONTEND o ACCESO_CLAVE_EQUIPO)')
        return faltan


@lru_cache(maxsize=1)
def configuracion() -> Configuracion:
    """La configuración del proceso. En los tests: `configuracion.cache_clear()` tras cambiar el entorno, o mejor,
    construir una `Configuracion` a mano y pasársela a `crear_app(configuracion=...)`."""
    return Configuracion.desde_entorno()
