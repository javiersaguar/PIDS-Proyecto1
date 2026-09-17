"""Entrenar el modelo definitivo con TODAS las tomas y dejarlo listo para la demo.

Carpeta resultante (nunca sobreescribe una existente):
    modelo.keras | modelo.joblib   el modelo
    modelo.tflite, modelo_cuant.tflite   (redes) para Raspberry Pi / movil
    etiquetas.json                 clases en el orden de las salidas del modelo
    preprocesado.json              normalizacion, espejo y forma de entrada
    ficha.json                     de donde sale: datos, semilla, versiones, metricas
    curvas.png/.pdf                (redes) curvas de aprendizaje

Antes de dar la exportacion por buena se recarga la carpeta con ClasificadorGestos y
se comprueba que predice exactamente lo mismo que el modelo recien entrenado a
partir de las coordenadas crudas: si alguna vez la demo y el entrenamiento
preprocesaran distinto, esta comprobacion fallaria.
"""
from pathlib import Path

import numpy as np

from . import constantes as C
from . import features as F
from . import modelos as MOD
from . import protocolos as PR
from . import utils
from .experimento import preparar_datos, resumen_dataset


def exportar(df_landmarks, dir_salida, modelo='cnn_baseline', normalizacion='muneca_escala_rot', espejo=False,
             lado_espejo='Left', semilla=0, aumentar=0, voltear=False, frac_val=0.15, hp=None,
             dispositivo='auto', metricas_referencia=None, log=print):
    dir_salida = Path(dir_salida)
    if dir_salida.exists():
        raise FileExistsError('ya existe %s: elige otro --nombre' % dir_salida)
    if espejo and voltear:
        raise ValueError('--espejo y --voltear son alternativas: usa solo una')
    avisos = []
    datos = preparar_datos(df_landmarks, avisos)
    muestras, P, ar, h, y, clases = (datos[k] for k in ('muestras', 'P', 'ar', 'h', 'y', 'clases'))
    forma = MOD.FORMA_ENTRADA[modelo]

    tr, va = PR._separar_ultimos(muestras, np.arange(len(muestras)), frac_val)
    P_tr, ar_tr, h_tr, y_tr = P[tr], ar[tr], h[tr], y[tr]
    if aumentar > 0:
        rng = np.random.default_rng(utils.semilla_estable(semilla, 'final', 'aumentar'))
        B, A, idx = F.aumentar(P_tr, ar_tr, rng, aumentar, voltear=voltear)
        P_tr, ar_tr = np.concatenate([P_tr, B]), np.concatenate([ar_tr, A])
        h_tr, y_tr = np.concatenate([h_tr, h_tr[idx]]), np.concatenate([y_tr, y_tr[idx]])

    def entrada(Pp, aa, hh):
        return F.preparar_entrada(F.transformar(Pp, aa, hh, normalizacion, espejo, lado_espejo), forma)

    X_tr, X_va = entrada(P_tr, ar_tr, h_tr), entrada(P[va], ar[va], h[va])
    if MOD.FAMILIA[modelo] == 'red neuronal':
        from .experimento import resolver_gpu
        usar_gpu = resolver_gpu(dispositivo)
        utils.preparar_entorno(usar_gpu=usar_gpu)
        utils.silenciar_logs_tf()
    m = MOD.crear_modelo(modelo, len(clases), hp)
    utils.fijar_semillas(semilla)
    log('entrenando %s con %d muestras (%d de validacion)...' % (modelo, len(X_tr), len(va)))
    with utils.Cronometro() as cr:
        m.ajustar(X_tr, y_tr, X_va, y[va], semilla)
    acc_val = float((m.predecir_proba(X_va).argmax(1) == y[va]).mean()) if len(va) else None

    dir_salida.mkdir(parents=True)
    ruta_modelo = m.guardar(dir_salida)
    extra = {}
    if m.familia == 'red neuronal':
        from .rendimiento import _tflite, tflite_disponible
        if tflite_disponible():
            try:
                import tensorflow as tf
                info, plano = _tflite(m.modelo, X_va[:1] if len(va) else X_tr[:1])
                (dir_salida / 'modelo.tflite').write_bytes(plano)
                with utils.sin_salida():
                    conv = tf.lite.TFLiteConverter.from_keras_model(m.modelo)
                    conv.optimizations = [tf.lite.Optimize.DEFAULT]
                    (dir_salida / 'modelo_cuant.tflite').write_bytes(conv.convert())
                extra = info
            except Exception as e:
                extra = {'tflite_error': str(e)[:300]}
        else:
            extra = {'tflite_disponible': False}
        from . import graficas as G
        G.curvas_aprendizaje(m.historial, dir_salida / 'curvas', 'Curvas de aprendizaje: %s (modelo final)' % modelo,
                             'Todas las tomas; validacion = ultimos fotogramas de cada toma y gesto.', m.mejor_epoca)

    utils.guardar_json({'clases': clases}, dir_salida / 'etiquetas.json')
    utils.guardar_json({'modelo': modelo, 'normalizacion': normalizacion, 'espejo': bool(espejo),
                        'lado_espejo': lado_espejo, 'forma_entrada': forma, 'fichero_modelo': ruta_modelo.name,
                        'entrada': 'x, y crudas de MediaPipe HandLandmarker (21 landmarks) + handedness + ancho/alto',
                        'umbral_deteccion_mediapipe': 0.5, 'num_hands': 1}, dir_salida / 'preprocesado.json')
    por_part, _ = resumen_dataset(df_landmarks)
    utils.guardar_json({
        'fecha': utils.ahora(), 'semilla': semilla, 'aumentar': aumentar, 'voltear': voltear,
        'hiperparametros': m.hp if hasattr(m, 'hp') else None, 'epocas': m.epocas_entrenadas,
        'mejor_epoca': m.mejor_epoca, 'accuracy_validacion': acc_val, 'segundos_entrenamiento': round(cr.segundos, 1),
        'parametros': m.n_parametros(), 'bytes_modelo': ruta_modelo.stat().st_size, **extra,
        'dataset': {'muestras_con_mano': int(len(muestras)), 'participantes': sorted(muestras['participante'].unique()),
                    'tomas': sorted(muestras['toma'].unique()), 'por_participante': por_part.to_dict(orient='records')},
        'metricas_referencia': metricas_referencia, 'avisos': avisos, 'versiones': utils.versiones(),
    }, dir_salida / 'ficha.json')

    # comprobacion de paridad entrenamiento <-> demo
    from .inferencia import ClasificadorGestos
    clf = ClasificadorGestos(dir_salida)
    k = np.arange(len(muestras))[:: max(1, len(muestras) // 200)]
    xy = np.stack([muestras.iloc[k][C.COLS_X].to_numpy(float), muestras.iloc[k][C.COLS_Y].to_numpy(float)], axis=-1)
    anchos, altos = muestras.iloc[k]['ancho'].to_numpy(float), muestras.iloc[k]['alto'].to_numpy(float)
    p_demo = np.concatenate([clf.probabilidades(clf.entrada(xy[i], h[k][i], anchos[i], altos[i])) for i in range(len(k))])
    p_entreno = m.predecir_proba(entrada(P[k], ar[k], h[k]))
    iguales = bool(np.array_equal(p_demo.argmax(1), p_entreno.argmax(1)) and np.allclose(p_demo, p_entreno, atol=1e-4))
    if not iguales:
        raise AssertionError('la carpeta exportada NO reproduce las predicciones del entrenamiento')
    log('paridad entrenamiento/demo comprobada en %d muestras' % len(k))
    return {'carpeta': dir_salida, 'accuracy_validacion': acc_val, 'epocas': m.epocas_entrenadas, 'clases': clases}
