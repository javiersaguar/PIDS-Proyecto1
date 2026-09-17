"""Agregacion de un experimento ya ejecutado: tablas CSV, figuras e informe.md.

Se puede relanzar tantas veces como se quiera sin reentrenar (evaluar.py).

Como se agregan las cifras:
  1. dentro de cada pliegue se promedia sobre semillas (el azar de la inicializacion);
  2. entre pliegues se da media y desviacion tipica. En lopo esa desviacion es la
     variabilidad ENTRE PERSONAS, que es la incertidumbre que de verdad importa. En
     aleatorio y temporal (un unico pliegue) se muestra la desviacion entre semillas.
  El IC al 95% "del repo" (common/evaluation.py) se incluye para comparar con el
  enunciado, avisando de que supone muestras independientes y no lo son.

Protocolo de referencia para elegir "el mejor modelo": el mas honesto disponible
(lopo, si no temporal, si no aleatorio). Nunca se elige mirando el test de otro
protocolo mas optimista.
"""
from pathlib import Path

import numpy as np
import pandas as pd

from . import constantes as C
from . import graficas as G
from . import metricas as M
from . import modelos as MOD
from . import utils

CLAVES = ['normalizacion', 'protocolo', 'modelo']
NOMBRES_PROTOCOLO = {'aleatorio': 'aleatorio', 'temporal': 'temporal (repo)', 'lopo': 'LOPO'}


def _pct(v):
    return '' if v is None or (isinstance(v, float) and np.isnan(v)) else '%.1f' % (100 * v)


def cargar(dir_exp):
    d = Path(dir_exp)
    ctx = {'dir': d, 'config': utils.leer_json(d / 'config.json')}
    ctx['clases'] = ctx['config']['clases']
    ctx['pliegues'] = pd.read_csv(d / 'resultados_pliegues.csv', dtype={'pliegue': str})
    ctx['pred'] = pd.read_csv(d / 'predicciones.csv.gz', dtype={'pliegue': str})
    ctx['muestras'] = pd.read_csv(d / 'muestras.csv.gz', dtype=C.DTYPES_TEXTO, index_col='indice')
    ctx['landmarks'] = pd.read_csv(d / 'landmarks_todas.csv.gz', dtype=C.DTYPES_TEXTO) \
        if (d / 'landmarks_todas.csv.gz').exists() else None
    ctx['historiales'] = utils.leer_json(d / 'historiales.json') if (d / 'historiales.json').exists() else []
    ctx['rendimiento'] = pd.read_csv(d / 'rendimiento.csv') if (d / 'rendimiento.csv').exists() else pd.DataFrame()
    return ctx


def tabla_resumen(pl):
    if 'accuracy_espejado' not in pl.columns:          # experimentos anteriores a esta medida
        pl = pl.assign(accuracy_espejado=np.nan)
    g = pl.groupby(CLAVES + ['pliegue'])
    por_pliegue = g.agg(accuracy=('accuracy', 'mean'), accuracy_espejado=('accuracy_espejado', 'mean'),
                        balanced_accuracy=('balanced_accuracy', 'mean'),
                        f1_macro=('f1_macro', 'mean'), accuracy_std_sem=('accuracy', 'std'),
                        n_semillas=('semilla', 'nunique'), n_test=('n_test', 'first'),
                        tiempo=('tiempo_entrenamiento_s', 'mean'), epocas=('epocas', 'mean')).reset_index()
    r = por_pliegue.groupby(CLAVES).agg(
        accuracy=('accuracy', 'mean'),
        accuracy_espejado=('accuracy_espejado', 'mean'),
        accuracy_std_pliegues=('accuracy', lambda s: s.std(ddof=1) if len(s) > 1 else np.nan),
        accuracy_min=('accuracy', 'min'),
        balanced_accuracy=('balanced_accuracy', 'mean'),
        f1_macro=('f1_macro', 'mean'),
        accuracy_std_semillas=('accuracy_std_sem', 'mean'),
        n_pliegues=('pliegue', 'nunique'), n_semillas=('n_semillas', 'max'), n_test=('n_test', 'sum'),
        tiempo_entrenamiento_s=('tiempo', 'mean'), epocas=('epocas', 'mean')).reset_index()
    r['ic95_repo'] = [M.ic95_repo(n, a) for n, a in zip(r['n_test'], r['accuracy'])]
    r['dispersion'] = r['accuracy_std_pliegues'].fillna(r['accuracy_std_semillas'])
    orden_m = {m: i for i, m in enumerate(MOD.MODELOS)}
    orden_n = {n: i for i, n in enumerate(C.NORMALIZACIONES)}
    orden_p = {p: i for i, p in enumerate(C.PROTOCOLOS)}
    r = r.sort_values(by=['protocolo', 'normalizacion', 'modelo'],
                      key=lambda s: s.map({**orden_p, **orden_n, **orden_m})).reset_index(drop=True)
    return r, por_pliegue


