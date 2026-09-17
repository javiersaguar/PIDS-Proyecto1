"""TODO el entrenamiento del proyecto en una orden, ajustado a un presupuesto de tiempo.

Uso (desde entrenamiento/):
    ..\\.venv\\Scripts\\python.exe entrenar_todo.py                  # presupuesto de 115 min
    ..\\.venv\\Scripts\\python.exe entrenar_todo.py --presupuesto-min 90

Experimentos, en orden de prioridad (lo imprescindible primero):

  1. principal   MINIMO de la presentacion + mejora 1 (modelos alternativos y trade-off) + mejora 3a
                 (normalizaciones): cnn_baseline, mlp, svm, random_forest, knn, logreg x 4 normalizaciones
                 x protocolos temporal y LOPO x 3 semillas. Mide latencia y tamano.
  2. espejo      mejora 6 (invarianza izquierda/derecha) reflejando cada mano segun la lateralidad de
                 MediaPipe. LOPO.
  3. aumento     mejora 3b (aumentacion de datos: giros, zoom, desplazamientos y ruido; 3 copias por
                 muestra), sin normalizar y con la normalizacion completa. LOPO.
  4. volteo      mejoras 3b + 6: aumentacion que ademas voltea la mitad de las copias, la otra forma de
                 conseguir invarianza izquierda/derecha. LOPO.
  5. exportar    el mejor modelo en LOPO de todo el plan (y la mejor CNN si es otro), listo para la demo.

Todos los experimentos miden tambien la precision con la mano opuesta simulada (test reflejado).

Presupuesto: antes de cada experimento se estima su duracion con el tiempo medio por entrenamiento de
red medido en los anteriores (en el primero, con el de la prueba en GPU: ~55 s). Si no cabe, se reduce
a 1 semilla; si aun asi no cabe, se salta y se avisa. Nunca se corta un experimento a medias.
Las redes entrenan en la GPU NVIDIA (8 procesos); scikit-learn va en CPU.
"""
import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from hgr import cli, constantes as C, modelos as MOD, utils  # noqa: E402

SEG_POR_RED_INICIAL = 55.0      # medido en prueba_gpu (5 tomas reales, 6 procesos en GPU, paciencia 20)
REDES = {'cnn_baseline', 'mlp', 'cnn_repo'}

PLAN = [
    {'nombre': 'principal', 'modelos': MOD.MODELOS_POR_DEFECTO, 'normalizaciones': C.NORMALIZACIONES,
     'protocolos': C.PROTOCOLOS_POR_DEFECTO, 'semillas': [0, 1, 2], 'extra': [], 'aumentar': 0,
     'mide': True, 'que': 'minimo + mejora 1 (modelos y trade-off) + mejora 3a (normalizaciones)'},
    {'nombre': 'espejo', 'modelos': ['cnn_baseline', 'mlp', 'svm', 'logreg'],
     'normalizaciones': ['muneca_escala', 'muneca_escala_rot'], 'protocolos': ['lopo'], 'semillas': [0, 1, 2],
     'extra': ['--espejo'], 'aumentar': 0, 'mide': False,
     'que': 'mejora 6: invarianza izquierda/derecha reflejando segun MediaPipe'},
    {'nombre': 'aumento', 'modelos': ['cnn_baseline', 'mlp', 'svm', 'logreg'],
     'normalizaciones': ['ninguna', 'muneca_escala_rot'], 'protocolos': ['lopo'], 'semillas': [0, 1],
     'extra': ['--aumentar', '3'], 'aumentar': 3, 'mide': False,
     'que': 'mejora 3b: aumentacion de datos (giros, zoom, desplazamiento, ruido)'},
    {'nombre': 'volteo', 'modelos': ['cnn_baseline', 'mlp', 'svm', 'logreg'],
     'normalizaciones': ['muneca_escala_rot'], 'protocolos': ['lopo'], 'semillas': [0, 1],
     'extra': ['--aumentar', '3', '--voltear'], 'aumentar': 3, 'mide': False,
     'que': 'mejoras 3b + 6: aumentacion con volteos para la invarianza izquierda/derecha'},
]


def n_pliegues(protocolos, n_participantes=5):
    return sum({'aleatorio': 1, 'temporal': 1, 'lopo': n_participantes}[p] for p in protocolos)


