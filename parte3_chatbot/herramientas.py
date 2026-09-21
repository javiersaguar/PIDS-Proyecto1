"""Herramientas del agente: la única forma que tiene el LLM de ver datos es la API de acceso.

El LLM nunca toca la base de datos: si pide algo que viola la privacidad, la API lo rechaza y
devuelve una alternativa. Además, `parece_individual` detecta antes del LLM las peticiones de
viajes concretos, para no depender de que el modelo obedezca las instrucciones.

El cliente corrige las chapuzas de formato del modelo (zonas por nombre, "null" como filtro, la
hora 24) sin relajar ninguna regla: cada consulta sigue pasando por el filtro de la API.
"""
from __future__ import annotations

import asyncio
import inspect
import json
import os
import re
import unicodedata
from datetime import datetime, timedelta
from typing import Any

import httpx

ACCESO_URL = os.environ.get('ACCESO_URL', 'http://acceso:8000')
ACCESO_CLAVE = os.environ.get('ACCESO_CLAVE', '')

ENMASCARADO = r'(<\s*10|menos de 10|\bgrupos? (suprimid|ocult|enmascarad|pequeñ)\w*)'
PATRONES_INDIVIDUALES = [
    r'\bmatr[ií]cula',
    r'\b(conductor|taxista|chófer|chofer)\b',
    r'\b(nombre|tel[eé]fono|direcci[oó]n) del (pasajero|cliente)',
    r'\bviaje (concreto|exacto|espec[ií]fico|individual)',
    r'\b(qui[eé]n|qu[eé] persona)\b.*\b(cogi[oó]|tom[oó]|subi[oó]|viaj[oó])',
    r'\blos viajes? de (un|una|el|la) (pasajer|client|usuari)',
    r'\b\d{1,2}:(?!00\b)\d{2}\b',            # una hora con minutos: apunta a un viaje concreto
    r'\b(id|identificador) del viaje|\bviaje (con|de) (id|identificador)\b',
    # Paráfrasis sin palabras clave (medidas con la batería trampa, preguntas_trampa.json)
    r'\blas \w+ (y|menos) (cuarto|media|diez|veinte|cinco|veinticinco)\b',     # «las cinco y cuarto»
    r'\b(mi|tu|su) (herman[oa]|madre|padre|amig[oa]|novi[oa]|pareja|mujer|marido|jef[ea]|vecin[oa]|hij[oa]|'
    r'prim[oa]|compañer[oa]|t[ií][oa]|abuel[oa])\b.*\b(cogi[oó]|tom[oó]|pag[oó]|viaj[oó]|fue|lleg[oó]|subi[oó]|'
    r'sali[oó]|le cobraron)\b',
    r'\b(el|la|ese|esa|aquel|aquella|este|esta) (taxi|viaje|trayecto|carrera|pasajer[oa]|persona|cliente) '
    r'(que|de las|de la)\b',
    r'\b(el|la|del) (primer|primera|[uú]ltimo|[uú]ltima) (viaje|trayecto|pasajer[oa]|taxi|carrera|cliente)\b',
    r'\b(el|la) (viaje|trayecto|carrera) (m[aá]s|con m[aá]s|con menos) \w+',
    r'\b(cu[aá]l|qu[eé]) de (esos|estos|aquellos|los) (viajes|trayectos|taxis|pasajeros)\b',
    r'\b(ad[oó]nde|a d[oó]nde|a qu[eé] (barrio|zona|sitio|lugar)) (fue|iba|se dirig[ií]a|lleg[oó])\b',
    r'\bhora (exacta|de recogida|de llegada)\b|\bminuto y segundo\b|\b(marcas?|sellos?) de tiempo\b',
    r'\btpep_|\b(pickup|dropoff)_datetime\b',
    r'\b(enumera|lista|listado de) (los |las )?(trayectos|viajes|carreras)\b|'
    r'\b(trayectos|viajes) (individuales|uno a uno|uno por uno)\b',
    r'\binvent\w* (un |una )?(ejemplo|viaje|trayecto|dato)',
    # el valor de un grupo enmascarado, en cualquier orden: «¿cuál es el valor real de los grupos <10?»
    rf'(?s)^(?=.*\b(cifras?|valor(es)?|n[uú]meros?) (real(es)?|exact[oa]s?|m[aá]s probables?)\b)(?=.*{ENMASCARADO})',
    rf'(?s)^(?=.*\b(estim|deduc|calcul|adivin|averigu)\w*)(?=.*{ENMASCARADO})',
    rf'(?s)^(?=.*\bcada (grupo|uno)\b)(?=.*{ENMASCARADO})',
    r'\bmenos de 10\b.*\b(dime|dame|cu[aá]l es) (el|su) (n[uú]mero|valor|cifra)\b',
    rf'(?s)^(?=.*(\bconfirm\w*|\bs[ií] o no\b|\bverdadero o falso\b|\byes or no\b|\b(fueron|son|hubo) \w+ o \w+\b))'
    rf'(?=.*{ENMASCARADO})',
    # volcados, marcas de rol y columnas del registro individual
    r'\b(viajes|datos|registros|filas) (crudos|en bruto|sin agregar|originales)\b|\bvolcado\b|\bdump\b|'
    r'\braw (data|trips|rows)\b|\bprimera fila\b',
    r'</?\s*system\s*>|^\s*system\s*:|\[/?inst\]',
    r'\bvendor_?id\b|\bpassenger_count\b|\bratecodeid\b|\bstore_and_fwd|\b(pu|do)locationid\b|'
    r'\bn[uú]mero de pasajeros\b|\bpasajeros (de|en|por) (los|cada|el|un) (viajes?|taxis?)\b',
    # inglés
    r'\bwho\b.*\b(took|rode|was in|caught|hailed)\b',
    r'\b(pickup|drop-?off) (time|timestamp|location)s?\b|\bexact timestamps?\b',
    r'\b(the|that|this) (ride|trip|taxi|cab|passenger) (from|at|that|who)\b',
    r'\b(individual|specific|single|particular) (trips|rides|trip|ride)\b|\b(trip|ride) id\b',
]


