"""Revisa la auditoría con pids_auditor y comprueba permisos sin alterar documentos."""
from __future__ import annotations

import argparse
import os
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

from pymongo import MongoClient
from pymongo.errors import OperationFailure, PyMongoError

RAIZ = Path(__file__).resolve().parents[1]


def entorno(ruta: Path = RAIZ / '.env') -> dict[str, str]:
    """Lee la plantilla local de pares CLAVE=valor; el entorno del proceso tiene prioridad."""
    valores = {}
    if ruta.is_file():
        for linea in ruta.read_text(encoding='utf-8').splitlines():
            if linea.strip() and not linea.lstrip().startswith('#') and '=' in linea:
                clave, valor = linea.split('=', 1)
                valores[clave.strip()] = valor.strip().strip('\"\'')
    return {**valores, **os.environ}


def fecha_utc(texto: str) -> datetime:
    fecha = datetime.fromisoformat(texto.replace('Z', '+00:00'))
    return fecha.replace(tzinfo=timezone.utc) if fecha.tzinfo is None else fecha.astimezone(timezone.utc)


def celda(valor) -> str:
    return str(valor).replace('|', '\\|').replace('\n', ' ').replace('\r', ' ')


def tabla(cabeceras: list[str], filas) -> str:
    filas = list(filas)
    if not filas:
        return '_Sin registros en este periodo._\n'
    lineas = ['| ' + ' | '.join(cabeceras) + ' |', '| ' + ' | '.join(['---'] * len(cabeceras)) + ' |']
    lineas += ['| ' + ' | '.join(celda(v) for v in fila) + ' |' for fila in filas]
    return '\n'.join(lineas) + '\n'


def tipo_de_motivo(motivo: str) -> str:
    """'petición de datos individuales: <texto de la pregunta>' -> 'petición de datos individuales'.

    Los motivos llevan detrás de ': ' el detalle de cada consulta; sin quitarlo, cada pregunta distinta sería
    un motivo distinto y la tabla de los más frecuentes no diría nada.
    """
    return motivo.split(': ', 1)[0]


def resumir(decisiones, limite: int = 10) -> dict:
    """Una pasada sobre el cursor; solo conserva los rechazos recientes que se van a mostrar."""
    resultados, clientes, motivos = Counter(), Counter(), Counter()
    recientes = []
    total = 0
    for d in decisiones:  # el repositorio entrega el cursor ordenado por instante descendente
        total += 1
        resultados[d.get('resultado', 'sin resultado')] += 1
        clientes[d.get('cliente', 'sin cliente')] += 1
        if d.get('resultado') == 'rechazada':
            motivos.update(tipo_de_motivo(m) for m in d.get('motivos', []))
            if len(recientes) < limite:
                recientes.append(d)
    return {'total': total, 'resultados': resultados, 'clientes': clientes,
            'motivos': motivos, 'recientes': recientes}


def informe(resumen: dict, cargas: list[dict], desde: datetime, hasta: datetime) -> str:
    partes = ['# Auditoría de privacidad\n',
              f'Periodo UTC: {desde.isoformat()} → {hasta.isoformat()} (fin excluido).\n',
              f'Decisiones: **{resumen["total"]}**. Lectura con `pids_auditor`.\n',
              '## Decisiones por resultado\n', tabla(['Resultado', 'Cantidad'], resumen['resultados'].most_common()),
              '## Decisiones por cliente\n', tabla(['Cliente', 'Cantidad'], resumen['clientes'].most_common()),
              '## Motivos de rechazo más frecuentes\n',
              tabla(['Motivo', 'Cantidad'], resumen['motivos'].most_common(20)),
              '## Rechazos recientes\n', tabla(['Instante UTC', 'Cliente', 'Motivos'], [
                  (d.get('instante', ''), d.get('cliente', ''), '; '.join(d.get('motivos', [])))
                  for d in resumen['recientes']]),
              '## Cargas en el periodo\n', tabla(['Instante UTC', 'Lote', 'Leídos', 'Válidos', 'Rechazados'], [
                  (d.get('instante', ''), d.get('lote', ''), d.get('filas', ''), d.get('validos', ''),
                   d.get('rechazados', ''))
                  for d in cargas])]
    return '\n'.join(partes)


