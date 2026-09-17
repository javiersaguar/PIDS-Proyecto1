"""Perfila un fichero de viajes (CSV o Parquet): volumen, rango de fechas, calidad y distribuciones.

Aplica el mismo esquema y las mismas reglas que la plataforma (parte2_plataforma/comun/esquema.py).

Uso:
    uv run python scripts/perfilar_datos.py data/muestra/yellow_tripdata_2020_muestra.csv
    uv run python scripts/perfilar_datos.py data/crudo/yellow_tripdata_2020-01.parquet --informe informes/2020-01.md
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from parte2_plataforma.comun import esquema as E  # noqa: E402


def leer(ruta: Path) -> pd.DataFrame:
    if ruta.suffix == '.parquet':
        return pd.read_parquet(ruta)
    return pd.read_csv(ruta, dtype=str, keep_default_na=False, na_values=[''])


def tabla(serie: pd.Series, campo: str | None = None) -> str:
    """Frecuencias de una columna; con `campo`, añade el significado del código (diccionario de la TLC)."""
    total = serie.size
    filas = ['| valor | viajes | % |', '|---|---|---|']
    for valor, n in serie.value_counts(dropna=False).sort_index().items():
        etiqueta = f'{valor} ({E.nombre(campo, valor)})' if campo else valor
        filas.append(f'| {etiqueta} | {n:,} | {100 * n / total:.1f} |')
    return '\n'.join(filas)


def informe(ruta: Path) -> str:
    bruto = leer(ruta)
    df, extra = E.normalizar(bruto)
    validos, rechazados = E.validar(df)
    L = [f'# Perfil de `{ruta.name}`', '',
         f'- Filas: **{len(df):,}** · válidas **{len(validos):,}** ({100 * len(validos) / max(1, len(df)):.1f} %) '
         f'· rechazadas **{len(rechazados):,}**',
         f'- Columnas de la fuente: {len(bruto.columns)}'
         + (f' · no reconocidas (se ignoran): `{", ".join(extra)}`' if extra else ''),
         f'- Recogidas entre {df["recogida"].min()} y {df["recogida"].max()}',
         f'- Zonas de origen distintas: {df["zona_origen"].nunique()}', '']

    L += ['## Motivos de rechazo', '', '| motivo | viajes |', '|---|---|']
    motivos = rechazados['motivos'].explode().value_counts() if len(rechazados) else pd.Series(dtype=int)
    L += [f'| {m} | {n:,} |' for m, n in motivos.items()] or ['| (ninguno) | 0 |']

    L += ['', '## Avisos (no invalidan el viaje)', '', '| aviso | viajes |', '|---|---|']
    L += [f'| {k} | {v:,} |' for k, v in E.avisos(validos).items()]

    L += ['', '## Viajes válidos', '',
          '### Numéricas', '',
          validos[['distancia_millas', 'tarifa', 'propina', 'importe_total', 'pasajeros']]
          .describe().round(2).to_markdown(),
          '', '### Tipo de pago', '', tabla(validos['tipo_pago'], 'tipo_pago'),
          '', '### Tarifa', '', tabla(validos['tarifa_id'], 'tarifa_id'),
          '', '### Proveedor (VendorID)', '', tabla(validos['vendor_id'], 'vendor_id'),
          '', '### Viajes por hora del día', '', tabla(validos['recogida'].dt.hour),
          '']
    return '\n'.join(str(x) for x in L)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('fichero', type=Path)
    p.add_argument('--informe', type=Path, default=None, help='guardar el informe en Markdown')
    args = p.parse_args()
    texto = informe(args.fichero)
    print(texto)
    if args.informe:
        args.informe.parent.mkdir(parents=True, exist_ok=True)
        args.informe.write_text(texto, encoding='utf-8')
        print(f'\nInforme guardado en {args.informe}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
