"""Ejecucion de un experimento: rejilla normalizacion x protocolo x pliegue x modelo x semilla.

Cada combinacion es un 'trabajo' independiente que se ejecuta en un proceso aparte, con
PyTorch limitado a un hilo de CPU y algoritmos deterministas, de modo que el resultado de
cada trabajo solo depende de su semilla, no del orden ni de cuantos corran en paralelo.

Dos grupos de procesos:
  - redes neuronales (Keras con backend PyTorch) -> procesos que ven la GPU NVIDIA
    (6 por defecto: los modelos son diminutos y la tarjeta se reparte bien entre varios);
  - modelos de scikit-learn -> procesos de CPU con la GPU oculta (no la usan y asi no
    reservan memoria de la tarjeta).
Con --dispositivo cpu todo va a CPU.

Todo lo necesario para rehacer tablas y figuras sin reentrenar se guarda en disco
(evaluar.py las regenera): config, muestras usadas, resultado por pliegue,
predicciones de test, historiales de entrenamiento y rendimiento.
"""
import contextlib
import time
import traceback
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import asdict, dataclass, field
from multiprocessing import get_context
from pathlib import Path

import numpy as np
import pandas as pd

from . import constantes as C
from . import features as F
from . import metricas as M
from . import modelos as MOD
from . import protocolos as PR
from . import utils


@dataclass
class ConfigExperimento:
    nombre: str
    modelos: list
    normalizaciones: list
    protocolos: list
    semillas: list
    espejo: bool = False
    lado_espejo: str = 'Left'
    aumentar: int = 0
    voltear: bool = False
    epocas: int = MOD.HP_REDES['epocas']
    paciencia: int = MOD.HP_REDES['paciencia']
    batch: int = MOD.HP_REDES['batch']
    frac_val: float = 0.15
    workers: int = field(default_factory=utils.workers_por_defecto)
    medir_rendimiento: bool = True
    min_deteccion: float = 0.5
    raices_datos: list = field(default_factory=list)
    incluir_pruebas: bool = False
    dispositivo: str = 'auto'       # auto | gpu | cpu  (solo afecta a las redes neuronales)
    workers_gpu: int = 6            # procesos que comparten la GPU

    def validar(self):
        if self.dispositivo not in ('auto', 'gpu', 'cpu'):
            raise ValueError('dispositivo debe ser auto, gpu o cpu')
        for nombre, valores, validos in (('modelo', self.modelos, MOD.MODELOS),
                                         ('normalizacion', self.normalizaciones, C.NORMALIZACIONES),
                                         ('protocolo', self.protocolos, C.PROTOCOLOS)):
            if not valores:
                raise ValueError('hace falta al menos un %s' % nombre)
            malos = [v for v in valores if v not in validos]
            if malos:
                raise ValueError('%s desconocido: %s (opciones: %s)' % (nombre, malos, validos))
        if not self.semillas:
            raise ValueError('hace falta al menos una semilla')
        if self.espejo and self.voltear:
            raise ValueError('--espejo y --voltear son estrategias alternativas de invarianza '
                             'izquierda/derecha; usa solo una')
        if self.lado_espejo not in ('Left', 'Right'):
            raise ValueError('lado_espejo debe ser Left o Right')
        return self


def preparar_datos(df_landmarks, avisos=None):
    """Filtra las imagenes con mano y deja los arrays que consumen los trabajos."""
    avisos = avisos if avisos is not None else []
    df = df_landmarks[df_landmarks['detectada']].reset_index(drop=True)
    if df.empty:
        raise ValueError('ninguna imagen con mano detectada')
    clases = sorted(df['clase'].unique())
    if clases != sorted(C.CLASES_ESPERADAS):
        avisos.append('las clases encontradas %s no coinciden con las esperadas %s' % (clases, C.CLASES_ESPERADAS))
    P, ar = F.coordenadas(df)
    h = df['handedness'].fillna('').astype(str).to_numpy()
    y = df['clase'].map({c: i for i, c in enumerate(clases)}).to_numpy(int)
    cols_muestras = [c for c in C.COLS_META if c in df.columns] + ['handedness', 'handedness_score', 'ancho', 'alto'] + C.COLS_X + C.COLS_Y
    return {'muestras': df[cols_muestras], 'P': P, 'ar': ar, 'h': h, 'y': y, 'clases': clases}


