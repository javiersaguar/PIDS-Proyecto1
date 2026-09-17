"""Metricas de clasificacion y analisis de errores."""
import numpy as np
import pandas as pd
from sklearn.metrics import (accuracy_score, balanced_accuracy_score, confusion_matrix, f1_score,
                             precision_recall_fscore_support)


def calcular(y_true, y_pred):
    y_true, y_pred = np.asarray(y_true), np.asarray(y_pred)
    if len(y_true) == 0:
        return {'accuracy': np.nan, 'balanced_accuracy': np.nan, 'f1_macro': np.nan, 'n': 0}
    return {'accuracy': float(accuracy_score(y_true, y_pred)),
            'balanced_accuracy': float(balanced_accuracy_score(y_true, y_pred)),
            'f1_macro': float(f1_score(y_true, y_pred, average='macro', zero_division=0)),
            'n': int(len(y_true))}


def matriz_confusion(y_true, y_pred, n_clases):
    return confusion_matrix(y_true, y_pred, labels=np.arange(n_clases))


def informe_por_clase(y_true, y_pred, clases):
    p, r, f, s = precision_recall_fscore_support(y_true, y_pred, labels=np.arange(len(clases)), zero_division=0)
    return pd.DataFrame({'clase': clases, 'precision': p, 'recall': r, 'f1': f, 'soporte': s})


def ic95_repo(n, accuracy):
    """Semiancho del IC al 95% con la aproximacion normal que usa common/evaluation.py.

    Supone muestras independientes. Nuestros fotogramas NO lo son (100 fotogramas
    seguidos de la misma persona), asi que este intervalo es mas estrecho de lo que
    deberia: se reporta para comparar con el enunciado, y la variabilidad real se
    mide con la dispersion entre participantes en lopo.
    """
    if not n:
        return np.nan
    return float(1.96 * np.sqrt(accuracy * (1.0 - accuracy) / n))


def principales_confusiones(cm, clases, top=10):
    filas = []
    totales = cm.sum(axis=1)
    for i in range(len(clases)):
        for j in range(len(clases)):
            if i != j and cm[i, j] > 0:
                filas.append({'real': clases[i], 'predicha': clases[j], 'n': int(cm[i, j]),
                              'pct_de_la_clase_real': 100.0 * cm[i, j] / max(1, totales[i])})
    df = pd.DataFrame(filas, columns=['real', 'predicha', 'n', 'pct_de_la_clase_real'])
    return df.sort_values(['n', 'pct_de_la_clase_real'], ascending=False).head(top).reset_index(drop=True)
