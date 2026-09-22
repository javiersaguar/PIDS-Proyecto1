"""Regla del grupo: en el repositorio solo figuramos los cinco del grupo como autores.

Rechaza las líneas que atribuyen un commit o un pull request a alguien de fuera: trailers
`Co-Authored-By`, firmas automáticas del tipo «Generated with …» y el emoji de robot con el que
algunas herramientas las acompañan. Ver docs/repositorio.md.

Tres usos:
  --mensaje FICHERO [--limpiar]   hook commit-msg (.githooks/commit-msg): con --limpiar quita las
                                  líneas prohibidas del mensaje en lugar de rechazar el commit
  --rango BASE..CABEZA            CI: revisa los mensajes de esos commits
  --texto                         CI: revisa el título y la descripción del pull request (entrada estándar)
Sale con código 1 si encuentra alguna línea prohibida.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

PROHIBIDAS = [
    re.compile(r'^\s*co-authored-by\s*:', re.IGNORECASE),
    re.compile(r'generated (with|by)\b', re.IGNORECASE),
    re.compile('\N{ROBOT FACE}'),
]


def prohibida(linea: str) -> bool:
    return any(p.search(linea) for p in PROHIBIDAS)


def lineas_prohibidas(texto: str) -> list[str]:
    return [l.strip() for l in texto.splitlines() if prohibida(l)]


def limpiar(texto: str) -> str:
    lineas = [l for l in texto.splitlines() if not prohibida(l)]
    while lineas and not lineas[-1].strip():
        lineas.pop()
    return '\n'.join(lineas) + '\n'


def commits_del_rango(rango: str) -> list[tuple[str, str]]:
    salida = subprocess.run(['git', 'log', '--format=%H%x00%B%x01', rango],
                            check=True, capture_output=True, text=True).stdout
    commits = []
    for bloque in salida.split('\x01'):
        if '\x00' in bloque:
            sha, cuerpo = bloque.split('\x00', 1)
            commits.append((sha.strip()[:7], cuerpo))
    return commits


def informar(donde: str, encontradas: list[str]) -> None:
    for linea in encontradas:
        print(f'  {donde}: {linea}', file=sys.stderr)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument('--mensaje', type=Path)
    g.add_argument('--rango')
    g.add_argument('--texto', action='store_true')
    p.add_argument('--limpiar', action='store_true')
    a = p.parse_args(argv)

    if a.mensaje:
        texto = a.mensaje.read_text(encoding='utf-8')
        encontradas = lineas_prohibidas(texto)
        if not encontradas:
            return 0
        if a.limpiar:
            a.mensaje.write_text(limpiar(texto), encoding='utf-8')
            print('Quitadas del mensaje del commit (en el repositorio solo figura el grupo como autor):',
                  file=sys.stderr)
            informar('mensaje', encontradas)
            return 0
        print('Mensaje de commit con atribuciones prohibidas:', file=sys.stderr)
        informar('mensaje', encontradas)
        return 1

    if a.texto:
        encontradas = lineas_prohibidas(sys.stdin.read())
        if encontradas:
            print('El título o la descripción del pull request tiene atribuciones prohibidas. '
                  'Edítalo y quita estas líneas:', file=sys.stderr)
            informar('pull request', encontradas)
            return 1
        print('Pull request sin atribuciones prohibidas.')
        return 0

    malos = 0
    commits = commits_del_rango(a.rango)
    for sha, cuerpo in commits:
        encontradas = lineas_prohibidas(cuerpo)
        if encontradas:
            malos += 1
            informar(f'commit {sha}', encontradas)
    if malos:
        print(f'{malos} commit(s) con atribuciones prohibidas. Hay que reescribirlos antes de fusionar '
              '(docs/repositorio.md, «Si se cuela una coautoría»).', file=sys.stderr)
        return 1
    print(f'{len(commits)} commit(s) revisados: solo autores del grupo.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