def protocolo_referencia(resumen):
    presentes = set(resumen['protocolo'])
    return next(p for p in C.PROTOCOLO_MAS_HONESTO if p in presentes)


def mejor_por_modelo(resumen, protocolo):
    d = resumen[resumen['protocolo'] == protocolo]
    return d.sort_values(['accuracy', 'dispersion'], ascending=[False, True]).groupby('modelo', sort=False).head(1)


def _filtrar(pred, norm, prot, modelo):
    return pred[(pred['normalizacion'] == norm) & (pred['protocolo'] == prot) & (pred['modelo'] == modelo)]


def por_participante(pred, norm, modelo):
    d = _filtrar(pred, norm, 'lopo', modelo)
    if d.empty:
        return pd.DataFrame(columns=['participante', 'accuracy'])
    acc = d.assign(ok=d['real'] == d['predicha']).groupby(['pliegue', 'semilla'])['ok'].mean()
    return acc.groupby('pliegue').mean().rename('accuracy').rename_axis('participante').reset_index()


def agregar(dir_exp, log=print):
    ctx = cargar(dir_exp)
    d, clases, pred, muestras = ctx['dir'], ctx['clases'], ctx['pred'], ctx['muestras']
    n_cl = len(clases)
    dir_fig, dir_tab = d / 'figuras', d / 'tablas'
    dir_fig.mkdir(exist_ok=True)
    dir_tab.mkdir(exist_ok=True)

    resumen, por_pliegue = tabla_resumen(ctx['pliegues'])
    resumen.to_csv(dir_tab / 'resumen.csv', index=False)
    por_pliegue.to_csv(dir_tab / 'resultados_por_pliegue_promedio_semillas.csv', index=False)

    ref = protocolo_referencia(resumen)
    mejores = mejor_por_modelo(resumen, ref)
    top = mejores.iloc[0]
    modelos = [m for m in MOD.MODELOS if m in set(resumen['modelo'])]
    normas = [n for n in C.NORMALIZACIONES if n in set(resumen['normalizacion'])]
    protos = [p for p in C.PROTOCOLOS if p in set(resumen['protocolo'])]
    norma_de = dict(zip(mejores['modelo'], mejores['normalizacion']))

    # --- brecha entre protocolos (con la mejor normalizacion de cada modelo en ref)
    filas = []
    for m in modelos:
        fila = {'modelo': m, 'normalizacion': norma_de[m]}
        for p in protos:
            v = resumen[(resumen['modelo'] == m) & (resumen['normalizacion'] == norma_de[m]) & (resumen['protocolo'] == p)]
            fila[p] = float(v['accuracy'].iloc[0]) if len(v) else np.nan
        for p in protos:
            if p != ref:
                fila['brecha_%s_menos_%s_pp' % (p, ref)] = 100 * (fila[p] - fila[ref])
        filas.append(fila)
    brecha = pd.DataFrame(filas)
    brecha.to_csv(dir_tab / 'brecha_protocolos.csv', index=False)

    # --- configuraciones que se analizan en detalle
    detalle = [(top['normalizacion'], top['modelo'])]
    if 'cnn_baseline' in modelos and 'ninguna' in normas and ('ninguna', 'cnn_baseline') not in detalle:
        detalle.append(('ninguna', 'cnn_baseline'))       # la CNN del enunciado tal cual, sin normalizar
    if 'cnn_baseline' in modelos and (norma_de['cnn_baseline'], 'cnn_baseline') not in detalle:
        detalle.append((norma_de['cnn_baseline'], 'cnn_baseline'))

    por_clase, confusiones, participantes = {}, {}, {}
    for norm, modelo in detalle:
        dd = _filtrar(pred, norm, ref, modelo)
        por_clase[(norm, modelo)] = M.informe_por_clase(dd['real'], dd['predicha'], clases)
        cm = M.matriz_confusion(dd['real'], dd['predicha'], n_cl)
        confusiones[(norm, modelo)] = M.principales_confusiones(cm, clases)
        por_clase[(norm, modelo)].to_csv(dir_tab / ('por_clase_%s_%s_%s.csv' % (modelo, norm, ref)), index=False)
        confusiones[(norm, modelo)].to_csv(dir_tab / ('confusiones_%s_%s_%s.csv' % (modelo, norm, ref)), index=False)
        if 'lopo' in protos:
            participantes[(norm, modelo)] = por_participante(pred, norm, modelo)
            participantes[(norm, modelo)].to_csv(dir_tab / ('por_participante_%s_%s.csv' % (modelo, norm)), index=False)

    rend = _tabla_rendimiento(ctx['rendimiento'])
    if not rend.empty:
        rend.to_csv(dir_tab / 'rendimiento.csv', index=False)

    # --- invarianza izquierda/derecha: test normal frente a test reflejado (mano opuesta simulada)
    inv = mejores[['modelo', 'normalizacion', 'accuracy', 'accuracy_espejado']].copy()
    inv['caida_pp'] = 100 * (inv['accuracy'] - inv['accuracy_espejado'])
    inv.to_csv(dir_tab / ('invarianza_mano_%s.csv' % ref), index=False)

    diversidad = diversidad_dataset(ctx['landmarks'])
    if diversidad is not None:
        diversidad['resumen'].to_csv(dir_tab / 'diversidad_dataset.csv', index=False)

    figuras = _figuras(ctx, resumen, ref, modelos, normas, protos, mejores, norma_de, detalle, participantes, rend)
    if diversidad is not None:
        figuras.append(G.diversidad(diversidad['muestras'], dir_fig / 'diversidad_dataset'))
    errores = _errores(pred, muestras, clases, top['normalizacion'], ref, top['modelo'])
    errores.to_csv(dir_tab / ('errores_%s_%s_%s.csv' % (top['modelo'], top['normalizacion'], ref)), index=False)
    fig_err = _galeria(errores, ctx, dir_fig, top, ref)
    if fig_err:
        figuras.append(fig_err)

    informe = _informe(ctx, resumen, ref, mejores, brecha, detalle, por_clase, confusiones, participantes,
                       rend, figuras, protos, normas, modelos, inv, diversidad)
    (d / 'informe.md').write_text(informe, encoding='utf-8')
    log('informe: %s' % (d / 'informe.md'))
    return {'resumen': resumen, 'referencia': ref, 'mejor': top, 'brecha': brecha, 'figuras': figuras}


