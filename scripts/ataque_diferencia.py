"""Ataque por diferencia contra la plataforma, usando solo la API de acceso (como un analista externo).

La plataforma publica los mismos viajes en varios niveles. Si un nivel «padre» (viajes por día y barrio)
es visible y en uno «hijo» del mismo día y barrio hay UN solo grupo suprimido, restar basta para saber
su valor exacto:

    grupo oculto = total del día y barrio − suma de los grupos visibles

Se prueban dos vectores:
  · hora_zona:     los grupos por hora y zona de un día suman el total del día en su barrio.
  · od_dia_barrio: los flujos que salen de un barrio en un día suman el total del día en ese barrio.
Si el total de un día y barrio está suprimido pero todos sus flujos de salida son visibles, el atacante
lo reconstruye sumándolos y lo usa igual (así se comprueba que ocultar el total basta de verdad).

Solo se manejan recuentos de grupos (ningún viaje individual). Todas las consultas quedan en la
auditoría de la plataforma con el cliente de la clave usada.

Uso (con la plataforma levantada):
    source .env && uv run python scripts/ataque_diferencia.py --dias 60
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from pathlib import Path

import requests

RAIZ = Path(__file__).resolve().parents[1]
K_MINIMO = json.loads((RAIZ / 'config' / 'privacidad.json').read_text(encoding='utf-8'))['k_minimo']


# --- análisis (lógica pura) -------------------------------------------------------------------

@dataclass
class Particion:
    """Un día y un barrio: el total publicado y los grupos hijos (None = suprimido)."""
    dia: str
    barrio: str
    total: int
    visibles: list[int] = field(default_factory=list)
    suprimidos: int = 0

    @property
    def oculto(self) -> int:
        """Viajes que suman entre todos los grupos suprimidos."""
        return self.total - sum(self.visibles)


def rango_por_grupo(oculto: int, suprimidos: int, k: int = K_MINIMO) -> tuple[int, int] | None:
    """Valores posibles de CADA grupo suprimido, suponiendo que todos tienen entre 1 y k-1 viajes.

    Devuelve None si esa suposición es imposible (la suma oculta no cabe): entonces algún grupo
    suprimido tiene k o más viajes, que es justo lo que provoca la supresión complementaria, y el
    atacante ya no puede acotar nada con esta cuenta.
    """
    if suprimidos == 0:
        return None
    if not suprimidos <= oculto <= suprimidos * (k - 1):
        return None
    minimo = max(1, oculto - (k - 1) * (suprimidos - 1))
    maximo = min(k - 1, oculto - (suprimidos - 1))
    return minimo, maximo


def clasificar(p: Particion, k: int = K_MINIMO) -> str:
    """'sin_suprimidos', 'revelado' (valor exacto), 'acotado' (rango de 1 o 2 valores) o 'protegido'."""
    if p.suprimidos == 0:
        return 'sin_suprimidos'
    rango = rango_por_grupo(p.oculto, p.suprimidos, k)
    if rango is None:
        return 'protegido'
    ancho = rango[1] - rango[0]
    if ancho == 0:
        return 'revelado'
    return 'acotado' if ancho <= 1 else 'protegido'


def resumir(particiones: list[Particion], k: int = K_MINIMO) -> dict:
    conteo: dict[str, int] = defaultdict(int)
    grupos_revelados = 0
    for p in particiones:
        clase = clasificar(p, k)
        conteo[clase] += 1
        if clase == 'revelado':
            grupos_revelados += p.suprimidos      # todos los suprimidos de la partición quedan fijados
    con_suprimidos = sum(v for c, v in conteo.items() if c != 'sin_suprimidos')
    return {
        'particiones': len(particiones),
        'con_suprimidos': con_suprimidos,
        'reveladas': conteo['revelado'],
        'acotadas': conteo['acotado'],
        'protegidas': conteo['protegido'],
        'grupos_revelados': grupos_revelados,
        'pct_reveladas': round(100 * conteo['revelado'] / con_suprimidos, 1) if con_suprimidos else 0.0,
    }


# --- acceso a la API --------------------------------------------------------------------------

class ClienteApi:
    def __init__(self, url: str, clave: str):
        self.url = url.rstrip('/')
        self.sesion = requests.Session()
        self.sesion.headers['X-API-Key'] = clave
        self.consultas = 0

    def filas(self, nivel: str, desde: datetime, hasta: datetime, metricas=('n_viajes',)) -> list[dict]:
        self.consultas += 1
        r = self.sesion.post(f'{self.url}/consultas', timeout=60, json={
            'nivel': nivel, 'desde': desde.isoformat(), 'hasta': hasta.isoformat(), 'metricas': list(metricas)})
        if r.status_code != 200:
            raise RuntimeError(f'{nivel} {desde:%Y-%m-%d %H}h: HTTP {r.status_code} {r.text[:200]}')
        cuerpo = r.json()
        if cuerpo.get('truncada'):
            raise RuntimeError(f'{nivel} {desde}: respuesta truncada; hay que trocear más la consulta')
        return cuerpo['filas']


def _valor(fila: dict) -> int | None:
    return None if fila.get('suprimido') else int(fila['n_viajes'])


def totales_del_dia(dia_barrio: list[dict], od: list[dict]) -> tuple[dict[str, int], dict[str, int]]:
    """Totales por barrio que conoce el atacante: los publicados y, si un total está suprimido pero
    todos los flujos que salen de ese barrio son visibles, el que se reconstruye sumándolos.

    Devuelve (publicados, reconstruidos).
    """
    publicados = {f['barrio_origen']: n for f in dia_barrio if (n := _valor(f)) is not None}
    suprimidos = {f['barrio_origen'] for f in dia_barrio if f.get('suprimido')}
    flujos: dict[str, list[int | None]] = defaultdict(list)
    for f in od:
        flujos[f.get('barrio_origen') or 'desconocido'].append(_valor(f))
    reconstruidos = {b: sum(v) for b, v in flujos.items()
                     if b in suprimidos and v and all(n is not None for n in v)}
    return publicados, reconstruidos


def particiones_de_un_dia(api: ClienteApi, dia: datetime) -> tuple[list[Particion], list[Particion]]:
    """Las particiones (día, barrio) de los dos vectores de ataque para un día."""
    manana = dia + timedelta(days=1)
    od = api.filas('od_dia_barrio', dia, manana)
    publicados, reconstruidos = totales_del_dia(api.filas('dia_barrio', dia, manana), od)
    totales = publicados | reconstruidos      # un total suprimido sirve si se puede reconstruir

    def nueva(barrio: str) -> Particion:
        return Particion(dia=f'{dia:%Y-%m-%d}', barrio=barrio, total=totales[barrio])

    por_hora: dict[str, Particion] = {}
    for h in range(24):                     # por horas: un día entero supera las 500 filas por respuesta
        inicio = dia + timedelta(hours=h)
        for f in api.filas('hora_zona', inicio, inicio + timedelta(hours=1)):
            barrio = f.get('barrio_origen') or 'desconocido'
            if barrio not in totales:
                continue
            p = por_hora.setdefault(barrio, nueva(barrio))
            n = _valor(f)
            if n is None:
                p.suprimidos += 1
            else:
                p.visibles.append(n)

    por_destino: dict[str, Particion] = {}
    for f in od:
        barrio = f.get('barrio_origen') or 'desconocido'
        if barrio not in publicados:          # un total reconstruido desde estos mismos flujos no aporta
            continue
        p = por_destino.setdefault(barrio, nueva(barrio))
        n = _valor(f)
        if n is None:
            p.suprimidos += 1
        else:
            p.visibles.append(n)
    return list(por_hora.values()), list(por_destino.values())


def dias_de_muestra(n: int) -> list[datetime]:
    """n días repartidos por todo 2020 (366 días)."""
    paso = 366 / n
    return [datetime(2020, 1, 1) + timedelta(days=int(i * paso)) for i in range(n)]


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--dias', type=int, default=60, help='días de 2020 a atacar (repartidos por el año)')
    p.add_argument('--url', default=os.environ.get('ACCESO_URL', 'http://localhost:8002'))
    p.add_argument('--clave', default=os.environ.get('ACCESO_CLAVE_EQUIPO'))
    p.add_argument('--salida', type=Path, default=None, help='JSON con el detalle (por defecto en informes/)')
    args = p.parse_args()
    if not args.clave:
        print('Falta la clave de la API (--clave o ACCESO_CLAVE_EQUIPO; haz source .env)', file=sys.stderr)
        return 2

    api = ClienteApi(args.url, args.clave)
    vectores: dict[str, list[Particion]] = {'hora_zona': [], 'od_dia_barrio': []}
    for i, dia in enumerate(dias_de_muestra(args.dias), 1):
        por_hora, por_destino = particiones_de_un_dia(api, dia)
        vectores['hora_zona'] += por_hora
        vectores['od_dia_barrio'] += por_destino
        print(f'\r  {i}/{args.dias} días atacados ({api.consultas} consultas)', end='', flush=True)
    print()

    resultado = {'fecha': datetime.now().isoformat(timespec='seconds'), 'k_minimo': K_MINIMO,
                 'dias': args.dias, 'consultas': api.consultas,
                 'vectores': {v: resumir(ps) for v, ps in vectores.items()}}
    print(f'\nAtaque por diferencia sobre {args.dias} días ({api.consultas} consultas a la API), k = {K_MINIMO}\n')
    print('| vector | particiones con suprimidos | reveladas (valor exacto) | acotadas (±1) | protegidas | grupos revelados |')
    print('|---|---|---|---|---|---|')
    for v, r in resultado['vectores'].items():
        print(f"| {v} | {r['con_suprimidos']} | {r['reveladas']} ({r['pct_reveladas']} %) | {r['acotadas']} | "
              f"{r['protegidas']} | {r['grupos_revelados']} |")

    salida = args.salida or RAIZ / 'informes' / f'ataque_diferencia_{datetime.now():%Y%m%d_%H%M%S}.json'
    salida.parent.mkdir(parents=True, exist_ok=True)
    detalle = {v: [asdict(pa) | {'oculto': pa.oculto, 'clase': clasificar(pa)} for pa in ps]
               for v, ps in vectores.items()}
    salida.write_text(json.dumps(resultado | {'detalle': detalle}, ensure_ascii=False, indent=1), encoding='utf-8')
    print(f'\nDetalle en {salida.relative_to(RAIZ) if salida.is_relative_to(RAIZ) else salida}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
