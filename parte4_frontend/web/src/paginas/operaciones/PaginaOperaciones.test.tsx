import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { toast } from 'sonner'
import { describe, expect, it, vi } from 'vitest'

import type { EjecucionAirflow, Simulacion } from '@/api/tipos'
import { renderizarRutas, simularApi } from '@/pruebas/utilidades'

vi.mock('sonner', () => ({
  toast: { success: vi.fn(), error: vi.fn(), info: vi.fn(), warning: vi.fn() },
}))

const EJECUCIONES: EjecucionAirflow[] = [
  {
    dag_run_id: 'manual__2026-09-21T10:00:00+00:00',
    estado: 'success',
    conf: { mes: '2020-03', muestra: false },
    inicio: '2026-09-21T10:00:00Z',
    fin: '2026-09-21T10:07:30Z',
  },
  { dag_run_id: 'manual__2026-09-22T08:00:00+00:00', estado: 'running', conf: { mes: '2020-01', muestra: true }, inicio: '2026-09-22T08:00:00Z', fin: null },
  { dag_run_id: 'manual__2026-09-20T09:00:00+00:00', estado: 'failed', conf: { mes: '2020-02', muestra: false }, inicio: '2026-09-20T09:00:00Z', fin: '2026-09-20T09:01:00Z' },
]

const SIMULACION_PARADA: Simulacion = {
  activa: false,
  lote: null,
  fichero: null,
  enviados: 0,
  total: 0,
  ritmo: 50,
  inicio: null, fin: null,
  error: null,
}

const SIMULACION_ACTIVA: Simulacion = {
  activa: true,
  lote: 'portal-yellow_tripdata_2020_muestra.csv-20260922T080000',
  fichero: 'yellow_tripdata_2020_muestra.csv',
  enviados: 250,
  total: 999,
  ritmo: 50,
  inicio: '2026-09-22T08:00:00Z', fin: null,
  error: null,
}

const FICHEROS = ['yellow_tripdata_2020_muestra.csv', 'exportacion_formato_europeo.csv']

function apiBase(extra: Record<string, unknown> = {}) {
  return simularApi({
    'GET /api/sesion': { autenticado: true },
    'GET /api/panel': { enlaces: { airflow: 'http://localhost:8085' }, servicios: [] },
    'GET /api/operaciones/airflow/ejecuciones': EJECUCIONES,
    'GET /api/operaciones/simulacion': SIMULACION_PARADA,
    'GET /api/operaciones/simulacion/ficheros': FICHEROS,
    ...extra,
  } as Parameters<typeof simularApi>[0])
}

function llamadas(espia: ReturnType<typeof simularApi>, metodo: string, sufijo: string) {
  return espia.mock.calls.filter(([url, init]) => String(url).endsWith(sufijo) && (init?.method ?? 'GET') === metodo)
}