def diversidad_dataset(landmarks):
    """Pruebas numericas de que se grabo con distintas distancias, angulos y posiciones.

    - tamano de la mano: distancia muneca -> nudillo del corazon en unidades de alto de imagen
      (cuanto mayor, mas cerca de la camara);
    - inclinacion: angulo de ese vector respecto a la vertical, en grados;
    - posicion: coordenadas de la muneca en el encuadre (0-1).
    """
    if landmarks is None or landmarks.empty:
        return None
    lm = landmarks.copy()
    lm = lm[lm['detectada'].astype(str).str.lower().eq('true')]
    if lm.empty:
        return None
    ar = lm['ancho'].astype(float) / lm['alto'].astype(float)
    dx = (lm['x9'].astype(float) - lm['x0'].astype(float)) * ar
    dy = lm['y9'].astype(float) - lm['y0'].astype(float)
    m = pd.DataFrame({'participante': lm['participante'].to_numpy(), 'clase': lm['clase'].to_numpy(),
                      'tamano': np.hypot(dx, dy).to_numpy(),
                      'angulo': np.degrees(np.arctan2(dx, -dy)).to_numpy(),
                      'x_muneca': lm['x0'].astype(float).to_numpy(), 'y_muneca': lm['y0'].astype(float).to_numpy(),
                      'lado_mp': lm['handedness'].to_numpy()})

    def rango(s):
        return '%.2f - %.2f' % (s.quantile(0.05), s.quantile(0.95))

    g = m.groupby('participante')
    res = pd.DataFrame({
        'tamano_mano_p5_p95': g['tamano'].apply(rango),
        'tamano_max_sobre_min': g['tamano'].apply(lambda s: s.quantile(0.95) / max(1e-9, s.quantile(0.05))),
        'inclinacion_grados_p5_p95': g['angulo'].apply(lambda s: '%.0f - %.0f' % (s.quantile(0.05), s.quantile(0.95))),
        'x_muneca_p5_p95': g['x_muneca'].apply(rango),
        'y_muneca_p5_p95': g['y_muneca'].apply(rango),
        'mediapipe_left_%': g['lado_mp'].apply(lambda s: 100 * s.eq('Left').mean()),
    }).reset_index()
    return {'resumen': res, 'muestras': m}


