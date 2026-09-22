"""Indexación y recuperación del chatbot RAG sin red: Qdrant en memoria y embeddings falsos."""
import sys
from pathlib import Path

import httpx
import pytest
from langchain_core.embeddings import DeterministicFakeEmbedding
from qdrant_client import AsyncQdrantClient, QdrantClient

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / 'parte3_chatbot'))
sys.path.insert(0, str(RAIZ / 'parte3_chatbot_rag'))

import corpus as C  # noqa: E402
import fichas as F  # noqa: E402
import indexar as I  # noqa: E402
import recuperador as R  # noqa: E402

FILA_DIA = {'dia': '2020-03-03T00:00:00', 'barrio_origen': 'Manhattan', 'n_viajes': 203866, 'distancia_media': 2.9,
            'importe_medio': 18.5, 'propina_media': 2.07, 'pct_pago_tarjeta': 71.2, 'suprimido': False}
FILA_OCULTA = {'dia': '2020-01-01T00:00:00', 'barrio_origen': 'Staten Island', 'n_viajes': 'oculto',
               'distancia_media': None, 'importe_medio': None, 'propina_media': None, 'pct_pago_tarjeta': None,
               'suprimido': True}
FILA_FLUJO = {'dia': '2020-01-01T00:00:00', 'barrio_origen': 'Manhattan', 'barrio_destino': 'Bronx', 'n_viajes': 1311,
              'distancia_media': 8.23, 'importe_medio': 31.52, 'propina_media': 1.88, 'pct_pago_tarjeta': 37.38,
              'suprimido': False}

# --- indexación y recuperación en memoria -------------------------------------------------------------------------

EMBEDDINGS = DeterministicFakeEmbedding(size=64)
CONOCIMIENTO = [
    C.documento('Zona de taxi 132: JFK Airport, en el barrio Queens. También se le llama JFK, Kennedy, aeropuerto.',
                'zona', 'api:/zonas', 'Zona 132 · JFK Airport', zona_id=132, barrio='Queens'),
    C.documento('Los grupos con menos de 10 viajes se publican enmascarados, sin cifras.', 'doc',
                'config/privacidad.json', 'Reglas de privacidad (E3)'),
    C.documento('Pregunta: ¿Qué barrio tuvo más viajes el 3 de marzo?\nLlamada: consultar_viajes(nivel="dia_barrio")',
                'ejemplo', 'corpus/ejemplos.json', '¿Qué barrio tuvo más viajes el 3 de marzo?',
                herramienta='consultar_viajes'),
]
FICHAS = F.fichas([{**FILA_DIA, 'nivel': 'dia_barrio'}, {**FILA_OCULTA, 'nivel': 'dia_barrio'},
                   {**FILA_FLUJO, 'nivel': 'od_dia_barrio'},
                   {**FILA_DIA, 'nivel': 'dia_barrio', 'barrio_origen': 'Queens', 'n_viajes': 12145}])


async def _indexado(**opciones) -> tuple[AsyncQdrantClient, R.RecuperadorQdrant]:
    cliente = AsyncQdrantClient(':memory:')
    callar = lambda _: None  # noqa: E731
    await I.indexar_conocimiento(cliente, EMBEDDINGS, CONOCIMIENTO, avisar=callar, pausa=0)
    await I.indexar_fichas(cliente, EMBEDDINGS, FICHAS, avisar=callar, pausa=0)
    return cliente, R.RecuperadorQdrant(cliente, EMBEDDINGS, **opciones)


async def test_indexa_en_memoria_sin_duplicar_y_recupera_lo_mas_parecido():
    cliente, recuperador = await _indexado()
    assert await I.estado(cliente) == {R.COLECCION_CONOCIMIENTO: 3, R.COLECCION_FICHAS: 4}
    assert await I.subir(cliente, R.COLECCION_FICHAS, EMBEDDINGS, FICHAS, pausa=0, avisar=lambda _: None) == 4
    assert await I.subir(cliente, R.COLECCION_FICHAS, EMBEDDINGS, FICHAS, pausa=0, reanudar=True,
                         avisar=lambda _: None) == 0
    assert await I.estado(cliente) == {R.COLECCION_CONOCIMIENTO: 3, R.COLECCION_FICHAS: 4}      # idempotente
    docs = await recuperador.recuperar(CONOCIMIENTO[0].page_content, k=4)
    assert docs[0].metadata['titulo'] == 'Zona 132 · JFK Airport' and docs[0].metadata['puntuacion'] > 0.99
    assert docs[0].metadata['coleccion'] == R.COLECCION_CONOCIMIENTO and 'puntuacion' in docs[0].metadata
    assert {d.metadata['coleccion'] for d in docs} == {R.COLECCION_CONOCIMIENTO, R.COLECCION_FICHAS}
    assert len(docs) == 4 and len({d.metadata['_id'] for d in docs}) == 4
    ficha = await recuperador.recuperar(FICHAS[2].page_content, k=1)
    assert ficha[0].metadata['titulo'] == 'Manhattan → Bronx · 2020-01-01' and ficha[0].metadata['n_viajes'] == 1311
    assert F.fila_desde_metadatos(ficha[0].metadata) == FILA_FLUJO
    await cliente.close()


