"""Cargar un modelo exportado y clasificar landmarks de MediaPipe en vivo (para la demo).

El modelo exportado viaja con su lista de clases (etiquetas.json) y con su
preprocesado (preprocesado.json), y este modulo aplica EXACTAMENTE las mismas
funciones de features.py que se usaron al entrenar. Asi se evitan los dos fallos del
demo del repo: la lista de clases escrita a mano (6 nombres para un modelo de 7
salidas) y una normalizacion distinta a la del entrenamiento.
"""
from pathlib import Path

import numpy as np

from . import features as F
from . import utils
from .modelos import cargar_modelo


class ClasificadorGestos:
    def __init__(self, carpeta):
        self.carpeta = Path(carpeta)
        pre = utils.leer_json(self.carpeta / 'preprocesado.json')
        self.clases = utils.leer_json(self.carpeta / 'etiquetas.json')['clases']
        self.nombre_modelo = pre['modelo']
        self.normalizacion = pre['normalizacion']
        self.espejo = bool(pre['espejo'])
        self.lado_espejo = pre['lado_espejo']
        self.forma = pre['forma_entrada']
        ruta = self.carpeta / pre['fichero_modelo']
        self._es_keras = ruta.suffix == '.keras'
        self._modelo = cargar_modelo(ruta)

    def entrada(self, xy, handedness, ancho, alto):
        """xy: (21, 2) o (N, 21, 2) con las x, y crudas de MediaPipe; handedness: 'Left'/'Right' o lista."""
        xy = np.asarray(xy, dtype=float).reshape(-1, 21, 2)
        h = np.asarray([handedness] * len(xy) if isinstance(handedness, str) or handedness is None else handedness,
                       dtype=object)
        h = np.array(['' if v is None else str(v) for v in h])
        P, ar = F.coordenadas_desde_mediapipe(xy, ancho, alto)
        return F.preparar_entrada(F.transformar(P, ar, h, self.normalizacion, self.espejo, self.lado_espejo), self.forma)

    def probabilidades(self, X):
        if self._es_keras:
            import keras
            # con el backend de PyTorch la salida es un tensor (quiza en la GPU): np.asarray no vale
            return np.asarray(keras.ops.convert_to_numpy(self._modelo(X, training=False)))
        p = self._modelo.predict_proba(X)
        completo = np.zeros((len(X), len(self.clases)))
        completo[:, np.asarray(self._modelo.classes_, dtype=int)] = p
        return completo

    def predecir(self, xy, handedness, ancho, alto):
        """(clase, confianza, vector de probabilidades) para UNA mano."""
        p = self.probabilidades(self.entrada(xy, handedness, ancho, alto))[0]
        k = int(np.argmax(p))
        return self.clases[k], float(p[k]), p

    def predecir_resultado_mediapipe(self, resultado, ancho, alto):
        """Directamente sobre el resultado de HandLandmarker.detect(). None si no hay mano."""
        if resultado is None or not resultado.hand_landmarks:
            return None
        xy = [[p.x, p.y] for p in resultado.hand_landmarks[0]]
        lado = resultado.handedness[0][0].category_name if resultado.handedness else ''
        return self.predecir(xy, lado, ancho, alto)
