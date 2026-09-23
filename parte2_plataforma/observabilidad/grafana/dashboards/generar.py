"""Genera los cuadros de Grafana en esta carpeta. Prometheus es la única fuente.

    python parte2_plataforma/observabilidad/grafana/dashboards/generar.py

Los viajes individuales no salen aquí: MongoDB solo tiene agregados ya protegidos y S3 guarda el crudo.
"""
from __future__ import annotations

import json
from pathlib import Path

CARPETA = Path(__file__).parent
PROM = {'type': 'prometheus', 'uid': 'prometheus'}
CUADROS = [
    ('pids-plataforma', 'Plataforma'),
    ('pids-privacidad', 'Privacidad'),
    ('pids-chatbots', 'Chatbots'),
    ('pids-kafka', 'Kafka y captura'),
    ('pids-spark', 'Spark'),
    ('pids-mongo', 'MongoDB'),
    ('pids-s3', 'S3'),
    ('pids-tiempo-real', 'Tiempo real'),
]


class Lienzo:
    def __init__(self) -> None:
        self.paneles: list[dict] = []
        self._y = 0
        self._x = 0
        self._alto = 0
        self._n = 0

    def fila(self, titulo: str) -> None:
        self._cerrar_fila()
        self._n += 1
        self.paneles.append({
            'id': self._n, 'type': 'row', 'title': titulo, 'collapsed': False,
            'gridPos': {'h': 1, 'w': 24, 'x': 0, 'y': self._y}, 'panels': [],
        })
        self._y += 1

    def panel(self, tipo: str, titulo: str, ancho: int, alto: int, **extra) -> None:
        if self._x + ancho > 24:
            self._cerrar_fila()
        self._n += 1
        panel = {
            'id': self._n, 'type': tipo, 'title': titulo,
            'gridPos': {'h': alto, 'w': ancho, 'x': self._x, 'y': self._y},
            'datasource': PROM,
        }
        panel.update(extra)
        if panel.get('datasource') is None:
            panel.pop('datasource', None)
        self.paneles.append(panel)
        self._x += ancho
        self._alto = max(self._alto, alto)

    def _cerrar_fila(self) -> None:
        if self._x:
            self._y += self._alto
        self._x = 0
        self._alto = 0

    def terminar(self) -> list[dict]:
        self._cerrar_fila()
        return self.paneles


def consulta(expr: str, leyenda: str = '', instantaneo: bool = False) -> dict:
    destino = {'refId': 'A', 'expr': expr}
    if leyenda:
        destino['legendFormat'] = leyenda
    if instantaneo:
        # El valor de ahora, sin depender del paso del rango (una métrica recién creada cabe en un paso de 5 min y se ve vacía).
        destino['instant'] = True
    return destino


def serie(titulo: str, expr: str, leyenda: str, ancho: int = 12, alto: int = 8, unidad: str = 'short', **extra) -> dict:
    return {
        'tipo': 'timeseries', 'titulo': titulo, 'ancho': ancho, 'alto': alto,
        'targets': [consulta(expr, leyenda)],
        'fieldConfig': {'defaults': {'unit': unidad}, 'overrides': extra.get('overrides', [])},
        'description': extra.get('description', ''),
    }


def stat(titulo: str, expr: str, ancho: int = 6, alto: int = 4, **extra) -> dict:
    campo = {'unit': extra.get('unidad', 'short')}
    if 'umbrales' in extra:
        campo['thresholds'] = {'mode': 'absolute', 'steps': extra['umbrales']}
    if 'color' in extra:
        campo['color'] = {'mode': 'fixed', 'fixedColor': extra['color']}
    return {
        'tipo': 'stat', 'titulo': titulo, 'ancho': ancho, 'alto': alto,
        'targets': [consulta(expr, extra.get('leyenda', ''), instantaneo=True)],
        'options': {'colorMode': extra.get('colorMode', 'value'), 'graphMode': 'area', 'reduceOptions': {'calcs': ['lastNotNull']}},
        'fieldConfig': {'defaults': campo, 'overrides': extra.get('overrides', [])},
        'description': extra.get('description', ''),
    }