describe('PaginaOperaciones', () => {
  it('lista las ejecuciones de Airflow con su chip de estado y el enlace a Airflow', async () => {
    apiBase()
    renderizarRutas('/operaciones')

    const tabla = await screen.findByRole('table')
    expect(within(tabla).getByText('correcta')).toBeInTheDocument()
    expect(within(tabla).getByText('en ejecución')).toBeInTheDocument()
    expect(within(tabla).getByText('fallida')).toBeInTheDocument()
    expect(within(tabla).getByText('marzo de 2020')).toBeInTheDocument()
    expect(within(tabla).getByText('Muestra de prueba, enero de 2020')).toBeInTheDocument()
    expect(within(tabla).getByText('7 min 30 s')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Abrir Airflow' })).toHaveAttribute('href', 'http://localhost:8085')
  })

  it('lanza la carga solo tras confirmar en el diálogo y avisa de que ha empezado', async () => {
    const espia = apiBase({
      'POST /api/operaciones/airflow/cargas': { status: 202, json: { ...EJECUCIONES[1], dag_run_id: 'manual__nueva', estado: 'queued' } },
    })
    renderizarRutas('/operaciones')
    const usuario = userEvent.setup()

    await usuario.click(await screen.findByRole('button', { name: 'Cargar viajes' }))

    const dialogo = await screen.findByRole('dialog')
    expect(dialogo).toHaveTextContent('90 MB')
    expect(dialogo).toHaveTextContent('varios minutos')
    expect(llamadas(espia, 'POST', '/api/operaciones/airflow/cargas')).toHaveLength(0)

    await usuario.click(within(dialogo).getByRole('button', { name: 'Sí, cargar' }))

    await waitFor(() => expect(llamadas(espia, 'POST', '/api/operaciones/airflow/cargas')).toHaveLength(1))
    const [, init] = llamadas(espia, 'POST', '/api/operaciones/airflow/cargas')[0]
    expect(JSON.parse(init?.body as string)).toEqual({ mes: '2020-01', muestra: false })
    await waitFor(() => expect(toast.success).toHaveBeenCalledWith('La carga ya ha empezado', { description: 'Se está cargando enero de 2020.' }))
    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument())
  })

  it('«Cancelar» cierra el diálogo sin lanzar nada; con «solo la muestra» el cuerpo lleva muestra: true', async () => {
    const espia = apiBase({ 'POST /api/operaciones/airflow/cargas': { status: 202, json: EJECUCIONES[1] } })
    renderizarRutas('/operaciones')
    const usuario = userEvent.setup()

    await usuario.click(await screen.findByRole('button', { name: 'Cargar viajes' }))
    await usuario.click(within(await screen.findByRole('dialog')).getByRole('button', { name: 'Cancelar' }))
    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument())
    expect(llamadas(espia, 'POST', '/api/operaciones/airflow/cargas')).toHaveLength(0)

    await usuario.click(screen.getByRole('switch', { name: /999 viajes de prueba/ }))
    await usuario.click(screen.getByRole('button', { name: 'Cargar viajes' }))
    const dialogo = await screen.findByRole('dialog')
    expect(dialogo).toHaveTextContent('999 viajes')
    await usuario.click(within(dialogo).getByRole('button', { name: 'Sí, cargar' }))
    await waitFor(() => expect(llamadas(espia, 'POST', '/api/operaciones/airflow/cargas')).toHaveLength(1))
    expect(JSON.parse(llamadas(espia, 'POST', '/api/operaciones/airflow/cargas')[0][1]?.body as string)).toEqual({ mes: '2020-01', muestra: true })
  })

  it('si Airflow rechaza la carga, el error llega como toast y el diálogo sigue abierto', async () => {
    apiBase({ 'POST /api/operaciones/airflow/cargas': { status: 502, json: { detail: 'Airflow no responde' } } })
    renderizarRutas('/operaciones')
    const usuario = userEvent.setup()

    await usuario.click(await screen.findByRole('button', { name: 'Cargar viajes' }))
    await usuario.click(within(await screen.findByRole('dialog')).getByRole('button', { name: 'Sí, cargar' }))

    await waitFor(() => expect(toast.error).toHaveBeenCalledWith('No se ha podido empezar la carga', { description: 'Airflow no responde' }))
    expect(screen.getByRole('dialog')).toBeInTheDocument()
  })

  it('con una simulación activa muestra el progreso y «Parar» llama a DELETE', async () => {
    const espia = apiBase({
      'GET /api/operaciones/simulacion': SIMULACION_ACTIVA,
      'DELETE /api/operaciones/simulacion': { ...SIMULACION_ACTIVA, activa: false },
    })
    renderizarRutas('/operaciones')
    const usuario = userEvent.setup()

    expect(await screen.findByText('Simulación en marcha')).toBeInTheDocument()
    expect(screen.getByText('250 / 999 viajes enviados (25 %)')).toBeInTheDocument()
    expect(screen.getByRole('progressbar', { name: 'Viajes enviados' })).toHaveAttribute('aria-valuenow', '25')
    expect(screen.getByText('portal-yellow_tripdata_2020_muestra.csv-20260922T080000')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Empezar' })).not.toBeInTheDocument()

    await usuario.click(screen.getByRole('button', { name: 'Parar' }))
    await waitFor(() => expect(llamadas(espia, 'DELETE', '/api/operaciones/simulacion')).toHaveLength(1))
    await waitFor(() => expect(toast.success).toHaveBeenCalledWith('Simulación parada'))
  })

  it('«Empezar» envía fichero, ritmo y máximo; un 409 avisa de que ya hay una simulación activa', async () => {
    const espia = apiBase({
      'POST /api/operaciones/simulacion': { status: 409, json: { detail: 'Ya hay una simulación en curso' } },
    })
    renderizarRutas('/operaciones')
    const usuario = userEvent.setup()

    const boton = await screen.findByRole('button', { name: 'Empezar' })
    await waitFor(() => expect(boton).toBeEnabled())
    await usuario.clear(screen.getByLabelText('Cuántos por segundo'))
    await usuario.type(screen.getByLabelText('Cuántos por segundo'), '20')
    await usuario.type(screen.getByLabelText(/Máximo de viajes/), '300')
    await usuario.click(boton)

    await waitFor(() => expect(llamadas(espia, 'POST', '/api/operaciones/simulacion')).toHaveLength(1))
    expect(JSON.parse(llamadas(espia, 'POST', '/api/operaciones/simulacion')[0][1]?.body as string)).toEqual({
      fichero: 'yellow_tripdata_2020_muestra.csv',
      ritmo: 20,
      maximo: 300,
    })
    await waitFor(() => expect(toast.error).toHaveBeenCalledWith('Ya hay una simulación activa', expect.anything()))
  })

  it('muestra el error del simulador y los estados de error de Airflow con «Reintentar»', async () => {
    apiBase({
      'GET /api/operaciones/simulacion': { ...SIMULACION_PARADA, error: 'La API de captura ha devuelto 401' },
      'GET /api/operaciones/airflow/ejecuciones': { status: 503, json: { detail: 'Airflow no disponible' } },
    })
    renderizarRutas('/operaciones')

    expect(await screen.findByText(/La API de captura ha devuelto 401/)).toBeInTheDocument()
    const alertas = await screen.findAllByRole('alert')
    const alertaAirflow = alertas.find((a) => a.textContent?.includes('Airflow no disponible'))
    expect(alertaAirflow).toBeDefined()
    expect(within(alertaAirflow!).getByRole('button', { name: 'Reintentar' })).toBeInTheDocument()
  })
})
