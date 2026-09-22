"""Prueba de alta disponibilidad de la API de acceso (T09): carga continua mientras cae una réplica y vuelve.

Manda peticiones al proxy (http://127.0.0.1:PUERTO_ACCESO) con la clave `equipo`: GET /catalogo, que no deja
rastro en la auditoría, y una de cada cinco POST /consultas de un día y barrio, que sí queda, como cualquier
consulta. Mientras tanto:

  1. las dos réplicas en marcha
  2. `docker compose stop acceso-a` (parada ordenada) y, con solo acceso-b, una pregunta al chatbot
  3. `docker compose start acceso-a` y espera a que esté sana
  4. `docker compose kill acceso-b` (caída brusca, sin terminar lo que tenga en curso)
  5. `docker compose start acceso-b`

Por fase: peticiones, errores, latencia p50/p95 y qué réplica ha contestado (cabecera X-Replica que pone el
proxy). Sale con código 1 si alguna petición ha fallado o el chatbot no ha respondido.

Uso (desde la raíz, con la plataforma y el chatbot levantados):
    uv run python scripts/probar_alta_disponibilidad.py
    uv run python scripts/probar_alta_disponibilidad.py --segundos 15 --ritmo 30 --sin-chatbot
"""
from __future__ import annotations

import argparse
import asyncio
import os
import statistics
import subprocess
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

import httpx

RAIZ = Path(__file__).resolve().parents[1]
CONSULTA = {'nivel': 'dia_barrio', 'desde': '2020-03-03T00:00:00', 'hasta': '2020-03-04T00:00:00',
            'barrio_origen': 'Manhattan'}
PREGUNTA_CHATBOT = '¿Qué barrio tuvo más viajes el 3 de marzo?'


def entorno() -> dict[str, str]:
    valores = {}
    ruta = RAIZ / '.env'
    if ruta.is_file():
        for linea in ruta.read_text(encoding='utf-8').splitlines():
            if '=' in linea and not linea.lstrip().startswith('#'):
                clave, valor = linea.split('=', 1)
                valores[clave.strip()] = valor.strip().strip('"\'')
    return {**valores, **os.environ}


