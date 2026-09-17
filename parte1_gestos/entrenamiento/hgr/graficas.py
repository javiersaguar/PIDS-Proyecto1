"""Figuras para la memoria (PNG 200 dpi + PDF vectorial).

Estilo: paleta categorica validada para daltonismo con las series en orden FIJO
(protocolos: azul/naranja/aqua; normalizaciones: + amarillo), rampa secuencial de un
solo tono (azul) para matrices, marcas finas, rejilla horizontal discreta y texto
siempre en tinta, nunca del color de la serie. Aqua y amarillo quedan por debajo de
3:1 de contraste con el fondo, por eso las barras llevan etiquetas de valor
selectivas y todas las cifras estan tambien en las tablas del informe.
"""
from pathlib import Path

import numpy as np

PALETA = ['#2a78d6', '#eb6834', '#1baf7a', '#eda100', '#e87ba4', '#008300', '#4a3aa7', '#e34948']
SUPERFICIE, TINTA, TINTA2, APAGADO = '#fcfcfb', '#0b0b0b', '#52514e', '#898781'
REJILLA, EJE = '#e1e0d9', '#c3c2b7'
SECUENCIAL = ['#f4f8fe', '#cde2fb', '#b7d3f6', '#9ec5f4', '#86b6ef', '#6da7ec', '#5598e7', '#3987e5',
              '#2a78d6', '#256abf', '#1c5cab', '#184f95', '#104281', '#0d366b']
CONEXIONES_MANO = [(0, 1), (1, 2), (2, 3), (3, 4), (0, 5), (5, 6), (6, 7), (7, 8), (5, 9), (9, 10), (10, 11),
                   (11, 12), (9, 13), (13, 14), (14, 15), (15, 16), (13, 17), (17, 18), (18, 19), (19, 20), (0, 17)]

_plt = None


def _pyplot():
    global _plt
    if _plt is None:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        plt.rcParams.update({
            'font.family': ['Segoe UI', 'DejaVu Sans'], 'font.size': 10,
            'figure.facecolor': SUPERFICIE, 'axes.facecolor': SUPERFICIE, 'savefig.facecolor': SUPERFICIE,
            'axes.edgecolor': EJE, 'axes.linewidth': 1.0, 'axes.labelcolor': TINTA2,
            'axes.titlecolor': TINTA, 'axes.titlesize': 12, 'axes.titleweight': 'bold',
            'axes.titlelocation': 'left', 'xtick.color': APAGADO, 'ytick.color': APAGADO,
            'xtick.labelcolor': TINTA2, 'ytick.labelcolor': TINTA2, 'legend.frameon': False,
            'legend.labelcolor': TINTA2, 'lines.linewidth': 2, 'lines.solid_capstyle': 'round',
            'lines.solid_joinstyle': 'round', 'grid.color': REJILLA, 'grid.linewidth': 1.0, 'grid.linestyle': '-',
        })
        _plt = plt
    return _plt


def _ejes(ax, rejilla_y=True):
    for lado in ('top', 'right'):
        ax.spines[lado].set_visible(False)
    ax.set_axisbelow(True)
    if rejilla_y:
        ax.yaxis.grid(True)
    ax.tick_params(length=0)


def _envolver(texto, ancho_pulgadas):
    import textwrap
    return textwrap.fill(texto, width=max(40, int(ancho_pulgadas * 15)))


def _titulo(fig, ax, titulo, subtitulo=None):
    if not subtitulo:
        ax.set_title(titulo, pad=10)
        return
    sub = _envolver(subtitulo, ax.get_position().width * fig.get_figwidth())
    lineas = sub.count('\n') + 1
    ax.set_title(titulo, pad=14 + 13 * lineas)
    ax.text(0, 1.0, sub, transform=ax.transAxes, color=TINTA2, fontsize=9, va='bottom',
            linespacing=1.3, bbox={'boxstyle': 'square,pad=0.35', 'facecolor': 'none', 'edgecolor': 'none'})


def _eje_porcentaje(ax, escala, ylim):
    """Aire por encima de 100 para bigotes y etiquetas, pero marcas solo hasta 100."""
    if escala == 100.0 and tuple(ylim) == (0, 100):
        ax.set_ylim(0, 112)
        ax.set_yticks(np.arange(0, 101, 20))
    else:
        ax.set_ylim(*ylim)


def guardar(fig, ruta_sin_ext):
    plt = _pyplot()
    ruta = Path(ruta_sin_ext)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(ruta.with_suffix('.png'), dpi=200, bbox_inches='tight')
    fig.savefig(ruta.with_suffix('.pdf'), bbox_inches='tight')
    plt.close(fig)
    return ruta.with_suffix('.png')