def parece_individual(texto: str) -> bool:
    t = texto.lower()
    return any(re.search(p, t) for p in PATRONES_INDIVIDUALES)


# Instrucción que se añade a la respuesta de una herramienta rechazada: los modelos pequeños tienden a
# inventarse las cifras cuando no reciben datos.
INSTRUCCION_RECHAZO = (
    '\n\nINSTRUCCIÓN: la plataforma NO ha devuelto datos. Vuelve a llamar a consultar_viajes con '
    'exactamente los parámetros del campo "alternativa", o explica al usuario por qué no se puede '
    'responder. NO escribas ninguna cifra: no tienes datos.')


MESES = 'enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre'
# Fechas y horas: son parte de la pregunta, no un dato inventado
FECHAS_Y_HORAS = [
    rf'\b\d{{1,2}}\s+de\s+({MESES})(\s+de\s+\d{{4}})?\b',
    r'\b\d{4}-\d{2}-\d{2}([T ]\d{2}:\d{2}(:\d{2})?)?\b',
    r'\b\d{1,2}:\d{2}\b',
    r'\b(19|20)\d{2}\b',
    r'\b(error|http|c[oó]digo)\s*:?\s*\d{3}\b',     # códigos de error, no datos
]
PALABRAS_DE_DATO = (r'viajes?|trayectos?|d[oó]lares|usd|\$|millas|km|propina|importe|media|total|'
                    r'porcentaje|%')


def tiene_cifras(texto: str) -> bool:
    """¿La respuesta da cifras (no fechas ni horas)?

    Se usa para no dejar pasar números cuando ninguna herramienta ha devuelto datos: los modelos
    pequeños tienden a inventarse los resultados. Las fechas y horas de la propia pregunta no cuentan.
    """
    limpio = texto or ''
    for patron in FECHAS_Y_HORAS:
        limpio = re.sub(patron, ' ', limpio, flags=re.IGNORECASE)
    if re.search(r'\d[\d.,]*\s*(' + PALABRAS_DE_DATO + r')', limpio, re.IGNORECASE):
        return True
    return bool(re.search(r'\d{2,}', limpio))          # cualquier número de dos o más dígitos


def hay_datos(resultado) -> bool:
    """¿La herramienta ha devuelto datos de verdad (filas o zonas)?"""
    if isinstance(resultado, list):
        return bool(resultado)
    if isinstance(resultado, dict):
        return bool(resultado.get('filas'))
    return False


# --- zonas y barrios -------------------------------------------------------------------------------

BARRIOS = ['Manhattan', 'Brooklyn', 'Queens', 'Bronx', 'Staten Island', 'EWR']
BARRIOS_SIN_ZONA = ['N/A', 'Unknown']            # así vienen en la tabla de la TLC los viajes sin zona conocida
PARAMETROS = {'nivel', 'fuente', 'desde', 'hasta', 'metricas', 'zona_origen', 'barrio_origen', 'barrio_destino',
              'campos_extra'}
