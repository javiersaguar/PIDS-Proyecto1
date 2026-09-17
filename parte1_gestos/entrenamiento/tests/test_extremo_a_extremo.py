"""Prueba de extremo a extremo con imagenes REALES de manos (lenta: unos minutos).

Construye 5 tomas falsas con el formato del kit v2 a partir del dataset de ejemplo del
repo de la asignatura (6 gestos x 50 imagenes de UNA persona, repartidas entre 5
'participantes' ficticios), en una carpeta con tildes y espacios, y recorre todo el
pipeline: preprocesar -> entrenar -> evaluar -> exportar -> inferencia.

OJO: como en realidad es una sola persona, las cifras de accuracy de esta prueba no
significan nada; solo se comprueba que la mecanica es correcta.
"""
import json
import shutil
import sys
import tempfile
import unittest
from concurrent.futures import ProcessPoolExecutor
from dataclasses import asdict
from multiprocessing import get_context
from pathlib import Path
from unittest import mock

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
from hgr import constantes as C, utils   # noqa: E402

EJEMPLO = C.RAIZ_PROYECTO / 'upstream' / 'HAR_mediapipe' / 'data' / 'new_dataset'
PARTICIPANTES = ['p1', 'p2', 'p3', 'p4', 'p5']


def construir_tomas(base):
    for k, p in enumerate(PARTICIPANTES):
        toma = base / ('gestos_%s_20260101-00000%d' % (p, k))
        for clase_dir in sorted((EJEMPLO / 'train').iterdir()):
            c = clase_dir.name
            fuentes = sorted(list((EJEMPLO / 'train' / c).glob('*.jpg')) + list((EJEMPLO / 'test' / c).glob('*.jpg')))
            for i, src in enumerate(fuentes[k * 10:(k + 1) * 10], start=1):
                sub = 'train' if i <= 7 else 'test'
                dst = toma / sub / c / ('%s_%05d.jpg' % (c, i))
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(src, dst)
        (toma / 'metadata.json').write_text(json.dumps({
            'participante': p, 'mano': 'derecha', 'estado': 'completa', 'kit_version': '2',
            'toma': toma.name, 'imagenes_por_clase': 10}), encoding='utf-8')


def _trabajo_en_proceso_nuevo(datos, cfg_dict, trabajo, usar_gpu=False):
    from hgr import experimento as E
    with ProcessPoolExecutor(max_workers=1, mp_context=get_context('spawn'),
                             initializer=E._init_worker, initargs=(datos, cfg_dict, usar_gpu, True)) as ex:
        return ex.submit(E._ejecutar_seguro, trabajo).result()