def conectar(cfg: dict, usuario: str = 'pids_auditor') -> MongoClient:
    clave = {'pids_auditor': 'MONGO_AUDITOR_PASSWORD', 'pids_acceso': 'MONGO_ACCESO_PASSWORD'}[usuario]
    if not cfg.get(clave):
        raise ValueError(f'Falta {clave} en el entorno o en .env')
    return MongoClient(host=cfg.get('AUDITORIA_MONGO_HOST', '127.0.0.1'),
                       port=int(cfg.get('PUERTO_MONGO', '27018')), username=usuario,
                       password=cfg[clave], authSource='admin', tz_aware=True,
                       serverSelectionTimeoutMS=5000, connectTimeoutMS=5000, socketTimeoutMS=10000)


def comprobar_permisos(auditor, acceso) -> list[dict]:
    """Exige Unauthorized (13). Incluso con permisos erróneos, las operaciones no cambian datos.

    El insert reutiliza un _id existente (fallaría por duplicado); update/delete usan una condición
    siempre falsa y nunca upsert. Un error distinto de autorización NO demuestra la protección.
    """
    doc = auditor.find_one({}, {'_id': 1})
    if doc is None:
        raise ValueError('La prueba segura de insert requiere al menos una decisión existente')
    imposible = {'$expr': {'$eq': [1, 0]}}
    operaciones = [
        ('pids_auditor', 'insert', lambda: auditor.insert_one({'_id': doc['_id']})),
        ('pids_auditor', 'delete', lambda: auditor.delete_one(imposible)),
        ('pids_acceso', 'update',
         lambda: acceso.update_one(imposible, {'$set': {'prueba_permisos': True}}, upsert=False)),
        ('pids_acceso', 'delete', lambda: acceso.delete_one(imposible)),
    ]
    salidas = []
    for usuario, operacion, ejecutar in operaciones:
        codigo = None
        try:
            ejecutar()
        except OperationFailure as error:
            codigo = error.code
        salidas.append({'usuario': usuario, 'operacion': operacion, 'codigo': codigo,
                        'denegada': codigo == 13})
    return salidas


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    periodo = p.add_mutually_exclusive_group()
    periodo.add_argument('--horas', type=float, default=24)
    periodo.add_argument('--desde', type=fecha_utc, help='Fecha ISO; sin zona se interpreta como UTC')
    p.add_argument('--limite', type=int, default=10, help='Rechazos recientes que se muestran')
    p.add_argument('--salida', type=Path, help='Fichero Markdown dentro de informes/')
    p.add_argument('--comprobar-permisos', action='store_true')
    args = p.parse_args()
    hasta = datetime.now(timezone.utc)
    desde = args.desde or hasta - timedelta(hours=args.horas)
    if desde >= hasta or args.horas <= 0 or args.limite < 1:
        p.error('El periodo debe ser positivo y el límite, al menos 1')
    if args.salida and not args.salida.resolve().is_relative_to((RAIZ / 'informes').resolve()):
        p.error('--salida debe estar dentro de informes/')
    try:
        cfg = entorno()
        with conectar(cfg) as mongo:
            auditoria = mongo['auditoria']
            filtro = {'instante': {'$gte': desde, '$lt': hasta}}
            campos = {'instante': 1, 'cliente': 1, 'resultado': 1, 'motivos': 1}
            cursor = auditoria.decisiones.find(filtro, campos).sort('instante', -1)
            resumen = resumir(cursor, args.limite)
            campos = {'instante': 1, 'lote': 1, 'filas': 1, 'validos': 1, 'rechazados': 1}
            cargas = list(auditoria.cargas.find(filtro, campos).sort('instante', -1))
            texto = informe(resumen, cargas, desde, hasta)
            correcto = True
            if args.comprobar_permisos:
                with conectar(cfg, 'pids_acceso') as acceso:
                    pruebas = comprobar_permisos(auditoria.decisiones, acceso['auditoria'].decisiones)
                correcto = all(prueba['denegada'] for prueba in pruebas)
                cabeceras = ['Usuario', 'Operación', 'Código MongoDB', 'Resultado']
                texto += '\n## Comprobación de permisos\n\n' + tabla(cabeceras, [
                    (prueba['usuario'], prueba['operacion'], prueba['codigo'],
                     'denegada' if prueba['denegada'] else 'NO CONFIRMADA') for prueba in pruebas])
                texto += ('\nLas operaciones de prueba no alteran documentos. Solo el código 13 confirma la '
                          'denegación.\n')
        print(texto)
        if args.salida:
            args.salida.parent.mkdir(parents=True, exist_ok=True)
            args.salida.write_text(texto, encoding='utf-8')
        return 0 if correcto else 1
    except (PyMongoError, ValueError) as error:
        # Las excepciones de conexión pueden incluir direcciones y opciones: no imprimir credenciales.
        print(f'No se pudo completar el informe ({type(error).__name__}). Revisa la conexión y las variables '
              'requeridas.')
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