def colocar(lienzo: Lienzo, piezas: list[dict]) -> None:
    for pieza in piezas:
        tipo = pieza.pop('tipo')
        titulo = pieza.pop('titulo')
        ancho = pieza.pop('ancho')
        alto = pieza.pop('alto')
        if tipo == 'texto':
            lienzo.panel('text', titulo, ancho, alto, options={'mode': 'markdown', 'content': pieza['content']}, transparent=True)
            continue
        if tipo == 'alerta':
            lienzo.panel('alertlist', titulo, ancho, alto, datasource=None, options={
                'viewMode': 'list', 'groupMode': 'default', 'maxItems': 20, 'sortOrder': 1,
                'dashboardAlerts': False, 'alertName': 'PIDS',
                'stateFilter': {'firing': True, 'pending': True, 'error': True, 'noData': True, 'normal': False},
            })
            continue
        lienzo.panel(tipo, titulo, ancho, alto, **{k: v for k, v in pieza.items() if v != ''})


def colores_resultado() -> list[dict]:
    fijos = {'permitida': 'green', 'enmascarada': 'orange', 'rechazada': 'red'}
    return [{'matcher': {'id': 'byName', 'options': nombre},
             'properties': [{'id': 'color', 'value': {'mode': 'fixed', 'fixedColor': color}}]}
            for nombre, color in fijos.items()]


def cuadro(uid: str, titulo: str, horas: str, lienzo: Lienzo) -> dict:
    return {
        'uid': uid,
        'title': f'PIDS · {titulo}',
        'tags': ['pids'],
        'timezone': 'browser',
        'schemaVersion': 39,
        'version': 2,
        'refresh': '30s',
        'time': {'from': f'now-{horas}', 'to': 'now'},
        'graphTooltip': 1,
        'links': [{'title': 'Otros cuadros de PIDS', 'type': 'dashboards', 'icon': 'dashboard',
                   'tags': ['pids'], 'asDropdown': True, 'keepTime': True, 'includeVars': False, 'targetBlank': False}],
        'panels': lienzo.terminar(),
    }


def plataforma() -> dict:
    l = Lienzo()
    l.fila('Servicios')
    colocar(l, [
        stat('Servicios activos', 'count(up == 1)', 4, umbrales=[{'color': 'red', 'value': None}, {'color': 'green', 'value': 8}]),
        stat('Servicios caídos', 'count(up == 0) or vector(0)', 4, color='red',
             umbrales=[{'color': 'green', 'value': None}, {'color': 'red', 'value': 1}]),
        stat('Workers de Spark', 'metrics_master_aliveWorkers_Value', 4),
        stat('Frescura del tiempo real',
             'clamp_min(time() - max(publico_ultima_actualizacion_timestamp_segundos{fuente="tiempo_real"}), 0)',
             6, unidad='s', umbrales=[{'color': 'green', 'value': None}, {'color': 'orange', 'value': 120}, {'color': 'red', 'value': 300}],
             description='Segundos desde que Spark escribió agregados de tiempo real. 0 si nunca ha publicado.'),
        stat('Crudo en S3', 'SeaweedFS_s3_bucket_size_bytes{bucket="crudo"}', 6, unidad='bytes'),
    ])
    l.fila('Qué está pasando')
    colocar(l, [
        serie('Decisiones de la puerta de salida', 'sum by (resultado) (rate(acceso_consultas_total[5m]))', '{{resultado}}',
              overrides=colores_resultado(), description='Consultas por segundo, por veredicto.'),
        serie('Viajes que entran a la cola', 'sum by (tipo) (rate(captura_eventos_total[1m]))', '{{tipo}}', unidad='reqps'),
        serie('Registros que Kafka acepta',
              'sum by (redpanda_topic) (rate(redpanda_kafka_records_produced_total{redpanda_topic=~"viajes-crudos|gestos"}[5m]))',
              '{{redpanda_topic}}', unidad='reqps'),
        {'tipo': 'bargauge', 'titulo': 'Estado de cada servicio', 'ancho': 12, 'alto': 8,
         'targets': [consulta('up', '{{job}} {{replica}}')],
         'options': {'orientation': 'horizontal', 'displayMode': 'basic', 'reduceOptions': {'calcs': ['lastNotNull']}},
         'fieldConfig': {'defaults': {'min': 0, 'max': 1, 'mappings': [
             {'type': 'value', 'options': {'0': {'text': 'caído', 'color': 'red'}, '1': {'text': 'activo', 'color': 'green'}}},
         ], 'thresholds': {'mode': 'absolute', 'steps': [{'color': 'red', 'value': None}, {'color': 'green', 'value': 1}]}}}},
        {'tipo': 'alerta', 'titulo': 'Alertas activas', 'ancho': 12, 'alto': 8},
    ])
    return cuadro('pids-plataforma', 'Plataforma', '6h', l)