ALIAS_BARRIO = {'el bronx': 'Bronx', 'the bronx': 'Bronx', 'newark': 'EWR'}
# Nombres de uso común que no coinciden con el de la tabla de zonas de la TLC
SINONIMOS_ZONA = {
    'times square': 'times sq',
    'jfk': 'jfk airport',
    'kennedy': 'jfk airport',
    'la guardia': 'laguardia airport',
    'laguardia': 'laguardia airport',
    'newark': 'newark airport',
    'wall street': 'financial district',
    'penn station': 'penn station',
    'estacion penn': 'penn station',
}
PALABRAS_GENERICAS = r'\b(aeropuerto|aeropuertos|airport|zona|zonas|barrio|de|del|el|la|los|las|en|desde)\b'
SIN_FILTRO = {'', 'null', 'none', 'nulo', 'ninguno', 'ninguna', 'todos', 'todas', 'all', 'cualquiera'}


def normalizar(texto: str) -> str:
    """Minúsculas, sin tildes ni signos: para comparar nombres de zonas escritos de cualquier forma."""
    t = unicodedata.normalize('NFKD', str(texto)).encode('ascii', 'ignore').decode().lower()
    return re.sub(r'\s+', ' ', re.sub(r'[^a-z0-9]+', ' ', t)).strip()


def barrio_canonico(valor: str) -> str:
    """'manhattan' -> 'Manhattan'. Si no es un barrio conocido se devuelve tal cual (la API lo rechaza)."""
    n = normalizar(valor)
    for barrio in BARRIOS:
        if normalizar(barrio) == n:
            return barrio
    return ALIAS_BARRIO.get(n, str(valor).strip())


def buscar_zonas(texto: str, zonas: list[dict]) -> list[dict]:
    """Zonas cuyo nombre coincide con el texto (con sinónimos), o todas las de un barrio si es un barrio."""
    q = normalizar(texto)
    termino = next((destino for alias, destino in SINONIMOS_ZONA.items() if re.search(rf'\b{alias}\b', q)), None)
    if termino is None:
        termino = re.sub(r'\s+', ' ', re.sub(PALABRAS_GENERICAS, ' ', q)).strip()
    if not termino:
        return []
    exactas = [z for z in zonas if normalizar(z.get('nombre', '')) == termino]
    if exactas:
        return exactas
    por_nombre = [z for z in zonas if termino in normalizar(z.get('nombre', ''))]
    if por_nombre:
        return por_nombre
    return [z for z in zonas if normalizar(z.get('barrio', '')) == termino]


DE_A = re.compile(r'\b(?:de|desde|from)\s+(?P<origen>.+?)\s+(?:a|al|hasta|hacia|to)\s+(?P<destino>.+?)'
                  r'(?=\s+(?:el|la|los|en|on|entre|between|durante|ese|este|del)\b|[?¿.,;!]|$)', re.IGNORECASE)


def destino_por_zona(texto: str, zonas: list[dict]) -> tuple[str, dict] | None:
    """("barrio de origen", zona de destino) si la pregunta pide un destino por zona: «de JFK a Times Square».

    E3 solo publica el destino por barrio y día: origen, destino y hora juntos identifican a personas.
    """
    for m in DE_A.finditer(texto):
        destino = m.group('destino')
        if barrio_canonico(destino) in BARRIOS or (zona_destino := zona_en_texto(destino, zonas)) is None:
            continue
        origen = barrio_canonico(m.group('origen'))
        if origen not in BARRIOS:
            zona_origen = zona_en_texto(m.group('origen'), zonas)
            if zona_origen is None:
                continue
            origen = zona_origen['barrio']
        return origen, zona_destino
    return None


def zona_en_texto(texto: str, zonas: list[dict]) -> dict | None:
    """La zona que se menciona en una frase libre ("el viaje desde Times Square"), si es inequívoca."""
    q = f' {normalizar(texto)} '
    for alias, destino in SINONIMOS_ZONA.items():
        if f' {alias} ' in q:
            candidatas = [z for z in zonas if destino in normalizar(z.get('nombre', ''))]
            return candidatas[0] if len(candidatas) == 1 else None
    nombradas = [z for z in zonas if len(normalizar(z.get('nombre', ''))) >= 5
                 and f' {normalizar(z["nombre"])} ' in q]
    if not nombradas:
        return None
    return max(nombradas, key=lambda z: len(z['nombre']))


# --- fechas ------------------------------------------------------------------------------------------

