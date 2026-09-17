"""Particiones train / val / test. Tres protocolos, de mas optimista a mas honesto.

aleatorio  70/30 al azar sobre todos los fotogramas (estratificado por participante y
           gesto). Fotogramas casi identicos, grabados con un segundo de diferencia,
           caen a ambos lados: es el techo optimista, sirve para ENSENAR el sesgo.
temporal   la particion que hace el propio grabador de la asignatura: dentro de cada
           toma y gesto, los primeros 70 fotogramas a train y los ultimos 30 a test.
           Todos los participantes estan en train y en test.
lopo       leave-one-participant-out: se entrena con 4 personas y se evalua con la
           quinta, 5 veces. Mide lo que importa en la demo: reconocer a alguien a
           quien el modelo no ha visto nunca.

Validacion (early stopping de las redes): siempre dentro de la parte de entrenamiento,
nunca del test. Son los ULTIMOS fotogramas de cada toma y gesto (no al azar), para que
la validacion no este plagada de gemelos de los fotogramas de train. El notebook del
repo usaba el propio test como validacion, de modo que el test elegia el modelo.
"""
from dataclasses import dataclass

import numpy as np
from sklearn.model_selection import train_test_split

from . import constantes as C


@dataclass
class Pliegue:
    protocolo: str
    nombre: str
    indice: int
    train: np.ndarray
    val: np.ndarray
    test: np.ndarray

    def comprobar(self):
        a, b, c = set(self.train), set(self.val), set(self.test)
        assert not (a & b) and not (a & c) and not (b & c), 'particiones solapadas en %s/%s' % (self.protocolo, self.nombre)
        assert len(self.train) and len(self.test), 'particion vacia en %s/%s' % (self.protocolo, self.nombre)
        return self


def _separar_ultimos(meta, idx, frac):
    """Dentro de cada (toma, clase), los ultimos 'frac' fotogramas van a val."""
    idx = np.asarray(idx)
    if len(idx) == 0 or frac <= 0:
        return idx, idx[:0]
    sub = meta.iloc[idx][['toma', 'clase', 'frame']].copy()
    sub['_i'] = idx
    resto, ultimos = [], []
    for _, g in sub.groupby(['toma', 'clase'], sort=True):
        g = g.sort_values('frame')
        k = int(round(frac * len(g))) if len(g) >= 4 else 0
        corte = len(g) - k
        resto.extend(g['_i'].iloc[:corte])
        ultimos.extend(g['_i'].iloc[corte:])
    return np.sort(np.array(resto, dtype=int)), np.sort(np.array(ultimos, dtype=int))


def _estratificado(idx, estratos, frac, semilla):
    try:
        return train_test_split(idx, test_size=frac, random_state=semilla, stratify=estratos)
    except ValueError:            # algun estrato con 1 muestra: se estratifica solo por clase
        return train_test_split(idx, test_size=frac, random_state=semilla)


def generar_pliegues(meta, protocolo, semilla=0, frac_val=0.15, frac_test=0.30):
    """meta: DataFrame (solo filas con mano detectada) con toma, participante, clase, subset, frame."""
    meta = meta.reset_index(drop=True)
    idx = np.arange(len(meta))

    if protocolo == 'aleatorio':
        estrato = (meta['participante'] + '|' + meta['clase']).to_numpy()
        trval, test = _estratificado(idx, estrato, frac_test, semilla)
        tr, va = _estratificado(trval, estrato[trval], frac_val, semilla)
        return [Pliegue('aleatorio', 'unico', 0, np.sort(tr), np.sort(va), np.sort(test)).comprobar()]

    if protocolo == 'temporal':
        test = idx[meta['subset'].to_numpy() == 'test']
        trval = idx[meta['subset'].to_numpy() == 'train']
        tr, va = _separar_ultimos(meta, trval, frac_val)
        return [Pliegue('temporal', 'unico', 0, tr, va, test).comprobar()]

    if protocolo == 'lopo':
        participantes = sorted(meta['participante'].unique())
        if len(participantes) < 2:
            raise ValueError('lopo necesita al menos 2 participantes (hay %d)' % len(participantes))
        pliegues = []
        part = meta['participante'].to_numpy()
        for k, p in enumerate(participantes):
            test = idx[part == p]
            tr, va = _separar_ultimos(meta, idx[part != p], frac_val)
            pliegues.append(Pliegue('lopo', p, k, tr, va, test).comprobar())
        return pliegues

    raise ValueError('protocolo desconocido: %r (opciones: %s)' % (protocolo, C.PROTOCOLOS))