def privacidad() -> dict:
    l = Lienzo()
    l.fila('Decisiones')
    colocar(l, [
        stat('Permitidas', 'sum(increase(acceso_consultas_total{resultado="permitida"}[$__range]))', 8, color='green'),
        stat('Enmascaradas', 'sum(increase(acceso_consultas_total{resultado="enmascarada"}[$__range]))', 8, color='orange'),
        stat('Rechazadas', 'sum(increase(acceso_consultas_total{resultado="rechazada"}[$__range]))', 8, color='red',
             description='Una pregunta que pedía un viaje, una persona o un grupo más fino de lo que E3 permite.'),
        serie('Por minuto', 'sum by (resultado) (increase(acceso_consultas_total[1m]))', '{{resultado}}', 16,
              overrides=colores_resultado()),
        {'tipo': 'piechart', 'titulo': 'Quién pregunta', 'ancho': 8, 'alto': 8,
         'targets': [consulta('sum by (cliente) (increase(acceso_consultas_total[$__range]))', '{{cliente}}')],
         'options': {'legend': {'displayMode': 'table', 'placement': 'right'}, 'reduceOptions': {'calcs': ['lastNotNull']}}},
        serie('Grupos enmascarados', 'sum by (nivel) (increase(acceso_grupos_enmascarados_total[5m]))', '{{nivel}}',
              description='Grupos devueltos sin cifras porque tenían menos de k = 10 viajes.'),
        serie('Cada réplica de la puerta', 'sum by (replica) (rate(acceso_consultas_total[5m]))', 'réplica {{replica}}',
              unidad='reqps', description='Si una réplica se para, la otra se queda con las consultas.'),
    ])
    return cuadro('pids-privacidad', 'Privacidad', '24h', l)


def chatbots() -> dict:
    clientes = 'cliente=~"chatbot|chatbot_rag|frontend"'
    l = Lienzo()
    l.fila('Preguntas')
    colocar(l, [
        {'tipo': 'texto', 'titulo': 'De dónde sale cada pregunta', 'ancho': 24, 'alto': 3, 'content':
         '**Ollama** es el cliente `chatbot`. **DeepSeek en Helmcode** es `chatbot_rag`. **TAXI AI**, el asistente de esta web, entra como `frontend`, igual que el explorador. Una serie vacía significa que ese cliente no ha preguntado en el periodo.'},
        stat('Ollama', f'sum(increase(acceso_consultas_total{{{clientes},cliente="chatbot"}}[$__range]))', 8),
        stat('DeepSeek (Helmcode)', f'sum(increase(acceso_consultas_total{{{clientes},cliente="chatbot_rag"}}[$__range]))', 8),
        stat('Portal (TAXI AI y explorador)', f'sum(increase(acceso_consultas_total{{cliente="frontend"}}[$__range]))', 8),
        serie('Preguntas por minuto', f'sum by (cliente) (increase(acceso_consultas_total{{{clientes}}}[1m]))', '{{cliente}}', 16),
        {'tipo': 'bargauge', 'titulo': 'Veredicto de cada asistente', 'ancho': 8, 'alto': 8,
         'targets': [consulta(f'sum by (cliente, resultado) (increase(acceso_consultas_total{{{clientes}}}[$__range]))',
                              '{{cliente}} · {{resultado}}')],
         'options': {'orientation': 'horizontal', 'displayMode': 'gradient', 'reduceOptions': {'calcs': ['lastNotNull']}}},
        serie('Rechazos de los asistentes',
              f'sum by (cliente) (increase(acceso_consultas_total{{{clientes},resultado="rechazada"}}[5m]))',
              '{{cliente}}', description='El prefiltro ni siquiera llama al modelo cuando la pregunta pide un viaje concreto.'),
        serie('Respuestas enmascaradas',
              f'sum by (cliente) (increase(acceso_consultas_total{{{clientes},resultado="enmascarada"}}[5m]))', '{{cliente}}'),
    ])
    return cuadro('pids-chatbots', 'Chatbots', '24h', l)