async def test_si_la_pregunta_menciona_un_dia_las_fichas_son_de_ese_dia():
    cliente, recuperador = await _indexado()
    docs = await recuperador.recuperar('¿Qué barrio tuvo más viajes el 3 de marzo?', k=6)
    fichas = [d for d in docs if d.metadata['tipo'] == 'ficha']
    assert fichas and {d.metadata['dia'] for d in fichas} == {'2020-03-03'}
    assert {d.metadata['nivel'] for d in fichas} == {'dia_barrio'}
    assert any(d.metadata['coleccion'] == R.COLECCION_CONOCIMIENTO for d in docs)      # el conocimiento no se filtra
    flujo = await recuperador.recuperar('¿Cuántos viajes hubo de Manhattan a Bronx el 1 de enero?', k=6)
    assert [d.metadata['titulo'] for d in flujo if d.metadata['tipo'] == 'ficha'] == ['Manhattan → Bronx · 2020-01-01']
    sin_dia = [d for d in await recuperador.recuperar('viajes de taxi', k=6) if d.metadata['tipo'] == 'ficha']
    assert sin_dia and all(d.metadata['nivel'] == 'dia_barrio' and not d.metadata['suprimido'] for d in sin_dia)
    solo_queens = [d for d in await recuperador.recuperar('viajes de taxi en Queens en marzo', k=6)
                   if d.metadata['tipo'] == 'ficha']
    assert [d.metadata['titulo'] for d in solo_queens] == ['Queens · 2020-03-03']
    explicito = await recuperador.recuperar('el 3 de marzo', k=6, filtro={'dia': '2020-01-01'})
    assert {d.metadata['dia'] for d in explicito} == {'2020-01-01'}
    await cliente.close()


async def test_filtra_por_metadatos_y_busca_fichas_exactas():
    cliente, recuperador = await _indexado()
    solo_queens = await recuperador.recuperar('viajes', k=5, filtro={'barrio_origen': 'Queens'})
    assert [d.metadata['titulo'] for d in solo_queens] == ['Queens · 2020-03-03']
    del_dia = await recuperador.fichas(dia='2020-03-03')
    assert [d.metadata['barrio_origen'] for d in del_dia] == ['Manhattan', 'Queens']
    assert [d.metadata['titulo'] for d in await recuperador.fichas(dia='2020-01-01', nivel='od_dia_barrio')] == \
        ['Manhattan → Bronx · 2020-01-01']
    assert await recuperador.fichas(dia='2020-07-04') == []
    ocultas = await recuperador.recuperar('viajes', k=5, filtro={'suprimido': True})
    assert [d.metadata['barrio_origen'] for d in ocultas] == ['Staten Island']
    varios = await recuperador.recuperar('viajes', k=5, filtro={'barrio_origen': ['Queens', 'Staten Island']})
    assert len(varios) == 2
    with pytest.raises(ValueError):
        R.filtro_qdrant({'texto': 'x'})
    assert R.filtro_qdrant({'dia': None}) is None and R.filtro_qdrant(None) is None
    await cliente.close()


async def test_sin_colecciones_devuelve_vacio_y_con_otra_dimension_pide_recrear():
    cliente = AsyncQdrantClient(':memory:')
    assert await R.RecuperadorQdrant(cliente, EMBEDDINGS).recuperar('hola') == []
    await I.preparar_coleccion(cliente, R.COLECCION_FICHAS, 8, avisar=lambda _: None)
    with pytest.raises(SystemExit):
        await I.preparar_coleccion(cliente, R.COLECCION_FICHAS, 64, avisar=lambda _: None)
    await I.preparar_coleccion(cliente, R.COLECCION_FICHAS, 64, recrear=True, avisar=lambda _: None)
    assert (await cliente.get_collection(R.COLECCION_FICHAS)).config.params.vectors.size == 64
    await cliente.close()


def test_la_fusion_garantiza_un_minimo_por_coleccion_y_ordena_por_puntuacion():
    def doc(i, p):
        return C.documento(f'texto {i}', 'doc', 'f', f't{i}', puntuacion=p)
    por_coleccion = {'a': [doc(1, 0.9), doc(2, 0.8), doc(3, 0.7)], 'b': [doc(4, 0.2), doc(5, 0.1)]}
    assert [d.metadata['titulo'] for d in R.fusionar(por_coleccion, 3)] == ['t1', 't2', 't4']
    assert [d.metadata['titulo'] for d in R.fusionar(por_coleccion, 2, minimo_por_coleccion=2)] == ['t1', 't2']
    assert [d.metadata['titulo'] for d in R.fusionar(por_coleccion, 3, minimo_por_coleccion=0)] == ['t1', 't2', 't3']
    assert [d.metadata['titulo'] for d in R.fusionar(por_coleccion, 10)] == ['t1', 't2', 't3', 't4', 't5']
    assert [d.metadata['titulo'] for d in R.fusionar(por_coleccion, 3, {'b': 2})] == ['t1', 't4', 't5']
    assert R.fusionar({}, 3) == []
    ejemplos = [C.documento(f'e{i}', 'ejemplo', 'f', f'e{i}') for i in range(4)] + [C.documento('d', 'doc', 'f', 'd')]
    assert [d.metadata['titulo'] for d in R.limitar_tipo(ejemplos, 'ejemplo', 2)] == ['e0', 'e1', 'd']


