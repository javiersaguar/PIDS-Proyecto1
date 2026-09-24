import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'

import { renderizarRutas, simularApi } from '@/pruebas/utilidades'

describe('PaginaDocumentacion', () => {
  it('pinta el lienzo y, al pulsar una pieza, explica qué es y abre el enlace del panel', async () => {
    simularApi({
      'GET /api/sesion': { autenticado: true },
      'GET /api/panel': { servicios: [], enlaces: { grafana: 'http://grafana.local:3000', airflow: 'http://airflow.local:8085' } },
    })
    renderizarRutas('/grafo')
    const usuario = userEvent.setup()

    const lienzo = await screen.findByRole('region', { name: 'Arquitectura de la plataforma' })
    expect(within(lienzo).getByRole('button', { name: /Redpanda/ })).toBeInTheDocument()
    expect(within(lienzo).getByRole('button', { name: /API de acceso/ })).toBeInTheDocument()
    expect(within(lienzo).getByRole('button', { name: /Spark/ })).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'La plataforma y el escenario E3' })).not.toBeInTheDocument()

    await usuario.click(within(lienzo).getByRole('button', { name: /Redpanda/ }))
    const ficha = await screen.findByRole('dialog')
    expect(within(ficha).getByRole('heading', { name: 'Redpanda' })).toBeInTheDocument()
    expect(within(ficha).getByText('Qué es')).toBeInTheDocument()
    expect(within(ficha).getByText('Qué hace')).toBeInTheDocument()
    expect(within(ficha).getByText('Cómo se conecta aquí')).toBeInTheDocument()
    expect(within(ficha).getByText(/sala de espera|cola de lo que acaba de llegar/i)).toBeInTheDocument()

    await usuario.click(within(ficha).getByRole('button', { name: 'Cerrar' }))
    await usuario.click(within(lienzo).getByRole('button', { name: /Grafana/ }))
    await waitFor(() => expect(screen.getByRole('link', { name: 'Abrir Grafana' })).toHaveAttribute('href', 'http://grafana.local:3000'))

    await usuario.click(screen.getByRole('button', { name: 'Cerrar' }))
    await usuario.click(within(lienzo).getByRole('button', { name: /Airflow/ }))
    expect(await screen.findByRole('link', { name: 'Abrir Airflow' })).toHaveAttribute('href', 'http://airflow.local:8085')
  })

  it('con una carga y una simulación en marcha, la barra lo cuenta y el lienzo ilumina sus tramos', async () => {
    simularApi({
      'GET /api/sesion': { autenticado: true },
      'GET /api/panel': { servicios: [], enlaces: {}, frescura_tiempo_real: { instante: null, segundos: 900 } },
      'GET /api/operaciones/airflow/ejecuciones': [
        { dag_run_id: 'manual__2', estado: 'running', conf: { mes: '2020-03', muestra: false }, inicio: '2026-09-22T09:58:00+00:00', fin: null },
        { dag_run_id: 'manual__1', estado: 'success', conf: { mes: '2020-02', muestra: false }, inicio: '2026-09-22T09:40:00+00:00', fin: '2026-09-22T09:42:00+00:00' },
      ],
      'GET /api/operaciones/simulacion': {
        activa: true, lote: 'portal-muestra', fichero: 'yellow_tripdata_2020_muestra.csv', enviados: 450, total: 999,
        ritmo: 50, inicio: '2026-09-22T09:59:50+00:00', fin: null, error: null,
      },
    })
    renderizarRutas('/grafo')

    const barra = await screen.findByRole('status', { name: 'Actividad de la plataforma' })
    await waitFor(() => expect(barra).toHaveTextContent('En marcha ahora'))
    expect(barra).toHaveTextContent(/Carga histórica de marzo de 2020 en ejecución/)
    expect(barra).toHaveTextContent('Simulación en marcha: 450 de 999 viajes · 50 viajes/s')
    expect(barra).not.toHaveTextContent('Spark publicó')          // la frescura de 900 s no cuenta como publicando

    const lienzo = screen.getByRole('region', { name: 'Arquitectura de la plataforma' })
    const activas = [...lienzo.querySelectorAll('[data-activa="true"]')].map((g) => g.getAttribute('data-arista')).sort()
    expect(activas).toEqual(['airflow-s3', 'captura-redpanda', 'redpanda-spark', 's3-spark', 'simulador-captura', 'spark-mongo'])
    expect(lienzo.querySelectorAll('.arista-flujo')).toHaveLength(6)
    expect(lienzo.querySelectorAll('animateMotion').length).toBeGreaterThan(0)
    expect(within(lienzo).getByRole('button', { name: /Airflow/ })).toHaveTextContent('Cargando marzo de 2020')
    expect(within(lienzo).getByRole('button', { name: /Simulador/ })).toHaveTextContent('450 de 999 viajes')
    expect(within(lienzo).getByRole('button', { name: /Grafana/ })).not.toHaveAttribute('data-activo')
  })

  it('sin nada en marcha, la barra dice la última carga y de dónde se lanza algo', async () => {
    simularApi({
      'GET /api/sesion': { autenticado: true },
      'GET /api/panel': { servicios: [], enlaces: {}, frescura_tiempo_real: { instante: null, segundos: null } },
      'GET /api/operaciones/airflow/ejecuciones': [
        { dag_run_id: 'manual__1', estado: 'success', conf: { mes: '2020-02', muestra: true }, inicio: '2026-09-22T09:40:00+00:00', fin: '2026-09-22T09:42:00+00:00' },
      ],
      'GET /api/operaciones/simulacion': { activa: false, lote: null, fichero: null, enviados: 0, total: 0, ritmo: 50, inicio: null, fin: null, error: null },
    })
    renderizarRutas('/grafo')

    const barra = await screen.findByRole('status', { name: 'Actividad de la plataforma' })
    expect(barra).toHaveTextContent('Sin procesos en marcha')
    await waitFor(() => expect(barra).toHaveTextContent(/Última carga: la muestra de prueba \(febrero de 2020\), correcta/))
    expect(within(barra).getByRole('link', { name: 'Lanzar una carga o el simulador' })).toHaveAttribute('href', '/operaciones')
    const lienzo = screen.getByRole('region', { name: 'Arquitectura de la plataforma' })
    expect(lienzo.querySelectorAll('[data-activa="true"]')).toHaveLength(0)
  })

  it('sin /api/panel usa los enlaces por defecto', async () => {
    simularApi({ 'GET /api/sesion': { autenticado: true } })
    renderizarRutas('/grafo')
    const usuario = userEvent.setup()

    const lienzo = await screen.findByRole('region', { name: 'Arquitectura de la plataforma' })
    await usuario.click(within(lienzo).getByRole('button', { name: /Spark/ }))
    const fichaSpark = await screen.findByRole('dialog')
    expect(within(fichaSpark).getByRole('heading', { name: 'Spark' })).toBeInTheDocument()
    // sin login: el enlace existe, pero solo responde con `make ver`, y lo dice
    expect(within(fichaSpark).getByRole('link', { name: 'Abrir Spark (make ver)' })).toHaveAttribute('href', 'http://localhost:8090')

    await usuario.click(screen.getByRole('button', { name: 'Cerrar' }))
    await usuario.click(within(lienzo).getByRole('button', { name: /API de acceso/ }))
    expect(await screen.findByRole('link', { name: 'Abrir la API de acceso' })).toHaveAttribute('href', 'http://localhost:8002/docs')

    await usuario.click(screen.getByRole('button', { name: 'Cerrar' }))
    await usuario.click(within(lienzo).getByRole('button', { name: /Chatbots/ }))
    expect(await screen.findByRole('link', { name: 'Abrir con Ollama' })).toHaveAttribute('href', 'http://localhost:8010')
    expect(screen.getByRole('link', { name: 'Abrir con Mistral' })).toHaveAttribute('href', 'http://localhost:8011')

    await usuario.click(screen.getByRole('button', { name: 'Cerrar' }))
    await usuario.click(within(lienzo).getByRole('button', { name: /^Mistral/ }))
    const fichaHelmcode = await screen.findByRole('dialog')
    expect(within(fichaHelmcode).getByRole('heading', { name: 'Mistral' })).toBeInTheDocument()
    expect(within(fichaHelmcode).getByText(/Ministral/)).toBeInTheDocument()
  })

  it('«Capturar datos» arranca la captura en directo, el lienzo ilumina su camino y la para al apagarlo', async () => {
    const parada = { activa: false, lote: null, fichero: null, enviados: 0, total: 0, ritmo: 50, inicio: null, fin: null, error: null }
    const enMarcha = {
      activa: true, lote: 'directo-20260922120000', fichero: null, enviados: 12345, total: 0, ritmo: 41.6,
      inicio: '2026-09-22T10:00:00+00:00', fin: null, error: null, modo: 'directo', reloj: '2020-12-01T14:35:00', velocidad: 60,
    }
    let estado: Record<string, unknown> = parada
    const espia = simularApi({
      'GET /api/sesion': { autenticado: true },
      'GET /api/panel': { servicios: [], enlaces: {}, frescura_tiempo_real: { instante: null, segundos: null } },
      'GET /api/operaciones/airflow/ejecuciones': [],
      'GET /api/operaciones/simulacion': () => estado,
      'GET /api/operaciones/captura': {
        disponible: true, primer_dia: '2020-12-01', ultimo_dia: '2020-12-31', reloj: null,
        velocidad_por_defecto: 60, velocidad_maxima: 600,
      },
      'POST /api/operaciones/captura': () => {
        estado = enMarcha
        return { status: 202, json: enMarcha }
      },
      'DELETE /api/operaciones/captura': () => {
        estado = { ...enMarcha, activa: false, fin: '2026-09-22T10:05:00+00:00' }
        return estado
      },
    })
    renderizarRutas('/grafo')
    const usuario = userEvent.setup()

    const captura = await screen.findByRole('group', { name: 'Captura en directo' })
    const interruptor = within(captura).getByRole('switch', { name: /Capturar datos/ })
    await waitFor(() => expect(interruptor).toBeEnabled())
    expect(captura).toHaveTextContent('Viajes reales de 2020, en su orden')
    await usuario.selectOptions(within(captura).getByRole('combobox', { name: 'Velocidad de la captura' }), '360')

    await usuario.click(interruptor)
    await waitFor(() => expect(interruptor).toBeChecked())
    const envio = espia.mock.calls.find(([url, init]) => String(url).endsWith('/api/operaciones/captura') && init?.method === 'POST')
    expect(JSON.parse(envio?.[1]?.body as string)).toEqual({ velocidad: 360 })
    expect(captura).toHaveTextContent('01/12/2020 14:35 · 12.345 viajes · 42/s')

    // la misma simulación que ve la animación (T15): el camino de la captura se ilumina
    const lienzo = screen.getByRole('region', { name: 'Arquitectura de la plataforma' })
    await waitFor(() => expect(lienzo.querySelector('[data-arista="simulador-captura"]')).toHaveAttribute('data-activa', 'true'))

    await usuario.click(interruptor)
    await waitFor(() => expect(interruptor).not.toBeChecked())
    expect(espia.mock.calls.some(([url, init]) => String(url).endsWith('/api/operaciones/captura') && init?.method === 'DELETE')).toBe(true)
  })

  it('sin viajes preparados, el interruptor se bloquea y dice cómo prepararlos', async () => {
    simularApi({
      'GET /api/sesion': { autenticado: true },
      'GET /api/operaciones/captura': { disponible: false, primer_dia: null, ultimo_dia: null, reloj: null, velocidad_por_defecto: 60, velocidad_maxima: 600 },
      'GET /api/operaciones/simulacion': { activa: false, lote: null, fichero: null, enviados: 0, total: 0, ritmo: 50, inicio: null, fin: null, error: null },
    })
    renderizarRutas('/grafo')
    const captura = await screen.findByRole('group', { name: 'Captura en directo' })
    await waitFor(() => expect(captura).toHaveTextContent('make captura-preparar'))
    expect(within(captura).getByRole('switch', { name: /Capturar datos/ })).toBeDisabled()
  })

  it('los botones de zoom acercan y alejan el grafo sin tocar el zoom del navegador', async () => {
    simularApi({ 'GET /api/sesion': { autenticado: true } })
    renderizarRutas('/grafo')
    const usuario = userEvent.setup()

    const lienzo = await screen.findByRole('region', { name: 'Arquitectura de la plataforma' })
    const zoom = within(lienzo).getByRole('group', { name: 'Zoom del grafo' })
    const escala = () => Number(/scale\(([\d.]+)\)/.exec((lienzo.querySelector('[style*="scale"]') as HTMLElement).style.transform)?.[1])
    const inicial = escala()
    await usuario.click(within(zoom).getByRole('button', { name: 'Acercar' }))
    expect(escala()).toBeCloseTo(inicial * 1.25)
    await usuario.click(within(zoom).getByRole('button', { name: 'Alejar' }))
    await usuario.click(within(zoom).getByRole('button', { name: 'Alejar' }))
    expect(escala()).toBeCloseTo(inicial / 1.25)
  })

  it('la ruta antigua /documentacion lleva al grafo', async () => {
    simularApi({ 'GET /api/sesion': { autenticado: true } })
    const { enrutador } = renderizarRutas('/documentacion')
    await screen.findByRole('region', { name: 'Arquitectura de la plataforma' })
    expect(enrutador.state.location.pathname).toBe('/grafo')
  })
})
