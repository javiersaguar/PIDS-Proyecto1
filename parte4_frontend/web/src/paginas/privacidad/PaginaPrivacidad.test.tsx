import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'

import type { AuditoriaResumen, Carga, Catalogo, DecisionAuditada } from '@/api/tipos'
import { renderizarRutas, simularApi } from '@/pruebas/utilidades'

const CATALOGO: Catalogo = {
  k_minimo: 10,
  max_dias_por_consulta: 31,
  metricas: ['n_viajes', 'distancia_media', 'importe_medio', 'propina_media', 'pct_pago_tarjeta'],
  niveles: {
    hora_zona: { descripcion: 'Viajes por hora y zona de origen. Sin destino.', dimensiones: ['hora', 'zona_origen'] },
    dia_barrio: { descripcion: 'Viajes por día y barrio (borough) de origen.', dimensiones: ['dia', 'barrio_origen'] },
    od_dia_barrio: { descripcion: 'Flujos entre barrios por día.', dimensiones: ['dia', 'barrio_origen', 'barrio_destino'] },
  },
  fuentes: ['historico', 'tiempo_real'],
  barrios: ['Bronx', 'Brooklyn', 'Manhattan', 'Queens', 'Staten Island'],
}

const RESUMEN: AuditoriaResumen = {
  desde: '2026-09-21T08:00:00Z',
  hasta: '2026-09-22T08:00:00Z',
  total: 1234,
  resultados: { permitida: 1000, enmascarada: 200, rechazada: 34 },
  clientes: { chatbot: 900, frontend: 300, equipo: 34 },
  motivos: [
    { motivo: 'petición de datos individuales', cantidad: 20 },
    { motivo: 'ventana demasiado corta', cantidad: 14 },
  ],
  disponible: true,
}

const DECISIONES: DecisionAuditada[] = [
  {
    instante: '2026-09-22T07:59:00Z',
    cliente: 'chatbot',
    componente: 'acceso',
    resultado: 'rechazada',
    motivos: ['petición de datos individuales: Dame el viaje de las 3:12', 'la plataforma solo publica agregados de al menos 10 viajes'],
    consulta: { texto: 'Dame el viaje de las 3:12 desde Times Square' },
    alternativa: { nivel: 'hora_zona', desde: '2020-01-15T03:00:00', hasta: '2020-01-15T04:00:00', zona_origen: 230 },
  },
  {
    instante: '2026-09-22T07:58:00Z',
    cliente: 'frontend',
    componente: 'acceso',
    resultado: 'permitida',
    motivos: [],
    consulta: { nivel: 'dia_barrio', desde: '2020-03-03T00:00:00', hasta: '2020-03-04T00:00:00' },
    alternativa: null,
    filas_devueltas: 5,
    grupos_enmascarados: 0,
  },
]

const CARGAS: Carga[] = [
  {
    lote: 'yellow_tripdata_2020-01',
    entrada: 's3a://crudo/historico/yellow_tripdata_2020-01.parquet',
    origen: 'historico',
    filas: 6405008,
    validos: 6339567,
    rechazados: 65441,
    motivos: { 'distancia fuera de rango': 60000, 'zona desconocida': 5441 },
    grupos_publicados: { hora_zona: 120000, dia_barrio: 186, od_dia_barrio: 900 },
    grupos_suprimidos: { hora_zona: 45000, dia_barrio: 12, od_dia_barrio: 300 },
    grupos_complementarios: { hora_zona: 3, dia_barrio: 4, od_dia_barrio: 50 },
    version_reglas: 1,
    instante: '2026-09-20T10:00:00Z',
  },
]

function apiBase(extra: Record<string, unknown> = {}) {
  return simularApi({
    'GET /api/sesion': { autenticado: true },
    'GET /api/catalogo': CATALOGO,
    'GET /api/auditoria/resumen': RESUMEN,
    'GET /api/auditoria/decisiones': (_init: RequestInit, url: URL) =>
      url.searchParams.get('resultado') ? DECISIONES.filter((d) => d.resultado === url.searchParams.get('resultado')) : DECISIONES,
    'GET /api/auditoria/cargas': CARGAS,
    ...extra,
  } as Parameters<typeof simularApi>[0])
}

