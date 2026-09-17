"""PASO 2. Entrena y evalua la rejilla de experimentos y genera tablas, figuras e informe.

Ejemplos:
    python entrenar.py --rapido
        comprobacion en pocos minutos: cnn_baseline, svm y logreg; sin normalizar y con
        la normalizacion completa; protocolos temporal y lopo; una semilla.
    python entrenar.py --nombre principal
        rejilla por defecto: 6 modelos x 4 normalizaciones x protocolos temporal y lopo x 3 semillas
        (sin cnn_repo, que ya entrena el notebook, ni el protocolo aleatorio; ver modelos.py y constantes.py).
    python entrenar_todo.py
        TODO el plan (principal + mejoras 3 y 6 + exportacion) ajustado a un presupuesto de tiempo.
    python entrenar.py --nombre espejo --normalizaciones muneca_escala_rot --espejo
        mejora 5: invarianza izquierda/derecha reflejando segun la lateralidad de MediaPipe.
    python entrenar.py --nombre aumento --aumentar 5
        mejora 2: aumentacion de datos sobre los landmarks (5 copias por muestra de train).

Resultados en entrenamiento/resultados/<nombre>/ (nunca se sobreescribe uno existente):
    informe.md            resumen legible con todas las tablas
    figuras/              PNG (200 dpi) y PDF
    tablas/               CSV de cada tabla
    resultados_pliegues.csv, predicciones.csv.gz, historiales.json, rendimiento.csv, config.json
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from hgr import cli, constantes as C, modelos as MOD, utils  # noqa: E402


def construir_parser():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--nombre', default=None, help='nombre del experimento (por defecto exp_<fecha-hora>)')
    p.add_argument('--rapido', action='store_true', help='rejilla reducida para comprobar que todo funciona')
    p.add_argument('--modelos', nargs='+', default=None, help='%s o todos (por defecto: %s)' % (MOD.MODELOS, MOD.MODELOS_POR_DEFECTO))
    p.add_argument('--normalizaciones', nargs='+', default=['todas'], help='%s o todas' % C.NORMALIZACIONES)
    p.add_argument('--protocolos', nargs='+', default=None, help='%s o todos (por defecto: %s)' % (C.PROTOCOLOS, C.PROTOCOLOS_POR_DEFECTO))
    p.add_argument('--semillas', nargs='+', type=int, default=[0, 1, 2])
    p.add_argument('--espejo', action='store_true', help='reflejar las manos segun la lateralidad de MediaPipe')
    p.add_argument('--lado-espejo', default='Left', choices=['Left', 'Right'])
    p.add_argument('--aumentar', type=int, default=0, help='copias aumentadas por muestra de train (0 = sin aumentacion)')
    p.add_argument('--voltear', action='store_true', help='en la aumentacion, reflejar la mitad de las copias')
    p.add_argument('--epocas', type=int, default=MOD.HP_REDES['epocas'])
    p.add_argument('--paciencia', type=int, default=MOD.HP_REDES['paciencia'])
    p.add_argument('--batch', type=int, default=MOD.HP_REDES['batch'])
    p.add_argument('--sin-rendimiento', action='store_true', help='no medir latencia ni tamano')
    cli.argumentos_computo(p)
    cli.argumentos_datos(p)
    return p


def main(argv=None):
    cli.configurar_consola()
    args = construir_parser().parse_args(argv)
    info_disp = utils.info_dispositivo()
    if info_disp['dispositivo'] == 'cuda':
        print('Dispositivo de cómputo: CUDA (%s, %.1f GB VRAM)' % (info_disp['gpu'], info_disp['vram_gb']))
    else:
        print('Dispositivo de cómputo: CPU (no se detecta GPU CUDA)')

    if args.rapido:
        modelos, normas, protos, semillas = ['cnn_baseline', 'svm', 'logreg'], ['ninguna', 'muneca_escala_rot'], \
            ['temporal', 'lopo'], [args.semillas[0]]
        if args.paciencia == MOD.HP_REDES['paciencia']:
            args.paciencia = 20
    else:
        modelos = cli.lista(args.modelos, MOD.MODELOS) if args.modelos else list(MOD.MODELOS_POR_DEFECTO)
        normas = cli.lista(args.normalizaciones, C.NORMALIZACIONES)
        protos = cli.lista(args.protocolos, C.PROTOCOLOS) if args.protocolos else list(C.PROTOCOLOS_POR_DEFECTO)
        semillas = args.semillas

    from hgr.experimento import ConfigExperimento, ejecutar_experimento
    from hgr.evaluacion import agregar
    nombre = args.nombre or 'exp_' + utils.marca_temporal()
    dir_salida = C.DIR_RESULTADOS / nombre
    if dir_salida.exists():
        print('[ERROR] ya existe %s. Elige otro --nombre: los resultados anteriores no se sobreescriben.' % dir_salida)
        return 2

    cfg = ConfigExperimento(nombre=nombre, modelos=modelos, normalizaciones=normas, protocolos=protos,
                            semillas=semillas, espejo=args.espejo, lado_espejo=args.lado_espejo,
                            aumentar=args.aumentar, voltear=args.voltear, epocas=args.epocas,
                            paciencia=args.paciencia, batch=args.batch, workers=args.workers,
                            medir_rendimiento=not args.sin_rendimiento, min_deteccion=args.min_deteccion,
                            raices_datos=[str(r) for r in (args.datos or C.RAICES_DATOS_POR_DEFECTO)],
                            incluir_pruebas=args.incluir_pruebas,
                            dispositivo=args.dispositivo, workers_gpu=args.workers_gpu)
    try:
        cfg.validar()
    except ValueError as e:
        print('[ERROR] %s' % e)
        return 2

    tomas, df, avisos = cli.cargar_dataset(args)
    if df is None or df.empty:
        print('\nNo hay tomas. Descomprime las tomas en entrenamiento/datos/ o indica --datos.')
        return 1
    ejecutar_experimento(cfg, df, dir_salida, avisos=avisos)
    res = agregar(dir_salida)

    r, ref, top = res['resumen'], res['referencia'], res['mejor']
    print('\n' + '=' * 78)
    print(' RESULTADO (%s)' % ref)
    print('=' * 78)
    t = r[r['protocolo'] == ref].pivot(index='modelo', columns='normalizacion', values='accuracy') * 100
    print(t.round(1).to_string())
    print('\nMejor: %s con %s -> accuracy %.1f%% (desviacion %.1f pp)'
          % (top['modelo'], top['normalizacion'], 100 * top['accuracy'], 100 * (top['dispersion'] if top['dispersion'] == top['dispersion'] else 0)))
    print('Informe completo: %s' % (dir_salida / 'informe.md'))
    if (dir_salida / 'errores_ejecucion.txt').exists():
        print('[AVISO] algunos trabajos fallaron: %s' % (dir_salida / 'errores_ejecucion.txt'))
        return 3
    return 0


if __name__ == '__main__':
    sys.exit(main())