def kafka() -> dict:
    temas = 'redpanda_topic=~"viajes-crudos|gestos"'
    l = Lienzo()
    l.fila('Cola')
    colocar(l, [
        stat('Temas', 'redpanda_cluster_topics', 4),
        stat('Particiones no disponibles', 'sum(redpanda_cluster_unavailable_partitions)', 5, color='red',
             umbrales=[{'color': 'green', 'value': None}, {'color': 'red', 'value': 1}]),
        stat('Réplicas retrasadas', 'sum(redpanda_kafka_under_replicated_replicas)', 5,
             umbrales=[{'color': 'green', 'value': None}, {'color': 'orange', 'value': 1}]),
        stat('Brokers', 'redpanda_cluster_brokers', 4),
        stat('Memoria usada', 'redpanda_memory_allocated_memory', 6, unidad='bytes'),
        serie('Registros producidos', f'sum by (redpanda_topic) (rate(redpanda_kafka_records_produced_total{{{temas}}}[1m]))',
              '{{redpanda_topic}}', unidad='reqps'),
        serie('Registros leídos', f'sum by (redpanda_topic) (rate(redpanda_kafka_records_fetched_total{{{temas}}}[1m]))',
              '{{redpanda_topic}}', unidad='reqps'),
        serie('Latencia p95 de Kafka',
              'histogram_quantile(0.95, sum by (le, redpanda_request) (rate(redpanda_kafka_request_latency_seconds_bucket[5m])))',
              '{{redpanda_request}}', unidad='s'),
        serie('Bytes de petición', 'sum by (redpanda_topic) (rate(redpanda_kafka_request_bytes_total[5m]))',
              '{{redpanda_topic}}', unidad='Bps'),
    ])
    l.fila('Entrada')
    colocar(l, [
        serie('Eventos aceptados por la captura', 'sum by (tipo) (rate(captura_eventos_total[1m]))', '{{tipo}}', unidad='reqps'),
        serie('Peticiones rechazadas en la entrada', 'sum by (motivo) (rate(captura_peticiones_rechazadas_total[5m]))', '{{motivo}}'),
    ])
    return cuadro('pids-kafka', 'Kafka y captura', '6h', l)


def spark() -> dict:
    l = Lienzo()
    l.fila('Máster')
    colocar(l, [
        stat('Workers vivos', 'metrics_master_aliveWorkers_Value', 6,
             umbrales=[{'color': 'red', 'value': None}, {'color': 'green', 'value': 2}]),
        stat('Workers registrados', 'metrics_master_workers_Value', 6),
        stat('Aplicaciones', 'metrics_master_apps_Value', 6),
        stat('Aplicaciones en espera', 'metrics_master_waitingApps_Value', 6,
             umbrales=[{'color': 'green', 'value': None}, {'color': 'orange', 'value': 1}]),
        serie('Aplicaciones en el máster', 'metrics_master_apps_Value', 'en marcha', 12),
        serie('Workers', 'metrics_master_aliveWorkers_Value', 'vivos', 12),
    ])
    l.fila('Workers')
    colocar(l, [
        serie('Núcleos usados', 'metrics_worker_coresUsed_Value', '{{instance}}'),
        serie('Núcleos libres', 'metrics_worker_coresFree_Value', '{{instance}}'),
        serie('Memoria usada', 'metrics_worker_memUsed_MB_Value', '{{instance}}', unidad='decmbytes'),
        serie('Memoria libre', 'metrics_worker_memFree_MB_Value', '{{instance}}', unidad='decmbytes'),
        serie('Ejecutores', 'metrics_worker_executors_Value', '{{instance}}'),
        stat('Núcleos usados ahora', 'sum(metrics_worker_coresUsed_Value)', 8),
        stat('Memoria usada ahora', 'sum(metrics_worker_memUsed_MB_Value)', 8, unidad='decmbytes'),
        stat('Ejecutores', 'sum(metrics_worker_executors_Value)', 8),
    ])
    return cuadro('pids-spark', 'Spark', '6h', l)


