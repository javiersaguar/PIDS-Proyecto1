"""Genera .env a partir de .env.example rellenando cada valor vacío con una clave aleatoria.

No sobrescribe un .env existente (usa --forzar para regenerarlo; cambiar las claves obliga a
recrear los volúmenes de MongoDB y Airflow, porque los usuarios se crean al inicializarlos).
"""
from __future__ import annotations

import argparse
import base64
import os
import secrets
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]


def valor_para(clave: str) -> str:
    if clave == 'AIRFLOW_FERNET_KEY':
        return base64.urlsafe_b64encode(os.urandom(32)).decode()
    if clave.endswith('ACCESS_KEY'):
        return secrets.token_hex(10).upper()
    return secrets.token_urlsafe(24)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--forzar', action='store_true')
    args = p.parse_args()
    destino = RAIZ / '.env'
    if destino.exists() and not args.forzar:
        print('.env ya existe; no se toca (usa --forzar para regenerarlo)')
        return 0
    lineas = []
    for linea in (RAIZ / '.env.example').read_text(encoding='utf-8').splitlines():
        if '=' in linea and not linea.lstrip().startswith('#'):
            clave, valor = linea.split('=', 1)
            if not valor:
                linea = f'{clave}={valor_para(clave)}'
        lineas.append(linea)
    destino.write_text('\n'.join(lineas) + '\n', encoding='utf-8')
    destino.chmod(0o600)
    print('.env generado con claves aleatorias')
    return 0


if __name__ == '__main__':
    sys.exit(main())
