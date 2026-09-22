"""Frescura, informe y seguridad de las comprobaciones; sin contenedores ni escrituras reales."""
import importlib.util
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, Mock

import pandas as pd
import pytest
from pymongo.errors import DuplicateKeyError, OperationFailure

from parte2_plataforma.acceso import app as acceso
from parte2_plataforma.acceso.repositorio import RepositorioMongo
from parte2_plataforma.comun import esquema
from scripts import informe_auditoria as auditoria
from scripts import medir_latencia_tiempo_real as latencia
from test_apis import RepoFalso


@pytest.mark.parametrize('instante,esperado', [
    (None, 0),
    (datetime(2026, 9, 21, 10), datetime(2026, 9, 21, 10, tzinfo=timezone.utc).timestamp()),
    (datetime(2026, 9, 21, 10, tzinfo=timezone.utc), datetime(2026, 9, 21, 10, tzinfo=timezone.utc).timestamp()),
])
async def test_frescura_usa_procesamiento_y_cero_si_no_hay_publicacion(instante, esperado):
    repo = RepoFalso([])
    repo.ultima_actualizacion_tiempo_real = AsyncMock(return_value=instante)
    await acceso._refrescar_frescura(repo)
    assert acceso.ULTIMA_ACTUALIZACION.labels('tiempo_real')._value.get() == esperado


async def test_error_de_lectura_no_conserva_frescura_anterior():
    repo = RepoFalso([])
    repo.ultima_actualizacion_tiempo_real = AsyncMock(side_effect=RuntimeError('sin conexión'))
    acceso.ULTIMA_ACTUALIZACION.labels('tiempo_real').set(123)
    await acceso._refrescar_frescura(repo)
    assert math.isnan(acceso.ULTIMA_ACTUALIZACION.labels('tiempo_real')._value.get())


async def test_frescura_no_recuerda_el_dia_del_viaje_ni_consulta_historico():
    coleccion = Mock()
    momento = datetime(2026, 9, 21, 10)
    coleccion.find_one = AsyncMock(return_value={'actualizado_en': momento})
    repo = RepositorioMongo.__new__(RepositorioMongo)
    repo.publico = {'tr_viajes_hora_zona': coleccion}
    assert await repo.ultima_actualizacion_tiempo_real() == momento
    argumentos = coleccion.find_one.call_args
    assert argumentos.kwargs['sort'] == [('actualizado_en', -1)]
    assert argumentos.kwargs['max_time_ms'] == 5000
    assert argumentos.args[1] == {'_id': 0, 'actualizado_en': 1}
    coleccion.find_one.return_value = None
    assert await repo.ultima_actualizacion_tiempo_real() is None


def test_los_ocho_cuadros_de_grafana_estan_generados():
    ruta = Path(__file__).parents[1] / 'parte2_plataforma/observabilidad/grafana/dashboards/generar.py'
    spec = importlib.util.spec_from_file_location('generar_dashboards', ruta)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    for uid, _titulo in modulo.CUADROS:
        tablero = json.loads((ruta.parent / f'{uid}.json').read_text())
        assert tablero['uid'] == uid
        assert any(panel.get('targets') for panel in tablero['panels'])


async def test_inventario_cuenta_las_colecciones_de_agregados_y_el_catalogo():
    class Publico:
        def __init__(self):
            self.pedidas = []

        async def command(self, orden, nombre):
            assert orden == 'collStats'
            self.pedidas.append(nombre)
            return {'count': len(nombre), 'size': 1000}

    repo = RepositorioMongo.__new__(RepositorioMongo)
    repo.publico = Publico()
    filas = await repo.inventario()
    assert repo.publico.pedidas == [
        'viajes_hora_zona', 'viajes_dia_barrio', 'od_dia_barrio',
        'tr_viajes_hora_zona', 'tr_viajes_dia_barrio', 'tr_od_dia_barrio', 'zonas',
    ]
    assert filas[-1] == {'coleccion': 'zonas', 'fuente': 'catalogo', 'documentos': 5, 'bytes': 1000}
    assert filas[0]['fuente'] == 'historico' and filas[3]['fuente'] == 'tiempo_real'


async def test_el_inventario_publica_documentos_y_bytes():
    repo = RepoFalso([])
    repo.inventario = AsyncMock(return_value=[
        {'coleccion': 'viajes_dia_barrio', 'fuente': 'historico', 'documentos': 12, 'bytes': 340},
    ])
    await acceso._refrescar_inventario(repo)
    assert acceso.DOCUMENTOS.labels('viajes_dia_barrio', 'historico')._value.get() == 12
    assert acceso.DATOS_BYTES.labels('viajes_dia_barrio', 'historico')._value.get() == 340


def test_informe_cuenta_y_limita_rechazos_sin_perder_totales():
    decisiones = [
        {'resultado': 'rechazada', 'cliente': 'equipo', 'motivos': ['campo | privado\nsensible']},
        {'resultado': 'rechazada', 'cliente': 'chatbot', 'motivos': ['campo | privado\nsensible', 'granularidad']},
        {'resultado': 'enmascarada', 'cliente': 'equipo', 'motivos': ['grupo pequeño']},
        {'resultado': 'permitida', 'cliente': 'equipo'},
    ]
    datos = auditoria.resumir(iter(decisiones), limite=1)
    assert datos['total'] == 4 and len(datos['recientes']) == 1
    assert datos['resultados'] == {'rechazada': 2, 'enmascarada': 1, 'permitida': 1}
    assert datos['clientes']['equipo'] == 3
    assert datos['motivos'] == {'campo | privado\nsensible': 2, 'granularidad': 1}
    agrupados = auditoria.resumir(iter([
        {'resultado': 'rechazada', 'motivos': ['petición de datos individuales: ¿quién cogió el taxi?']},
        {'resultado': 'rechazada', 'motivos': ['petición de datos individuales: dame el viaje de las 3:12']}]))
    assert agrupados['motivos'] == {'petición de datos individuales': 2}
    assert 'dame el viaje de las 3:12' in agrupados['recientes'][1]['motivos'][0]
    ahora = datetime.now(timezone.utc)
    texto = auditoria.informe(datos, [{'lote': 'prueba', 'validos': 15}], ahora, ahora)
    assert 'campo \\| privado sensible' in texto and 'prueba' in texto
    assert 'Sin registros' not in texto


