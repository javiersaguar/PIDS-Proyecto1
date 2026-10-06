"""Análisis no supervisado del dataset de gestos: ¿los puntos de la mano se agrupan por gesto o por persona?

Agrupa las 2931 manos detectadas sin mirar las etiquetas (k-means y Ward con k = 6) y compara los grupos con
el gesto, con la persona que grabó y con la mano (izquierda o derecha). Se repite con tres representaciones:
las coordenadas de MediaPipe sin tocar, la normalización completa (muñeca + escala + giro) y esa misma
normalización llevando todas las manos a la misma lateralidad (espejo). Escribe métricas, informe y figuras.

    python parte1_gestos/entrenamiento/clustering.py [--salida parte1_gestos/resultados/clustering]
"""
import argparse
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.optimize import linear_sum_assignment
from sklearn.cluster import AgglomerativeClustering, KMeans
from sklearn.manifold import TSNE
from sklearn.metrics import adjusted_rand_score, normalized_mutual_info_score, silhouette_score

PARTE1 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PARTE1 / 'entrenamiento'))
from hgr import features as F  # noqa: E402

DATOS = PARTE1 / 'datos_generados' / 'landmarks_todas.csv.gz'
REPRESENTACIONES = {
    'sin normalizar': ('ninguna', False),
    'normalizada': ('muneca_escala_rot', False),
    'normalizada + espejo': ('muneca_escala_rot', True),
}
GESTOS = ['ok', 'paper', 'rock', 'rockandroll', 'scissors', 'thumbsup']
COLOR_GESTO = ['#2563EB', '#7C3AED', '#E11D48', '#059669', '#D97706', '#0891B2']
COLOR_PERSONA = ['#1E3A8A', '#F97316', '#16A34A', '#DB2777', '#64748B']
FONDO, TINTA, GRIS = '#FAFAF8', '#1E293B', '#64748B'
SEMILLA = 0


def estilo():
    plt.rcParams.update({'font.family': ['Segoe UI', 'DejaVu Sans'], 'font.size': 11, 'axes.edgecolor': '#CBD5E1',
                         'axes.labelcolor': GRIS, 'xtick.color': GRIS, 'ytick.color': GRIS, 'figure.facecolor': FONDO,
                         'axes.facecolor': FONDO, 'savefig.facecolor': FONDO, 'axes.spines.top': False,
                         'axes.spines.right': False})


def titulo(fig, t, sub):
    fig.text(0.02, 0.975, t, fontsize=17, fontweight='bold', color='black', va='top')
    fig.text(0.02, 0.915, sub, fontsize=11.5, color=GRIS, va='top')


def cargar():
    df = pd.read_csv(DATOS)
    df = df[df['detectada'].astype(bool)].reset_index(drop=True)
    P, ar = F.coordenadas(df)
    return df, P, ar


def representar(df, P, ar, metodo, espejo):
    Q = F.transformar(P, ar, df['handedness'].tolist(), metodo, espejo=espejo)
    return Q.reshape(len(Q), -1)


def pureza(y, grupos):
    """Acierto del mejor emparejamiento uno a uno entre grupos y etiquetas (algoritmo húngaro)."""
    etiquetas = sorted(set(y))
    tabla = pd.crosstab(pd.Series(grupos, name='grupo'), pd.Series(y, name='etiqueta')).reindex(columns=etiquetas, fill_value=0)
    filas, cols = linear_sum_assignment(-tabla.to_numpy())
    return tabla.to_numpy()[filas, cols].sum() / len(y), tabla, dict(zip(tabla.index[filas], tabla.columns[cols]))


def medir(X, df):
    km = KMeans(n_clusters=6, n_init=20, random_state=SEMILLA).fit_predict(X)
    ward = AgglomerativeClustering(n_clusters=6, linkage='ward').fit_predict(X)
    km5 = KMeans(n_clusters=5, n_init=20, random_state=SEMILLA).fit_predict(X)
    gesto, persona, mano = df['clase'].to_numpy(), df['participante'].to_numpy(), df['handedness'].to_numpy()
    r = {
        'kmeans6_ari_gesto': adjusted_rand_score(gesto, km), 'kmeans6_nmi_gesto': normalized_mutual_info_score(gesto, km),
        'kmeans6_pureza_gesto': pureza(gesto, km)[0],
        'ward6_ari_gesto': adjusted_rand_score(gesto, ward), 'ward6_pureza_gesto': pureza(gesto, ward)[0],
        'kmeans5_ari_persona': adjusted_rand_score(persona, km5), 'kmeans5_nmi_persona': normalized_mutual_info_score(persona, km5),
        'kmeans5_pureza_persona': pureza(persona, km5)[0],
        'kmeans6_nmi_mano': normalized_mutual_info_score(mano, km),
        'silueta_gesto': silhouette_score(X, gesto), 'silueta_persona': silhouette_score(X, persona),
    }
    return {k: float(v) for k, v in r.items()}, km