def barras_agrupadas(grupos, series, medias, errores, ruta, titulo, subtitulo=None, etiqueta_y='Accuracy (%)',
                     serie_etiquetada=None, nombres_series=None, escala=100.0, ylim=(0, 100)):
    """medias/errores: dict (grupo, serie) -> valor en [0,1]."""
    plt = _pyplot()
    n_g, n_s = len(grupos), len(series)
    fig, ax = plt.subplots(figsize=(max(6.5, 1.25 * n_g + 2), 4.2))
    ranura = 0.8 / n_s
    ancho = min(ranura * 0.86, 0.26)
    x = np.arange(n_g)
    for k, s in enumerate(series):
        pos = x - 0.4 + ranura * (k + 0.5)
        vals = np.array([medias.get((g, s), np.nan) for g in grupos]) * escala
        errs = np.array([errores.get((g, s), np.nan) for g in grupos]) * escala
        ax.bar(pos, vals, width=ancho, color=PALETA[k], label=(nombres_series or {}).get(s, s), linewidth=0, zorder=2)
        ok = ~np.isnan(errs)
        if ok.any():
            ax.errorbar(pos[ok], vals[ok], yerr=errs[ok], fmt='none', ecolor=TINTA2, elinewidth=1, capsize=2, zorder=3)
        if s == serie_etiquetada:
            for px, v, e in zip(pos, vals, errs):
                if not np.isnan(v):
                    ax.text(px, v + (0 if np.isnan(e) else e) + 1.2, '%.0f' % v, ha='center', va='bottom',
                            fontsize=8, color=TINTA)
    ax.set_xticks(x, grupos)
    ax.set_ylabel(etiqueta_y)
    _eje_porcentaje(ax, escala, ylim)
    _ejes(ax)
    _titulo(fig, ax, titulo, subtitulo)
    ax.legend(ncol=n_s, loc='upper left', bbox_to_anchor=(0, -0.09), handlelength=1.0, columnspacing=1.4)
    return guardar(fig, ruta)


def barras_simple(categorias, valores, ruta, titulo, subtitulo=None, etiqueta_y='Accuracy (%)', escala=100.0,
                  ylim=(0, 100)):
    plt = _pyplot()
    fig, ax = plt.subplots(figsize=(max(5, 0.9 * len(categorias) + 2), 3.8))
    v = np.asarray(valores, dtype=float) * escala
    ax.bar(np.arange(len(v)), v, width=min(0.5, 0.26 * 2), color=PALETA[0], linewidth=0, zorder=2)
    for i, val in enumerate(v):
        ax.text(i, val + 1.2, '%.1f' % val, ha='center', va='bottom', fontsize=9, color=TINTA)
    ax.set_xticks(np.arange(len(v)), categorias)
    ax.set_ylabel(etiqueta_y)
    _eje_porcentaje(ax, escala, ylim)
    _ejes(ax)
    _titulo(fig, ax, titulo, subtitulo)
    return guardar(fig, ruta)


def dispersion_tradeoff(df, col_x, col_y, ruta, titulo, etiqueta_x, subtitulo=None, etiqueta_y='Accuracy (%)',
                        escala_y=100.0, log_x=True):
    """Un punto por modelo, etiquetado con su nombre. El color solo distingue 2 familias."""
    plt = _pyplot()
    fig, ax = plt.subplots(figsize=(6.8, 4.4))
    familias = [f for f in ('red neuronal', 'clasico') if f in set(df['familia'])]
    for k, fam in enumerate(familias):
        d = df[df['familia'] == fam]
        ax.scatter(d[col_x], d[col_y] * escala_y, s=70, color=PALETA[k], edgecolors=SUPERFICIE, linewidths=2,
                   zorder=3, label=fam)
    for _, r in df.iterrows():
        ax.annotate(r['modelo'], (r[col_x], r[col_y] * escala_y), xytext=(7, 5), textcoords='offset points',
                    fontsize=8.5, color=TINTA2)
    xs = df[col_x].astype(float)
    if log_x:
        ax.set_xscale('log')
        ax.set_xlim(xs.min() / 2.5, xs.max() * 6)          # sitio para las etiquetas a la derecha
    else:
        rango = xs.max() - xs.min() or 1.0
        ax.set_xlim(xs.min() - 0.05 * rango, xs.max() + 0.3 * rango)
    ax.margins(y=0.15)
    ax.set_xlabel(etiqueta_x)
    ax.set_ylabel(etiqueta_y)
    _ejes(ax)
    ax.xaxis.grid(True, which='major')
    _titulo(fig, ax, titulo, subtitulo)
    ax.legend(loc='upper left', bbox_to_anchor=(0, -0.14), ncol=2, handletextpad=0.3, columnspacing=1.4)
    return guardar(fig, ruta)