def _tabla_rendimiento(rend):
    if rend.empty:
        return rend
    r = rend.copy()
    for c in ('parametros', 'bytes_disco', 'tflite_bytes', 'tflite_cuant_bytes', 'latencia_ms', 'latencia_tflite_ms'):
        if c not in r.columns:
            r[c] = np.nan
    r['kb_disco'] = r['bytes_disco'] / 1024
    r['kb_tflite'] = r['tflite_bytes'] / 1024
    r['kb_tflite_cuant'] = r['tflite_cuant_bytes'] / 1024
    # formato de despliegue: TFLite para las redes; el propio modelo para los clasicos
    r['latencia_despliegue_ms'] = r['latencia_tflite_ms'].fillna(r['latencia_ms'])
    r['kb_despliegue'] = r['kb_tflite'].fillna(r['kb_disco'])
    return r


def _figuras(ctx, resumen, ref, modelos, normas, protos, mejores, norma_de, detalle, participantes, rend):
    dfig, clases, pred = ctx['dir'] / 'figuras', ctx['clases'], ctx['pred']
    figs = []
    disp = 'desviacion entre participantes (LOPO) o entre semillas (resto)'

    if len(protos) > 1:
        for norm in normas:
            dd = resumen[resumen['normalizacion'] == norm]
            medias = {(r.modelo, r.protocolo): r.accuracy for r in dd.itertuples()}
            errs = {(r.modelo, r.protocolo): r.dispersion for r in dd.itertuples()}
            figs.append(G.barras_agrupadas(
                modelos, protos, medias, errs, dfig / ('protocolos_%s' % norm),
                'Accuracy segun el protocolo de evaluacion',
                'Normalizacion: %s. Barras: media; bigotes: %s. Etiquetado: %s.' % (norm, disp, NOMBRES_PROTOCOLO[ref]),
                serie_etiquetada=ref, nombres_series=NOMBRES_PROTOCOLO))

    if len(normas) > 1:
        dd = resumen[resumen['protocolo'] == ref]
        medias = {(r.modelo, r.normalizacion): r.accuracy for r in dd.itertuples()}
        errs = {(r.modelo, r.normalizacion): r.dispersion for r in dd.itertuples()}
        figs.append(G.barras_agrupadas(
            modelos, normas, medias, errs, dfig / ('normalizaciones_%s' % ref),
            'Accuracy segun la normalizacion de los landmarks',
            'Protocolo: %s. Barras: media; bigotes: %s.' % (NOMBRES_PROTOCOLO[ref], disp)))

    if not rend.empty and 'latencia_despliegue_ms' in rend.columns:
        mp = rend[rend['modelo'] == 'extractor_mediapipe']
        mp_ms = float(mp['latencia_ms'].iloc[0]) if len(mp) and 'latencia_ms' in mp and not mp['latencia_ms'].isna().all() else np.nan
        t = mejores[['modelo', 'normalizacion', 'accuracy']].merge(rend, on='modelo', how='inner')
        t = t[t['familia'] != 'extractor'].dropna(subset=['latencia_despliegue_ms'])
        if len(t):
            nota = ('Extractor de MediaPipe: %.0f ms por fotograma (domina la latencia total).' % mp_ms) if not np.isnan(mp_ms) else ''
            hay_tflite = 'latencia_tflite_ms' in rend.columns and not rend['latencia_tflite_ms'].isna().all()
            sub_lat = ('Protocolo %s, mejor normalizacion de cada modelo. %s%s'
                       % (NOMBRES_PROTOCOLO[ref], 'Redes medidas en TFLite. ' if hay_tflite else '', nota))
            figs.append(G.dispersion_tradeoff(
                t, 'latencia_despliegue_ms', 'accuracy', dfig / 'tradeoff_latencia',
                'Accuracy frente a latencia de inferencia del clasificador',
                'Latencia por muestra (ms, batch 1, 1 hilo, escala log)',
                sub_lat))
            sub_tam = ('Protocolo %s. Redes: %s; clasicos: joblib.'
                       % (NOMBRES_PROTOCOLO[ref], 'fichero TFLite float32' if hay_tflite else 'formato Keras'))
            figs.append(G.dispersion_tradeoff(
                t.dropna(subset=['kb_despliegue']), 'kb_despliegue', 'accuracy', dfig / 'tradeoff_tamano',
                'Accuracy frente a tamano del modelo',
                'Tamano en disco (KB, escala log)',
                sub_tam))

    for prot in protos:
        for norm, modelo in detalle:
            dd = _filtrar(pred, norm, prot, modelo)
            if dd.empty:
                continue
            cm = M.matriz_confusion(dd['real'], dd['predicha'], len(clases)).astype(float)
            pct = 100 * cm / np.maximum(1, cm.sum(axis=1, keepdims=True))
            acc = (dd['real'] == dd['predicha']).mean()
            figs.append(G.mapa_calor(
                pct, clases, clases, dfig / ('confusion_%s_%s_%s' % (modelo, norm, prot)),
                'Matriz de confusion: %s, %s' % (modelo, NOMBRES_PROTOCOLO[prot]),
                'Normalizacion %s. Accuracy %.1f%%. Cada fila suma 100%% de la clase real (%d predicciones).'
                % (norm, 100 * acc, len(dd)),
                fmt='%.0f', etiqueta_filas='Clase real', etiqueta_columnas='Clase predicha', etiqueta_barra='% de la fila'))

    for (norm, modelo), dfp in participantes.items():
        if len(dfp):
            figs.append(G.barras_simple(
                list(dfp['participante']), list(dfp['accuracy']), dfig / ('participantes_%s_%s' % (modelo, norm)),
                'Accuracy con cada participante no visto (LOPO)',
                '%s, normalizacion %s. Media %.1f%%, desviacion %.1f pp.'
                % (modelo, norm, 100 * dfp['accuracy'].mean(), 100 * dfp['accuracy'].std(ddof=1) if len(dfp) > 1 else 0)))

    f1 = []
    for m in modelos:
        dd = _filtrar(pred, norma_de[m], ref, m)
        f1.append(M.informe_por_clase(dd['real'], dd['predicha'], clases)['f1'].to_numpy() * 100)
    f1 = np.array(f1)
    # escala de color ajustada al rango: si todo esta entre 85 y 100, sobre 0-100 todo saldria igual de oscuro
    vmin = float(max(0.0, np.floor((np.nanmin(f1) - 5) / 10) * 10)) if f1.size else 0.0
    figs.append(G.mapa_calor(
        f1, modelos, clases, dfig / ('f1_por_clase_%s' % ref), 'F1 por gesto y modelo',
        'Protocolo %s, mejor normalizacion de cada modelo. Escala de color de %.0f a 100: los tonos claros '
        'son los gestos dificiles.' % (NOMBRES_PROTOCOLO[ref], vmin), fmt='%.0f', vmin=vmin, etiqueta_barra='F1 (%)'))

    for h in ctx['historiales']:
        if h['protocolo'] == ref and h['normalizacion'] == norma_de.get(h['modelo']) and h['historial']:
            figs.append(G.curvas_aprendizaje(
                h['historial'], dfig / ('curvas_%s_%s_%s' % (h['modelo'], h['normalizacion'], ref)),
                'Curvas de aprendizaje: %s' % h['modelo'],
                '%s, pliegue %s, semilla %s, normalizacion %s. Se restauran los pesos de la mejor epoca en validacion.'
                % (NOMBRES_PROTOCOLO[ref], h['pliegue'], h['semilla'], h['normalizacion']),
                mejor_epoca=h.get('mejor_epoca')))
    return [f for f in figs if f]