async def test_el_rerank_reordena_y_si_falla_se_queda_el_orden_por_similitud():
    async def invertir(pregunta, textos, top_n):
        return [(i, 1.0 - i / 10) for i in reversed(range(len(textos)))][:top_n]

    async def romper(pregunta, textos, top_n):
        raise httpx.HTTPError('sin rerank')

    cliente, recuperador = await _indexado(rerank=True, reordenador=invertir)
    normal = await R.RecuperadorQdrant(cliente, EMBEDDINGS).recuperar(CONOCIMIENTO[1].page_content, k=3)
    reordenados = await recuperador.recuperar(CONOCIMIENTO[1].page_content, k=3)
    assert len(reordenados) == 3 and all('puntuacion_rerank' in d.metadata for d in reordenados)
    assert reordenados[0].metadata['_id'] != normal[0].metadata['_id']
    roto = await R.RecuperadorQdrant(cliente, EMBEDDINGS, rerank=True, reordenador=romper).recuperar(
        CONOCIMIENTO[1].page_content, k=3)
    assert [d.metadata['_id'] for d in roto] == [d.metadata['_id'] for d in normal]
    await cliente.close()


async def test_tambien_funciona_con_el_cliente_sincrono_de_qdrant():
    cliente = QdrantClient(':memory:')
    callar = lambda _: None  # noqa: E731
    await I.indexar_fichas(cliente, EMBEDDINGS, FICHAS, avisar=callar, pausa=0)
    recuperador = R.obtener_recuperador(k=2, rerank=False, cliente=cliente, embeddings=EMBEDDINGS)
    docs = await recuperador.recuperar(FICHAS[0].page_content)          # el texto nombra Manhattan y el 3 de marzo
    assert [d.metadata['titulo'] for d in docs] == ['Manhattan · 2020-03-03']
    assert len(await recuperador.recuperar('viajes', filtro={})) == 2
    assert [d.metadata['barrio_origen'] for d in await recuperador.fichas(dia='2020-03-03')] == ['Manhattan', 'Queens']
    assert await I.estado(cliente) == {R.COLECCION_FICHAS: 4}


def test_obtener_recuperador_lee_el_entorno_y_acepta_clientes_inyectados(monkeypatch):
    monkeypatch.setenv('RAG_K', '9')
    monkeypatch.setenv('RAG_RERANK', 'true')
    r = R.obtener_recuperador(cliente=AsyncQdrantClient(':memory:'), embeddings=EMBEDDINGS)
    assert isinstance(r, R.RecuperadorQdrant) and r.k == 9 and r.rerank is True
    assert R.obtener_recuperador(k=2, rerank=False, cliente=AsyncQdrantClient(':memory:'), embeddings=EMBEDDINGS).k == 2


def test_el_filtro_deducido_de_la_pregunta_es_el_dia_que_menciona_y_el_nivel():
    assert R.filtro_para('¿Qué barrio tuvo más viajes el 3 de marzo?') == {'dia': '2020-03-03', 'nivel': 'dia_barrio'}
    assert R.filtro_para('Trips on January 15') == {'dia': '2020-01-15', 'nivel': 'dia_barrio'}
    assert R.filtro_para('¿Por qué hay grupos <10?') == {'nivel': 'dia_barrio', 'suprimido': False}
    assert R.filtro_para('Propina media en Manhattan la primera semana de febrero') == \
        {'nivel': 'dia_barrio', 'mes': 2, 'suprimido': False, 'barrio_origen': 'Manhattan'}
    assert R.filtro_para('¿Cuántos viajes hubo el último día de febrero en el Bronx?') == \
        {'nivel': 'dia_barrio', 'mes': 2, 'suprimido': False, 'barrio_origen': 'Bronx'}
    assert R.filtro_para('Compara Manhattan y Brooklyn en enero y febrero') == \
        {'nivel': 'dia_barrio', 'suprimido': False}
    assert R.filtro_para('¿Cuántos viajes hubo de Queens a Manhattan el 10 de enero?') == \
        {'nivel': 'od_dia_barrio', 'dia': '2020-01-10'}
    for pregunta in ('¿Cuántos viajes hubo de Queens a Manhattan el 10 de enero?',
                     'Flujos entre barrios el 25 de diciembre', 'viajes hacia Brooklyn el 2 de mayo',
                     '¿A qué barrio fueron más viajes desde Queens el 10 de enero?',
                     '¿Cuántos viajes llegaron al Bronx el 4 de julio?'):
        assert R.nivel_para(pregunta) == 'od_dia_barrio', pregunta
    for pregunta in ('Propina media en Manhattan la primera semana de febrero',
                     'viajes desde Staten Island el 1 de enero', 'viajes que salieron de Brooklyn el 14 de febrero'):
        assert R.nivel_para(pregunta) == 'dia_barrio', pregunta
