import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'

import type { TiempoReal } from '@/api/tipos'
import { renderizarRutas, simularApi } from '@/pruebas/utilidades'

const TIEMPO_REAL: TiempoReal = {
  acceso_disponible: true,
  frescura: { instante: '2026-09-21T10:15:00+00:00', segundos: 45 },
  ultimo_dia: '2020-12-30T00:00:00',
  por_hora: [
    { hora: '2020-12-30T18:00:00', n_viajes: 120, grupos: 5, grupos_enmascarados: 2 },
    { hora: '2020-12-30T19:00:00', n_viajes: 98, grupos: 4, grupos_enmascarados: 0 },
    { hora: '2020-12-30T20:00:00', n_viajes: 15, grupos: 1, grupos_enmascarados: 3 },
  ],
  por_zona_ultima_hora: [
    { hora: '2020-12-30T20:00:00', zona_origen: 265, zona_origen_nombre: 'Outside of NYC', barrio_origen: 'N/A', n_viajes: 15, suprimido: false },
    { hora: '2020-12-30T20:00:00', zona_origen: 4, zona_origen_nombre: 'Alphabet City', barrio_origen: 'Manhattan', n_viajes: 'oculto', suprimido: true },
    { hora: '2020-12-30T20:00:00', zona_origen: 7, zona_origen_nombre: 'Astoria', barrio_origen: 'Queens', n_viajes: 'oculto', suprimido: true },
    { hora: '2020-12-30T20:00:00', zona_origen: 12, zona_origen_nombre: 'Battery Park', barrio_origen: 'Manhattan', n_viajes: 'oculto', suprimido: true },
  ],
}

function conSesion(manejador: unknown) {
  return simularApi({ 'GET /api/sesion': { autenticado: true }, 'GET /api/tiempo-real': manejador })
}

describe('PaginaTiempoReal', () => {
  it('muestra la frescura con semáforo y «hace X s», el último día y la última hora', async () => {
    conSesion(TIEMPO_REAL)
    renderizarRutas('/tiempo-real')

    const indicadores = await screen.findByRole('region', { name: 'Indicadores' })
    expect(within(indicadores).getByText(/^hace 4[5-7] s$/)).toBeInTheDocument()
    expect(within(indicadores).getByRole('img', { name: 'Estado: al día' })).toBeInTheDocument()
    expect(within(indicadores).getByText('al día')).toBeInTheDocument()
    expect(within(indicadores).getByText('30/12/2020')).toBeInTheDocument()
    expect(within(indicadores).getByText('15')).toBeInTheDocument()
    expect(within(indicadores).getByText('20:00')).toBeInTheDocument()
    expect(screen.queryByRole('note')).not.toBeInTheDocument()
    expect(screen.queryByText(/datos simulados/i)).not.toBeInTheDocument()
  })

  it('pinta las barras por hora y la tabla de la última hora con los enmascarados marcados', async () => {
    conSesion(TIEMPO_REAL)
    renderizarRutas('/tiempo-real')

    const grafico = await screen.findByRole('img', { name: 'Viajes por hora, últimas 6 horas con datos' })
    expect(grafico.querySelectorAll('.recharts-bar-rectangle')).toHaveLength(3)
    expect(grafico).toHaveTextContent('18:00')

    const tabla = screen.getByRole('table', { name: 'Última hora por zona' })
    const [, cuerpo, pie] = within(tabla).getAllByRole('rowgroup')
    const filas = within(cuerpo).getAllByRole('row')
    expect(filas).toHaveLength(4)
    // Ordenada por viajes de mayor a menor: la visible primero, los enmascarados después.
    expect(filas[0]).toHaveTextContent('Outside of NYC')
    expect(within(cuerpo).getAllByText('enmascarado por privacidad')).toHaveLength(3)
    expect(within(cuerpo).getAllByText('oculto')).toHaveLength(3)
    expect(pie).toHaveTextContent('3 enmascarados no incluidos')
    expect(within(pie).getByText('15')).toBeInTheDocument()
  })

  it('el selector 6/12/24 pide las horas elegidas al BFF', async () => {
    const espia = conSesion((_init: RequestInit, url: URL) => ({ ...TIEMPO_REAL, por_hora: TIEMPO_REAL.por_hora.slice(0, url.searchParams.get('horas') === '6' ? 3 : 2) }))
    renderizarRutas('/tiempo-real')
    const usuario = userEvent.setup()

    await screen.findByRole('img', { name: 'Viajes por hora, últimas 6 horas con datos' })
    await usuario.click(screen.getByRole('tab', { name: '24 h' }))

    expect(await screen.findByRole('img', { name: 'Viajes por hora, últimas 24 horas con datos' })).toBeInTheDocument()
    const urls = espia.mock.calls.map(([entrada]) => String(entrada))
    expect(urls).toContain('/api/tiempo-real?horas=6')
    expect(urls).toContain('/api/tiempo-real?horas=24')
  })

  it('con la frescura vieja o sin dato, el semáforo se pone en rojo', async () => {
    conSesion({ ...TIEMPO_REAL, frescura: { instante: null, segundos: null } })
    renderizarRutas('/tiempo-real')

    const indicadores = await screen.findByRole('region', { name: 'Indicadores' })
    expect(within(indicadores).getByText('Sin dato')).toBeInTheDocument()
    expect(within(indicadores).getByRole('img', { name: 'Estado: sin datos recientes' })).toBeInTheDocument()
  })

  it('sin agregados de tiempo real, ofrece ir a Operaciones', async () => {
    conSesion({ frescura: { instante: null, segundos: null }, ultimo_dia: null, por_hora: [], por_zona_ultima_hora: [] })
    renderizarRutas('/tiempo-real')

    expect(await screen.findByText('Sin datos de tiempo real')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Ir a Operaciones' })).toHaveAttribute('href', '/operaciones')
  })

  it('con el simulador en marcha, el indicador «En vivo» lo dice; la frescura reciente cuenta como Spark publicando', async () => {
    simularApi({
      'GET /api/sesion': { autenticado: true },
      'GET /api/tiempo-real': TIEMPO_REAL,
      'GET /api/panel': { servicios: [], enlaces: {}, frescura_tiempo_real: { instante: null, segundos: 45 } },
      'GET /api/operaciones/simulacion': {
        activa: true, lote: 'portal-muestra', fichero: 'yellow_tripdata_2020_muestra.csv', enviados: 450, total: 999,
        ritmo: 50, inicio: '2026-09-22T09:59:50+00:00', fin: null, error: null,
      },
    })
    renderizarRutas('/tiempo-real')

    const estado = await screen.findByRole('status', { name: 'Actividad de la plataforma' })
    await waitFor(() => expect(estado).toHaveTextContent('2 procesos en marcha'))
    expect(screen.queryByText(/Nueva hora/)).not.toBeInTheDocument()       // la primera respuesta no es una hora nueva
    expect(screen.getByRole('img', { name: 'Viajes por hora, últimas 6 horas con datos' }).querySelectorAll('.recharts-bar-rectangle')).toHaveLength(3)
  })

  it('si el BFF falla, muestra el error con «Reintentar»', async () => {
    conSesion({ status: 503, json: { detail: 'La API de acceso no responde' } })
    renderizarRutas('/tiempo-real')

    const alerta = await screen.findByRole('alert')
    expect(alerta).toHaveTextContent('No se ha podido cargar el tiempo real')
    expect(alerta).toHaveTextContent('La API de acceso no responde')
    await waitFor(() => expect(within(alerta).getByRole('button', { name: 'Reintentar' })).toBeEnabled())
  })
})
