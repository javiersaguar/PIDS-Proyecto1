"""Regenera tablas, figuras e informe.md de un experimento YA entrenado (sin reentrenar).

Uso:
    python evaluar.py --experimento completo
    python evaluar.py --experimento resultados/completo
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from hgr import cli, constantes as C  # noqa: E402


def main():
    cli.configurar_consola()
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--experimento', required=True, help='nombre o ruta de la carpeta del experimento')
    args = p.parse_args()
    d = Path(args.experimento)
    if not (d / 'config.json').exists():
        d = C.DIR_RESULTADOS / args.experimento
    if not (d / 'config.json').exists():
        print('[ERROR] no encuentro el experimento %s' % args.experimento)
        return 2
    from hgr.evaluacion import agregar
    res = agregar(d)
    print('Mejor en %s: %s con %s -> %.1f%%' % (res['referencia'], res['mejor']['modelo'],
                                               res['mejor']['normalizacion'], 100 * res['mejor']['accuracy']))
    return 0


if __name__ == '__main__':
    sys.exit(main())
