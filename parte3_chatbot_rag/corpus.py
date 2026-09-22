"""Corpus de conocimiento del chatbot RAG: qué se indexa en la colección `conocimiento` y cómo se trocea.

Fuentes (todas públicas o ya protegidas; ningún dato individual):
  - `docs/*.md` del repositorio, troceados por cabeceras (tipo `doc`);
  - `config/privacidad.json`, contado en prosa (tipo `doc`);
  - `parte3_chatbot_rag/corpus/*.md`: guía de consultas, preguntas frecuentes y contexto de 2020 (tipo `doc`);
  - el calendario de 2020, generado: el día de la semana de cada fecha (tipo `doc`);
  - `GET /catalogo` de la API de acceso (tipo `catalogo`);
  - `GET /zonas`: una ficha por zona, con sus sinónimos, y un resumen por barrio (tipo `zona`);
  - `corpus/ejemplos.json`: preguntas con la llamada correcta a las herramientas (tipo `ejemplo`).

Cada documento lleva en `metadata` al menos `tipo`, `fuente`, `titulo` y `_id`, un UUID estable a partir de la
fuente y el título: reindexar sustituye en vez de duplicar. Todo es lógica pura; las dos llamadas a la API
(`catalogo` y `zonas`) se hacen fuera y se pasan como argumento, así se prueba sin servicios.
"""
from __future__ import annotations

import json
import os
import re
import uuid
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from langchain_core.documents import Document
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter

from herramientas import ClienteAcceso, SINONIMOS_ZONA, normalizar

RAIZ = Path(__file__).resolve().parents[1]
CARPETA_CORPUS = Path(__file__).resolve().parent / 'corpus'
RUTA_DOCS = Path(os.environ.get('PIDS_DOCS_DIR', RAIZ / 'docs'))
RUTA_CONFIG = Path(os.environ.get('PIDS_CONFIG_DIR', RAIZ / 'config'))

# Hablan de la organización del equipo y de la puesta a punto de WSL, no de los datos: solo meterían ruido.
DOCS_EXCLUIDOS = frozenset({'plan.md', 'herramientas.md'})
TIPOS = ('doc', 'catalogo', 'zona', 'ejemplo', 'ficha')
ESPACIO_IDS = uuid.UUID('6f1c1d1e-0b6e-4f8a-9c1e-2a7d6c5b4a30')
TAMANO_TROZO, SOLAPE_TROZO, MINIMO_TROZO = 1800, 150, 40

DIAS_SEMANA = ['lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado', 'domingo']
MESES = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre',
         'noviembre', 'diciembre']
BARRIOS_TEXTO = {'EWR': 'EWR (aeropuerto de Newark, en Nueva Jersey)',
                 'N/A': 'N/A (viajes fuera de la ciudad)',
                 'Unknown': 'Unknown (viajes sin localización registrada)'}
ALIAS_VISIBLES = {'jfk': 'JFK', 'laguardia': 'LaGuardia', 'estacion penn': 'Estación Penn'}


def identificador(*partes: Any) -> str:
    """UUID estable (Qdrant exige UUID o entero): las mismas partes dan siempre el mismo id."""
    return str(uuid.uuid5(ESPACIO_IDS, '|'.join(str(p) for p in partes)))


def documento(texto: str, tipo: str, fuente: str, titulo: str, **extra: Any) -> Document:
    if tipo not in TIPOS:
        raise ValueError(f'tipo desconocido: {tipo!r}')
    metadatos = {'tipo': tipo, 'fuente': fuente, 'titulo': titulo, **extra}
    metadatos.setdefault('_id', identificador(tipo, fuente, titulo))
    return Document(page_content=texto.strip(), metadata=metadatos)


# --- Markdown -------------------------------------------------------------------------------------------

_CABECERAS = [('#', 'h1'), ('##', 'h2'), ('###', 'h3')]


def sin_bloques_de_codigo(texto: str) -> str:
    """Quita los bloques de código y los diagramas: no ayudan a recuperar y gastan contexto."""
    return re.sub(r'```.*?```', '', texto, flags=re.DOTALL)