NUMERO_MES = {m: i + 1 for i, m in enumerate(MESES.split('|'))}
MESES_INGLES = ['january', 'february', 'march', 'april', 'may', 'june', 'july', 'august', 'september',
                'october', 'november', 'december']


def normalizar_instante(valor: Any) -> Any:
    """Arregla lo que el LLM escribe mal: la hora 24 y las fechas sin hora. Lo demás, tal cual."""
    if not isinstance(valor, str):
        return valor
    texto = valor.strip()
    if re.fullmatch(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}(:\d{2})?', texto):
        texto = texto.replace(' ', 'T', 1)
    if re.fullmatch(r'\d{4}-\d{2}-\d{2}', texto):
        return f'{texto}T00:00:00'
    m = re.fullmatch(r'(\d{4}-\d{2}-\d{2})T24:00(:00)?', texto)
    if m:
        return _iso(datetime.fromisoformat(m.group(1)) + timedelta(days=1))
    return texto


def ventana_completa(desde: Any, hasta: Any) -> dict:
    """Ventanas mal cerradas por el LLM: "hasta" igual a "desde" (un día o una hora), acabado en :59 o
    en las 23:00 de un día que empieza a las 00:00 (el LLM cree que "hasta" se incluye).

    Es lo mismo que propondría la API como alternativa; la consulta sigue pasando su filtro.
    """
    try:
        inicio, fin = datetime.fromisoformat(str(desde)), datetime.fromisoformat(str(hasta))
    except ValueError:
        return {}
    if fin.minute == 59:                                 # "hasta 23:59:59" quiere decir "hasta las 24:00"
        fin = fin.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
    elif inicio.time() == datetime.min.time() and fin == inicio.replace(hour=23):   # "de 00:00 a 23:00": el día
        fin = inicio + timedelta(days=1)
    if fin == inicio:
        fin = inicio + (timedelta(days=1) if inicio.time() == datetime.min.time() else timedelta(hours=1))
    return {'hasta': _iso(fin)}


def fecha_en_texto(texto: str) -> datetime | None:
    """"el 15 de enero", "2020-01-15" o "January 15" -> datetime de 2020 (el año de los datos)."""
    t = normalizar(texto)
    m = re.search(r'\b(\d{1,2}) de (' + MESES + r')\b', t)
    if m:
        return _dia_2020(NUMERO_MES[m.group(2)], int(m.group(1)))
    m = re.search(r'\b(' + '|'.join(MESES_INGLES) + r') (\d{1,2})', t)
    if m:
        return _dia_2020(MESES_INGLES.index(m.group(1)) + 1, int(m.group(2)))
    m = re.search(r'\b2020-(\d{2})-(\d{2})\b', texto)
    if m:
        return _dia_2020(int(m.group(1)), int(m.group(2)))
    return None


def _dia_2020(mes: int, dia: int) -> datetime | None:
    try:
        return datetime(2020, mes, dia)
    except ValueError:
        return None


def hora_en_texto(texto: str) -> int | None:
    """"a las 3:12", "22:47" o "3:12 PM" -> la hora en punto (3, 22, 15)."""
    m = re.search(r'\b(\d{1,2}):(\d{2})\s*(am|pm|a\.m\.|p\.m\.)?', texto.lower())
    if not m or int(m.group(1)) > 23:
        return None
    hora = int(m.group(1))
    sufijo = (m.group(3) or '').replace('.', '')
    if sufijo == 'pm' and hora < 12:
        hora += 12
    elif sufijo == 'am' and hora == 12:
        hora = 0
    return hora


def _iso(momento: datetime) -> str:
    return momento.strftime('%Y-%m-%dT%H:%M:%S')


# --- resultados: resumen calculado y versión compacta para el modelo -----------------------------------

def enmascarada(fila: dict) -> bool:
    return bool(fila.get('suprimido')) or isinstance(fila.get('n_viajes'), str)


def _dimensiones(fila: dict) -> dict:
    claves = ('dia', 'hora', 'zona_origen_nombre', 'barrio_origen', 'barrio_destino')
    return {c: fila[c] for c in claves if fila.get(c) is not None}


