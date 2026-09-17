"""Invarianzas de las normalizaciones, espejo y aumentacion. Rapido: no carga TensorFlow."""
import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from hgr import constantes as C          # noqa: E402
from hgr import features as F            # noqa: E402

ANCHO, ALTO = 1280, 720


def manos_aleatorias(n=40, semilla=0):
    """Coordenadas crudas tipo MediaPipe (x, y en [0,1]) de manos plausibles."""
    rng = np.random.default_rng(semilla)
    base = rng.uniform(-0.08, 0.08, (21, 2))
    base[C.MUNECA] = 0.0
    base[C.MCP_CORAZON] = [0.0, -0.1]
    xy = []
    for _ in range(n):
        ang = rng.uniform(-0.6, 0.6)
        R = np.array([[np.cos(ang), -np.sin(ang)], [np.sin(ang), np.cos(ang)]])
        m = (base @ R.T) * rng.uniform(0.5, 1.5) + rng.uniform(0.3, 0.7, 2)
        m[:, 0] /= ANCHO / ALTO
        xy.append(m)
    return np.array(xy)


def df_desde_xy(xy, handedness=None):
    d = {'ancho': ANCHO, 'alto': ALTO}
    for i in range(21):
        d['x%d' % i] = xy[:, i, 0]
        d['y%d' % i] = xy[:, i, 1]
    df = pd.DataFrame(d)
    df['handedness'] = handedness if handedness is not None else ['Right'] * len(xy)
    return df


def rotar_en_pixeles(P, grados, centro):
    t = np.deg2rad(grados)
    R = np.array([[np.cos(t), -np.sin(t)], [np.sin(t), np.cos(t)]])
    return (P - centro) @ R.T + centro


class TestNormalizaciones(unittest.TestCase):
    def setUp(self):
        self.xy = manos_aleatorias()
        self.P, self.ar = F.coordenadas(df_desde_xy(self.xy))

    def test_aspecto_corregido(self):
        np.testing.assert_allclose(self.P[..., 0], self.xy[..., 0] * ANCHO / ALTO)
        np.testing.assert_allclose(self.P[..., 1], self.xy[..., 1])

    def test_ninguna_devuelve_exactamente_las_coordenadas_de_mediapipe(self):
        np.testing.assert_allclose(F.normalizar(self.P, self.ar, 'ninguna'), self.xy, atol=1e-12)

    def test_muneca_deja_el_landmark_0_en_el_origen(self):
        # el fallo de normalize_from_0_landmark del repo: dejaba x0, y0 absolutos
        Q = F.normalizar(self.P, self.ar, 'muneca')
        np.testing.assert_allclose(Q[:, C.MUNECA], 0.0, atol=1e-12)

    def test_muneca_es_invariante_a_desplazar_la_mano(self):
        Q1 = F.normalizar(self.P, self.ar, 'muneca')
        Q2 = F.normalizar(self.P + np.array([0.3, -0.2]), self.ar, 'muneca')
        np.testing.assert_allclose(Q1, Q2, atol=1e-12)

    def test_escala_es_invariante_a_la_distancia_a_la_camara(self):
        Q1 = F.normalizar(self.P, self.ar, 'muneca_escala')
        centro = self.P[:, :1]
        Q2 = F.normalizar(centro + 2.7 * (self.P - centro), self.ar, 'muneca_escala')
        np.testing.assert_allclose(Q1, Q2, atol=1e-10)
        np.testing.assert_allclose(np.linalg.norm(Q1[:, C.MCP_CORAZON], axis=1), 1.0, atol=1e-10)

    def test_rotacion_es_invariante_al_giro_en_el_plano(self):
        Q1 = F.normalizar(self.P, self.ar, 'muneca_escala_rot')
        for grados in (-150, -35, 10, 90, 179):
            P2 = rotar_en_pixeles(self.P, grados, centro=np.array([0.9, 0.4]))
            np.testing.assert_allclose(F.normalizar(P2, self.ar, 'muneca_escala_rot'), Q1, atol=1e-9)

    def test_rotacion_deja_el_nudillo_del_corazon_arriba(self):
        Q = F.normalizar(self.P, self.ar, 'muneca_escala_rot')
        np.testing.assert_allclose(Q[:, C.MCP_CORAZON], np.tile([0.0, -1.0], (len(Q), 1)), atol=1e-10)

    def test_rotar_sin_corregir_el_aspecto_romperia_la_invarianza(self):
        # justifica el paso de corregir aspecto: girando las x,y crudas la forma se deforma
        P_crudo, ar_uno = self.xy.copy(), np.ones(len(self.xy))
        Q1 = F.normalizar(P_crudo, ar_uno, 'muneca_escala_rot')
        P_girado_en_pixeles = rotar_en_pixeles(self.P, 40, np.array([0.5, 0.5]))
        crudo_girado = P_girado_en_pixeles.copy()
        crudo_girado[..., 0] /= ANCHO / ALTO
        Q2 = F.normalizar(crudo_girado, ar_uno, 'muneca_escala_rot')
        self.assertGreater(np.abs(Q1 - Q2).max(), 1e-3)

    def test_normalizacion_desconocida(self):
        with self.assertRaises(ValueError):
            F.normalizar(self.P, self.ar, 'L0')