def trocear_markdown(texto: str, fuente: str, tamano: int = TAMANO_TROZO, solape: int = SOLAPE_TROZO) -> list[Document]:
    """Trocea por cabeceras y, si una sección es muy larga, por tamaño. Cada trozo empieza por su título
    («Escenario E3 › Reglas propias») para que se entienda solo, sin el resto del fichero."""
    secciones = MarkdownHeaderTextSplitter(_CABECERAS, strip_headers=True).split_text(sin_bloques_de_codigo(texto))
    por_tamano = RecursiveCharacterTextSplitter(chunk_size=tamano, chunk_overlap=solape)
    salida: list[Document] = []
    vistos: dict[str, int] = {}
    for seccion in secciones:
        titulo = ' › '.join(seccion.metadata[c] for _, c in _CABECERAS if seccion.metadata.get(c)) or Path(fuente).stem
        contenido = seccion.page_content.strip()
        trozos = por_tamano.split_text(contenido) if len(contenido) > tamano else [contenido]
        for i, trozo in enumerate(trozos):
            if len(trozo.strip()) < MINIMO_TROZO:            # una cabecera sin contenido, una línea suelta
                continue
            nombre = titulo + (f' ({i + 1}/{len(trozos)})' if len(trozos) > 1 else '')
            vistos[nombre] = vistos.get(nombre, 0) + 1
            if vistos[nombre] > 1:                            # dos secciones con la misma cabecera
                nombre += f' · {vistos[nombre]}'
            salida.append(documento(f'{titulo}\n\n{trozo}', 'doc', fuente, nombre))
    return salida


def documentos_markdown(carpeta: Path, prefijo_fuente: str, excluidos: frozenset[str] = frozenset()) -> list[Document]:
    """Todos los *.md de una carpeta (en orden alfabético), troceados."""
    salida: list[Document] = []
    for ruta in sorted(Path(carpeta).glob('*.md')):
        if ruta.name not in excluidos:
            salida.extend(trocear_markdown(ruta.read_text(encoding='utf-8'), f'{prefijo_fuente}/{ruta.name}'))
    return salida


# --- configuración de privacidad, en prosa ----------------------------------------------------------------

def documento_privacidad(cfg: dict | None = None) -> Document:
    cfg = cfg or json.loads((RUTA_CONFIG / 'privacidad.json').read_text(encoding='utf-8'))
    niveles = '\n'.join(f'- `{nombre}`: {n["descripcion"]} Dimensiones: {", ".join(n["dimensiones"])}; '
                        f'granularidad mínima: {"una hora" if n["tiempo"] == "hora" else "un día"}.'
                        for nombre, n in cfg['niveles'].items())
    texto = f"""Reglas de privacidad de la plataforma (escenario E3, versión {cfg['version']} de las reglas)

Umbral k: los grupos con menos de {cfg['k_minimo']} viajes, y los que se ocultan para que no se deduzcan \
restando, se publican enmascarados con n_viajes "oculto", sin cifras, y nunca se suman a ningún total. Las medias se redondean a {cfg['decimales']} decimales. La granularidad temporal mínima \
es de {cfg['granularidad_temporal_minima_horas']} hora en el nivel por horas y de un día en los demás. Cada \
consulta abarca como máximo {cfg['max_dias_por_consulta']} días y devuelve como máximo \
{cfg['max_filas_por_respuesta']} filas.

Métricas publicadas: {', '.join(cfg['metricas'])}. No existe ninguna otra.

Niveles de agregación publicados:
{niveles}

Fuentes: {', '.join(cfg['fuentes'])} (las colecciones de tiempo real llevan el prefijo \
«{cfg['fuentes']['tiempo_real']}»).

Campos individuales que nunca se publican y cuya petición rechaza la consulta: {', '.join(cfg['campos_individuales'])}.
"""
    return documento(texto, 'doc', 'config/privacidad.json', 'Reglas de privacidad (E3)')


# --- calendario ------------------------------------------------------------------------------------------