def mapa_calor(matriz, filas, columnas, ruta, titulo, subtitulo=None, fmt='%.0f', vmin=0.0, vmax=100.0,
               etiqueta_filas=None, etiqueta_columnas=None, etiqueta_barra=None):
    plt = _pyplot()
    from matplotlib.colors import LinearSegmentedColormap
    cmap = LinearSegmentedColormap.from_list('azul', SECUENCIAL)
    m = np.asarray(matriz, dtype=float)
    fig, ax = plt.subplots(figsize=(0.78 * len(columnas) + 2.6, 0.62 * len(filas) + 1.9))
    im = ax.imshow(m, cmap=cmap, vmin=vmin, vmax=vmax, aspect='auto')
    for i in range(m.shape[0]):
        for j in range(m.shape[1]):
            if np.isnan(m[i, j]):
                continue
            claro = (m[i, j] - vmin) / max(1e-9, vmax - vmin) > 0.55
            ax.text(j, i, fmt % m[i, j], ha='center', va='center', fontsize=8.5,
                    color='#ffffff' if claro else TINTA)
    ax.set_xticks(np.arange(len(columnas)), columnas, rotation=30, ha='right')
    ax.set_yticks(np.arange(len(filas)), filas)
    if etiqueta_filas:
        ax.set_ylabel(etiqueta_filas)
    if etiqueta_columnas:
        ax.set_xlabel(etiqueta_columnas)
    for lado in ax.spines.values():
        lado.set_visible(False)
    ax.tick_params(length=0)
    barra = fig.colorbar(im, ax=ax, fraction=0.04, pad=0.02)
    barra.outline.set_visible(False)
    barra.ax.tick_params(length=0, labelcolor=TINTA2)
    if etiqueta_barra:
        barra.set_label(etiqueta_barra, color=TINTA2)
    _titulo(fig, ax, titulo, subtitulo)
    return guardar(fig, ruta)


def curvas_aprendizaje(historial, ruta, titulo, subtitulo=None, mejor_epoca=None):
    plt = _pyplot()
    alto = 4.1
    fig, ejes = plt.subplots(1, 2, figsize=(9.5, alto))
    # loss baja con las epocas (su hueco libre esta arriba); accuracy sube (hueco abajo)
    for ax, clave, nombre, arriba in ((ejes[0], 'loss', 'Loss', True), (ejes[1], 'accuracy', 'Accuracy', False)):
        epocas = np.arange(1, len(historial.get(clave, [])) + 1)
        if clave in historial:
            ax.plot(epocas, historial[clave], color=PALETA[0], label='train')
        if 'val_' + clave in historial:
            ax.plot(epocas, historial['val_' + clave], color=PALETA[1], label='validacion')
        if mejor_epoca:
            ax.axvline(mejor_epoca, color=APAGADO, linewidth=1)
            ax.text(mejor_epoca, 0.97 if arriba else 0.03, 'mejor epoca (%d) ' % mejor_epoca, ha='right',
                    va='top' if arriba else 'bottom', transform=ax.get_xaxis_transform(), color=TINTA2, fontsize=8)
        ax.set_xlabel('Epoca')
        ax.set_ylabel(nombre)
        _ejes(ax)
    cab = 0.62 + (0.2 if subtitulo else 0)
    fig.subplots_adjust(left=0.07, right=0.98, bottom=0.14, top=1 - (cab + 0.25) / alto, wspace=0.25)
    fig.text(0.01, 1 - 0.3 / alto, titulo, color=TINTA, fontsize=12, fontweight='bold', va='center')
    if subtitulo:
        fig.text(0.01, 1 - 0.58 / alto, _envolver(subtitulo, 6.5), color=TINTA2, fontsize=9, va='center')
    manejadores, etiquetas = ejes[0].get_legend_handles_labels()
    fig.legend(manejadores, etiquetas, loc='center right', bbox_to_anchor=(0.99, 1 - 0.42 / alto), ncol=2,
               handlelength=1.6)
    return guardar(fig, ruta)