@unittest.skipUnless(EJEMPLO.exists(), 'falta el dataset de ejemplo del repo en %s' % EJEMPLO)
class TestExtremoAExtremo(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        raiz = Path(cls.tmp.name)
        cls.datos = raiz / 'Tomas de José Muñoz'
        construir_tomas(cls.datos)
        cls.parches = [mock.patch.object(C, 'DIR_CACHE', raiz / 'cache'),
                       mock.patch.object(C, 'DIR_RESULTADOS', raiz / 'resultados'),
                       mock.patch.object(C, 'DIR_MODELOS', raiz / 'modelos')]
        for p in cls.parches:
            p.start()

    @classmethod
    def tearDownClass(cls):
        for p in cls.parches:
            p.stop()
        cls.tmp.cleanup()

    def test_a_preprocesar(self):
        import preprocesar
        with mock.patch.object(sys, 'argv', ['preprocesar.py', '--datos', str(self.datos), '--workers', '6']):
            self.assertEqual(preprocesar.main(), 0)
        csvs = sorted((C.DIR_CACHE / 'landmarks').glob('*.csv'))
        self.assertEqual(len(csvs), 5)
        df = pd.concat(pd.read_csv(f) for f in csvs)
        self.assertEqual(len(df), 5 * 6 * 10)
        self.assertGreater(df['detectada'].mean(), 0.9)
        # segunda pasada: todo desde cache, sin reprocesar
        from hgr import cli
        args = cli.argumentos_datos(__import__('argparse').ArgumentParser()).parse_args(['--datos', str(self.datos)])
        mensajes = []
        cli.cargar_dataset(args, log=mensajes.append)
        self.assertEqual(sum('[cache]' in m for m in mensajes), 5)
        self.assertFalse(any('[nuevo]' in m for m in mensajes))

    def test_b_entrenar_y_evaluar(self):
        import entrenar
        import evaluar
        argv = ['--nombre', 'e2e', '--modelos', 'cnn_baseline', 'svm', 'logreg', 'knn',
                '--normalizaciones', 'ninguna', 'muneca_escala_rot', '--protocolos', 'todos',
                '--semillas', '0', '1', '--epocas', '30', '--paciencia', '5',
                '--datos', str(self.datos), '--workers', '8']
        self.assertEqual(entrenar.main(argv), 0)
        d = C.DIR_RESULTADOS / 'e2e'
        self.assertFalse((d / 'errores_ejecucion.txt').exists())

        pl = pd.read_csv(d / 'resultados_pliegues.csv', dtype={'pliegue': str})
        # por normalizacion: aleatorio 2 semillas x 4 modelos = 8; temporal 2+2+1+1 = 6; lopo 5 x 6 = 30
        self.assertEqual(len(pl), 2 * (8 + 6 + 30))
        self.assertTrue(pl['accuracy'].between(0, 1).all())

        info_disp = utils.info_dispositivo()
        if info_disp['dispositivo'] == 'cuda':
            redes_pl = pl[pl['modelo'] == 'cnn_baseline']
            self.assertTrue(redes_pl['dispositivo'].str.startswith('cuda').all())

        pred = pd.read_csv(d / 'predicciones.csv.gz', dtype={'pliegue': str})
        self.assertEqual(len(pred), pl['n_test'].sum())
        muestras = pd.read_csv(d / 'muestras.csv.gz', index_col='indice')
        lopo = pred[pred['protocolo'] == 'lopo']
        for _, g in lopo.groupby(['normalizacion', 'modelo', 'semilla']):
            np.testing.assert_array_equal(np.sort(g['indice'].to_numpy()), np.arange(len(muestras)))
            # el participante de test de cada pliegue es el que da nombre al pliegue
            self.assertTrue((muestras.loc[g['indice'], 'participante'].to_numpy() == g['pliegue'].to_numpy()).all())

        rend = pd.read_csv(d / 'rendimiento.csv')
        self.assertEqual(set(rend['modelo']), {'cnn_baseline', 'svm', 'logreg', 'knn', 'extractor_mediapipe'})
        cnn = rend[rend['modelo'] == 'cnn_baseline'].iloc[0]
        self.assertEqual(int(cnn['parametros']), 23126)
        from hgr.rendimiento import tflite_disponible
        if tflite_disponible():
            self.assertGreater(cnn['tflite_bytes'], 0)

        informe = (d / 'informe.md').read_text(encoding='utf-8')
        for trozo in ('## 1. Dataset', 'LOPO', 'Cuanto engana', '## 5. Coste computacional', 'extractor de MediaPipe'):
            self.assertIn(trozo, informe)
        pngs = {f.stem for f in (d / 'figuras').glob('*.png')}
        for esperado in ('protocolos_ninguna', 'protocolos_muneca_escala_rot', 'normalizaciones_lopo',
                         'tradeoff_latencia', 'tradeoff_tamano', 'f1_por_clase_lopo'):
            self.assertIn(esperado, pngs)
        self.assertTrue(any(s.startswith('confusion_') for s in pngs))
        self.assertTrue(any(s.startswith('curvas_cnn_baseline') for s in pngs))
        self.assertTrue(any(s.startswith('participantes_') for s in pngs))
        self.assertEqual(len(list((d / 'figuras').glob('*.png'))), len(list((d / 'figuras').glob('*.pdf'))))

        # evaluar.py regenera exactamente el mismo informe sin reentrenar
        with mock.patch.object(sys, 'argv', ['evaluar.py', '--experimento', 'e2e']):
            self.assertEqual(evaluar.main(), 0)
        self.assertEqual((d / 'informe.md').read_text(encoding='utf-8'), informe)

        # no se machaca un experimento existente
        self.assertEqual(entrenar.main(argv), 2)

    def test_c_mismo_trabajo_en_procesos_distintos_da_lo_mismo(self):
        from hgr import cli
        from hgr.experimento import ConfigExperimento, construir_trabajos, preparar_datos, resolver_gpu
        args = cli.argumentos_datos(__import__('argparse').ArgumentParser()).parse_args(['--datos', str(self.datos)])
        _, df, _ = cli.cargar_dataset(args, log=lambda *a: None)
        datos = preparar_datos(df)
        cfg = ConfigExperimento(nombre='det', modelos=['cnn_baseline'], normalizaciones=['muneca_escala_rot'],
                                protocolos=['lopo'], semillas=[3], epocas=12, paciencia=4, medir_rendimiento=False)
        trabajo = construir_trabajos(cfg, datos['muestras'])[0]
        dw = {k: datos[k] for k in ('P', 'ar', 'h', 'y', 'clases')}
        usar_gpu = resolver_gpu(cfg.dispositivo)
        a = _trabajo_en_proceso_nuevo(dw, asdict(cfg), trabajo, usar_gpu=usar_gpu)
        b = _trabajo_en_proceso_nuevo(dw, asdict(cfg), trabajo, usar_gpu=usar_gpu)
        self.assertNotIn('_error', a, a.get('_error'))
        np.testing.assert_array_equal(a['_pred'], b['_pred'])
        np.testing.assert_allclose(a['_conf'], b['_conf'], atol=1e-4)

    def test_d_exportar_e_inferir_con_mediapipe_real(self):
        import exportar_modelo
        with mock.patch.object(sys, 'argv', [
                'exportar_modelo.py', '--modelo', 'cnn_baseline', '--normalizacion', 'muneca_escala_rot', '--espejo',
                '--epocas', '30', '--paciencia', '5', '--nombre', 'final', '--datos', str(self.datos)]):
            self.assertEqual(exportar_modelo.main(), 0)       # dentro comprueba la paridad entrenamiento/demo
        d = C.DIR_MODELOS / 'final'
        for f in ('modelo.keras', 'etiquetas.json', 'preprocesado.json', 'ficha.json', 'curvas.png'):
            self.assertTrue((d / f).exists(), f)
        from hgr.rendimiento import tflite_disponible
        if tflite_disponible():
            for f in ('modelo.tflite', 'modelo_cuant.tflite'):
                self.assertTrue((d / f).exists(), f)
        self.assertTrue(json.loads((d / 'preprocesado.json').read_text(encoding='utf-8'))['espejo'])

        from hgr import utils
        from hgr.extraccion import _crear_detector, detectar
        from hgr.inferencia import ClasificadorGestos
        clf = ClasificadorGestos(d)
        img_path = next((self.datos / 'gestos_p2_20260101-000001' / 'test').rglob('*.jpg'))
        img = utils.leer_imagen(img_path)
        det = _crear_detector(C.MODELO_MEDIAPIPE.read_bytes(), 0.5)
        res = clf.predecir_resultado_mediapipe(detectar(det, img), img.shape[1], img.shape[0])
        self.assertIsNotNone(res)
        clase, conf, probs = res
        self.assertIn(clase, clf.clases)
        self.assertAlmostEqual(float(np.sum(probs)), 1.0, places=4)
        self.assertIsNone(clf.predecir_resultado_mediapipe(None, 1280, 720))

        with self.assertRaises(FileExistsError):                 # tampoco se machaca un modelo exportado
            from hgr.exportacion import exportar
            exportar(pd.DataFrame({'detectada': []}), d)

    def test_e_informe_con_mano_opuesta_diversidad_y_comandos(self):
        d = C.DIR_RESULTADOS / 'e2e'
        pl = pd.read_csv(d / 'resultados_pliegues.csv')
        self.assertTrue(pl['accuracy_espejado'].between(0, 1).all())
        informe = (d / 'informe.md').read_text(encoding='utf-8')
        for trozo in ('Invarianza mano izquierda', 'Diversidad de la grabacion', 'comando_tanque'):
            self.assertIn(trozo, informe)
        self.assertTrue((d / 'figuras' / 'diversidad_dataset.png').exists())

    def test_f_plan_completo_con_presupuesto(self):
        import entrenar_todo
        extra = ['--epocas', '8', '--paciencia', '3', '--workers', '6']
        plan = [
            {'nombre': 'principal', 'modelos': ['cnn_baseline', 'logreg'], 'normalizaciones': ['ninguna'],
             'protocolos': ['lopo'], 'semillas': [0, 1], 'extra': extra, 'aumentar': 0, 'mide': True, 'que': 'test'},
            {'nombre': 'volteo', 'modelos': ['cnn_baseline', 'logreg'], 'normalizaciones': ['muneca_escala_rot'],
             'protocolos': ['lopo'], 'semillas': [0], 'extra': extra + ['--aumentar', '1', '--voltear'],
             'aumentar': 1, 'mide': False, 'que': 'test'},
            {'nombre': 'aumento', 'modelos': ['cnn_baseline'], 'normalizaciones': ['ninguna'],
             'protocolos': ['lopo'], 'semillas': [0, 1], 'extra': extra, 'aumentar': 2000, 'mide': False, 'que': 'test'},
        ]
        with mock.patch.object(entrenar_todo, 'PLAN', plan), \
                mock.patch.object(sys, 'argv', ['entrenar_todo.py']):
            self.assertEqual(entrenar_todo.main(['--prefijo', 'plan_t', '--presupuesto-min', '14',
                                                 '--experimentos', 'principal', 'volteo', 'aumento',
                                                 '--workers-gpu', '4', '--datos', str(self.datos)]), 0)
        comp = pd.read_csv(C.DIR_RESULTADOS / 'plan_t_comparativa.csv')
        self.assertEqual(set(comp['experimento']), {'principal', 'volteo'})   # 'aumento' no cabe: se salta
        self.assertTrue(comp['lopo_mano_opuesta_%'].notna().all())
        self.assertTrue(any((C.DIR_MODELOS).glob('plan_t_*')))


if __name__ == '__main__':
    unittest.main(verbosity=2)