def pureza_mayoria(y, grupos):
    """Fracción de manos cuyo grupo tiene como gesto mayoritario el suyo (varios grupos pueden ser del mismo gesto)."""
    return float(pd.crosstab(grupos, y).max(axis=1).sum() / len(y))


def barrido_k(X, y, ks=range(2, 21)):
    silueta, mayoria = {}, {}
    for k in ks:
        g = KMeans(n_clusters=k, n_init=10, random_state=SEMILLA).fit_predict(X)
        silueta[k], mayoria[k] = float(silhouette_score(X, g)), pureza_mayoria(y, g)
    return silueta, mayoria


def figura_tsne(df, incrustaciones, ruta):
    fig, ejes = plt.subplots(2, 3, figsize=(15, 9.4))
    fig.subplots_adjust(left=0.07, right=0.99, top=0.82, bottom=0.1, wspace=0.08, hspace=0.12)
    titulo(fig, 'Las manos en dos dimensiones (t-SNE), sin usar ninguna etiqueta',
           'Arriba, cada punto coloreado por gesto; abajo, por la persona que lo grabó. Solo cambia la representación.')
    for j, (nombre, Y) in enumerate(incrustaciones.items()):
        for i, (col, valores, colores) in enumerate([('clase', GESTOS, COLOR_GESTO),
                                                     ('participante', sorted(df['participante'].unique()), COLOR_PERSONA)]):
            ax = ejes[i, j]
            for v, c in zip(valores, colores):
                m = df[col].to_numpy() == v
                ax.scatter(Y[m, 0], Y[m, 1], s=5, color=c, alpha=0.75, linewidths=0, label=v)
            ax.set_xticks([]); ax.set_yticks([])
            for lado in ('left', 'bottom'):
                ax.spines[lado].set_visible(False)
            if i == 0:
                ax.set_title(nombre, fontsize=13, color=TINTA, fontweight='bold', pad=8)
            if j == 0:
                ax.set_ylabel('por gesto' if i == 0 else 'por persona', fontsize=12, color=TINTA)
    for i, n in enumerate((6, 5)):
        handles, labels = ejes[i, 0].get_legend_handles_labels()
        ejes[i, 2].legend(handles, labels, loc='center left', bbox_to_anchor=(1.0, 0.5), frameon=False, markerscale=3, fontsize=10.5)
    fig.subplots_adjust(right=0.88)
    fig.savefig(ruta, dpi=150)
    plt.close(fig)


def figura_metricas(metricas, ruta):
    nombres = list(metricas)
    x = np.arange(len(nombres))
    fig, ax = plt.subplots(figsize=(10, 5.6))
    fig.subplots_adjust(top=0.8, bottom=0.17, left=0.08, right=0.98)
    titulo(fig, '¿Los grupos coinciden con el gesto o con la persona?',
           'Acuerdo entre los grupos de k-means y las etiquetas reales (ARI: 0 = al azar, 1 = idénticos).')
    series = [('Grupos frente al gesto (k = 6)', 'kmeans6_ari_gesto', '#2563EB'),
              ('Grupos frente a la persona (k = 5)', 'kmeans5_ari_persona', '#F97316')]
    for d, (etq, clave, color) in enumerate(series):
        v = [metricas[n][clave] for n in nombres]
        barras = ax.bar(x + (d - 0.5) * 0.36, v, 0.34, color=color, label=etq)
        for b, val in zip(barras, v):
            ax.text(b.get_x() + b.get_width() / 2, val + 0.012, f'{val:.2f}'.replace('.', ','), ha='center', fontsize=11, color=TINTA)
    ax.set_xticks(x, nombres, fontsize=12, color=TINTA)
    ax.set_ylim(0, max(1.0, max(metricas[n][s[1]] for n in nombres for s in series) + 0.1))
    ax.set_ylabel('ARI')
    ax.yaxis.grid(True, color='#E2E8F0'); ax.set_axisbelow(True)
    ax.legend(frameon=False, loc='upper left', fontsize=11)
    fig.savefig(ruta, dpi=150)
    plt.close(fig)