def galeria_errores(filas, ruta, titulo, subtitulo=None, columnas=6, max_imagenes=24):
    """filas: dicts con ruta_imagen, xs, ys (coordenadas MediaPipe), real, predicha, confianza."""
    import cv2
    from . import utils
    plt = _pyplot()
    filas = list(filas)[:max_imagenes]
    if not filas:
        return None
    n_filas = int(np.ceil(len(filas) / columnas))
    cabecera, alto_fila = 0.8, 2.45
    alto_fig = alto_fila * n_filas + cabecera      # ojo: 'alto' se usa abajo para la altura de cada imagen
    fig, ejes = plt.subplots(n_filas, columnas, figsize=(2.1 * columnas, alto_fig))
    fig.subplots_adjust(left=0.01, right=0.99, bottom=0.25 / alto_fig, top=1 - cabecera / alto_fig,
                        wspace=0.06, hspace=0.3)
    ejes = np.atleast_2d(ejes)
    for ax in ejes.ravel():
        ax.axis('off')
    for ax, f in zip(ejes.ravel(), filas):
        img = utils.leer_imagen(f['ruta_imagen'])
        if img is None:
            continue
        alto, ancho = img.shape[:2]
        px = np.clip(np.asarray(f['xs']) * ancho, 0, ancho - 1)
        py = np.clip(np.asarray(f['ys']) * alto, 0, alto - 1)
        lado = max(px.max() - px.min(), py.max() - py.min()) * 0.75 + 40
        cx, cy = (px.max() + px.min()) / 2, (py.max() + py.min()) / 2
        x0, x1 = int(max(0, cx - lado)), int(min(ancho, cx + lado))
        y0, y1 = int(max(0, cy - lado)), int(min(alto, cy + lado))
        rec = cv2.cvtColor(img[y0:y1, x0:x1], cv2.COLOR_BGR2RGB)
        ax.imshow(rec)
        for a, b in CONEXIONES_MANO:
            ax.plot([px[a] - x0, px[b] - x0], [py[a] - y0, py[b] - y0], color=PALETA[0], linewidth=1.2)
        ax.scatter(px - x0, py - y0, s=9, color=PALETA[0], edgecolors=SUPERFICIE, linewidths=0.8, zorder=3)
        ax.set_title('%s -> %s  (%.0f%%)' % (f['real'], f['predicha'], 100 * f['confianza']), fontsize=8,
                     color=TINTA, loc='center', fontweight='normal', pad=3)
        if f.get('pie'):
            ax.text(0.5, -0.04, f['pie'], transform=ax.transAxes, ha='center', va='top', fontsize=7, color=TINTA2)
    fig.text(0.01, 1 - 0.25 / alto_fig, titulo, color=TINTA, fontsize=12, fontweight='bold', va='center')
    if subtitulo:
        fig.text(0.01, 1 - 0.52 / alto_fig, subtitulo, color=TINTA2, fontsize=9, va='center')
    return guardar(fig, ruta)


def diversidad(muestras, ruta):
    """Distribucion por participante del tamano de la mano (distancia a la camara) y de su inclinacion."""
    plt = _pyplot()
    parts = sorted(muestras['participante'].unique())
    fig, ejes = plt.subplots(1, 2, figsize=(10, 3.9))
    paneles = (('tamano', 'Tamano de la mano en la imagen\n(alto de imagen; mayor = mas cerca)'),
               ('angulo', 'Inclinacion de la mano (grados;\n0 = vertical)'))
    for ax, (col, etiqueta) in zip(ejes, paneles):
        datos = [muestras.loc[muestras['participante'] == p, col].to_numpy() for p in parts]
        bp = ax.boxplot(datos, widths=0.45, patch_artist=True, showfliers=False,
                        medianprops={'color': SUPERFICIE, 'linewidth': 2},
                        boxprops={'facecolor': PALETA[0], 'edgecolor': PALETA[0]},
                        whiskerprops={'color': TINTA2}, capprops={'color': TINTA2})
        ax.set_xticks(range(1, len(parts) + 1), parts)
        ax.set_ylabel(etiqueta)
        _ejes(ax)
    alto = 3.9
    fig.subplots_adjust(left=0.08, right=0.98, bottom=0.12, top=1 - 0.85 / alto, wspace=0.3)
    fig.text(0.01, 1 - 0.28 / alto, 'Diversidad de la grabacion por participante', color=TINTA, fontsize=12,
             fontweight='bold', va='center')
    fig.text(0.01, 1 - 0.56 / alto, 'Cajas: del percentil 25 al 75; linea: mediana; bigotes: 1,5 veces el rango '
             'intercuartilico. Rangos amplios = distintas distancias y angulos.', color=TINTA2, fontsize=9, va='center')
    return guardar(fig, ruta)