def _errores(pred, muestras, clases, norm, prot, modelo):
    dd = _filtrar(pred, norm, prot, modelo)
    dd = dd[dd['semilla'] == dd['semilla'].min()]
    err = dd[dd['real'] != dd['predicha']].copy()
    if err.empty:
        return pd.DataFrame(columns=['toma', 'participante', 'clase_real', 'clase_predicha', 'confianza', 'frame', 'ruta'])
    m = muestras.loc[err['indice']]
    out = pd.DataFrame({
        'indice': err['indice'].to_numpy(), 'toma': m['toma'].to_numpy(), 'participante': m['participante'].to_numpy(),
        'clase_real': [clases[i] for i in err['real']], 'clase_predicha': [clases[i] for i in err['predicha']],
        'confianza': err['confianza'].to_numpy(), 'frame': m['frame'].to_numpy(),
        'ruta': [str(Path(c) / r) for c, r in zip(m['carpeta_toma'], m['ruta_relativa'])],
        'handedness': m['handedness'].to_numpy()})
    return out.sort_values('confianza', ascending=False).reset_index(drop=True)


def _galeria(errores, ctx, dfig, top, ref, max_por_par=3):
    if errores.empty:
        return None
    muestras = ctx['muestras']
    elegidos = errores.groupby(['clase_real', 'clase_predicha'], sort=False).head(max_por_par).head(24)
    filas = []
    for r in elegidos.itertuples():
        s = muestras.loc[r.indice]
        filas.append({'ruta_imagen': r.ruta, 'xs': s[C.COLS_X].to_numpy(float), 'ys': s[C.COLS_Y].to_numpy(float),
                      'real': r.clase_real, 'predicha': r.clase_predicha, 'confianza': r.confianza,
                      'pie': '%s, frame %d' % (r.participante, r.frame)})
    return G.galeria_errores(
        filas, dfig / ('errores_%s_%s_%s' % (top['modelo'], top['normalizacion'], ref)),
        'Errores mas seguros del mejor modelo (%s, %s)' % (top['modelo'], NOMBRES_PROTOCOLO[ref]),
        'real -> predicha (confianza). Como mucho %d por cada par de clases confundidas.' % max_por_par)