def documentos_calendario(anio: int = 2020) -> list[Document]:
    """Un documento por mes con el día de la semana de cada fecha: los modelos calculan mal los días de la semana."""
    salida = []
    for mes in range(1, 13):
        primero = date(anio, mes, 1)
        ultimo = (date(anio + 1, 1, 1) if mes == 12 else date(anio, mes + 1, 1)) - timedelta(days=1)
        dias = [primero + timedelta(days=i) for i in range(ultimo.day)]
        por_semana = {d: [x.day for x in dias if x.weekday() == i] for i, d in enumerate(DIAS_SEMANA)}
        texto = (f'Calendario de {MESES[mes - 1]} de {anio}: {ultimo.day} días; el 1 fue '
                 f'{DIAS_SEMANA[primero.weekday()]} y el {ultimo.day} fue {DIAS_SEMANA[ultimo.weekday()]}.\n'
                 + '\n'.join(f'- {d.capitalize()}: {", ".join(map(str, ns))}' for d, ns in por_semana.items())
                 + f'\nDía a día: {", ".join(f"{d.day} {DIAS_SEMANA[d.weekday()]}" for d in dias)}.\n'
                 f'Ventana ISO del mes completo: desde {primero.isoformat()}T00:00:00 hasta '
                 f'{(ultimo + timedelta(days=1)).isoformat()}T00:00:00 ({ultimo.day} días).')
        salida.append(documento(texto, 'doc', 'calendario', f'Calendario de {MESES[mes - 1]} de {anio}', mes=mes))
    return salida


# --- catálogo y zonas (de la API de acceso) ----------------------------------------------------------------

def documento_catalogo(catalogo: dict) -> Document:
    niveles = '\n'.join(f'- `{n}`: {v.get("descripcion", "")} Dimensiones: {", ".join(v.get("dimensiones", []))}.'
                        for n, v in catalogo.get('niveles', {}).items())
    barrios = ', '.join(BARRIOS_TEXTO.get(b, b) for b in catalogo.get('barrios', []))
    texto = (f'Catálogo de la API de acceso: qué se puede consultar.\n\n'
             f'Umbral k mínimo por grupo: {catalogo.get("k_minimo")} viajes. Rango máximo por consulta: '
             f'{catalogo.get("max_dias_por_consulta")} días.\nMétricas: {", ".join(catalogo.get("metricas", []))}.\n'
             f'Fuentes: {", ".join(catalogo.get("fuentes", []))}.\nNiveles:\n{niveles}\n'
             f'Barrios (valores válidos de barrio_origen y barrio_destino): {barrios}.')
    return documento(texto, 'catalogo', 'api:/catalogo', 'Catálogo de la API de acceso')


def sinonimos_zona(zona: dict) -> list[str]:
    """Otros nombres con los que se pregunta por la zona: los alias del chatbot y «aeropuerto» en los aeropuertos."""
    nombre = normalizar(zona.get('nombre', ''))
    alias = [ALIAS_VISIBLES.get(a, a.title()) for a, destino in SINONIMOS_ZONA.items()
             if destino in nombre and normalizar(a) != nombre]
    if 'airport' in nombre or zona.get('tipo_servicio') in ('Airports', 'EWR'):
        alias += ['aeropuerto', 'aeropuerto ' + zona.get('nombre', '').replace(' Airport', '')]
    return list(dict.fromkeys(alias))


def documento_zona(zona: dict) -> Document:
    nombre, barrio, id_ = zona.get('nombre', ''), zona.get('barrio', ''), zona.get('_id')
    alias = sinonimos_zona(zona)
    texto = (f'Zona de taxi {id_}: {nombre}, en el barrio {BARRIOS_TEXTO.get(barrio, barrio)}'
             f' (tipo de servicio: {zona.get("tipo_servicio", "?")}).')
    if alias:
        texto += f' También se le llama: {", ".join(alias)}.'
    texto += (f' Para consultar sus viajes por horas: nivel hora_zona con zona_origen={id_} (o el nombre «{nombre}»). '
              f'Su barrio para dia_barrio y od_dia_barrio es «{barrio}».')
    return documento(texto, 'zona', 'api:/zonas', f'Zona {id_} · {nombre}', zona_id=id_, barrio=barrio)


def documento_barrio(barrio: str, zonas: list[dict]) -> Document:
    nombres = ', '.join(f'{z["nombre"]} ({z["_id"]})' for z in sorted(zonas, key=lambda z: z.get('nombre', '')))
    texto = (f'El barrio {BARRIOS_TEXTO.get(barrio, barrio)} tiene {len(zonas)} zonas de taxi: {nombres}. '
             f'Por barrio se consultan los niveles dia_barrio y od_dia_barrio con barrio_origen="{barrio}"; por horas, '
             f'hora_zona con barrio_origen (se consultan todas sus zonas) o con la zona_origen concreta.')
    return documento(texto, 'zona', 'api:/zonas', f'Zonas del barrio {barrio}', barrio=barrio)