def construir_trabajos(cfg, muestras):
    trabajos, medido = [], set()
    for norm in cfg.normalizaciones:
        for prot in cfg.protocolos:
            for i_sem, semilla in enumerate(cfg.semillas):
                # en 'aleatorio' la semilla tambien cambia la particion; en temporal y
                # lopo la particion es fija y la semilla solo afecta a los modelos estocasticos
                pliegues = PR.generar_pliegues(muestras, prot, semilla=semilla if prot == 'aleatorio' else 0,
                                               frac_val=cfg.frac_val)
                for pl in pliegues:
                    for modelo in cfg.modelos:
                        estocastico = modelo in MOD.ESTOCASTICOS or cfg.aumentar > 0
                        if i_sem > 0 and not estocastico and prot != 'aleatorio':
                            continue
                        medir = cfg.medir_rendimiento and modelo not in medido
                        medido.add(modelo)
                        trabajos.append({
                            'id': len(trabajos), 'normalizacion': norm, 'protocolo': prot,
                            'pliegue': pl.nombre, 'indice_pliegue': pl.indice, 'modelo': modelo,
                            'semilla': int(semilla), 'train': pl.train, 'val': pl.val, 'test': pl.test,
                            'medir_rendimiento': medir,
                            'guardar_historial': MOD.FAMILIA[modelo] == 'red neuronal' and i_sem == 0 and pl.indice == 0,
                        })
    return trabajos


# ------------------------------------------------------------------ trabajo
_DATOS = None


def _init_worker(datos, cfg_dict, usar_gpu=False, con_redes=True):
    utils.preparar_entorno(usar_gpu=usar_gpu)
    dispositivo = 'cpu'
    if con_redes:
        utils.configurar_torch(hilos=1, determinista=True)
        info = utils.info_dispositivo()
        if info['dispositivo'] == 'cuda':
            dispositivo = 'cuda: ' + info['gpu']
    global _DATOS
    _DATOS = dict(datos, cfg=cfg_dict, dispositivo=dispositivo)


def resolver_gpu(dispositivo):
    """True si las redes deben entrenar en GPU. Falla si se pidio gpu y no hay."""
    if dispositivo == 'cpu':
        return False
    info = utils.info_dispositivo()
    if info['dispositivo'] != 'cuda':
        if dispositivo == 'gpu':
            raise RuntimeError('se pidio --dispositivo gpu pero PyTorch no ve ninguna GPU CUDA')
        return False
    return True