def _informe(ctx, resumen, ref, mejores, brecha, detalle, por_clase, confusiones, participantes, rend, figuras,
             protos, normas, modelos, inv=None, diversidad=None):
    cfg, conf = ctx['config'], ctx['config']['experimento']
    top = mejores.iloc[0]
    L = []
    L.append('# Informe del experimento `%s`\n' % conf['nombre'])
    v = cfg.get('versiones', {})
    disp_redes = []
    if 'pliegues' in ctx and 'dispositivo' in ctx['pliegues'].columns:
        disp_redes = [d for d in ctx['pliegues']['dispositivo'].dropna().unique() if str(d).strip()]
    disp_txt = (', '.join(disp_redes)) if disp_redes else (('GPU ' + v.get('gpu')) if v.get('gpu') else 'CPU')
    backend_txt = v.get('keras_backend') or 'torch'
    L.append('Generado a partir de `%s`. Entrenado el %s con Keras %s (backend %s, dispositivo: %s), scikit-learn %s y MediaPipe %s '
             '(%s CPUs logicas).\n' % (ctx['dir'].name, cfg.get('fecha'), v.get('keras'), backend_txt, disp_txt,
                                       v.get('sklearn'), v.get('mediapipe'), v.get('cpus_logicas')))
    L.append('**Configuracion:** modelos %s; normalizaciones %s; protocolos %s; semillas %s; espejo=%s; '
             'aumentacion=%s copias%s; hasta %s epocas, paciencia %s, batch %s.\n'
             % (', '.join(conf['modelos']), ', '.join(conf['normalizaciones']), ', '.join(conf['protocolos']),
                conf['semillas'], conf['espejo'], conf['aumentar'], ' + volteo' if conf['voltear'] else '',
                conf['epocas'], conf['paciencia'], conf['batch']))

    L.append('## 1. Dataset\n')
    ds = cfg['dataset']
    L.append('%d imagenes, %d con mano detectada (%.1f%%), %d participantes, %d tomas. Clases: %s.\n'
             % (ds['imagenes'], ds['con_mano'], 100 * ds['con_mano'] / max(1, ds['imagenes']),
                len(ds['participantes']), len(ds['tomas']), ', '.join('`%s`' % c for c in ctx['clases'])))
    pp = pd.DataFrame(ds['por_participante'])
    if len(pp):
        pp['tasa_deteccion'] = pp['tasa_deteccion'].map(lambda x: '%.1f%%' % (100 * x))
        L.append(utils.tabla_markdown(pp) + '\n')
    if ctx['landmarks'] is not None:
        lm = ctx['landmarks'].copy()
        lm['detectada'] = lm['detectada'].astype(str).str.lower().eq('true')
        piv = lm.pivot_table(index='participante', columns='clase', values='detectada', aggfunc='mean') * 100
        L.append('Tasa de deteccion de mano (%) por participante y gesto. Las imagenes sin mano no se usan:\n')
        L.append(utils.tabla_markdown(piv.round(1), indice=True) + '\n')
    comandos = pd.DataFrame([{'gesto': c, 'comando_tanque': C.COMANDOS_TANQUE.get(c, '-')} for c in ctx['clases']])
    L.append('Gestos y comando del vehiculo tanque (Project 2) que activa cada uno:\n')
    L.append(utils.tabla_markdown(comandos) + '\n')
    if diversidad is not None:
        L.append('**Diversidad de la grabacion** (la presentacion pide distintos participantes, angulos y '
                 'distancias). Rango del 5 al 95 % por participante: tamano de la mano en la imagen (muneca a '
                 'nudillo del corazon, en unidades de alto de imagen; mas grande = mas cerca de la camara), su '
                 'inclinacion respecto a la vertical y la posicion de la muneca en el encuadre. `mediapipe_left_%` '
                 'es el % de fotogramas que MediaPipe etiqueta como mano izquierda: ronda el 50 % en todos aunque '
                 'cada persona grabo con una mano, porque al girar la muneca se ve el dorso, y el dorso de una '
                 'mano tiene en 2D la misma forma que la palma de la contraria. Esa etiqueta no es fiable aqui.\n')
        L.append(utils.tabla_markdown(diversidad['resumen'], formatos={
            'tamano_max_sobre_min': '{:.1f}x', 'mediapipe_left_%': '{:.0f}%'}) + '\n')
    if cfg.get('avisos'):
        L.append('**Avisos:**\n\n' + '\n'.join('- %s' % a for a in cfg['avisos']) + '\n')

    L.append('## 2. Resultado principal\n')
    L.append('Protocolo de referencia: **%s** (el mas honesto de los ejecutados). Mejor configuracion: **`%s` con '
             'normalizacion `%s`**: accuracy **%s%%** (desviacion %s pp), F1 macro %s%%, balanced accuracy %s%%. '
             'IC95 del repo: +/- %s pp (optimista: supone fotogramas independientes).\n'
             % (NOMBRES_PROTOCOLO[ref], top['modelo'], top['normalizacion'], _pct(top['accuracy']),
                _pct(top['dispersion']), _pct(top['f1_macro']), _pct(top['balanced_accuracy']), _pct(top['ic95_repo'])))
    dref = resumen[resumen['protocolo'] == ref]
    tabla = dref.pivot(index='modelo', columns='normalizacion', values='accuracy').reindex(index=modelos, columns=normas)
    tdisp = dref.pivot(index='modelo', columns='normalizacion', values='dispersion').reindex(index=modelos, columns=normas)
    celdas = tabla.copy().astype(object)
    for m in modelos:
        for n in normas:
            a, s = tabla.loc[m, n], tdisp.loc[m, n]
            celdas.loc[m, n] = '' if pd.isna(a) else ('%.1f +/- %.1f' % (100 * a, 100 * s) if not pd.isna(s) else '%.1f' % (100 * a))
    L.append('Accuracy (%%) en %s, media +/- desviacion:\n' % NOMBRES_PROTOCOLO[ref])
    L.append(utils.tabla_markdown(celdas, indice=True) + '\n')

    if len(protos) > 1:
        L.append('## 3. Cuanto engana un mal protocolo de evaluacion\n')
        L.append('Misma configuracion (mejor normalizacion de cada modelo en %s), evaluada con cada protocolo. '
                 'La brecha, en puntos porcentuales, es el optimismo que se habria reportado sin separar participantes.\n'
                 % NOMBRES_PROTOCOLO[ref])
        b = brecha.copy()
        fm = {p: _pct for p in protos}
        fm.update({c: (lambda x: '%+.1f' % x) for c in b.columns if c.startswith('brecha_')})
        L.append(utils.tabla_markdown(b, formatos=fm) + '\n')

    L.append('## 4. Analisis por gesto y errores\n')
    for norm, modelo in detalle:
        L.append('### `%s`, normalizacion `%s` (%s)\n' % (modelo, norm, NOMBRES_PROTOCOLO[ref]))
        pc = por_clase[(norm, modelo)]
        L.append(utils.tabla_markdown(pc, formatos={'precision': _pct, 'recall': _pct, 'f1': _pct}) + '\n')
        cf = confusiones[(norm, modelo)]
        if len(cf):
            L.append('Confusiones mas frecuentes:\n')
            L.append(utils.tabla_markdown(cf, formatos={'pct_de_la_clase_real': '{:.1f}%'}) + '\n')
        if (norm, modelo) in participantes and len(participantes[(norm, modelo)]):
            dp = participantes[(norm, modelo)]
            L.append('Accuracy con cada participante no visto: ' + ', '.join(
                '%s %.1f%%' % (p, 100 * a) for p, a in zip(dp['participante'], dp['accuracy'])) + '.\n')

    if not rend.empty:
        L.append('## 5. Coste computacional\n')
        hay_tflite = 'latencia_tflite_ms' in rend.columns and not rend['latencia_tflite_ms'].isna().all()
        txt_tflite = ('; `latencia_tflite_ms`, el interprete TFLite, que es el formato de despliegue en esos dispositivos'
                      if hay_tflite else '')
        L.append('Medido al terminar el entrenamiento, modelo a modelo en un proceso aparte con la CPU libre, con batch 1 '
                 'y un solo hilo (como en la demo, y mas cercano a una Raspberry Pi o un movil). `latencia_ms` es la '
                 'llamada directa desde Python (Keras o scikit-learn)%s. Mediana de 300 a 1000 repeticiones.\n' % txt_tflite)
        cols = [c for c in ('modelo', 'familia', 'parametros', 'kb_disco', 'kb_tflite', 'kb_tflite_cuant',
                            'latencia_ms', 'latencia_tflite_ms') if c in rend.columns]
        fk = {c: '{:.1f}' for c in ('kb_disco', 'kb_tflite', 'kb_tflite_cuant')}
        fk.update({'latencia_ms': '{:.3f}', 'latencia_tflite_ms': '{:.4f}', 'parametros': '{:.0f}'})
        L.append(utils.tabla_markdown(rend[cols], formatos=fk) + '\n')
        mp = rend[rend['modelo'] == 'extractor_mediapipe']
        if len(mp) and not mp['latencia_ms'].isna().all():
            mp_ms = float(mp['latencia_ms'].iloc[0])
            fila_top = rend[rend['modelo'] == top['modelo']]
            clf_ms = float(fila_top['latencia_despliegue_ms'].iloc[0]) if len(fila_top) else 0.0
            L.append('El extractor de MediaPipe tarda **%.1f ms** por fotograma (%s). Con el mejor clasificador '
                     '(%.3f ms) el techo teorico es ~%.0f fotogramas por segundo en este portatil, sin contar captura '
                     'ni dibujo: la latencia la domina el extractor, no el clasificador.\n'
                     % (mp_ms, mp['resolucion'].iloc[0] if 'resolucion' in mp else '', clf_ms, 1000 / (mp_ms + clf_ms)))

    if inv is not None and len(inv) and not inv['accuracy_espejado'].isna().all():
        L.append('## 5b. Invarianza mano izquierda / derecha\n')
        L.append('Nadie grabo con la otra mano, asi que se simula: cada muestra de test se refleja horizontalmente '
                 '(la misma pose hecha con la mano opuesta) y se intercambia la etiqueta Left/Right de MediaPipe. '
                 'Una caida grande significa que el modelo depende de con que mano se haga el gesto. Configuracion de '
                 'este experimento: espejo=%s, aumentacion con volteo=%s.\n' % (conf['espejo'], conf['voltear']))
        L.append(utils.tabla_markdown(inv, formatos={'accuracy': _pct, 'accuracy_espejado': _pct,
                                                     'caida_pp': '{:+.1f}'}) + '\n')

    L.append('## 6. Tabla completa\n')
    cols = ['protocolo', 'normalizacion', 'modelo', 'accuracy', 'accuracy_espejado', 'dispersion', 'accuracy_min',
            'f1_macro', 'balanced_accuracy', 'ic95_repo', 'n_pliegues', 'n_semillas', 'n_test', 'epocas',
            'tiempo_entrenamiento_s']
    L.append(utils.tabla_markdown(resumen[cols], formatos={
        'accuracy': _pct, 'accuracy_espejado': _pct, 'dispersion': _pct, 'accuracy_min': _pct, 'f1_macro': _pct,
        'balanced_accuracy': _pct, 'ic95_repo': _pct, 'epocas': '{:.0f}', 'tiempo_entrenamiento_s': '{:.1f}'}) + '\n')
    L.append('Cifras de accuracy en %; dispersion y IC en puntos porcentuales. Tablas en `tablas/`.\n')

    L.append('## 7. Figuras\n')
    for f in figuras:
        rel = Path(f).relative_to(ctx['dir']).as_posix()
        L.append('- [`%s`](%s) (tambien en PDF)' % (Path(f).stem, rel))
    L.append('')

    L.append('## Notas metodologicas\n')
    L.append('\n'.join([
        '- **Validacion separada del test.** El early stopping usa los ultimos fotogramas de cada toma y gesto '
        'dentro de la parte de entrenamiento. El notebook del repo validaba con el test.',
        '- **Mismo train para todos los modelos.** Los clasicos no usan la validacion; asi la comparacion es justa.',
        '- **Imagenes sin mano detectada** se excluyen de entrenamiento y test (ver tasas en la seccion 1).',
        '- **Reproducibilidad.** Semillas fijas, determinismo de TensorFlow activado, oneDNN desactivado y un hilo '
        'por trabajo: el resultado de cada trabajo depende solo de su semilla.',
        '- **Temporal = la particion del grabador** (primeros 70 fotogramas a train, ultimos 30 a test). '
        'Los fotogramas se capturan a 1 Hz de una misma sesion continua: train y test estan muy correlacionados.',
    ]) + '\n')
    return '\n'.join(L)