def documentos_zonas(zonas: list[dict]) -> list[Document]:
    por_barrio: dict[str, list[dict]] = {}
    for z in zonas:
        por_barrio.setdefault(z.get('barrio') or 'Unknown', []).append(z)
    return [documento_zona(z) for z in zonas] + [documento_barrio(b, zs) for b, zs in sorted(por_barrio.items())]


# --- ejemplos ---------------------------------------------------------------------------------------------

def _llamada(llamada: dict) -> str:
    argumentos = ', '.join(f'{k}={json.dumps(v, ensure_ascii=False)}' for k, v in llamada.get('argumentos', {}).items())
    return f'{llamada["herramienta"]}({argumentos})'


def documentos_ejemplos(ruta: Path) -> list[Document]:
    datos = json.loads(Path(ruta).read_text(encoding='utf-8'))
    salida = []
    for ejemplo in datos['ejemplos']:
        llamadas = ejemplo['llamadas']
        lineas = [f'Pregunta: {ejemplo["pregunta"]}']
        lineas += [f'Llamada{f" {i + 1}" if len(llamadas) > 1 else ""}: {_llamada(ll)}'
                   for i, ll in enumerate(llamadas)]
        if ejemplo.get('nota'):
            lineas.append(f'Nota: {ejemplo["nota"]}')
        salida.append(documento('\n'.join(lineas), 'ejemplo', 'corpus/ejemplos.json', ejemplo['pregunta'],
                                herramienta=llamadas[0]['herramienta']))
    return salida


# --- todo junto -------------------------------------------------------------------------------------------

def conocimiento(zonas: list[dict], catalogo: dict | None = None, ruta_docs: Path = RUTA_DOCS,
                 carpeta_corpus: Path = CARPETA_CORPUS, cfg_privacidad: dict | None = None) -> list[Document]:
    """Todos los documentos de la colección `conocimiento`, sin tocar la red (zonas y catálogo vienen de fuera)."""
    ruta_docs, carpeta_corpus = Path(ruta_docs), Path(carpeta_corpus)
    salida = documentos_markdown(ruta_docs, 'docs', DOCS_EXCLUIDOS) if ruta_docs.is_dir() else []
    salida += documentos_markdown(carpeta_corpus, 'corpus')
    salida.append(documento_privacidad(cfg_privacidad))
    salida += documentos_calendario()
    if catalogo:
        salida.append(documento_catalogo(catalogo))
    salida += documentos_zonas(zonas)
    if (carpeta_corpus / 'ejemplos.json').is_file():
        salida += documentos_ejemplos(carpeta_corpus / 'ejemplos.json')
    comprobar_ids_unicos(salida)
    return salida


def comprobar_ids_unicos(documentos: list[Document]) -> None:
    """Dos documentos con el mismo id se pisarían al indexar: mejor fallar aquí, con sus títulos."""
    vistos: dict[str, str] = {}
    for d in documentos:
        id_, titulo = d.metadata['_id'], d.metadata['titulo']
        if id_ in vistos:
            raise ValueError(f'dos documentos con el mismo id: {vistos[id_]!r} y {titulo!r}')
        vistos[id_] = titulo


async def catalogo_desde_api(acceso: ClienteAcceso) -> dict:
    r = await acceso.http.get('/catalogo')
    r.raise_for_status()
    return r.json()


async def conocimiento_desde_api(acceso: ClienteAcceso) -> list[Document]:
    """Igual que `conocimiento`, pidiendo a la API de acceso las zonas y el catálogo."""
    return conocimiento(await acceso.zonas(), await catalogo_desde_api(acceso))


def resumen(documentos: list[Document]) -> dict[str, int]:
    """Cuántos documentos hay de cada tipo (para el informe del indexador y las pruebas)."""
    cuenta: dict[str, int] = {}
    for d in documentos:
        cuenta[d.metadata['tipo']] = cuenta.get(d.metadata['tipo'], 0) + 1
    return dict(sorted(cuenta.items()))