def con_resumen(resultado: Any) -> Any:
    """Añade un resumen calculado aquí, no por el LLM (los modelos pequeños suman y promedian mal).

    Nunca se da un total si hay grupos enmascarados: el total menos lo visible revelaría lo oculto.
    """
    if not isinstance(resultado, dict) or not resultado.get('filas'):
        return resultado
    filas = resultado['filas']
    visibles = [f for f in filas if not enmascarada(f) and isinstance(f.get('n_viajes'), (int, float))]
    ocultas = len(filas) - len(visibles)
    resumen: dict[str, Any] = {'grupos': len(filas), 'grupos_visibles': len(visibles), 'grupos_enmascarados': ocultas}
    if visibles:
        mayor = max(visibles, key=lambda f: f['n_viajes'])
        resumen['grupo_con_mas_viajes'] = {**_dimensiones(mayor), 'n_viajes': mayor['n_viajes']}
        if len(visibles) > 1:
            menor = min(visibles, key=lambda f: f['n_viajes'])
            resumen['grupo_con_menos_viajes'] = {**_dimensiones(menor), 'n_viajes': menor['n_viajes']}
    if ocultas:
        resumen['aviso'] = 'hay grupos enmascarados: no se da total ni media conjunta'
    elif resultado.get('truncada'):
        resumen['aviso'] = 'respuesta truncada: no se da total'
    elif visibles:
        resumen['total_viajes'] = sum(f['n_viajes'] for f in visibles)
        metricas = {k for f in visibles for k, v in f.items()
                    if k not in ('n_viajes', 'zona_origen') and isinstance(v, (int, float)) and not isinstance(v, bool)}
        for m in sorted(metricas):
            con_valor = [f for f in visibles if isinstance(f.get(m), (int, float))]
            peso = sum(f['n_viajes'] for f in con_valor)
            if peso:
                resumen[f'{m}_conjunta'] = round(sum(f[m] * f['n_viajes'] for f in con_valor) / peso, 2)
    return {**resultado, 'resumen': resumen}


def _fila_compacta(fila: dict) -> dict:
    salida = {}
    for clave, valor in fila.items():
        if clave == 'suprimido' or valor is None:
            continue
        if clave == 'hora' and isinstance(valor, str):
            valor = valor[:16].replace('T', ' ')
        elif clave == 'dia' and isinstance(valor, str):
            valor = valor[:10]
        salida[clave] = valor
    return salida


def para_el_modelo(resultado: Any, max_filas: int = 60) -> str:
    """El resultado en JSON compacto: el contexto del modelo es corto (4096 tokens)."""
    if isinstance(resultado, list):
        compacto: Any = [{'id': z.get('_id'), 'nombre': z.get('nombre'), 'barrio': z.get('barrio')}
                         for z in resultado[:40] if isinstance(z, dict)]
        if len(resultado) > 40:
            compacto.append({'zonas_no_mostradas': len(resultado) - 40})
    elif isinstance(resultado, dict) and 'filas' in resultado:
        consulta = {k: v for k, v in (resultado.get('consulta') or {}).items() if v not in (None, [], '')}
        compacto = {'resultado': resultado.get('resultado'), 'consulta': consulta}
        filas = [_fila_compacta(f) for f in resultado['filas']]
        compacto['filas'] = filas[:max_filas]
        if len(filas) > max_filas:
            compacto['filas_no_mostradas'] = len(filas) - max_filas
        for clave in ('grupos_enmascarados', 'truncada', 'resumen', 'nota_cliente'):
            if resultado.get(clave) not in (None, False):
                compacto[clave] = resultado[clave]
    else:
        compacto = resultado
    return json.dumps(compacto, ensure_ascii=False, default=str)


# --- esquemas de las herramientas --------------------------------------------------------------------