def ejecutar_trabajo(t, D=None):
    D = D if D is not None else _DATOS
    cfg = D['cfg']
    P, ar, h, y = D['P'], D['ar'], D['h'], D['y']
    forma = MOD.FORMA_ENTRADA[t['modelo']]
    tr, va, te = t['train'], t['val'], t['test']

    P_tr, ar_tr, h_tr, y_tr = P[tr], ar[tr], h[tr], y[tr]
    if cfg['aumentar'] > 0:
        rng = np.random.default_rng(utils.semilla_estable(t['semilla'], t['protocolo'], t['pliegue'], 'aumentar'))
        B, A, idx = F.aumentar(P_tr, ar_tr, rng, cfg['aumentar'], voltear=cfg['voltear'])
        P_tr, ar_tr = np.concatenate([P_tr, B]), np.concatenate([ar_tr, A])
        h_tr, y_tr = np.concatenate([h_tr, h_tr[idx]]), np.concatenate([y_tr, y_tr[idx]])

    def entrada(Pp, aa, hh):
        Q = F.transformar(Pp, aa, hh, t['normalizacion'], cfg['espejo'], cfg['lado_espejo'])
        return F.preparar_entrada(Q, forma)

    X_tr, X_va, X_te = entrada(P_tr, ar_tr, h_tr), entrada(P[va], ar[va], h[va]), entrada(P[te], ar[te], h[te])
    modelo = MOD.crear_modelo(t['modelo'], len(D['clases']),
                              {'epocas': cfg['epocas'], 'paciencia': cfg['paciencia'], 'batch': cfg['batch']})
    utils.fijar_semillas(t['semilla'])
    with utils.Cronometro() as c_fit:
        modelo.ajustar(X_tr, y_tr, X_va, y[va], t['semilla'])
    with utils.Cronometro() as c_pred:
        proba = modelo.predecir_proba(X_te)
    pred = proba.argmax(axis=1)
    m = M.calcular(y[te], pred)

    # Mejora 6 (invarianza izquierda/derecha). Nadie grabo con la otra mano, asi que se simula:
    # el test reflejado horizontalmente es la misma pose hecha con la mano opuesta. Tambien se
    # intercambia la etiqueta Left/Right, como la daria MediaPipe ante la mano contraria.
    P_esp = F.espejar(P[te], ar[te], np.ones(len(te), dtype=bool))
    h_esp = np.array([{'Left': 'Right', 'Right': 'Left'}.get(v, v) for v in h[te]])
    pred_esp = modelo.predecir_proba(entrada(P_esp, ar[te], h_esp)).argmax(axis=1)

    res = {k: t[k] for k in ('id', 'normalizacion', 'protocolo', 'pliegue', 'indice_pliegue', 'modelo', 'semilla')}
    res.update({
        'accuracy': m['accuracy'], 'balanced_accuracy': m['balanced_accuracy'], 'f1_macro': m['f1_macro'],
        'accuracy_espejado': M.calcular(y[te], pred_esp)['accuracy'],
        'accuracy_val': M.calcular(y[va], modelo.predecir_proba(X_va).argmax(1))['accuracy'] if len(va) else np.nan,
        'n_train': int(len(X_tr)), 'n_val': int(len(va)), 'n_test': int(len(te)),
        'tiempo_entrenamiento_s': c_fit.segundos, 'tiempo_prediccion_test_s': c_pred.segundos,
        'epocas': modelo.epocas_entrenadas, 'mejor_epoca': modelo.mejor_epoca,
        'dispositivo': D.get('dispositivo', 'cpu') if modelo.familia == 'red neuronal' else 'cpu',
        '_test': np.asarray(te, dtype=np.int32), '_pred': pred.astype(np.int16),
        '_conf': proba.max(axis=1).astype(np.float32),
    })
    if t['guardar_historial']:
        res['_historial'] = modelo.historial
    if t['medir_rendimiento'] and cfg.get('dir_rendimiento'):
        from .rendimiento import guardar_para_medir
        guardar_para_medir(modelo, X_te[:1], Path(cfg['dir_rendimiento']) / t['modelo'])
    return res


def _init_medicion():
    """CPU y un solo hilo (como en un dispositivo modesto): la latencia de despliegue que
    interesa es la de una Raspberry Pi o un movil, no la de la GPU del portatil."""
    utils.preparar_entorno(usar_gpu=False)
    utils.configurar_torch(hilos=1, determinista=False)


def _medir_en_serie(dir_rendimiento, imagen_mediapipe):
    """Se ejecuta en un proceso NUEVO y solo, cuando ya no queda nada entrenando."""
    from .rendimiento import medir_desde_disco, rendimiento_mediapipe
    filas = []
    for carpeta in sorted(Path(dir_rendimiento).iterdir()) if Path(dir_rendimiento).exists() else []:
        try:
            filas.append(medir_desde_disco(carpeta))
        except Exception as e:
            filas.append({'modelo': carpeta.name, 'error': '%s: %s' % (type(e).__name__, str(e)[:200])})
    if imagen_mediapipe is not None:
        try:
            filas.append(rendimiento_mediapipe(C.MODELO_MEDIAPIPE, imagen_mediapipe))
        except Exception as e:
            filas.append({'modelo': 'extractor_mediapipe', 'familia': 'extractor', 'error': str(e)[:200]})
    return filas


def _ejecutar_seguro(t):
    try:
        return ejecutar_trabajo(t)
    except Exception:
        return {**{k: t[k] for k in ('id', 'normalizacion', 'protocolo', 'pliegue', 'modelo', 'semilla')},
                '_error': traceback.format_exc()}


