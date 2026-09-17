"""PASO 3. Entrena el modelo definitivo con TODAS las tomas y lo deja listo para la demo.

Elige modelo y normalizacion a partir del informe (el mejor en LOPO). Ejemplos:
    python exportar_modelo.py --modelo cnn_baseline --normalizacion muneca_escala_rot
    python exportar_modelo.py --modelo cnn_baseline --normalizacion muneca_escala_rot --espejo \
        --experimento completo --nombre cnn_final

Con --experimento se copian a la ficha del modelo las metricas LOPO de esa configuracion,
para que la cifra que acompana al modelo sea la honesta y no la de validacion.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from hgr import cli, constantes as C, modelos as MOD, utils  # noqa: E402


def main():
    cli.configurar_consola()
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--modelo', required=True, choices=MOD.MODELOS)
    p.add_argument('--normalizacion', required=True, choices=C.NORMALIZACIONES)
    p.add_argument('--espejo', action='store_true')
    p.add_argument('--lado-espejo', default='Left', choices=['Left', 'Right'])
    p.add_argument('--aumentar', type=int, default=0)
    p.add_argument('--voltear', action='store_true')
    p.add_argument('--semilla', type=int, default=0)
    p.add_argument('--epocas', type=int, default=MOD.HP_REDES['epocas'])
    p.add_argument('--paciencia', type=int, default=MOD.HP_REDES['paciencia'])
    p.add_argument('--dispositivo', choices=['auto', 'gpu', 'cpu'], default='auto',
                   help='dispositivo para entrenar (auto: usa GPU CUDA si está disponible)')
    p.add_argument('--nombre', default=None, help='carpeta dentro de entrenamiento/modelos/')
    p.add_argument('--experimento', default=None, help='experimento del que copiar las metricas de referencia')
    cli.argumentos_datos(p)
    args = p.parse_args()

    info_disp = utils.info_dispositivo()
    if info_disp['dispositivo'] == 'cuda':
        print('Dispositivo de cómputo: CUDA (%s, %.1f GB VRAM)' % (info_disp['gpu'], info_disp['vram_gb']))
    else:
        print('Dispositivo de cómputo: CPU (no se detecta GPU CUDA)')

    metricas = None
    if args.experimento:
        import pandas as pd
        d = Path(args.experimento) if (Path(args.experimento) / 'tablas').exists() else C.DIR_RESULTADOS / args.experimento
        r = pd.read_csv(d / 'tablas' / 'resumen.csv')
        sel = r[(r['modelo'] == args.modelo) & (r['normalizacion'] == args.normalizacion)]
        cfg_exp = utils.leer_json(d / 'config.json')['experimento']
        if cfg_exp.get('espejo') != args.espejo or cfg_exp.get('aumentar') != args.aumentar:
            print('[AVISO] el experimento %s se hizo con espejo=%s y aumentar=%s; estas exportando con espejo=%s y '
                  'aumentar=%s: sus metricas no corresponden exactamente a este modelo'
                  % (d.name, cfg_exp.get('espejo'), cfg_exp.get('aumentar'), args.espejo, args.aumentar))
        metricas = {'experimento': d.name, 'por_protocolo': sel.to_dict(orient='records')}

    nombre = args.nombre or '%s_%s%s_%s' % (args.modelo, args.normalizacion, '_espejo' if args.espejo else '',
                                            utils.marca_temporal())
    _, df, _ = cli.cargar_dataset(args)
    if df is None or df.empty:
        print('No hay tomas.')
        return 1
    from hgr.exportacion import exportar
    res = exportar(df, C.DIR_MODELOS / nombre, modelo=args.modelo, normalizacion=args.normalizacion,
                   espejo=args.espejo, lado_espejo=args.lado_espejo, semilla=args.semilla, aumentar=args.aumentar,
                   voltear=args.voltear, hp={'epocas': args.epocas, 'paciencia': args.paciencia},
                   dispositivo=args.dispositivo, metricas_referencia=metricas)
    print('\nModelo exportado en %s' % res['carpeta'])
    print('Clases (orden de salida): %s' % res['clases'])
    if res['accuracy_validacion'] is not None:
        print('Accuracy en validacion: %.1f%% (optimista: la cifra honesta es la LOPO del informe)'
              % (100 * res['accuracy_validacion']))
    return 0


if __name__ == '__main__':
    sys.exit(main())