def mongo() -> dict:
    l = Lienzo()
    l.fila('Qué hay guardado')
    colocar(l, [
        {'tipo': 'texto', 'titulo': 'Solo agregados', 'ancho': 24, 'alto': 3, 'content':
         'MongoDB guarda totales con **k = 10** (base `publico`) y la auditoría. Los viajes de cada persona están en el bucket S3 `crudo`, no aquí. `historico` es 2020; `tiempo_real` es lo que Spark acaba de publicar.'},
        stat('Documentos publicados', 'sum(max by (coleccion) (publico_documentos))', 6,
             description='max entre las dos réplicas: las dos publican el mismo inventario.'),
        stat('Tamaño de los agregados', 'sum(max by (coleccion) (publico_datos_bytes))', 6, unidad='bytes'),
        stat('Último día histórico', 'max(publico_ultimo_dia_timestamp_segundos{fuente="historico"}) * 1000', 6, unidad='dateTimeAsIso'),
        stat('Último día de tiempo real', 'max(publico_ultimo_dia_timestamp_segundos{fuente="tiempo_real"}) * 1000', 6, unidad='dateTimeAsIso'),
        {'tipo': 'bargauge', 'titulo': 'Documentos por colección', 'ancho': 12, 'alto': 8,
         'targets': [consulta('max by (coleccion) (publico_documentos)', '{{coleccion}}', instantaneo=True)],
         'options': {'orientation': 'horizontal', 'displayMode': 'gradient', 'reduceOptions': {'calcs': ['lastNotNull']}}},
        {'tipo': 'bargauge', 'titulo': 'Bytes por colección', 'ancho': 12, 'alto': 8,
         'targets': [consulta('max by (coleccion) (publico_datos_bytes)', '{{coleccion}}', instantaneo=True)],
         'options': {'orientation': 'horizontal', 'displayMode': 'gradient', 'reduceOptions': {'calcs': ['lastNotNull']}},
         'fieldConfig': {'defaults': {'unit': 'bytes'}}},
        {'tipo': 'bargauge', 'titulo': 'Viajes del último día histórico, por barrio', 'ancho': 12, 'alto': 8,
         'targets': [consulta('max by (barrio) (publico_viajes_ultimo_dia{fuente="historico"})', '{{barrio}}')],
         'options': {'orientation': 'horizontal', 'displayMode': 'gradient', 'reduceOptions': {'calcs': ['lastNotNull']}},
         'description': 'Agregado protegido. Un barrio con menos de 10 viajes no aparece con su cifra.'},
        {'tipo': 'bargauge', 'titulo': 'Viajes del último día de tiempo real, por barrio', 'ancho': 12, 'alto': 8,
         'targets': [consulta('max by (barrio) (publico_viajes_ultimo_dia{fuente="tiempo_real"})', '{{barrio}}')],
         'options': {'orientation': 'horizontal', 'displayMode': 'gradient', 'reduceOptions': {'calcs': ['lastNotNull']}}},
    ])
    return cuadro('pids-mongo', 'MongoDB', '24h', l)