# ------------------------------------------------------------------ orquestacion
def resumen_dataset(df_landmarks):
    g = df_landmarks.groupby('participante')
    por_part = pd.DataFrame({
        'tomas': g['toma'].nunique(), 'imagenes': g.size(), 'con_mano': g['detectada'].sum(),
    })
    por_part['tasa_deteccion'] = por_part['con_mano'] / por_part['imagenes']
    tasa_clase = df_landmarks.pivot_table(index='participante', columns='clase', values='detectada', aggfunc='mean')
    return por_part.reset_index(), tasa_clase


def ejecutar_experimento(cfg, df_landmarks, dir_salida, log=print, avisos=None):
    avisos = avisos if avisos is not None else []
    cfg.validar()
    dir_salida = Path(dir_salida)
    dir_salida.mkdir(parents=True, exist_ok=False)          # nunca se machaca un experimento anterior

    datos = preparar_datos(df_landmarks, avisos)
    muestras = datos['muestras']
    if 'lopo' in cfg.protocolos and muestras['participante'].nunique() < 2:
        avisos.append('solo hay %d participante: se quita el protocolo lopo' % muestras['participante'].nunique())
        cfg.protocolos = [p for p in cfg.protocolos if p != 'lopo']
        if not cfg.protocolos:
            raise ValueError('no queda ningun protocolo que se pueda evaluar')
    trabajos = construir_trabajos(cfg, muestras)

    por_part, _ = resumen_dataset(df_landmarks)
    utils.guardar_json({
        'experimento': asdict(cfg), 'clases': datos['clases'], 'fecha': utils.ahora(),
        'versiones': utils.versiones(), 'n_trabajos': len(trabajos),
        'dataset': {'imagenes': int(len(df_landmarks)), 'con_mano': int(len(muestras)),
                    'participantes': sorted(muestras['participante'].unique()),
                    'tomas': sorted(muestras['toma'].unique()),
                    'por_participante': por_part.to_dict(orient='records')},
        'avisos': avisos,
    }, dir_salida / 'config.json')
    muestras.to_csv(dir_salida / 'muestras.csv.gz', index_label='indice')
    df_landmarks.to_csv(dir_salida / 'landmarks_todas.csv.gz', index=False)

    usar_gpu = resolver_gpu(cfg.dispositivo)
    info = utils.info_dispositivo()
    redes = [t for t in trabajos if MOD.FAMILIA[t['modelo']] == 'red neuronal']
    clasicos = [t for t in trabajos if MOD.FAMILIA[t['modelo']] != 'red neuronal']
    log('\n%d trabajos (%s)' % (len(trabajos), ', '.join(
        '%s=%d' % (k, v) for k, v in pd.Series([t['modelo'] for t in trabajos]).value_counts().sort_index().items())))
    if usar_gpu:
        log('  redes neuronales: %d trabajos en GPU (%s, %.1f GB) con %d procesos'
            % (len(redes), info['gpu'], info['vram_gb'], cfg.workers_gpu))
        log('  modelos clasicos: %d trabajos en CPU con %d procesos' % (len(clasicos), cfg.workers))
    else:
        log('  todo en CPU con %d procesos (dispositivo=%s)' % (cfg.workers, cfg.dispositivo))

    datos_worker = {k: datos[k] for k in ('P', 'ar', 'h', 'y', 'clases')}
    cfg_dict = asdict(cfg)
    cfg_dict['dir_rendimiento'] = str(dir_salida / 'modelos_rendimiento') if cfg.medir_rendimiento else None
    resultados, t0 = [], time.time()
    ctx = get_context('spawn')
    if usar_gpu:
        grupos = [(cfg.workers_gpu, True, True, redes), (cfg.workers, False, False, clasicos)]
    else:
        grupos = [(cfg.workers, False, bool(redes), trabajos)]
    with contextlib.ExitStack() as pila:
        futuros = {}
        for n_procesos, gpu, con_redes, lote in grupos:
            if not lote:
                continue
            ex = pila.enter_context(ProcessPoolExecutor(
                max_workers=n_procesos, mp_context=ctx, initializer=_init_worker,
                initargs=(datos_worker, cfg_dict, gpu, con_redes)))
            futuros.update({ex.submit(_ejecutar_seguro, t): t for t in lote})
        # Tiempo restante estimado por grupo: los clasicos tardan segundos y las redes minutos, asi que un
        # promedio conjunto daria una estimacion absurdamente optimista.
        total_g = {'red': len(redes), 'cla': len(clasicos)}
        hechos_g, suma_g = {'red': 0, 'cla': 0}, {'red': 0.0, 'cla': 0.0}
        procesos_g = {'red': cfg.workers_gpu if usar_gpu else cfg.workers, 'cla': cfg.workers}
        for i, fut in enumerate(as_completed(futuros), 1):
            r = fut.result()
            resultados.append(r)
            g = 'red' if MOD.FAMILIA[r['modelo']] == 'red neuronal' else 'cla'
            hechos_g[g] += 1
            suma_g[g] += float(r.get('tiempo_entrenamiento_s', 0) or 0)
            eta = max([(total_g[k] - hechos_g[k]) * (suma_g[k] / hechos_g[k]) / max(1, procesos_g[k])
                       for k in total_g if hechos_g[k]] or [0])
            if '_error' in r:
                log('  [%d/%d] ERROR %s | %s | %s %s | semilla %s'
                    % (i, len(trabajos), r['modelo'], r['normalizacion'], r['protocolo'], r['pliegue'], r['semilla']))
            else:
                log('  [%d/%d] %-13s %-17s %-9s %-5s sem %-2d acc %.3f  (%4.0f s, %s)  quedan ~%s'
                    % (i, len(trabajos), r['modelo'], r['normalizacion'], r['protocolo'], r['pliegue'],
                       r['semilla'], r['accuracy'], r['tiempo_entrenamiento_s'],
                       'GPU' if str(r.get('dispositivo', '')).startswith('cuda') else 'CPU', _duracion(eta)))
    filas_rend = []
    if cfg.medir_rendimiento:
        log('midiendo latencia y tamano de los modelos (en serie, con la CPU libre)...')
        muestra = datos['muestras'].iloc[0]
        img = utils.leer_imagen(Path(muestra['carpeta_toma']) / muestra['ruta_relativa'])
        with ProcessPoolExecutor(max_workers=1, mp_context=ctx, initializer=_init_medicion) as ex:
            filas_rend = ex.submit(_medir_en_serie, cfg_dict['dir_rendimiento'], img).result()
    guardar_resultados(resultados, datos, dir_salida, filas_rend)
    log('experimento terminado en %s' % _duracion(time.time() - t0))
    return dir_salida


