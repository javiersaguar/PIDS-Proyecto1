"""Particiones: disjuntas, sin fugas de participante y con la validacion donde toca."""
import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from hgr.protocolos import generar_pliegues   # noqa: E402

CLASES = ['ok', 'paper', 'rock', 'rockandroll', 'scissors', 'thumbsup']


def meta_sintetica(participantes=('p1', 'p2', 'p3', 'p4', 'p5'), frames=100, huecos=0):
    filas = []
    rng = np.random.default_rng(0)
    for p in participantes:
        toma = 'gestos_%s_20260914-120000' % p
        for c in CLASES:
            fr = np.arange(1, frames + 1)
            if huecos:                                   # imagenes sin mano detectada
                fr = np.sort(rng.choice(fr, frames - huecos, replace=False))
            for f in fr:
                filas.append({'toma': toma, 'participante': p, 'clase': c, 'frame': int(f),
                              'subset': 'train' if f <= int(frames * 0.7) else 'test'})
    return pd.DataFrame(filas)


class TestComunes(unittest.TestCase):
    def test_todas_disjuntas_y_no_vacias(self):
        meta = meta_sintetica(huecos=7)
        for prot in ('aleatorio', 'temporal', 'lopo'):
            for pl in generar_pliegues(meta, prot, semilla=3):
                self.assertFalse(set(pl.train) & set(pl.test))
                self.assertFalse(set(pl.val) & set(pl.test))
                self.assertFalse(set(pl.train) & set(pl.val))
                self.assertGreater(len(pl.train), 0)
                self.assertGreater(len(pl.val), 0)
                self.assertGreater(len(pl.test), 0)

    def test_protocolo_desconocido(self):
        with self.assertRaises(ValueError):
            generar_pliegues(meta_sintetica(), 'kfold')


class TestAleatorio(unittest.TestCase):
    def test_cubre_todo_y_proporciones(self):
        meta = meta_sintetica()
        pl = generar_pliegues(meta, 'aleatorio', semilla=0)[0]
        self.assertEqual(len(pl.train) + len(pl.val) + len(pl.test), len(meta))
        self.assertAlmostEqual(len(pl.test) / len(meta), 0.30, delta=0.01)

    def test_estratificado_por_participante_y_clase(self):
        meta = meta_sintetica()
        pl = generar_pliegues(meta, 'aleatorio', semilla=0)[0]
        conteo = meta.iloc[pl.test].groupby(['participante', 'clase']).size()
        self.assertLessEqual(conteo.max() - conteo.min(), 1)

    def test_depende_de_la_semilla_y_es_reproducible(self):
        meta = meta_sintetica()
        a = generar_pliegues(meta, 'aleatorio', semilla=1)[0].test
        b = generar_pliegues(meta, 'aleatorio', semilla=1)[0].test
        c = generar_pliegues(meta, 'aleatorio', semilla=2)[0].test
        np.testing.assert_array_equal(a, b)
        self.assertFalse(np.array_equal(a, c))


class TestTemporal(unittest.TestCase):
    def test_test_es_exactamente_la_carpeta_test_del_grabador(self):
        meta = meta_sintetica()
        pl = generar_pliegues(meta, 'temporal')[0]
        np.testing.assert_array_equal(np.sort(pl.test), np.flatnonzero(meta['subset'] == 'test'))

    def test_val_son_los_ultimos_fotogramas_de_train(self):
        meta = meta_sintetica(huecos=5)
        pl = generar_pliegues(meta, 'temporal')[0]
        for (toma, clase), g in meta.groupby(['toma', 'clase']):
            tr = meta.loc[np.intersect1d(pl.train, g.index), 'frame']
            va = meta.loc[np.intersect1d(pl.val, g.index), 'frame']
            self.assertGreater(len(va), 0)
            self.assertLess(tr.max(), va.min())

    def test_todos_los_participantes_en_train_y_en_test(self):
        meta = meta_sintetica()
        pl = generar_pliegues(meta, 'temporal')[0]
        self.assertEqual(set(meta.iloc[pl.train].participante), set(meta.iloc[pl.test].participante))


class TestLOPO(unittest.TestCase):
    def test_un_pliegue_por_participante_sin_fugas(self):
        meta = meta_sintetica()
        pls = generar_pliegues(meta, 'lopo')
        self.assertEqual([p.nombre for p in pls], ['p1', 'p2', 'p3', 'p4', 'p5'])
        for pl in pls:
            self.assertEqual(set(meta.iloc[pl.test].participante), {pl.nombre})
            self.assertNotIn(pl.nombre, set(meta.iloc[pl.train].participante))
            self.assertNotIn(pl.nombre, set(meta.iloc[pl.val].participante))
            self.assertEqual(len(pl.train) + len(pl.val) + len(pl.test), len(meta))

    def test_cada_muestra_es_test_exactamente_una_vez(self):
        meta = meta_sintetica()
        todos = np.concatenate([pl.test for pl in generar_pliegues(meta, 'lopo')])
        np.testing.assert_array_equal(np.sort(todos), np.arange(len(meta)))

    def test_participante_con_dos_tomas_cuenta_como_uno(self):
        meta = meta_sintetica(('p1', 'p2', 'p3'))
        extra = meta[meta.participante == 'p2'].copy()
        extra['toma'] = 'gestos_p2_20260915-090000'
        meta = pd.concat([meta, extra], ignore_index=True)
        pls = generar_pliegues(meta, 'lopo')
        self.assertEqual(len(pls), 3)
        p2 = [p for p in pls if p.nombre == 'p2'][0]
        self.assertEqual(meta.iloc[p2.test].toma.nunique(), 2)

    def test_necesita_dos_participantes(self):
        with self.assertRaises(ValueError):
            generar_pliegues(meta_sintetica(('p1',)), 'lopo')


if __name__ == '__main__':
    unittest.main(verbosity=2)