describe('PaginaPrivacidad', () => {
  it('«Reglas E3» explica las reglas en texto, con las cifras del catálogo', async () => {
    apiBase()
    renderizarRutas('/privacidad')

    expect(await screen.findByRole('heading', { name: 'Qué se publica' })).toBeInTheDocument()
    expect(screen.getByText(/como máximo 31 días/)).toBeInTheDocument()
    expect(screen.getByText(/menos de 10 viajes/)).toBeInTheDocument()
    expect(screen.getByText(/por hora y zona de origen/)).toBeInTheDocument()
    expect(screen.getByText(/la propina media/)).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Por qué no basta con ocultarla' })).toBeInTheDocument()
    expect(screen.getByText(/supresión complementaria/)).toBeInTheDocument()
    expect(screen.getByText(/una hora completa/)).toBeInTheDocument()
    expect(screen.queryByText('Staten Island')).not.toBeInTheDocument()
    expect(screen.queryByText(/Las reglas del escenario/)).not.toBeInTheDocument()
    expect(screen.getByRole('heading', { level: 1, name: 'Privacidad' })).toHaveClass('sr-only')
  })

  it('si el catálogo falla, muestra el error con «Reintentar» y mantiene la explicación', async () => {
    apiBase({ 'GET /api/catalogo': { status: 502, json: { detail: 'La API de acceso no responde' } } })
    renderizarRutas('/privacidad')

    const alerta = await screen.findByRole('alert')
    expect(alerta).toHaveTextContent('La API de acceso no responde')
    expect(within(alerta).getByRole('button', { name: 'Reintentar' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Por qué no basta con ocultarla' })).toBeInTheDocument()
  })

  it('«Auditoría» muestra el resumen, las barras y la tabla; el filtro por resultado se envía al BFF', async () => {
    const espia = apiBase()
    renderizarRutas('/privacidad?pestana=auditoria')
    const usuario = userEvent.setup()

    const kpis = await screen.findByRole('group', { name: 'Resumen por resultado' })
    expect(within(kpis).getByText('1234')).toBeInTheDocument()
    expect(within(kpis).getByText('1000')).toBeInTheDocument()
    expect(within(kpis).getByText('34')).toBeInTheDocument()
    expect(within(kpis).getByText('3 % del total')).toBeInTheDocument()
    const clientes = screen.getByRole('list', { name: 'Decisiones por cliente' })
    expect(within(clientes).getAllByRole('listitem').map((li) => li.textContent)).toEqual(['Chatbot900', 'Este portal300', 'El equipo34'])
    const motivos = screen.getByRole('list', { name: 'Motivos de rechazo más frecuentes' })
    expect(within(motivos).getByText('Pedía datos de un viaje concreto, y eso no se publica.')).toBeInTheDocument()

    // La tabla con las dos decisiones, y la fila del rechazo se expande con la consulta, los motivos y la alternativa.
    const tabla = await screen.findByRole('table')
    expect(within(tabla).getAllByRole('row')).toHaveLength(3)
    expect(within(tabla).getByText('Chatbot')).toBeInTheDocument()
    await usuario.click(within(tabla).getAllByRole('button', { name: 'Ver el detalle' })[0])
    expect(within(tabla).getByText('En su lugar')).toBeInTheDocument()
    expect(within(tabla).getByText(/zona de origen 230/)).toBeInTheDocument()
    expect(within(tabla).getAllByText(/Pedía datos de un viaje concreto/).length).toBeGreaterThan(0)
    expect(within(tabla).getByText('la plataforma solo publica agregados de al menos 10 viajes')).toBeInTheDocument()

    // Filtro por resultado: la petición al BFF lleva `resultado=rechazada` y la tabla se queda con una fila.
    await usuario.click(within(screen.getByRole('radiogroup', { name: 'Resultado' })).getByRole('radio', { name: 'Rechazadas' }))
    await waitFor(() => {
      const urls = espia.mock.calls.map(([url]) => String(url))
      expect(urls.some((u) => u.includes('/api/auditoria/decisiones') && u.includes('resultado=rechazada') && u.includes('horas=24'))).toBe(true)
    })
    await waitFor(() => expect(within(screen.getByRole('table')).getAllByRole('row')).toHaveLength(2))
    expect(within(screen.getByRole('table')).queryByText('frontend')).not.toBeInTheDocument()

    // Cambiar el periodo vuelve a pedir el resumen con otras horas.
    await usuario.click(within(screen.getByRole('radiogroup', { name: 'Periodo' })).getByRole('radio', { name: '7 días' }))
    await waitFor(() => {
      const urls = espia.mock.calls.map(([url]) => String(url))
      expect(urls.some((u) => u.includes('/api/auditoria/resumen?horas=168'))).toBe(true)
    })
  })

  it('con MongoDB caído (disponible: false) la auditoría dice «MongoDB no disponible» y no pide decisiones', async () => {
    const espia = apiBase({ 'GET /api/auditoria/resumen': { ...RESUMEN, total: 0, resultados: {}, clientes: {}, motivos: [], disponible: false } })
    renderizarRutas('/privacidad?pestana=auditoria')

    expect(await screen.findByText('MongoDB no disponible')).toBeInTheDocument()
    expect(screen.queryByRole('table')).not.toBeInTheDocument()
    expect(espia.mock.calls.some(([url]) => String(url).includes('/api/auditoria/decisiones'))).toBe(false)
  })

  it('«Cargas» lista cada carga con leídos, válidos, rechazados y los grupos por nivel', async () => {
    apiBase()
    renderizarRutas('/privacidad')
    const usuario = userEvent.setup()

    await usuario.click(await screen.findByRole('tab', { name: 'Cargas' }))

    const tabla = await screen.findByRole('table')
    expect(within(tabla).getByText('yellow_tripdata_2020-01')).toBeInTheDocument()
    expect(within(tabla).getByText('6.405.008')).toBeInTheDocument()
    expect(within(tabla).getByText('6.339.567')).toBeInTheDocument()
    expect(within(tabla).getByText('65.441')).toBeInTheDocument()
    expect(within(tabla).getByText('120.000')).toBeInTheDocument()
    expect(within(tabla).getByText('45.000')).toBeInTheDocument()
    expect(within(tabla).getByText('50')).toBeInTheDocument()
    expect(within(tabla).getAllByText('publicados').length).toBeGreaterThan(0)
    expect(within(tabla).getAllByText('sin cifra').length).toBeGreaterThan(0)
    expect(within(tabla).getAllByRole('columnheader').map((c) => c.textContent)).toEqual(
      expect.arrayContaining([expect.stringContaining('Por hora y zona'), expect.stringContaining('Entre barrios')]),
    )

    await usuario.click(within(tabla).getByRole('button', { name: 'Ver el detalle' }))
    expect(within(tabla).getByText('distancia fuera de rango')).toBeInTheDocument()
    expect(within(tabla).getByText('s3a://crudo/historico/yellow_tripdata_2020-01.parquet')).toBeInTheDocument()
  })

  it('sin cargas muestra el estado vacío', async () => {
    apiBase({ 'GET /api/auditoria/cargas': [] })
    renderizarRutas('/privacidad?pestana=cargas')
    expect(await screen.findByText('Todavía no hay cargas')).toBeInTheDocument()
  })
})
