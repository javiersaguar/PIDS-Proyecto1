"""Cliente de gestos (parte 1 -> parte 2): envía a la API de captura los gestos reconocidos.

Se ejecuta en WINDOWS, junto a la demo de gestos (la webcam no funciona bien dentro de WSL). Solo
usa la biblioteca estándar, para no añadir dependencias al entorno de la parte 1.
Desde Windows, la API de captura (dentro de WSL) está en http://localhost:8001.

Privacidad: solo sale la etiqueta del gesto y su confianza; nunca la imagen ni los puntos de la mano.

Uso desde la demo:
    from cliente_gestos import EmisorGestos
    emisor = EmisorGestos(clave=os.environ['PIDS_CLAVE_GESTOS'], modelo='mlp_muneca_escala_rot')
    ...
    emisor.observar(pred, conf)      # en cada predicción; solo envía cuando el gesto es estable

Prueba manual:
    python cliente_gestos.py --clave <CAPTURA_CLAVE_GESTOS> --gesto thumbsup
"""
from __future__ import annotations

import argparse
import json
import socket
import time
import urllib.error
import urllib.request


class EmisorGestos:
    def __init__(self, clave: str, modelo: str, url: str = 'http://localhost:8001',
                 dispositivo: str | None = None, estabilidad: int = 4, confianza_minima: float = 0.85,
                 repetir_cada_s: float = 3.0):
        self.url = url.rstrip('/') + '/gestos'
        self.clave = clave
        self.modelo = modelo
        self.dispositivo = dispositivo or socket.gethostname()
        self.estabilidad = estabilidad
        self.confianza_minima = confianza_minima
        self.repetir_cada_s = repetir_cada_s
        self._candidato, self._racha = None, 0
        self._ultimo, self._instante_ultimo = None, 0.0

    def observar(self, gesto: str, confianza: float) -> bool:
        """Registra una predicción. Envía si el gesto se mantiene `estabilidad` veces seguidas."""
        if gesto == 'None' or confianza < self.confianza_minima:
            self._candidato, self._racha = None, 0
            return False
        self._racha = self._racha + 1 if gesto == self._candidato else 1
        self._candidato = gesto
        ahora = time.monotonic()
        repetido = gesto == self._ultimo and ahora - self._instante_ultimo < self.repetir_cada_s
        if self._racha < self.estabilidad or repetido:
            return False
        self._ultimo, self._instante_ultimo = gesto, ahora
        return self.enviar(gesto, confianza)

    def enviar(self, gesto: str, confianza: float) -> bool:
        cuerpo = json.dumps({'gesto': gesto, 'confianza': round(float(confianza), 3),
                             'modelo': self.modelo, 'dispositivo': self.dispositivo}).encode('utf-8')
        peticion = urllib.request.Request(self.url, data=cuerpo, method='POST', headers={
            'Content-Type': 'application/json', 'X-API-Key': self.clave})
        try:
            with urllib.request.urlopen(peticion, timeout=2) as r:
                return r.status == 202
        except (urllib.error.URLError, TimeoutError) as e:
            print(f'[gestos] no se pudo enviar {gesto}: {e}')
            return False


def main() -> None:
    p = argparse.ArgumentParser(description='Envía un gesto de prueba a la API de captura')
    p.add_argument('--clave', required=True)
    p.add_argument('--gesto', default='thumbsup')
    p.add_argument('--url', default='http://localhost:8001')
    args = p.parse_args()
    ok = EmisorGestos(args.clave, modelo='prueba', url=args.url).enviar(args.gesto, 0.99)
    print('enviado' if ok else 'error')


if __name__ == '__main__':
    main()
