"""Genera .env a partir de .env.example rellenando cada valor vacío con una clave aleatoria.

No sobrescribe un .env existente (usa --forzar para regenerarlo; cambiar las claves obliga a
recrear los volúmenes de MongoDB y Airflow, porque los usuarios se crean al inicializarlos).
Con --completar añade a un .env existente las variables nuevas de .env.example sin tocar las demás.

Las claves de proveedores externos (LLM_API_KEY, NGROK_AUTHTOKEN, NGROK_DOMINIO) no se inventan: se dejan vacías
para pegarlas a mano.
"""
from __future__ import annotations

import argparse
import base64
import os
import secrets
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
SIN_RELLENO = {'LLM_API_KEY', 'NGROK_AUTHTOKEN', 'NGROK_DOMINIO'}


def valor_para(clave: str) -> str:
    if clave in SIN_RELLENO:
        return ''
    if clave == 'AIRFLOW_FERNET_KEY':
        return base64.urlsafe_b64encode(os.urandom(32)).decode()
    if clave.endswith('ACCESS_KEY'):
        return secrets.token_hex(10).upper()
    return secrets.token_urlsafe(24)


def variables(lineas: list[str]) -> dict[str, str]:
    pares = (l.split('=', 1) for l in lineas if '=' in l and not l.lstrip().startswith('#'))
    return {clave.strip(): valor for clave, valor in pares}


def generar(plantilla: list[str]) -> list[str]:
    lineas = []
    for linea in plantilla:
        if '=' in linea and not linea.lstrip().startswith('#'):
            clave, valor = linea.split('=', 1)
            if not valor:
                linea = f'{clave}={valor_para(clave)}'
        lineas.append(linea)
    return lineas


def completar(actual: list[str], plantilla: list[str]) -> tuple[list[str], list[str]]:
    """Añade al final las variables de la plantilla que faltan. Devuelve (líneas, claves añadidas)."""
    existentes = variables(actual)
    nuevas = [l for l in generar(plantilla) if '=' in l and not l.lstrip().startswith('#')
              and l.split('=', 1)[0] not in existentes]
    if not nuevas:
        return actual, []
    lineas = [l for l in actual]
    while lineas and not lineas[-1].strip():
        lineas.pop()
    lineas += ['', '# --- añadido por generar_env.py --completar ---', *nuevas]
    return lineas, [l.split('=', 1)[0] for l in nuevas]


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--forzar', action='store_true', help='regenera un .env existente')
    p.add_argument('--completar', action='store_true', help='añade a .env las variables que falten')
    args = p.parse_args()
    destino = RAIZ / '.env'
    plantilla = (RAIZ / '.env.example').read_text(encoding='utf-8').splitlines()
    if destino.exists() and args.completar:
        lineas, anadidas = completar(destino.read_text(encoding='utf-8').splitlines(), plantilla)
        if not anadidas:
            print('.env ya tiene todas las variables de .env.example')
            return 0
        destino.write_text('\n'.join(lineas) + '\n', encoding='utf-8')
        destino.chmod(0o600)
        print('Añadidas a .env: ' + ', '.join(anadidas))
        vacias = [c for c in anadidas if c in SIN_RELLENO]
        if vacias:
            print('Rellena a mano: ' + ', '.join(vacias))
        return 0
    if destino.exists() and not args.forzar:
        print('.env ya existe; no se toca (usa --forzar para regenerarlo o --completar para añadir lo nuevo)')
        return 0
    destino.write_text('\n'.join(generar(plantilla)) + '\n', encoding='utf-8')
    destino.chmod(0o600)
    print('.env generado con claves aleatorias' + (f' (rellena a mano: {", ".join(sorted(SIN_RELLENO))})'))
    return 0


if __name__ == '__main__':
    sys.exit(main())