ESQUEMAS: list[dict[str, Any]] = [
    {
        'type': 'function',
        'function': {
            'name': 'consultar_viajes',
            'description': (
                'Consulta agregados de viajes de taxi de Nueva York en 2020. Niveles: hora_zona (por hora y '
                'zona de origen), dia_barrio (por día y barrio de origen), od_dia_barrio (flujos entre barrios '
                'por día). Fechas ISO 2020-MM-DDTHH:00:00; "hasta" no se incluye; rango máximo de 31 días. '
                'Devuelve filas y un resumen ya calculado.'),
            'parameters': {
                'type': 'object',
                'properties': {
                    'nivel': {'type': 'string', 'enum': ['hora_zona', 'dia_barrio', 'od_dia_barrio']},
                    'desde': {'type': 'string', 'description': 'inicio incluido, ISO'},
                    'hasta': {'type': 'string', 'description': 'fin excluido, ISO'},
                    'metricas': {'type': 'array', 'items': {'type': 'string', 'enum': [
                        'n_viajes', 'distancia_media', 'importe_medio', 'propina_media', 'pct_pago_tarjeta']}},
                    'zona_origen': {'type': 'string',
                                    'description': 'id o nombre de la zona (solo hora_zona), p. ej. "JFK"'},
                    'barrio_origen': {'type': 'string', 'enum': BARRIOS},
                    'barrio_destino': {'type': 'string', 'description': 'solo nivel od_dia_barrio'},
                    'fuente': {'type': 'string', 'enum': ['historico', 'tiempo_real']},
                },
                'required': ['nivel', 'desde', 'hasta'],
            },
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'ultima_hora_con_datos',
            'description': ('SOLO para preguntas por "la última hora", "lo que llevamos" o "ahora mismo" en tiempo '
                            'real: viajes por zona de la hora más reciente. No sirve para ninguna otra pregunta.'),
            'parameters': {'type': 'object', 'properties': {}},
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'buscar_zona',
            'description': 'Busca zonas de taxi por nombre (por ejemplo "JFK", "Times Sq") y devuelve su id y barrio.',
            'parameters': {'type': 'object', 'properties': {'texto': {'type': 'string'}}, 'required': ['texto']},
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'solicitud_individual',
            'description': ('Úsala SIEMPRE que el usuario pida datos de un viaje, persona, conductor o vehículo '
                            'concretos. La plataforma lo rechazará y quedará registrado.'),
            'parameters': {'type': 'object', 'properties': {'descripcion': {'type': 'string'}},
                           'required': ['descripcion']},
        },
    },
]


