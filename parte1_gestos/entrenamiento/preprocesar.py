"""PASO 1. Busca las tomas, extrae los landmarks (con cache) y comprueba su calidad.

Uso:
    python preprocesar.py
    python preprocesar.py --datos datos C:/ruta/a/otra/carpeta

Ejecutalo cada vez que llegue la toma de un companero: solo procesa lo nuevo y te dice
si la toma sirve (imagenes por gesto, fotos negras, tasa de deteccion de la mano,
lateralidad) ANTES de meterla en un experimento.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from hgr import cli, constantes as C  # noqa: E402

UMBRAL_DETECCION = 0.90
UMBRAL_NEGRA = 10.0


def informe_calidad(tomas, df):
    import pandas as pd
    filas, avisos = [], []
    for t in tomas:
        d = df[df['toma'] == t.nombre]
        if d.empty:
            avisos.append('%s: sin imagenes' % t.nombre)
            continue
        por_clase = d.groupby('clase').size()
        det_clase = d.groupby('clase')['detectada'].mean()
        lados = d.loc[d['detectada'], 'handedness'].value_counts(normalize=True)
        negras = int((d['brillo'] < UMBRAL_NEGRA).sum())
        ilegibles = int(d['error'].notna().sum())
        fila = {'toma': t.nombre, 'participante': t.participante, 'mano': t.mano or '-', 'estado': t.estado,
                'imagenes': len(d), 'min_por_gesto': int(por_clase.min()), 'negras': negras, 'ilegibles': ilegibles,
                'deteccion_%': round(100 * d['detectada'].mean(), 1),
                'peor_gesto': '%s %.0f%%' % (det_clase.idxmin(), 100 * det_clase.min()),
                'lateralidad_mp': '%s %.0f%%' % (lados.index[0], 100 * lados.iloc[0]) if len(lados) else '-'}
        filas.append(fila)
        faltan = sorted(set(C.CLASES_ESPERADAS) - set(por_clase.index))
        if faltan:
            avisos.append('%s: faltan gestos %s' % (t.nombre, faltan))
        cortos = por_clase[por_clase < C.IMAGENES_POR_CLASE]
        if len(cortos) and not t.prueba:
            avisos.append('%s: gestos con menos de %d imagenes: %s' % (t.nombre, C.IMAGENES_POR_CLASE, {k: int(v) for k, v in cortos.items()}))
        if t.estado not in ('completa', 'desconocido'):
            avisos.append('%s: la toma esta %s segun su metadata.json' % (t.nombre, t.estado))
        if negras:
            avisos.append('%s: %d imagenes casi negras (obturador cerrado?)' % (t.nombre, negras))
        if ilegibles:
            avisos.append('%s: %d imagenes ilegibles' % (t.nombre, ilegibles))
        malos = det_clase[det_clase < UMBRAL_DETECCION]
        if len(malos):
            avisos.append('%s: deteccion de mano por debajo del %.0f%% en %s'
                          % (t.nombre, 100 * UMBRAL_DETECCION, ', '.join('%s (%.0f%%)' % (k, 100 * v) for k, v in malos.items())))
        if len(lados) and lados.iloc[0] < 0.8:
            avisos.append('%s: lateralidad mezclada (%s): cambio de mano a mitad de la toma?'
                          % (t.nombre, ', '.join('%s %.0f%%' % (k, 100 * v) for k, v in lados.items())))
    tabla = pd.DataFrame(filas)
    repetidos = tabla.groupby('participante')['toma'].count() if len(tabla) else []
    for p, n in (repetidos.items() if len(tabla) else []):
        if n > 1:
            avisos.append('el participante %s tiene %d tomas: si una es una repeticion fallida, borrala; '
                          'si no, contaran juntas como la misma persona en LOPO' % (p, n))
    return tabla, avisos


def main():
    cli.configurar_consola()
    p = cli.argumentos_datos(argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter))
    args = p.parse_args()
    tomas, df, avisos = cli.cargar_dataset(args)
    if df is None or df.empty:
        print('\nNo hay tomas que procesar. Descomprime las tomas en entrenamiento/datos/ o indica --datos.')
        return 1
    tabla, avisos_calidad = informe_calidad(tomas, df)
    from hgr import utils
    print('\nCALIDAD DE LAS TOMAS')
    print(tabla.to_string(index=False))
    salida = C.DIR_CACHE / 'verificacion_tomas.csv'
    tabla.to_csv(salida, index=False)
    todos = avisos + avisos_calidad
    print('\n%d participantes, %d imagenes, %d con mano (%.1f%%).'
          % (df['participante'].nunique(), len(df), df['detectada'].sum(), 100 * df['detectada'].mean()))
    if todos:
        print('\nAVISOS:')
        for a in todos:
            print('  - ' + a)
    else:
        print('Sin avisos: las tomas estan listas para entrenar.')
    print('\nTabla guardada en %s' % salida)
    return 0


if __name__ == '__main__':
    sys.exit(main())
