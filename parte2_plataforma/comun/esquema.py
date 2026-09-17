"""Esquema canónico de un viaje y reglas de validación (versión Python).

Las reglas están en `config/esquema_viaje.json`, que también lee el código Scala de Spark
(`pids.Esquema`). Así el histórico y el tiempo real aplican exactamente las mismas reglas, como
exige E3, y los tests de los dos lenguajes comprueban los mismos resultados sobre la muestra.

Los datos llegan con nombres y formatos distintos según la fuente:
  - exportación CSV de NYC Open Data: VendorID, fechas "01/01/2020 12:28:15 AM"
  - API de NYC Open Data (SODA):      vendorid, fechas ISO, todo como texto
  - Parquet mensual de la TLC:         VendorID, fechas ya como timestamp, alguna columna extra
`normalizar` lo lleva todo a los nombres canónicos y a tipos numéricos.

Semántica de nulos (igual en Scala): un campo vacío solo invalida el viaje si es obligatorio
(regla `falta_campo_obligatorio`); el resto de reglas no se consideran incumplidas por un nulo.
"""
from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path

import pandas as pd

RUTA_CONFIG = Path(os.environ.get('PIDS_CONFIG_DIR', Path(__file__).resolve().parents[2] / 'config'))


@lru_cache(maxsize=1)
def config() -> dict:
    return json.loads((RUTA_CONFIG / 'esquema_viaje.json').read_text(encoding='utf-8'))


def columnas() -> list[str]:
    return list(config()['alias'].values())


def normalizar(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    """Renombra a los nombres canónicos y convierte tipos.

    Devuelve el DataFrame canónico y las columnas de la fuente que no se reconocen (se ignoran,
    pero conviene saberlo: puede ser un cambio de formato del proveedor). Los valores que no se
    pueden convertir quedan como nulos y los detecta `validar`.
    """
    cfg = config()
    renombrar, extra = {}, []
    for col in df.columns:
        canon = cfg['alias'].get(str(col).strip().lower())
        if canon is None:
            extra.append(str(col))
        else:
            renombrar[col] = canon
    out = df.rename(columns=renombrar)[list(renombrar.values())].copy()
    for col in columnas():
        if col not in out.columns:
            out[col] = pd.NA
    for col in cfg['fechas']:
        out[col] = _a_fecha(out[col])
    for col in columnas():
        if col in cfg['fechas'] or col in cfg['texto']:
            continue
        valores = _a_numero(out[col], cfg.get('decimal_coma', False))
        out[col] = valores.astype('Int64') if col in cfg['enteras'] and _son_enteros(valores) else valores
    for col in cfg['texto']:
        out[col] = out[col].astype('string').str.strip().str.upper()
    return out[columnas()], extra


def _son_enteros(valores: pd.Series) -> bool:
    v = valores.dropna()
    return bool((v == v.round()).all())


def _a_numero(serie: pd.Series, decimal_coma: bool) -> pd.Series:
    """A número, aceptando el decimal con coma de la exportación completa ("1,2" o "1.234,56")."""
    if pd.api.types.is_numeric_dtype(serie):
        return serie
    texto = serie.astype('string').str.strip()
    if decimal_coma:
        con_coma = texto.str.contains(',', na=False)
        if con_coma.any():
            # con coma decimal, el punto es separador de miles
            texto = texto.mask(con_coma, texto.str.replace('.', '', regex=False).str.replace(',', '.', regex=False))
    return pd.to_numeric(texto, errors='coerce')


def _a_fecha(serie: pd.Series) -> pd.Series:
    """A datetime sin zona horaria y con la misma resolución, probando los formatos de cada fuente.

    Muestra de Moodle "01/01/2020 12:28:15 AM", exportación completa "2020 Jan 01 12:28:15 AM",
    API en ISO y Parquet ya como timestamp.
    """
    if pd.api.types.is_datetime64_any_dtype(serie):
        return (serie.dt.tz_localize(None) if serie.dt.tz is not None else serie).astype('datetime64[us]')
    texto = serie.astype('string').str.strip()
    fechas = pd.Series(pd.NaT, index=serie.index, dtype='datetime64[us]')
    for formato in config()['formatos_fecha_python'] + ['ISO8601']:
        pendientes = fechas.isna() & texto.notna()
        if not pendientes.any():
            break
        intento = pd.to_datetime(texto[pendientes], format=formato, errors='coerce')
        fechas[pendientes] = intento.astype('datetime64[us]')
    return fechas.astype('datetime64[us]')


def validar(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Separa los viajes válidos de los rechazados.

    Devuelve (validos, rechazados). `rechazados` lleva una columna `motivos` con la lista de
    reglas incumplidas, en el mismo orden que en Spark.
    """
    r = config()['reglas']
    duracion = df['llegada'] - df['recogida']
    zona_ok = range(r['zona_minima'], r['zona_maxima'] + 1)

    def fuera(col, validos):
        return df[col].notna() & ~df[col].isin(validos)

    reglas = {
        'falta_campo_obligatorio': df[config()['obligatorias']].isna().any(axis=1),
        'fecha_fuera_de_rango': df['recogida'].notna() & ~df['recogida'].between(
            pd.Timestamp(r['recogida_desde']), pd.Timestamp(r['recogida_hasta']), inclusive='left'),
        'duracion_no_positiva': duracion <= pd.Timedelta(0),
        'duracion_excesiva': duracion > pd.Timedelta(hours=r['duracion_maxima_horas']),
        'distancia_fuera_de_rango': df['distancia_millas'].notna()
                                    & ~df['distancia_millas'].between(0, r['distancia_maxima_millas']),
        'importe_negativo': (df['tarifa'] < 0) | (df['importe_total'] < 0),
        'vendor_desconocido': fuera('vendor_id', r['vendor_id']),
        'zona_desconocida': fuera('zona_origen', zona_ok) | fuera('zona_destino', zona_ok),
        'tipo_pago_desconocido': fuera('tipo_pago', r['tipo_pago']),
        'tarifa_desconocida': fuera('tarifa_id', r['tarifa_id']),
        'indicador_invalido': fuera('almacenado_y_reenviado', r['almacenado_y_reenviado']),
    }
    fallos = pd.DataFrame({k: v.astype('boolean').fillna(False).astype(bool) for k, v in reglas.items()},
                          index=df.index)
    malo = fallos.any(axis=1)
    rechazados = df[malo].copy()
    rechazados['motivos'] = [[k for k, v in fila.items() if v] for fila in fallos[malo].to_dict('records')]
    return df[~malo].copy(), rechazados


def avisos(df: pd.DataFrame) -> dict[str, int]:
    """Valores sospechosos que NO invalidan el viaje pero conviene vigilar."""
    return {
        'pasajeros_cero': int((df['pasajeros'] == 0).sum()),
        'pasajeros_nulos': int(df['pasajeros'].isna().sum()),
        'distancia_cero': int((df['distancia_millas'] == 0).sum()),
        'tarifa_cero': int((df['tarifa'] == 0).sum()),
    }


def nombre(campo: str, codigo) -> str:
    """Significado de un código según el diccionario de la TLC."""
    if pd.isna(codigo):
        return '?'
    return config()['diccionario'].get(campo, {}).get(str(int(codigo)), '?')