class TestEspejo(unittest.TestCase):
    def setUp(self):
        self.xy = manos_aleatorias()
        self.hand = np.array(['Left', 'Right'] * 20)
        self.P, self.ar = F.coordenadas(df_desde_xy(self.xy, self.hand))

    def test_espejo_dos_veces_es_la_identidad(self):
        m = self.hand == 'Left'
        np.testing.assert_allclose(F.espejar(F.espejar(self.P, self.ar, m), self.ar, m), self.P, atol=1e-12)

    def test_espejo_solo_toca_la_lateralidad_indicada(self):
        Q = F.espejar(self.P, self.ar, self.hand == 'Left')
        np.testing.assert_allclose(Q[self.hand == 'Right'], self.P[self.hand == 'Right'])

    def test_espejo_equivale_a_negar_x_tras_centrar(self):
        Q_esp = F.transformar(self.P, self.ar, self.hand, 'muneca', espejo=True)
        Q = F.normalizar(self.P, self.ar, 'muneca')
        izq = self.hand == 'Left'
        np.testing.assert_allclose(Q_esp[izq, :, 0], -Q[izq, :, 0], atol=1e-12)
        np.testing.assert_allclose(Q_esp[izq, :, 1], Q[izq, :, 1], atol=1e-12)

    def test_mano_reflejada_y_su_original_dan_la_misma_entrada(self):
        # invarianza izquierda/derecha: una mano izquierda que es el espejo exacto de una
        # derecha debe producir exactamente las mismas features con espejo=True
        derecha = self.P[:1]
        izquierda = F.espejar(derecha, self.ar[:1], [True])
        a = F.transformar(derecha, self.ar[:1], ['Right'], 'muneca_escala_rot', espejo=True)
        b = F.transformar(izquierda, self.ar[:1], ['Left'], 'muneca_escala_rot', espejo=True)
        np.testing.assert_allclose(a, b, atol=1e-10)


class TestAumentacion(unittest.TestCase):
    def setUp(self):
        self.P, self.ar = F.coordenadas(df_desde_xy(manos_aleatorias(10)))

    def test_formas_e_indices(self):
        B, A, idx = F.aumentar(self.P, self.ar, np.random.default_rng(0), 3)
        self.assertEqual(B.shape, (30, 21, 2))
        self.assertEqual(A.shape, (30,))
        np.testing.assert_array_equal(idx, np.repeat(np.arange(10), 3))

    def test_determinista_con_la_misma_semilla(self):
        a = F.aumentar(self.P, self.ar, np.random.default_rng(7), 2)[0]
        b = F.aumentar(self.P, self.ar, np.random.default_rng(7), 2)[0]
        c = F.aumentar(self.P, self.ar, np.random.default_rng(8), 2)[0]
        np.testing.assert_array_equal(a, b)
        self.assertFalse(np.allclose(a, c))

    def test_perturbacion_acotada(self):
        B, _, idx = F.aumentar(self.P, self.ar, np.random.default_rng(1), 5)
        self.assertLess(np.abs(B - self.P[idx]).max(), 0.5)

    def test_cero_copias(self):
        B, A, idx = F.aumentar(self.P, self.ar, np.random.default_rng(0), 0)
        self.assertEqual(len(B), 0)


class TestEntrada(unittest.TestCase):
    def test_forma_cnn_igual_que_arrange_input_data_for_network_del_repo(self):
        xy = manos_aleatorias(5)
        X = F.preparar_entrada(xy, 'cnn')
        self.assertEqual(X.shape, (5, 21, 2, 1))
        plano = xy.reshape(5, -1)                              # x0,y0,x1,y1,... como el .npy del repo
        np.testing.assert_allclose(X[:, :, 0, 0], plano[:, 0::2], atol=1e-6)
        np.testing.assert_allclose(X[:, :, 1, 0], plano[:, 1::2], atol=1e-6)

    def test_forma_plana(self):
        X = F.preparar_entrada(manos_aleatorias(5), 'plano')
        self.assertEqual(X.shape, (5, 42))
        self.assertEqual(X.dtype, np.float32)

    def test_coordenadas_desde_mediapipe_coincide_con_la_ruta_del_dataframe(self):
        xy = manos_aleatorias(6)
        P1, ar1 = F.coordenadas(df_desde_xy(xy))
        P2, ar2 = F.coordenadas_desde_mediapipe(xy, ANCHO, ALTO)
        np.testing.assert_allclose(P1, P2)
        np.testing.assert_allclose(ar1, ar2)


if __name__ == '__main__':
    unittest.main(verbosity=2)
