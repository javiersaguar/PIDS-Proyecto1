import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'

import type { Cuadro, PanelCuadro } from '@/api/observabilidad'
import { renderizarRutas, simularApi } from '@/pruebas/utilidades'

import { CUADROS, incrustable, urlCuadro } from './cuadros'
import { aFilas, colorPorUmbral, describirPeriodo, formatear } from './formatoUnidad'

const BASE: Omit<PanelCuadro, 'id' | 'tipo' | 'titulo'> = {
  descripcion: '', x: 0, y: 0, ancho: 24, alto: 8, unidad: 'short', color: null, umbrales: [], mapeos: {}, colores: {},
  texto: null,
}

function panel(id: number, tipo: PanelCuadro['tipo'], titulo: string, extra: Partial<PanelCuadro> = {}): PanelCuadro {
  return { ...BASE, id, tipo, titulo, ...extra }
}

const PLATAFORMA: Cuadro = {
  uid: 'pids-plataforma', titulo: 'Plataforma', periodo: '6h', actualizado: Date.now() / 1000, disponible: true,
  paneles: [
    panel(1, 'fila', 'De un vistazo', { alto: 1 }),
    panel(2, 'stat', 'Servicios caídos', { y: 1, ancho: 4, alto: 4, valores: [{ nombre: 'valor', valor: 0 }], chispa: [0, 0, 1, 0],
      umbrales: [{ color: 'green', desde: null }, { color: 'red', desde: 1 }] }),
    panel(3, 'serie', 'Consultas por minuto', { y: 5, ancho: 12, series: [
      { nombre: 'permitida', puntos: [[1_700_000_000, 3], [1_700_000_060, 5]] },
      { nombre: 'rechazada', puntos: [[1_700_000_000, 1], [1_700_000_060, null]] },
    ] }),
    panel(4, 'barras', 'Estado de los servicios', { x: 12, y: 5, ancho: 12, valores: [{ nombre: 'acceso', valor: 1 }, { nombre: 'spark', valor: 0 }],
      mapeos: { 0: { texto: 'Caído', color: 'red' }, 1: { texto: 'Arriba', color: 'green' } } }),
    panel(5, 'alertas', 'Alertas', { y: 13, alertas: [{ nombre: 'Datos del tiempo real antiguos', estado: 'firing', resumen: 'Hace 20 min' }] }),
  ],
}

const SPARK: Cuadro = {
  uid: 'pids-spark', titulo: 'Spark', periodo: '6h', actualizado: Date.now() / 1000, disponible: false,
  paneles: [panel(1, 'stat', 'Workers vivos', { ancho: 6, alto: 4, error: 'Prometheus no responde' })],
}

function api(enlaceGrafana: string) {
  return simularApi({
    'GET /api/sesion': { autenticado: true },
    'GET /api/panel': { servicios: [], enlaces: { grafana: enlaceGrafana } },
    'GET /api/observabilidad/cuadros': CUADROS.map(({ uid, titulo }) => ({ uid, titulo, periodo: '6h' })),
    'GET /api/observabilidad/cuadros/pids-plataforma': PLATAFORMA,
    'GET /api/observabilidad/cuadros/pids-spark': SPARK,
  })
}

describe('Observabilidad', () => {
  it('dibuja los paneles del cuadro de Grafana con sus datos y cambia de cuadro', async () => {
    api('http://localhost:3000')
    renderizarRutas('/observabilidad')
    const usuario = userEvent.setup()

    const cuadro = await screen.findByRole('tabpanel', { name: 'Cuadro Plataforma' })
    expect(within(cuadro).getByRole('heading', { name: 'De un vistazo' })).toBeInTheDocument()
    expect(within(cuadro).getByRole('region', { name: 'Servicios caídos' })).toHaveTextContent('0')
    expect(within(cuadro).getByRole('img', { name: 'Consultas por minuto' })).toBeInTheDocument()
    expect(within(cuadro).getByText('rechazada')).toBeInTheDocument()                      // leyenda de la serie
    expect(within(cuadro).getByText('Arriba')).toBeInTheDocument()                          // mapeo del valor 1
    expect(within(cuadro).getByText('Caído')).toBeInTheDocument()
    expect(within(cuadro).getByText('Disparada')).toBeInTheDocument()
    expect(screen.getByText(/Últimas 6 h/)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Abrir en Grafana' })).toHaveAttribute('href', urlCuadro('http://localhost:3000', 'pids-plataforma'))

    await usuario.click(screen.getByRole('tab', { name: /Spark/ }))
    const spark = await screen.findByRole('tabpanel', { name: 'Cuadro Spark' })
    expect(within(spark).getByText('Prometheus no responde')).toBeInTheDocument()
    expect(screen.getByText(/los paneles se quedan vacíos/)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Abrir en Grafana' })).toHaveAttribute('href', 'http://localhost:3000/d/pids-spark?orgId=1')
  })

  it('en la web pública y en la demostración enseña los cuadros y avisa de dónde está Grafana', async () => {
    expect(incrustable('http://localhost:3000', 'localhost')).toBe(true)
    expect(incrustable('http://localhost:3000', 'happytaxi-rust.vercel.app')).toBe(false)     // web pública
    expect(incrustable('https://github.com/javiersaguar/PIDS-Proyecto1', 'localhost')).toBe(false)  // demostración
    api('https://github.com/x')
    renderizarRutas('/observabilidad')
    expect(await screen.findByRole('tabpanel', { name: 'Cuadro Plataforma' })).toBeInTheDocument()
    expect(screen.getByText(/Son los mismos cuadros que en Grafana/)).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Abrir en Grafana' })).not.toBeInTheDocument()
  })

  it('formatea como Grafana, en español', () => {
    expect(formatear(1536, 'bytes')).toBe('1,5 KiB')
    expect(formatear(125, 's')).toBe('2 min 5 s')
    expect(formatear(0.5, 'reqps')).toBe('0,5/s')
    expect(formatear(12_345, 'short')).toBe('12,3 mil')
    expect(formatear(null, 'short')).toBe('—')
    expect(describirPeriodo('24h')).toBe('últimas 24 h')
    const umbrales = { color: null, umbrales: [{ color: 'green', desde: null }, { color: 'red', desde: 1 }] }
    expect(colorPorUmbral(umbrales, 0)).toBe('#17875a')
    expect(colorPorUmbral(umbrales, 3)).toBe('#dc2626')
    expect(aFilas([{ nombre: 'a', puntos: [[2, 1], [1, 4]] }, { nombre: 'b', puntos: [[1, 7]] }])).toEqual([
      { t: 1, a: 4, b: 7 }, { t: 2, a: 1 },
    ])
  })
})