def compose(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(['docker', 'compose', *args], cwd=RAIZ, capture_output=True, text=True, check=False)


async def en_hilo(*args: str) -> subprocess.CompletedProcess:
    return await asyncio.to_thread(compose, *args)


async def esperar_sana(servicio: str, limite: float = 90) -> float:
    """Segundos hasta que el healthcheck de Docker da `healthy`."""
    inicio = time.monotonic()
    while time.monotonic() - inicio < limite:
        ident = (await en_hilo('ps', '-q', servicio)).stdout.strip()
        if ident:
            estado = await asyncio.to_thread(
                subprocess.run, ['docker', 'inspect', '-f', '{{.State.Health.Status}}', ident],
                capture_output=True, text=True, check=False)
            if estado.stdout.strip() == 'healthy':
                return time.monotonic() - inicio
        await asyncio.sleep(1)
    raise RuntimeError(f'{servicio} no está sana tras {limite:.0f} s')


class Carga:
    """Peticiones a ritmo fijo; cada resultado se apunta en la fase en la que salió."""

    def __init__(self, url: str, clave: str, ritmo: float):
        self.http = httpx.AsyncClient(base_url=url, headers={'X-API-Key': clave}, timeout=10)
        self.ritmo = ritmo
        self.fase = ''
        self.resultados: dict[str, list[tuple[bool, float, str, str]]] = defaultdict(list)
        self.activa = True

    async def una(self, n: int) -> None:
        fase = self.fase
        inicio = time.monotonic()
        try:
            if n % 5 == 0:
                r = await self.http.post('/consultas', json=CONSULTA)
            else:
                r = await self.http.get('/catalogo')
            ok, detalle = r.status_code == 200, '' if r.status_code == 200 else f'HTTP {r.status_code}'
            replica = r.headers.get('x-replica', '?')
        except httpx.HTTPError as error:
            ok, detalle, replica = False, type(error).__name__, '-'
        self.resultados[fase].append((ok, (time.monotonic() - inicio) * 1000, replica, detalle))

    async def correr(self) -> None:
        tareas, n = set(), 0
        while self.activa:
            tarea = asyncio.create_task(self.una(n))
            tareas.add(tarea)
            tarea.add_done_callback(tareas.discard)
            n += 1
            await asyncio.sleep(1 / self.ritmo)
        await asyncio.gather(*tareas)
        await self.http.aclose()


async def preguntar_al_chatbot() -> tuple[bool, str]:
    r = await en_hilo('exec', '-T', 'chatbot', 'python', 'comprobar_agente.py', PREGUNTA_CHATBOT)
    salida = (r.stdout + r.stderr).strip()
    linea = next((l for l in reversed(salida.splitlines()) if l.strip()), '')
    return r.returncode == 0 and any(c.isdigit() for c in salida.split('Pregunta:')[-1]), linea[:160]


async def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--segundos', type=float, default=10, help='duración de cada fase con carga (por defecto 10)')
    p.add_argument('--ritmo', type=float, default=20, help='peticiones por segundo (por defecto 20)')
    p.add_argument('--sin-chatbot', action='store_true', help='no pregunta al chatbot con una réplica parada')
    args = p.parse_args()
    cfg = entorno()
    carga = Carga(f'http://127.0.0.1:{cfg.get("PUERTO_ACCESO", "8002")}', cfg['ACCESO_CLAVE_EQUIPO'], args.ritmo)
    for servicio in ('acceso-a', 'acceso-b', 'acceso'):
        await esperar_sana(servicio)
    chatbot = (True, 'sin comprobar')

    corredor = asyncio.create_task(carga.correr())
    pasos = [
        ('1 · las dos réplicas', None),
        ('2 · acceso-a parada (stop)', ('stop', 'acceso-a')),
        ('3 · acceso-a vuelve', ('start', 'acceso-a')),
        ('4 · acceso-b caída (kill)', ('kill', 'acceso-b')),
        ('5 · acceso-b vuelve', ('start', 'acceso-b')),
    ]
    for fase, orden in pasos:
        carga.fase = fase
        inicio = time.monotonic()
        if orden:
            r = await en_hilo(*orden)
            if r.returncode != 0:
                raise RuntimeError(f'docker compose {" ".join(orden)}: {r.stderr.strip()}')
            if orden[0] == 'start':
                segundos = await esperar_sana(orden[1])
                print(f'  {orden[1]} sana otra vez en {segundos:.1f} s', flush=True)
        if orden == ('stop', 'acceso-a') and not args.sin_chatbot:
            chatbot = await preguntar_al_chatbot()
            print(f'  chatbot con una sola réplica: {"responde" if chatbot[0] else "NO responde"} · {chatbot[1]}',
                  flush=True)
        await asyncio.sleep(max(0.0, args.segundos - (time.monotonic() - inicio)))
    carga.activa = False
    await corredor

    fallos_totales = 0
    print(f'\n{"fase":<30} {"peticiones":>10} {"fallos":>7} {"p50 ms":>8} {"p95 ms":>8}  réplicas')
    for fase, _ in pasos:
        filas = carga.resultados.get(fase, [])
        fallos = [f for f in filas if not f[0]]
        fallos_totales += len(fallos)
        tiempos = sorted(f[1] for f in filas)
        p50 = statistics.median(tiempos) if tiempos else 0
        p95 = tiempos[int(0.95 * (len(tiempos) - 1))] if tiempos else 0
        reparto = ', '.join(f'{r} {n}' for r, n in sorted(Counter(f[2] for f in filas if f[0]).items()))
        print(f'{fase:<30} {len(filas):>10} {len(fallos):>7} {p50:>8.0f} {p95:>8.0f}  {reparto}')
        for detalle, n in Counter(f[3] for f in fallos).items():
            print(f'{"":<30} {"":>10} {n:>7}  {detalle}')
    total = sum(len(v) for v in carga.resultados.values())
    print(f'\n{total} peticiones, {fallos_totales} fallos · chatbot con una réplica parada: '
          f'{"responde" if chatbot[0] else "NO responde"}')
    return 0 if fallos_totales == 0 and chatbot[0] else 1


if __name__ == '__main__':
    sys.exit(asyncio.run(main()))