def trabajos_red(exp, semillas):
    redes = [m for m in exp['modelos'] if m in REDES]
    return len(redes) * len(exp['normalizaciones']) * n_pliegues(exp['protocolos']) * len(semillas)


def estimar_min(exp, semillas, seg_por_red, workers_gpu):
    """Minutos estimados: redes en paralelo en la GPU + margen fijo para arranque, clasicos y metricas."""
    factor_datos = 1 + exp['aumentar']
    redes = trabajos_red(exp, semillas) * seg_por_red * factor_datos / workers_gpu / 60
    return redes + (4.0 if exp['mide'] else 2.0) + (3.0 if exp['aumentar'] else 0.0)


def seg_medidos_por_red(dir_exp, aumentar):
    import pandas as pd
    f = dir_exp / 'resultados_pliegues.csv'
    if not f.exists():
        return None
    r = pd.read_csv(f)
    r = r[r['modelo'].isin(REDES)]
    if r.empty:
        return None
    return float(r['tiempo_entrenamiento_s'].mean()) / (1 + aumentar)


def comparativa(plan_dirs, destino):
    """Tabla que junta los experimentos: LOPO normal y con la mano opuesta simulada."""
    import pandas as pd
    filas = []
    for nombre, d in plan_dirs.items():
        f = d / 'tablas' / 'resumen.csv'
        if not f.exists():
            continue
        r = pd.read_csv(f)
        r = r[r['protocolo'] == 'lopo']
        cfg = utils.leer_json(d / 'config.json')['experimento']
        for _, x in r.iterrows():
            filas.append({'experimento': nombre, 'modelo': x['modelo'], 'normalizacion': x['normalizacion'],
                          'espejo': cfg['espejo'], 'aumentar': cfg['aumentar'], 'voltear': cfg['voltear'],
                          'lopo_%': 100 * x['accuracy'], 'desv_pp': 100 * x['dispersion'],
                          'lopo_mano_opuesta_%': 100 * x['accuracy_espejado'] if 'accuracy_espejado' in x else float('nan'),
                          'semillas': int(x['n_semillas'])})
    t = pd.DataFrame(filas)
    if t.empty:
        return t
    t = t.sort_values('lopo_%', ascending=False).reset_index(drop=True)
    L = ['# Comparativa del plan de entrenamiento\n',
         'Accuracy en LOPO (participante no visto), media sobre participantes y semillas, y con la mano opuesta '
         'simulada (test reflejado). Ordenado de mejor a peor.\n',
         utils.tabla_markdown(t, formatos={'lopo_%': '{:.1f}', 'desv_pp': '{:.1f}', 'lopo_mano_opuesta_%': '{:.1f}'}),
         '', 'Informes completos de cada experimento:', '']
    L += ['- `%s`: %s' % (n, (d / 'informe.md')) for n, d in plan_dirs.items()]
    destino.write_text('\n'.join(L) + '\n', encoding='utf-8')
    t.to_csv(destino.with_suffix('.csv'), index=False)
    return t


