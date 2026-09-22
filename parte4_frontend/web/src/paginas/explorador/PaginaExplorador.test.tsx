import { fireEvent, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'

import type { Catalogo, Decision, Respuesta, Zona } from '@/api/tipos'
import { cuerpoEnviado, renderizarRutas, simularApi } from '@/pruebas/utilidades'

const CATALOGO: Catalogo = {
  k_minimo: 10,
  max_dias_por_consulta: 31,
  metricas: ['n_viajes', 'distancia_media', 'importe_medio', 'propina_media', 'pct_pago_tarjeta'],
  niveles: {
    hora_zona: { descripcion: 'Viajes por hora y zona de origen.', dimensiones: ['hora', 'zona_origen'] },
    dia_barrio: { descripcion: 'Viajes por día y barrio (borough) de origen.', dimensiones: ['dia', 'barrio_origen'] },
    od_dia_barrio: { descripcion: 'Flujos entre barrios por día.', dimensiones: ['dia', 'barrio_origen', 'barrio_destino'] },
  },
  fuentes: ['historico', 'tiempo_real'],
  barrios: ['Bronx', 'Brooklyn', 'EWR', 'Manhattan', 'N/A', 'Queens', 'Staten Island', 'Unknown'],
}

const ZONAS: Zona[] = [
  { _id: 132, nombre: 'JFK Airport', barrio: 'Queens', tipo_servicio: 'Airports' },
  { _id: 221, nombre: 'Stapleton', barrio: 'Staten Island', tipo_servicio: 'Boro Zone' },
]

const NOTA = 'Los grupos enmascarados no se suman a ningún total: ocultarlos no serviría si se pudieran deducir por diferencia.'

const RESPUESTA_ENMASCARADA: Respuesta = {
  resultado: 'enmascarada',
  consulta: { nivel: 'hora_zona', fuente: 'historico', desde: '2020-01-01T00:00:00', hasta: '2020-01-02T00:00:00', metricas: ['n_viajes'], zona_origen: 221 },
  filas: [
    { zona_origen: 221, zona_origen_nombre: 'Stapleton', barrio_origen: 'Staten Island', n_viajes: 'oculto', hora: '2020-01-01T05:00:00', suprimido: true },
    { zona_origen: 221, zona_origen_nombre: 'Stapleton', barrio_origen: 'Staten Island', n_viajes: 'oculto', hora: '2020-01-01T09:00:00', suprimido: true },
    { zona_origen: 221, zona_origen_nombre: 'Stapleton', barrio_origen: 'Staten Island', n_viajes: 12, hora: '2020-01-01T18:00:00', suprimido: false },
  ],
  grupos_enmascarados: 2,
  truncada: false,
  nota: NOTA,
}

const RESPUESTA_BARRIOS: Respuesta = {
  resultado: 'enmascarada',
  consulta: { nivel: 'dia_barrio', fuente: 'historico', desde: '2020-03-03T00:00:00', hasta: '2020-03-04T00:00:00', metricas: ['n_viajes', 'distancia_media', 'importe_medio', 'propina_media', 'pct_pago_tarjeta'] },
  filas: [
    { dia: '2020-03-03T00:00:00', barrio_origen: 'Manhattan', n_viajes: 203866, distancia_media: 2.2, importe_medio: 16.96, propina_media: 2.12, pct_pago_tarjeta: 78.07, suprimido: false },
    { dia: '2020-03-03T00:00:00', barrio_origen: 'Queens', n_viajes: 12145, distancia_media: 10.77, importe_medio: 45.0, propina_media: 5.11, pct_pago_tarjeta: 61.98, suprimido: false },
    { dia: '2020-03-03T00:00:00', barrio_origen: 'Staten Island', n_viajes: 'oculto', distancia_media: null, importe_medio: null, propina_media: null, pct_pago_tarjeta: null, suprimido: true },
  ],
  grupos_enmascarados: 1,
  truncada: false,
  nota: NOTA,
}

const RECHAZO: Decision = {
  resultado: 'rechazada',
  motivos: ['el nivel hora_zona no filtra por barrio; se usa dia_barrio', 'la granularidad mínima es de un día completo'],
  alternativa: {
    nivel: 'dia_barrio',
    fuente: 'historico',
    desde: '2020-01-01T00:00:00',
    hasta: '2020-01-02T00:00:00',
    metricas: ['n_viajes'],
    zona_origen: null,
    barrio_origen: 'Staten Island',
    barrio_destino: null,
  },
}

const BASE = {
  'GET /api/sesion': { autenticado: true },
  'GET /api/catalogo': CATALOGO,
  'GET /api/zonas': ZONAS,
}

const URL_ENMASCARADA = '/explorador?nivel=hora_zona&fuente=historico&desde=2020-01-01T00%3A00%3A00&hasta=2020-01-02T00%3A00%3A00&zona_origen=221'

describe('PaginaExplorador', () => {
  it('lanza la consulta de la URL y marca los grupos enmascarados con el chip y «oculto»', async () => {
    const espia = simularApi({ ...BASE, 'POST /api/consultas': RESPUESTA_ENMASCARADA })
    renderizarRutas(URL_ENMASCARADA)

    const resultado = await screen.findByRole('region', { name: 'Resultado de la consulta' })
    expect(await within(resultado).findByRole('heading', { name: 'Viajes por hora' })).toBeInTheDocument()
    expect(within(resultado).getByText(/Stapleton \(zona 221\)/)).toBeInTheDocument()
    expect(within(resultado).getByText('enmascarada')).toBeInTheDocument()
    expect(within(resultado).getByText('3 filas')).toBeInTheDocument()
    expect(within(resultado).getByText('2 grupos enmascarados')).toBeInTheDocument()

    const tabla = within(resultado).getByRole('table', { name: /^Filas:/ })
    expect(within(tabla).getAllByText('enmascarado por privacidad')).toHaveLength(2)
    expect(within(tabla).getAllByText('oculto')).toHaveLength(2)
    const [, cuerpo, pie] = within(tabla).getAllByRole('rowgroup')
    expect(within(cuerpo).getByText('12')).toBeInTheDocument()
    // El total del pie solo suma el grupo visible.
    expect(pie).toHaveTextContent('Total de los grupos visibles (1 grupo)')
    expect(pie).toHaveTextContent('2 enmascarados no incluidos')

    expect(within(resultado).getByText(NOTA)).toBeInTheDocument()
    expect(within(resultado).getByRole('img', { name: 'Viajes por hora' })).toBeInTheDocument()

    // Una única petición POST, con la consulta de la URL.
    const posts = espia.mock.calls.filter(([, init]) => (init as RequestInit | undefined)?.method === 'POST')
    expect(posts).toHaveLength(1)
    expect(cuerpoEnviado(espia, espia.mock.calls.indexOf(posts[0]))).toEqual({
      nivel: 'hora_zona',
      fuente: 'historico',
      desde: '2020-01-01T00:00:00',
      hasta: '2020-01-02T00:00:00',
      metricas: ['n_viajes'],
      zona_origen: 221,
    })

    // El formulario se ha rellenado con la consulta de la URL.
    expect(screen.getByRole('combobox', { name: 'Nivel de agregación' })).toHaveTextContent('Hora y zona')
    expect(await screen.findByDisplayValue('Stapleton')).toBeInTheDocument()
  })

  it('un 403 muestra la tarjeta de rechazo con los motivos y «Consultar la alternativa» la relanza', async () => {
    const espia = simularApi({
      ...BASE,
      'POST /api/consultas': (init: RequestInit) => {
        const cuerpo = JSON.parse(init.body as string) as { nivel: string }
        return cuerpo.nivel === 'hora_zona' ? { status: 403, json: RECHAZO } : { ...RESPUESTA_BARRIOS, consulta: RECHAZO.alternativa }
      },
    })
    renderizarRutas('/explorador?nivel=hora_zona&desde=2020-01-01T03%3A00%3A00&hasta=2020-01-01T04%3A00%3A00&barrio_origen=Staten%20Island')
    const usuario = userEvent.setup()

    const alerta = await screen.findByRole('alert')
    expect(alerta).toHaveTextContent('Consulta rechazada por privacidad')
    const motivos = within(alerta).getByRole('list', { name: 'Motivos del rechazo' })
    expect(within(motivos).getAllByRole('listitem').map((li) => li.textContent)).toEqual(RECHAZO.motivos)
    expect(alerta).toHaveTextContent('viajes por día desde Staten Island el 01/01/2020 (histórico)')

    await usuario.click(within(alerta).getByRole('button', { name: 'Consultar la alternativa' }))

    await waitFor(() => expect(screen.queryByRole('alert')).not.toBeInTheDocument())
    const resultado = screen.getByRole('region', { name: 'Resultado de la consulta' })
    expect(await within(resultado).findByRole('heading', { name: 'Viajes por día' })).toBeInTheDocument()
    expect(within(resultado).getByText('Staten Island · 1 día (el 01/01/2020)')).toBeInTheDocument()
    expect(within(resultado).getByRole('table', { name: /^Filas:/ })).toBeInTheDocument()
    expect(cuerpoEnviado(espia)).toEqual({
      nivel: 'dia_barrio',
      fuente: 'historico',
      desde: '2020-01-01T00:00:00',
      hasta: '2020-01-02T00:00:00',
      metricas: ['n_viajes'],
      barrio_origen: 'Staten Island',
    })
    // El formulario se ha rellenado con la alternativa.
    expect(screen.getByRole('combobox', { name: 'Nivel de agregación' })).toHaveTextContent('Día y barrio')
    expect(screen.getByRole('combobox', { name: 'Barrio de origen' })).toHaveTextContent('Staten Island')
  })

  it('valida en cliente: ventana vacía y rango mayor que el máximo, sin llamar a la API', async () => {
    const espia = simularApi({ ...BASE, 'POST /api/consultas': RESPUESTA_BARRIOS })
    renderizarRutas('/explorador')
    const usuario = userEvent.setup()

    expect(await screen.findByText('Sin consulta')).toBeInTheDocument()
    const hasta = screen.getByLabelText('Hasta (no incluido)')
    fireEvent.change(hasta, { target: { value: '2020-01-01' } })
    await usuario.click(screen.getByRole('button', { name: 'Consultar' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('La fecha de fin debe ser posterior a la de inicio')
    expect(hasta).toHaveAttribute('aria-invalid', 'true')

    fireEvent.change(hasta, { target: { value: '2020-02-02' } })
    expect(await screen.findByRole('alert')).toHaveTextContent('El rango máximo por consulta es de 31 días (la ventana elegida tiene 32 días).')
    expect(screen.getByRole('button', { name: 'Consultar' })).toBeDisabled()

    fireEvent.change(hasta, { target: { value: '2020-02-01' } })
    await waitFor(() => expect(screen.queryByRole('alert')).not.toBeInTheDocument())
    expect(screen.queryByText(/Ventana:/)).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Consultar' })).toBeEnabled()

    const posts = espia.mock.calls.filter(([, init]) => (init as RequestInit | undefined)?.method === 'POST')
    expect(posts).toHaveLength(0)
  })

  it('al enviar el formulario la consulta pasa a la URL y se pinta el gráfico de barras por barrio', async () => {
    const espia = simularApi({ ...BASE, 'POST /api/consultas': RESPUESTA_BARRIOS })
    const { enrutador } = renderizarRutas('/explorador')
    const usuario = userEvent.setup()

    fireEvent.change(await screen.findByLabelText('Desde'), { target: { value: '2020-03-03' } })
    fireEvent.change(screen.getByLabelText('Hasta (no incluido)'), { target: { value: '2020-03-04' } })
    await usuario.click(screen.getByRole('button', { name: 'Métricas' }))
    await usuario.click(await screen.findByRole('menuitemcheckbox', { name: 'Importe medio' }))
    await usuario.keyboard('{Escape}')
    await usuario.click(screen.getByRole('button', { name: 'Consultar' }))

    expect(await screen.findByRole('img', { name: 'Viajes por barrio de origen' })).toBeInTheDocument()
    expect(enrutador.state.location.search).toBe('?nivel=dia_barrio&fuente=historico&desde=2020-03-03T00%3A00%3A00&hasta=2020-03-04T00%3A00%3A00&metricas=n_viajes%2Cimporte_medio')
    expect(cuerpoEnviado(espia)).toEqual({
      nivel: 'dia_barrio',
      fuente: 'historico',
      desde: '2020-03-03T00:00:00',
      hasta: '2020-03-04T00:00:00',
      metricas: ['n_viajes', 'importe_medio'],
    })
    const tabla = screen.getByRole('table', { name: /^Filas:/ })
    expect(within(tabla).getByText('203.866')).toBeInTheDocument()
    expect(within(tabla).getByText('16,96 $')).toBeInTheDocument()
    expect(within(tabla).getByText('78,1 %')).toBeInTheDocument()
    // Selector de métrica del gráfico, porque la respuesta trae varias.
    expect(screen.getByRole('combobox', { name: 'Métrica del gráfico' })).toBeInTheDocument()
  })

  it('guarda la consulta actual como vista y la vuelve a lanzar', async () => {
    localStorage.clear()
    const espia = simularApi({ ...BASE, 'POST /api/consultas': RESPUESTA_BARRIOS })
    renderizarRutas('/explorador')
    const usuario = userEvent.setup()

    await usuario.click(await screen.findByRole('button', { name: 'Guardar esta consulta' }))
    const nombre = screen.getByLabelText('Nombre de la vista')
    await usuario.clear(nombre)
    await usuario.type(nombre, 'Mi día de enero')
    await usuario.click(screen.getByRole('button', { name: 'Guardar' }))

    await usuario.click(screen.getByRole('button', { name: 'Mi día de enero' }))

    expect(await screen.findByRole('img', { name: 'Viajes por barrio de origen' })).toBeInTheDocument()
    expect(cuerpoEnviado(espia)).toMatchObject({ nivel: 'dia_barrio', desde: '2020-01-01T00:00:00', hasta: '2020-01-02T00:00:00' })

    await usuario.click(screen.getByRole('button', { name: 'Quitar Mi día de enero' }))
    expect(screen.queryByRole('button', { name: 'Mi día de enero' })).not.toBeInTheDocument()
    localStorage.clear()
  })

  it('los ejemplos rápidos rellenan y lanzan la consulta', async () => {
    const espia = simularApi({ ...BASE, 'POST /api/consultas': RESPUESTA_BARRIOS })
    renderizarRutas('/explorador')
    const usuario = userEvent.setup()

    await usuario.click(await screen.findByRole('button', { name: 'Barrios el 03/03' }))

    expect(await screen.findByRole('img', { name: 'Viajes por barrio de origen' })).toBeInTheDocument()
    expect(cuerpoEnviado(espia)).toMatchObject({ nivel: 'dia_barrio', desde: '2020-03-03T00:00:00', hasta: '2020-03-04T00:00:00' })
    expect(screen.getByLabelText('Desde')).toHaveValue('2020-03-03')
  })

  it('un 422 se muestra como error con el detalle y «Reintentar»', async () => {
    simularApi({
      ...BASE,
      'POST /api/consultas': { status: 422, json: { detail: [{ msg: 'Input should be a valid datetime', loc: ['body', 'desde'] }] } },
    })
    renderizarRutas(URL_ENMASCARADA)

    const alerta = await screen.findByRole('alert')
    expect(alerta).toHaveTextContent('No se ha podido ejecutar la consulta')
    expect(alerta).toHaveTextContent('Input should be a valid datetime')
    expect(within(alerta).getByRole('button', { name: 'Reintentar' })).toBeInTheDocument()
  })

  it('si el catálogo no está disponible, el formulario sigue funcionando con los valores por defecto', async () => {
    simularApi({ 'GET /api/sesion': { autenticado: true }, 'GET /api/zonas': ZONAS, 'POST /api/consultas': RESPUESTA_BARRIOS })
    renderizarRutas('/explorador')
    const usuario = userEvent.setup()

    expect(await screen.findByText(/El catálogo no está disponible/)).toBeInTheDocument()
    expect(screen.getByRole('combobox', { name: 'Nivel de agregación' })).toHaveTextContent('Día y barrio')
    expect(screen.getByRole('button', { name: 'Consultar' })).toBeEnabled()
    await usuario.click(screen.getByRole('combobox', { name: 'Nivel de agregación' }))
    expect(await screen.findByRole('option', { name: 'Flujos entre barrios por día' })).toBeInTheDocument()
  })
})