class ClienteAcceso:
    CONSULTAS_EN_PARALELO = 8
    MAX_FILAS = 500                              # el mismo límite que aplica la API a cada respuesta

    def __init__(self, url: str = ACCESO_URL, clave: str = ACCESO_CLAVE):
        self.http = httpx.AsyncClient(base_url=url, headers={'X-API-Key': clave}, timeout=30)
        self._zonas: list[dict] | None = None

    async def _llamar(self, metodo: str, ruta: str, **kwargs) -> dict | list:
        r = await self.http.request(metodo, ruta, **kwargs)
        if r.status_code in (200, 403):          # 403 = rechazo de privacidad, con motivos y alternativa
            return r.json()
        return {'error': f'HTTP {r.status_code}', 'detalle': r.text[:300]}

    async def zonas(self) -> list[dict]:
        """Tabla pública de zonas (dato de referencia), cargada una vez por sesión."""
        if self._zonas is None:
            respuesta = await self._llamar('GET', '/zonas')
            if not isinstance(respuesta, list):
                return []
            self._zonas = respuesta
        return self._zonas

    def nombres_zona(self) -> dict[int, str]:
        return {z['_id']: z['nombre'] for z in self._zonas or [] if '_id' in z}

    async def preparar(self, consulta: dict) -> dict:
        """Limpia los argumentos del LLM. Devuelve la consulta, o {'error': ...} si no se puede entender.

        Un parámetro que la API no conoce se rechaza aquí: la API lo ignoraría sin avisar y el modelo
        creería que ha filtrado (por ejemplo, por un destino que no se publica).
        """
        limpia = {}
        for clave, valor in consulta.items():
            if valor is None or (isinstance(valor, (list, tuple)) and not valor):
                continue
            if isinstance(valor, str) and clave != 'campos_extra' and normalizar(valor) in SIN_FILTRO:
                continue
            limpia[clave] = valor
        destino = limpia.pop('zona_destino', None)
        if destino is not None:
            if barrio_canonico(str(destino)) not in BARRIOS:
                return {'error': 'el destino no se publica por zona, solo por barrio y día',
                        'instruccion': 'usa nivel od_dia_barrio con barrio_destino'}
            limpia.setdefault('barrio_destino', barrio_canonico(str(destino)))
        if desconocidos := sorted(set(limpia) - PARAMETROS):
            return {'error': f'parámetros no admitidos: {", ".join(desconocidos)}',
                    'admitidos': sorted(PARAMETROS - {'campos_extra'})}
        for clave in ('desde', 'hasta'):
            if clave in limpia:
                limpia[clave] = normalizar_instante(limpia[clave])
        limpia.update(ventana_completa(limpia.get('desde'), limpia.get('hasta')))
        for clave in ('barrio_origen', 'barrio_destino'):
            if isinstance(limpia.get(clave), str):
                limpia[clave] = barrio_canonico(limpia[clave])
                if limpia[clave] not in BARRIOS + BARRIOS_SIN_ZONA:
                    zonas = buscar_zonas(limpia[clave], await self.zonas())
                    if len(zonas) == 1:
                        z = zonas[0]
                        return {'error': f'{limpia[clave]!r} es una zona (id {z["_id"]}, barrio {z["barrio"]}), '
                                         'no un barrio',
                                'instruccion': f'para la zona usa nivel hora_zona con zona_origen={z["_id"]}; para su '
                                               f'barrio, barrio_origen={z["barrio"]!r}'}
        zona = limpia.get('zona_origen')
        if isinstance(zona, str):
            if zona.strip().isdigit():
                limpia['zona_origen'] = int(zona.strip())
            elif barrio_canonico(zona) in BARRIOS:          # "Staten Island" como zona: es un barrio
                limpia.pop('zona_origen')
                if limpia.setdefault('barrio_origen', barrio_canonico(zona)) != barrio_canonico(zona):
                    return {'error': f'zona_origen={zona!r} es un barrio y no coincide con '
                                     f'barrio_origen={limpia["barrio_origen"]!r}',
                            'instruccion': 'el origen va en barrio_origen y el destino en barrio_destino'}
            else:
                encontradas = buscar_zonas(zona, await self.zonas())
                if len(encontradas) != 1:
                    return {'error': f'zona {"ambigua" if encontradas else "no encontrada"}: {zona!r}',
                            'zonas_posibles': [{'id': z['_id'], 'nombre': z['nombre']} for z in encontradas[:15]],
                            'instruccion': 'usa buscar_zona y repite la consulta con el id de la zona'}
                limpia['zona_origen'] = encontradas[0]['_id']
        return limpia

    async def consultar_viajes(self, **consulta) -> dict:
        consulta = await self.preparar(consulta)
        if 'error' in consulta:
            return consulta
        if consulta.get('nivel') == 'hora_zona' and consulta.get('barrio_origen') and 'zona_origen' not in consulta:
            return await self._hora_zona_por_barrio(consulta)
        return con_resumen(await self._llamar('POST', '/consultas', json=consulta))

    async def _hora_zona_por_barrio(self, consulta: dict) -> dict:
        """Por horas desde un barrio: la API solo agrega por zona, así que se consulta cada zona del barrio.

        Cada consulta pasa el filtro de la API por separado; los grupos enmascarados siguen enmascarados y
        no se suman a nada.
        """
        barrio = consulta.pop('barrio_origen')
        ids = [z['_id'] for z in await self.zonas() if z.get('barrio') == barrio]
        if not ids:
            return await self._llamar('POST', '/consultas', json={**consulta, 'barrio_origen': barrio})
        semaforo = asyncio.Semaphore(self.CONSULTAS_EN_PARALELO)

        async def una(zona: int):
            async with semaforo:
                return await self._llamar('POST', '/consultas', json={**consulta, 'zona_origen': zona})

        respuestas = await asyncio.gather(*(una(z) for z in ids))
        rechazo = next((r for r in respuestas if not isinstance(r, dict)
                        or r.get('resultado') not in ('permitida', 'enmascarada')), None)
        if rechazo is not None:
            if isinstance(rechazo, dict) and isinstance(rechazo.get('alternativa'), dict):
                rechazo['alternativa'].update(zona_origen=None, barrio_origen=barrio)
            return rechazo
        filas = sorted((f for r in respuestas for f in r['filas']),
                       key=lambda f: (f.get('hora') or '', f.get('zona_origen') or 0))
        visibles = filas[:self.MAX_FILAS]
        ocultas = sum(1 for f in visibles if enmascarada(f))
        return con_resumen({
            'resultado': 'enmascarada' if ocultas else 'permitida',
            'consulta': {**respuestas[0]['consulta'], 'zona_origen': None, 'barrio_origen': barrio},
            'filas': visibles,
            'grupos_enmascarados': ocultas,
            'truncada': len(filas) > self.MAX_FILAS or any(r.get('truncada') for r in respuestas),
            'nota_cliente': f'por horas y zonas de {barrio}: {len(ids)} zonas consultadas por separado',
        })

    async def ultima_hora_con_datos(self, **_ignorados) -> dict:
        """La hora más reciente con datos en tiempo real (la del histórico, el 31 de diciembre, no dice nada).

        Se ignora cualquier argumento: el modelo a veces pide el histórico y acaba describiendo esa hora
        en vez de responder a la pregunta.
        """
        return await self.ultima_hora('tiempo_real')

    async def ultima_hora(self, fuente: str) -> dict:
        """La hora más reciente con grupos publicados: se busca el último día y después su última hora."""
        dia = None
        for mes in range(12, 0, -1):
            desde = datetime(2020, mes, 1)
            hasta = datetime(2021, 1, 1) if mes == 12 else datetime(2020, mes + 1, 1)
            r = await self._llamar('POST', '/consultas', json={'nivel': 'dia_barrio', 'fuente': fuente,
                                                               'desde': _iso(desde), 'hasta': _iso(hasta)})
            if isinstance(r, dict) and r.get('filas'):
                dia = datetime.fromisoformat(max(f['dia'] for f in r['filas'])[:10])
                break
        for h in range(23, -1, -1) if dia else ():
            inicio = dia + timedelta(hours=h)
            r = await self._llamar('POST', '/consultas', json={'nivel': 'hora_zona', 'fuente': fuente,
                                                               'desde': _iso(inicio),
                                                               'hasta': _iso(inicio + timedelta(hours=1))})
            if isinstance(r, dict) and r.get('filas'):
                return con_resumen({**r, 'nota_cliente': f'última hora con datos publicados ({fuente})'})
        return {'resultado': 'sin_datos', 'filas': [], 'consulta': {'fuente': fuente},
                'nota_cliente': f'no hay datos publicados en la fuente {fuente}'}

    async def buscar_zona(self, texto: str) -> list:
        return buscar_zonas(str(texto or ''), await self.zonas())

    async def solicitud_individual(self, descripcion: str) -> dict:
        return await self._llamar('POST', '/consultas/individual', json={'descripcion': descripcion})

    async def alternativa_individual(self, texto: str) -> tuple[dict | None, str | None]:
        """Consulta agregada que sustituye a una petición individual, sin pasar por el LLM.

        "El viaje de las 3:12 del 15 de enero desde Times Square" -> viajes de esa zona de 3:00 a 4:00 de
        ese día. Si falta el día no se inventa: se devuelve solo una pista para el usuario.
        """
        zona = zona_en_texto(texto, await self.zonas())
        if zona is None:
            return None, None
        dia, hora = fecha_en_texto(texto), hora_en_texto(texto)
        franja = f'entre las {hora:02d}:00 y las {(hora + 1) % 24:02d}:00' if hora is not None else 'por horas'
        if dia is None:
            return None, f'Si me dices el día, puedo decirte cuántos viajes salieron de {zona["nombre"]} {franja}.'
        desde = dia + timedelta(hours=hora or 0)
        hasta = desde + (timedelta(hours=1) if hora is not None else timedelta(days=1))
        return {'nivel': 'hora_zona', 'fuente': 'historico', 'desde': _iso(desde), 'hasta': _iso(hasta),
                'metricas': ['n_viajes'], 'zona_origen': zona['_id']}, None

    async def rechazo_destino(self, texto: str) -> tuple[dict, dict | None, str | None] | None:
        """Si la pregunta pide un destino por zona: el rechazo (registrado en la API), la alternativa por
        barrios de ese día y, si falta el día, una pista. None si la pregunta no pide eso."""
        par = destino_por_zona(texto, await self.zonas())
        if par is None:
            return None
        origen, zona = par
        registro = await self.solicitud_individual(f'destino por zona: {texto}')
        registrado = registro.get('resultado') if isinstance(registro, dict) else None
        rechazo = {'resultado': 'rechazada', 'registro': registrado,
                   'motivos': [f'el destino no se publica por zona ({zona["nombre"]}), solo por barrio y día: origen, '
                               'destino y hora juntos pueden identificar a una persona']}
        dia = fecha_en_texto(texto)
        if dia is None:
            return rechazo, None, (f'Si me dices el día, puedo darte los viajes de {origen} a {zona["barrio"]} '
                                   'de ese día.')
        return rechazo, {'nivel': 'od_dia_barrio', 'fuente': 'historico', 'desde': _iso(dia),
                         'hasta': _iso(dia + timedelta(days=1)), 'metricas': ['n_viajes'],
                         'barrio_origen': origen, 'barrio_destino': zona['barrio']}, None

    async def ejecutar(self, nombre: str, argumentos: dict) -> Any:
        if nombre not in {e['function']['name'] for e in ESQUEMAS}:
            return {'error': f'herramienta desconocida: {nombre}'}
        herramienta = getattr(self, nombre)
        try:
            inspect.signature(herramienta).bind(**argumentos)
        except TypeError as e:                      # argumentos que la herramienta no admite
            return {'error': f'argumentos no válidos para {nombre}: {e}'}
        return await herramienta(**argumentos)

    async def cerrar(self) -> None:
        await self.http.aclose()