def figura_mayoria(mayorias, ruta):
    fig, ax = plt.subplots(figsize=(10, 5.6))
    fig.subplots_adjust(top=0.8, bottom=0.13, left=0.09, right=0.97)
    titulo(fig, 'Cada gesto está hecho de varios subgrupos',
           '% de manos cuyo grupo de k-means tiene su mismo gesto como mayoritario, según el número de grupos k.')
    for (nombre, b), color in zip(mayorias.items(), ['#94A3B8', '#2563EB', '#7C3AED']):
        ax.plot(list(b), [v * 100 for v in b.values()], marker='o', ms=4, color=color, label=nombre, lw=2)
    ax.axvline(6, color='#CBD5E1', ls='--', lw=1)
    ax.text(6.15, 8, '6 gestos', color=GRIS, fontsize=10)
    ax.axhline(91.0, color='#F97316', ls=':', lw=1.5)
    ax.text(20, 92.2, 'k-NN supervisado (LOPO): 91 %', color='#F97316', fontsize=10, ha='right')
    ax.set_ylim(0, 100); ax.set_xticks(range(2, 21, 2))
    ax.set_xlabel('número de grupos k'); ax.set_ylabel('% de manos en un grupo de su gesto')
    ax.yaxis.grid(True, color='#E2E8F0'); ax.set_axisbelow(True)
    ax.legend(frameon=False)
    fig.savefig(ruta, dpi=150)
    plt.close(fig)


def informe(n, metricas, barridos, mayorias, ruta):
    f = lambda v: f'{v:.2f}'.replace('.', ',')
    pct = lambda v: f'{v * 100:.1f} %'.replace('.', ',')
    L = ['# Clustering del dataset de gestos', '',
         f'{n} manos detectadas (de 3000 imágenes), 42 valores por mano (x, y de los 21 puntos). Agrupadas **sin etiquetas**',
         'con k-means (k = 6, como gestos; k = 5, como personas) y Ward (k = 6), y comparadas después con las etiquetas.', '',
         '| Representación | ARI gesto (k-means) | Pureza gesto | ARI gesto (Ward) | ARI persona (k = 5) | NMI mano izq./der. | Silueta por gesto | Silueta por persona |',
         '|---|---|---|---|---|---|---|---|']
    for nombre, m in metricas.items():
        L.append(f"| {nombre} | {f(m['kmeans6_ari_gesto'])} | {pct(m['kmeans6_pureza_gesto'])} | {f(m['ward6_ari_gesto'])} | "
                 f"{f(m['kmeans5_ari_persona'])} | {f(m['kmeans6_nmi_mano'])} | {f(m['silueta_gesto'])} | {f(m['silueta_persona'])} |")
    L += ['', 'ARI: 0 = grupos al azar respecto a esa etiqueta, 1 = idénticos. Pureza: acierto del mejor emparejamiento uno a',
          'uno entre grupos y gestos. Silueta por etiqueta: cuánto se separan los gestos (o las personas) tal cual vienen',
          'etiquetados, de −1 a 1.', '', '## Según el número de grupos k (k-means)', '',
          'Pureza por mayoría: % de manos cuyo grupo tiene su mismo gesto como mayoritario (un gesto puede ocupar varios',
          'grupos). Silueta: separación de los grupos, de −1 a 1.', '',
          '| k | ' + ' | '.join(f'pureza {n}' for n in mayorias) + ' | ' + ' | '.join(f'silueta {n}' for n in barridos) + ' |',
          '|---|' + '---|' * (len(mayorias) + len(barridos))]
    for k in next(iter(barridos.values())):
        L.append(f'| {k} | ' + ' | '.join(pct(b[k]) for b in mayorias.values()) + ' | '
                 + ' | '.join(f(b[k]) for b in barridos.values()) + ' |')
    ruta.write_text('\n'.join(L) + '\n', encoding='utf-8')


def main():
    a = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    a.add_argument('--salida', type=Path, default=PARTE1 / 'resultados' / 'clustering')
    args = a.parse_args()
    args.salida.mkdir(parents=True, exist_ok=True)
    estilo()
    df, P, ar = cargar()
    metricas, incrustaciones, barridos, mayorias, grupos = {}, {}, {}, {}, {}
    for nombre, (metodo, espejo) in REPRESENTACIONES.items():
        X = representar(df, P, ar, metodo, espejo)
        metricas[nombre], grupos[nombre] = medir(X, df)
        barridos[nombre], mayorias[nombre] = barrido_k(X, df['clase'].to_numpy())
        incrustaciones[nombre] = TSNE(n_components=2, perplexity=30, init='pca', random_state=SEMILLA).fit_transform(X)
        print(nombre, {k: round(v, 3) for k, v in metricas[nombre].items()})
    (args.salida / 'metricas.json').write_text(json.dumps({'metricas': metricas, 'silueta_por_k': barridos, 'pureza_mayoria_por_k': mayorias}, indent=2, ensure_ascii=False), encoding='utf-8')
    informe(len(df), metricas, barridos, mayorias, args.salida / 'informe.md')
    figura_tsne(df, incrustaciones, args.salida / 'tsne_gesto_persona.png')
    figura_metricas(metricas, args.salida / 'ari_gesto_persona.png')
    figura_mayoria(mayorias, args.salida / 'subgrupos_por_k.png')
    print('escrito en', args.salida)


if __name__ == '__main__':
    main()