def guardar_resultados(resultados, datos, dir_salida, filas_rend):
    resultados = sorted(resultados, key=lambda r: r['id'])
    errores = [r for r in resultados if '_error' in r]
    buenos = [r for r in resultados if '_error' not in r]
    if errores:
        (dir_salida / 'errores_ejecucion.txt').write_text(
            '\n\n'.join('%s\n%s' % ({k: v for k, v in r.items() if k != '_error'}, r['_error']) for r in errores),
            encoding='utf-8')

    pd.DataFrame([{k: v for k, v in r.items() if not k.startswith('_')} for r in buenos]) \
        .to_csv(dir_salida / 'resultados_pliegues.csv', index=False)

    y = datos['y']
    partes = []
    for r in buenos:
        partes.append(pd.DataFrame({
            'trabajo': r['id'], 'normalizacion': r['normalizacion'], 'protocolo': r['protocolo'],
            'pliegue': r['pliegue'], 'modelo': r['modelo'], 'semilla': r['semilla'],
            'indice': r['_test'], 'real': y[r['_test']], 'predicha': r['_pred'], 'confianza': r['_conf']}))
    if partes:
        pd.concat(partes, ignore_index=True).to_csv(dir_salida / 'predicciones.csv.gz', index=False)

    utils.guardar_json([{**{k: r[k] for k in ('normalizacion', 'protocolo', 'pliegue', 'modelo', 'semilla')},
                         'historial': r['_historial'], 'mejor_epoca': r['mejor_epoca']}
                        for r in buenos if '_historial' in r], dir_salida / 'historiales.json')

    if filas_rend:
        pd.DataFrame(filas_rend).to_csv(dir_salida / 'rendimiento.csv', index=False)


def _duracion(s):
    s = int(round(s))
    if s < 60:
        return '%d s' % s
    if s < 3600:
        return '%d min %02d s' % (s // 60, s % 60)
    return '%d h %02d min' % (s // 3600, (s % 3600) // 60)
