"""Piezas comunes de los scripts de linea de comandos."""
import argparse
import sys
from pathlib import Path

from . import constantes as C
from . import utils


def configurar_consola():
    utils.silenciar_tf()
    for flujo in (sys.stdout, sys.stderr):
        try:
            flujo.reconfigure(encoding='utf-8', errors='replace')
        except (AttributeError, ValueError):
            pass


def argumentos_datos(p):
    g = p.add_argument_group('datos')
    g.add_argument('--datos', nargs='+', type=Path, default=None,
                   help='carpetas donde buscar tomas (por defecto: entrenamiento/datos y kit-grabacion/HAR_mediapipe/data)')
    g.add_argument('--incluir-pruebas', action='store_true', help='usar tambien las tomas grabadas con --prueba')
    g.add_argument('--incluir-incompletas', action='store_true', help='usar tambien tomas con estado interrumpida/en_curso/incompleta')
    g.add_argument('--min-deteccion', type=float, default=0.5, help='umbral de deteccion de MediaPipe (0.5)')
    g.add_argument('--workers', type=int, default=utils.workers_por_defecto(), help='procesos en paralelo')
    g.add_argument('--reextraer', action='store_true', help='ignorar la cache de landmarks')
    return p


def argumentos_computo(p):
    g = p.add_argument_group('cómputo y hardware')
    g.add_argument('--dispositivo', choices=['auto', 'gpu', 'cpu'], default='auto',
                   help='dispositivo para entrenar redes (auto: usa GPU CUDA si está disponible)')
    g.add_argument('--workers-gpu', type=int, default=6,
                   help='número máximo de procesos concurrentes con acceso a GPU (por defecto 6)')
    return p


def cargar_dataset(args, log=print):
    from .extraccion import extraer_tomas
    from .tomas import descubrir_tomas
    raices = args.datos or C.RAICES_DATOS_POR_DEFECTO
    avisos = []
    tomas = descubrir_tomas(raices, incluir_pruebas=getattr(args, 'incluir_pruebas', False),
                            incluir_incompletas=getattr(args, 'incluir_incompletas', False),
                            avisos=avisos)
    log('Tomas encontradas en %s:' % ', '.join(str(r) for r in raices))
    if not tomas:
        log('  (ninguna)')
        return tomas, None, avisos
    for t in tomas:
        log('  %-32s participante %-4s mano %-9s estado %-12s %s'
            % (t.nombre, t.participante, t.mano or '-', t.estado, '[PRUEBA]' if t.prueba else ''))
    df = extraer_tomas(tomas, workers=args.workers, min_deteccion=args.min_deteccion, forzar=args.reextraer,
                       log=log, avisos=avisos)
    return tomas, df, avisos


def lista(valor, validos):
    if valor == ['todos'] or valor == ['todas']:
        return list(validos)
    malos = [v for v in valor if v not in validos]
    if malos:
        raise argparse.ArgumentTypeError('valores no validos %s; opciones: %s' % (malos, validos))
    return valor