def test_informe_vacio_y_fechas_con_zona():
    ahora = auditoria.fecha_utc('2026-09-21T12:00:00+02:00')
    assert ahora.hour == 10 and ahora.tzinfo == timezone.utc
    assert auditoria.fecha_utc('2026-09-21').tzinfo == timezone.utc
    assert 'Sin registros' in auditoria.informe(auditoria.resumir([]), [], ahora, ahora)


def test_prueba_permisos_no_puede_borrar_o_modificar_documentos():
    auditor, escritor = Mock(), Mock()
    auditor.find_one.return_value = {'_id': 'existente'}
    for operacion in (auditor.insert_one, auditor.delete_one, escritor.update_one, escritor.delete_one):
        operacion.side_effect = OperationFailure('denegada', code=13)
    resultados = auditoria.comprobar_permisos(auditor, escritor)
    assert len(resultados) == 4 and all(r['denegada'] for r in resultados)
    auditor.insert_one.assert_called_once_with({'_id': 'existente'})
    for operacion in (auditor.delete_one, escritor.update_one, escritor.delete_one):
        assert operacion.call_args.args[0] == {'$expr': {'$eq': [1, 0]}}
    assert escritor.update_one.call_args.kwargs['upsert'] is False


def test_duplicado_no_se_confunde_con_denegacion_de_permiso():
    auditor, escritor = Mock(), Mock()
    auditor.find_one.return_value = {'_id': 'existente'}
    auditor.insert_one.side_effect = DuplicateKeyError('duplicado', code=11000)
    resultados = auditoria.comprobar_permisos(auditor, escritor)
    assert not any(r['denegada'] for r in resultados)
    auditor.find_one.return_value = None
    with pytest.raises(ValueError, match='existente'):
        auditoria.comprobar_permisos(auditor, escritor)


def test_lotes_sinteticos_son_validos_y_consultas_no_solapan():
    plan = latencia.planificar(datetime(2020, 12, 31), 265, 20)
    assert len({c['desde'] for c in plan}) == 20
    assert all(a['hasta'] <= b['desde'] for a, b in zip(plan, plan[1:]))
    viajes = [latencia.viaje(datetime.fromisoformat(c['desde']), 265, i) for c in plan for i in range(15)]
    normalizados, _ = esquema.normalizar(pd.DataFrame(viajes))
    validos, rechazados = esquema.validar(normalizados)
    assert len(validos) == 300 and rechazados.empty


def test_plan_con_zonas_distintas_no_adelanta_la_hora():
    plan = latencia.planificar(datetime(2020, 12, 31, 22), 265, 20, zonas_distintas=True)
    assert {c['desde'] for c in plan} == {'2020-12-31T22:00:00'}
    assert [c['zona_origen'] for c in plan] == list(range(265, 245, -1))
    with pytest.raises(ValueError):
        latencia.planificar(datetime(2020, 12, 31, 22), 10, 20, zonas_distintas=True)


@pytest.mark.parametrize('inicio,zona,n', [
    (datetime(2020, 12, 31, 12), 265, 20),
    (datetime(2020, 12, 31, 0, 1), 265, 20),
    (datetime(2020, 12, 31), 266, 20),
    (datetime(2020, 12, 31), 265, 19),
])
def test_plan_rechaza_fechas_fuera_de_2020_y_argumentos_invalidos(inicio, zona, n):
    with pytest.raises(ValueError):
        latencia.planificar(inicio, zona, n)


def test_percentiles_y_medidas_censuradas_no_parecen_exitos():
    assert latencia.percentil([40, 10, 30, 20], .5) == 25
    assert latencia.percentil([40, 10, 30, 20], .95) == pytest.approx(38.5)
    datos = latencia.resumen([{'estado': 'publicado', 'latencia_s': 12}, {'estado': 'timeout'}])
    assert datos['publicadas'] == 1 and datos['fallidas'] == 1
    assert latencia.resumen([])['p95_s'] is None
    assert not latencia.reconocido([{'n_viajes': '<10', 'suprimido': True}], 15)
    assert not latencia.reconocido([{'n_viajes': 30, 'suprimido': False}], 15)
    assert latencia.reconocido([{'n_viajes': 15, 'suprimido': False}], 15)


def test_reglas_sin_trafico_no_alertan_frescura_y_silencian_notificaciones():
    carpeta = auditoria.RAIZ / 'parte2_plataforma/observabilidad/grafana/provisioning/alerting'
    contenido = json.loads((carpeta / 'reglas.json').read_text())
    reglas = {r['uid']: r for r in contenido['groups'][0]['rules']}
    assert set(reglas) == {'pids-frescura', 'pids-rechazos', 'pids-servicio'}
    assert reglas['pids-servicio']['for'] == '1m'
    expr = reglas['pids-frescura']['data'][0]['model']['expr']
    assert 'captura_eventos_total' in expr and '> bool 0' in expr
    assert 'publico_ultima_actualizacion' in expr and '> bool 300' in expr
    notificaciones = json.loads((carpeta / 'notificaciones.json').read_text())
    assert notificaciones['policies'][0]['routes'][0]['mute_time_intervals'] == ['pids-solo-panel']
