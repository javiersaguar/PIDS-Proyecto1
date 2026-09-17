"""Descubrimiento de tomas: nombres v2 y v1, pruebas, zips anidados, rutas con tildes."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from hgr.tomas import descubrir_tomas, listar_imagenes   # noqa: E402


def crear_toma(base, nombre, meta=None, clases=('ok', 'rock'), n=3):
    d = Path(base) / nombre
    for sub, rango in (('train', range(1, n + 1)), ('test', range(n + 1, n + 2))):
        for c in clases:
            (d / sub / c).mkdir(parents=True, exist_ok=True)
            for f in rango:
                (d / sub / c / ('%s_%05d.jpg' % (c, f))).write_bytes(b'x')
    if meta is not None:
        (d / 'metadata.json').write_text(json.dumps(meta), encoding='utf-8')
    return d


class TestDescubrir(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name) / 'Grabación José'
        self.base.mkdir()

    def tearDown(self):
        self.tmp.cleanup()

    def test_v2_con_metadata(self):
        crear_toma(self.base, 'gestos_p3_20260914-153012', {'participante': 'p3', 'mano': 'derecha',
                                                            'estado': 'completa', 'kit_version': '2'})
        (t,) = descubrir_tomas([self.base])
        self.assertEqual((t.participante, t.mano, t.estado, t.version_kit, t.marca),
                         ('p3', 'derecha', 'completa', '2', '20260914-153012'))

    def test_legado_sin_metadata(self):
        crear_toma(self.base, 'gestos_pids_p1')
        (t,) = descubrir_tomas([self.base])
        self.assertEqual((t.participante, t.estado, t.marca), ('p1', 'desconocido', None))

    def test_pruebas_excluidas_por_defecto(self):
        crear_toma(self.base / '_pruebas', 'gestos_p2_20260914-100000', {'prueba': True})
        crear_toma(self.base, 'gestos_p2_20260914-110000', {'estado': 'completa'})
        self.assertEqual(len(descubrir_tomas([self.base])), 1)
        self.assertEqual(len(descubrir_tomas([self.base], incluir_pruebas=True)), 2)

    def test_zip_descomprimido_con_carpeta_anidada_y_raices_repetidas(self):
        crear_toma(self.base / 'gestos_p4_20260914-120000', 'gestos_p4_20260914-120000')
        tomas = descubrir_tomas([self.base, self.base / 'gestos_p4_20260914-120000'])
        self.assertEqual(len(tomas), 1)

    def test_nombre_no_reconocido_sin_metadata_se_ignora_pero_avisa(self):
        crear_toma(self.base, 'mi_toma_rara')
        avisos = []
        self.assertEqual(descubrir_tomas([self.base], avisos=avisos), [])
        self.assertTrue(any('IGNORA' in a for a in avisos))

    def test_carpeta_renombrada_con_metadata_se_recupera(self):
        crear_toma(self.base, 'toma de ana', {'participante': 'p2', 'toma': 'gestos_p2_20260914-101010',
                                              'estado': 'completa'})
        avisos = []
        (t,) = descubrir_tomas([self.base], avisos=avisos)
        self.assertEqual((t.participante, t.marca), ('p2', '20260914-101010'))
        self.assertTrue(any('renombrada' in a for a in avisos))

    def test_raiz_inexistente_no_falla(self):
        self.assertEqual(descubrir_tomas([self.base / 'no_existe']), [])

    def test_orden_por_participante(self):
        for p in ('p5', 'p1', 'p3'):
            crear_toma(self.base, 'gestos_%s_20260914-120000' % p)
        self.assertEqual([t.participante for t in descubrir_tomas([self.base])], ['p1', 'p3', 'p5'])


class TestListar(unittest.TestCase):
    def test_filas_y_clase_desde_la_carpeta(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = crear_toma(tmp, 'gestos_p1_20260914-120000', n=3)
            (d / 'train' / 'ok' / 'rock_00099.jpg').write_bytes(b'x')     # mal colocada
            (d / 'train' / 'ok' / 'notas.txt').write_text('ignorar')
            (t,) = descubrir_tomas([tmp])
            avisos = []
            filas = listar_imagenes(t, avisos)
            self.assertEqual(len(filas), 2 * 4 + 1)
            mal = [f for f in filas if f['frame'] == 99][0]
            self.assertEqual(mal['clase'], 'ok')
            self.assertTrue(avisos)
            self.assertEqual({f['subset'] for f in filas}, {'train', 'test'})


if __name__ == '__main__':
    unittest.main(verbosity=2)