def s3() -> dict:
    l = Lienzo()
    l.fila('Buckets')
    colocar(l, [
        stat('Crudo', 'SeaweedFS_s3_bucket_size_bytes{bucket="crudo"}', 6, unidad='bytes',
             description='Viajes individuales, el único sitio donde existen.'),
        stat('Referencia', 'SeaweedFS_s3_bucket_size_bytes{bucket="referencia"}', 6, unidad='bytes'),
        stat('Objetos en crudo', 'SeaweedFS_s3_bucket_object_count{bucket="crudo"}', 6),
        stat('Disco del volumen', 'sum(SeaweedFS_volumeServer_total_disk_size)', 6, unidad='bytes',
             description='Espacio que ocupan los volúmenes en disco, sumados.'),
        serie('Tamaño de cada bucket', 'SeaweedFS_s3_bucket_size_bytes', '{{bucket}}', unidad='bytes'),
        serie('Objetos', 'SeaweedFS_s3_bucket_object_count', '{{bucket}}'),
        serie('Peticiones por tipo', 'sum by (type, bucket) (rate(SeaweedFS_s3_request_total[5m]))', '{{bucket}} {{type}}', unidad='reqps'),
        serie('Bytes recibidos', 'sum by (bucket) (rate(SeaweedFS_s3_bucket_traffic_received_bytes_total[5m]))', '{{bucket}}', unidad='Bps'),
        serie('Bytes enviados', 'sum by (bucket) (rate(SeaweedFS_s3_bucket_traffic_sent_bytes_total[5m]))', '{{bucket}}', unidad='Bps'),
        serie('Errores de lectura', 'sum(rate(SeaweedFS_volumeServer_file_read_failures[5m]))', 'fallos', unidad='reqps'),
        stat('Peticiones en curso', 'sum(SeaweedFS_s3_in_flight_requests)', 8),
        stat('Volúmenes escribibles', 'sum(SeaweedFS_master_volume_layout_writable)', 8),
        stat('Errores de disco', 'sum(SeaweedFS_volumeServer_storage_io_error_total)', 8, color='red',
             umbrales=[{'color': 'green', 'value': None}, {'color': 'red', 'value': 1}]),
    ])
    return cuadro('pids-s3', 'S3', '24h', l)


def tiempo_real() -> dict:
    l = Lienzo()
    l.fila('Del taxi a la tabla')
    colocar(l, [
        stat('Segundos desde la última publicación',
             'clamp_min(time() - max(publico_ultima_actualizacion_timestamp_segundos{fuente="tiempo_real"}), 0)',
             8, unidad='s', umbrales=[{'color': 'green', 'value': None}, {'color': 'orange', 'value': 120}, {'color': 'red', 'value': 300}],
             description='Cuándo escribió Spark, no la fecha de 2020 del viaje.'),
        stat('Viajes por segundo en la entrada', 'sum(rate(captura_eventos_total{tipo="viaje"}[1m]))', 8, unidad='reqps'),
        stat('Documentos de tiempo real', 'sum(max by (coleccion) (publico_documentos{fuente="tiempo_real"}))', 8),
        serie('Entrada de viajes', 'sum(rate(captura_eventos_total{tipo="viaje"}[1m]))', 'viajes', unidad='reqps'),
        serie('La cola los acepta', 'sum(rate(redpanda_kafka_records_produced_total{redpanda_topic="viajes-crudos"}[1m]))',
              'viajes-crudos', unidad='reqps'),
        serie('Spark los lee', 'sum(rate(redpanda_kafka_records_fetched_total{redpanda_topic="viajes-crudos"}[1m]))',
              'leídos', unidad='reqps'),
        serie('Edad de la publicación',
              'clamp_min(time() - max(publico_ultima_actualizacion_timestamp_segundos{fuente="tiempo_real"}), 0)',
              'segundos', unidad='s'),
        serie('Ejecutores mientras publica', 'sum(metrics_worker_executors_Value)', 'ejecutores'),
        {'tipo': 'bargauge', 'titulo': 'Último día publicado, por barrio', 'ancho': 24, 'alto': 8,
         'targets': [consulta('max by (barrio) (publico_viajes_ultimo_dia{fuente="tiempo_real"})', '{{barrio}}')],
         'options': {'orientation': 'horizontal', 'displayMode': 'gradient', 'reduceOptions': {'calcs': ['lastNotNull']}}},
    ])
    return cuadro('pids-tiempo-real', 'Tiempo real', '3h', l)


def main() -> None:
    for tablero in (plataforma(), privacidad(), chatbots(), kafka(), spark(), mongo(), s3(), tiempo_real()):
        destino = CARPETA / f'{tablero["uid"]}.json'
        destino.write_text(json.dumps(tablero, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        print(destino.name, len(tablero['panels']), 'paneles')


if __name__ == '__main__':
    main()
