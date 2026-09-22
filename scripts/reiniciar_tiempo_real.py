"""Reinicia el tiempo real desde cero (T11): para dejarlo listo para una demo o una captura en directo nueva.

El trabajo de Spark descarta los viajes que llegan más de 2 h por detrás del más reciente que ha visto (watermark),
y esa marca vive en su checkpoint. Tras unas pruebas con viajes de finales de 2020 (`make latencia`, por ejemplo),
nada anterior se vuelve a agregar. Este script, en orden:

  1. para el trabajo `pids-tiempo-real` (mata el driver supervisado, para que el máster no lo relance);
  2. borra su checkpoint (`/opt/spark/checkpoints/tiempo_real`, volumen `spark-checkpoints`);
  3. recorta el topic `viajes-crudos` hasta el final: el trabajo lee desde el principio y, si no, volvería a ver
     los mismos viajes de prueba (ya están archivados en `s3://crudo/validos/tiempo_real`);
  4. vacía las colecciones `publico.tr_*` (solo agregados de tiempo real; el histórico no se toca);
  5. relanza el trabajo (`/opt/pids/lanzar.sh TiempoReal`).

Uso (desde la raíz, con la plataforma levantada):
    make tiempo-real-reiniciar          # pide confirmación
    uv run python scripts/reiniciar_tiempo_real.py --si
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
APLICACION = 'pids-tiempo-real'
CHECKPOINT = '/opt/spark/checkpoints/tiempo_real'
TOPIC = 'viajes-crudos'
COLECCIONES_TR = ('tr_viajes_hora_zona', 'tr_viajes_dia_barrio', 'tr_od_dia_barrio')


def compose(*args: str, entrada: str | None = None, comprobar: bool = True) -> str:
    r = subprocess.run(['docker', 'compose', *args], cwd=RAIZ, input=entrada, capture_output=True, text=True)
    if comprobar and r.returncode != 0:
        raise RuntimeError(f'docker compose {" ".join(args[:3])}…: {(r.stderr or r.stdout).strip()}')
    return r.stdout


def estado_spark() -> dict:
    return json.loads(compose('exec', '-T', 'spark-master', 'curl', '-sf', 'http://127.0.0.1:8080/json/'))


def drivers_activos(estado: dict) -> list[str]:
    return [d['id'] for d in estado.get('activedrivers', []) if d.get('mainclass') == 'pids.TiempoReal']


def parar_trabajo() -> None:
    drivers = drivers_activos(estado_spark())
    for driver in drivers:
        compose('exec', '-T', 'spark-master', '/opt/spark/bin/spark-class', 'org.apache.spark.deploy.Client',
                'kill', 'spark://spark-master:7077', driver)
    limite = time.monotonic() + 90
    while time.monotonic() < limite:
        estado = estado_spark()
        if not drivers_activos(estado) and not any(a.get('name') == APLICACION for a in estado.get('activeapps', [])):
            print(f'  1. trabajo parado ({len(drivers)} driver)' if drivers else '  1. no había trabajo en marcha')
            return
        time.sleep(3)
    raise RuntimeError('el trabajo de tiempo real no se ha parado en 90 s')


def borrar_checkpoint() -> None:
    compose('exec', '-T', 'spark-master', 'rm', '-rf', CHECKPOINT)
    print(f'  2. checkpoint borrado ({CHECKPOINT})')


def recortar_topic() -> None:
    descripcion = json.loads(compose('exec', '-T', 'redpanda', 'rpk', 'topic', 'describe', TOPIC, '-p',
                                     '--format', 'json'))
    fin = {str(p['partition']): p['high_watermark'] for p in descripcion[0]['partitions']}
    for particion, desplazamiento in sorted(fin.items()):
        compose('exec', '-T', 'redpanda', 'rpk', 'topic', 'trim-prefix', TOPIC, '--offset', str(desplazamiento),
                '--partitions', particion, '--no-confirm')
    print(f'  3. topic {TOPIC} recortado hasta el final ({len(fin)} particiones)')


def vaciar_colecciones() -> None:
    orden = '; '.join(f'print("{c}: " + db.getSiblingDB("publico").{c}.deleteMany({{}}).deletedCount)'
                      for c in COLECCIONES_TR)
    # la contraseña del administrador la pone Compose dentro del contenedor: no pasa por esta línea de órdenes
    salida = compose('exec', '-T', 'mongo', 'sh', '-c',
                     'mongosh --quiet -u "$MONGO_INITDB_ROOT_USERNAME" -p "$MONGO_INITDB_ROOT_PASSWORD" '
                     f'--authenticationDatabase admin --eval \'{orden}\'')
    print('  4. colecciones vaciadas: ' + ', '.join(l.strip() for l in salida.splitlines() if ':' in l))


def relanzar() -> None:
    compose('exec', '-T', 'spark-master', '/opt/pids/lanzar.sh', 'TiempoReal')
    limite = time.monotonic() + 120
    while time.monotonic() < limite:
        if any(a.get('name') == APLICACION for a in estado_spark().get('activeapps', [])):
            print('  5. trabajo relanzado y en marcha')
            return
        time.sleep(3)
    raise RuntimeError('el trabajo no aparece como activo tras relanzarlo: mira `make logs S=spark-master`')


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--si', action='store_true', help='no pedir confirmación')
    args = p.parse_args()
    if not args.si:
        respuesta = input('Se borran los agregados de tiempo real (tr_*) y los viajes pendientes de la cola. '
                          'El histórico no se toca. ¿Seguir? [s/N] ')
        if respuesta.strip().lower() not in ('s', 'si', 'sí'):
            print('Cancelado')
            return 1
    try:
        parar_trabajo()
        borrar_checkpoint()
        recortar_topic()
        vaciar_colecciones()
        relanzar()
    except (RuntimeError, ValueError) as error:
        print(f'Error: {error}', file=sys.stderr)
        return 1
    print('Tiempo real desde cero: la captura en directo empieza por el primer día preparado.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