def main(argv=None):
    cli.configurar_consola()
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--presupuesto-min', type=float, default=115.0, help='minutos maximos para todo el plan')
    p.add_argument('--experimentos', nargs='+', default=[e['nombre'] for e in PLAN],
                   choices=[e['nombre'] for e in PLAN])
    p.add_argument('--workers-gpu', type=int, default=8)
    p.add_argument('--sin-exportar', action='store_true')
    p.add_argument('--prefijo', default=None, help='prefijo de las carpetas (por defecto plan_<fecha-hora>)')
    p.add_argument('--datos', nargs='+', default=None, help='carpetas de tomas (por defecto las de siempre)')
    args = p.parse_args(argv)

    import entrenar
    info = utils.info_dispositivo()
    print('Dispositivo: %s' % ('GPU %s (%.1f GB)' % (info['gpu'], info['vram_gb']) if info['dispositivo'] == 'cuda'
                               else 'CPU (no se detecta GPU CUDA)'))
    prefijo = args.prefijo or 'plan_' + utils.marca_temporal()
    t0 = time.time()
    seg_red = SEG_POR_RED_INICIAL
    hechos, recortes = {}, []

    total_est = sum(estimar_min(e, e['semillas'], seg_red, args.workers_gpu) for e in PLAN if e['nombre'] in args.experimentos)
    print('Plan %s: %s | estimacion inicial %.0f min | presupuesto %.0f min\n'
          % (prefijo, ', '.join(args.experimentos), total_est, args.presupuesto_min))

    for exp in PLAN:
        if exp['nombre'] not in args.experimentos:
            continue
        gastado = (time.time() - t0) / 60
        queda = args.presupuesto_min - gastado - (4 if not args.sin_exportar else 0)
        semillas = list(exp['semillas'])
        est = estimar_min(exp, semillas, seg_red, args.workers_gpu)
        if est > queda and len(semillas) > 1:
            semillas = semillas[:1]
            est = estimar_min(exp, semillas, seg_red, args.workers_gpu)
            recortes.append('%s: reducido a 1 semilla para caber en el presupuesto' % exp['nombre'])
        if est > queda:
            recortes.append('%s: SALTADO (estimado %.0f min, quedaban %.0f)' % (exp['nombre'], est, queda))
            print('>>> se salta %s: estimado %.0f min y quedan %.0f' % (exp['nombre'], est, queda))
            continue

        nombre = '%s_%s' % (prefijo, exp['nombre'])
        print('=' * 78)
        print('>>> %s  (%s)' % (nombre, exp['que']))
        print('    estimado %.0f min | llevamos %.0f de %.0f' % (est, gastado, args.presupuesto_min))
        print('=' * 78)
        argv_exp = ['--nombre', nombre, '--modelos', *exp['modelos'], '--normalizaciones', *exp['normalizaciones'],
                    '--protocolos', *exp['protocolos'], '--semillas', *map(str, semillas),
                    '--dispositivo', 'auto', '--workers-gpu', str(args.workers_gpu), *exp['extra']]
        if args.datos:
            argv_exp += ['--datos', *args.datos]
        if not exp['mide']:
            argv_exp.append('--sin-rendimiento')
        t_exp = time.time()
        rc = entrenar.main(argv_exp)
        d = C.DIR_RESULTADOS / nombre
        hechos[exp['nombre']] = d
        medido = seg_medidos_por_red(d, exp['aumentar'])
        if medido:
            seg_red = medido
        print('<<< %s terminado en %.1f min (rc=%s). Tiempo medio por red: %.0f s\n'
              % (exp['nombre'], (time.time() - t_exp) / 60, rc, seg_red * (1 + exp['aumentar'])))

    tabla = comparativa(hechos, C.DIR_RESULTADOS / (prefijo + '_comparativa.md'))

    exportados = []
    if not args.sin_exportar and not tabla.empty:
        import exportar_modelo
        elegidos = [tabla.iloc[0]]
        cnn = tabla[tabla['modelo'] == 'cnn_baseline']
        if len(cnn) and cnn.index[0] != tabla.index[0]:
            elegidos.append(cnn.iloc[0])
        for fila in elegidos:
            nombre_mod = '%s_%s_%s' % (prefijo, fila['modelo'], fila['normalizacion'])
            argv_mod = ['--modelo', fila['modelo'], '--normalizacion', fila['normalizacion'],
                        '--experimento', str(C.DIR_RESULTADOS / ('%s_%s' % (prefijo, fila['experimento']))),
                        '--nombre', nombre_mod]
            if args.datos:
                argv_mod += ['--datos', *args.datos]   # exactamente los mismos datos que se evaluaron
            if fila['espejo']:
                argv_mod.append('--espejo')
            if fila['aumentar']:
                argv_mod += ['--aumentar', str(int(fila['aumentar']))]
            if fila['voltear']:
                argv_mod.append('--voltear')
            print('>>> exportando %s (%s, LOPO %.1f%%)' % (nombre_mod, fila['experimento'], fila['lopo_%']))
            sys.argv = ['exportar_modelo.py'] + argv_mod
            exportar_modelo.main()
            exportados.append(C.DIR_MODELOS / nombre_mod)

    print('\n' + '=' * 78)
    print(' PLAN TERMINADO en %.1f min (presupuesto %.0f)' % ((time.time() - t0) / 60, args.presupuesto_min))
    print('=' * 78)
    if not tabla.empty:
        print(tabla.head(12).to_string(index=False, float_format=lambda v: '%.1f' % v))
        print('\nComparativa: %s' % (C.DIR_RESULTADOS / (prefijo + '_comparativa.md')))
    for d in exportados:
        print('Modelo exportado: %s' % d)
    for r in recortes:
        print('[RECORTE] %s' % r)
    return 0


if __name__ == '__main__':
    sys.exit(main())
