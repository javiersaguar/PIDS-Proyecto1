import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'

import type { Fila } from '@/api/tipos'

import { TablaAgregados } from './TablaAgregados'

const FILAS_BARRIOS: Fila[] = [
  { dia: '2020-03-03T00:00:00', barrio_origen: 'Bronx', n_viajes: 233, importe_medio: 22.65, suprimido: false },
  { dia: '2020-03-03T00:00:00', barrio_origen: 'Manhattan', n_viajes: 203866, importe_medio: 16.96, suprimido: false },
  { dia: '2020-03-03T00:00:00', barrio_origen: 'Queens', n_viajes: 12145, importe_medio: 45.0, suprimido: false },
  { dia: '2020-03-03T00:00:00', barrio_origen: 'Staten Island', n_viajes: '<10', importe_medio: null, suprimido: true },
]

function barriosEnOrden(): string[] {
  const cuerpo = screen.getAllByRole('rowgroup')[1]
  return within(cuerpo)
    .getAllByRole('row')
    .map((fila) => within(fila).getAllByRole('cell')[1].textContent ?? '')
}

describe('TablaAgregados', () => {
  it('pinta las columnas del nivel con <th scope="col"> y las cifras en español', () => {
    render(<TablaAgregados filas={FILAS_BARRIOS} nivel="dia_barrio" metricas={['n_viajes', 'importe_medio']} />)

    const cabeceras = screen.getAllByRole('columnheader')
    expect(cabeceras.map((c) => c.textContent)).toEqual(['Día', 'Barrio de origen', 'Viajes', 'Importe medio'])
    cabeceras.forEach((c) => expect(c).toHaveAttribute('scope', 'col'))
    expect(screen.getByText('203.866')).toBeInTheDocument()
    expect(screen.getByText('16,96 $')).toBeInTheDocument()
    expect(screen.getAllByText('03/03/2020')).toHaveLength(4)
  })

  it('marca los grupos enmascarados con el chip violeta y «<10», sin cifras', () => {
    render(<TablaAgregados filas={FILAS_BARRIOS} nivel="dia_barrio" metricas={['n_viajes', 'importe_medio']} />)

    const fila = screen.getByText('Staten Island').closest('tr')
    expect(fila).not.toBeNull()
    expect(fila).toHaveAttribute('data-enmascarada', 'true')
    expect(within(fila as HTMLElement).getByText('enmascarado por privacidad')).toBeInTheDocument()
    expect(within(fila as HTMLElement).getByText('<10')).toBeInTheDocument()
    // La métrica del grupo enmascarado no se muestra.
    expect(within(fila as HTMLElement).getAllByRole('cell')[3]).toHaveTextContent('—')
  })

  it('ordena al pulsar la cabecera: las cifras de mayor a menor, y al repetir se invierte', async () => {
    const usuario = userEvent.setup()
    render(<TablaAgregados filas={FILAS_BARRIOS} nivel="dia_barrio" />)

    expect(barriosEnOrden()).toEqual(['Bronx', 'Manhattan', 'Queens', 'Staten Island'])

    await usuario.click(screen.getByRole('button', { name: 'Viajes' }))
    expect(screen.getByRole('columnheader', { name: 'Viajes' })).toHaveAttribute('aria-sort', 'descending')
    // El enmascarado (<10) se ordena por debajo de cualquier grupo visible.
    expect(barriosEnOrden()).toEqual(['Manhattan', 'Queens', 'Bronx', 'Staten Island'])

    await usuario.click(screen.getByRole('button', { name: 'Viajes' }))
    expect(screen.getByRole('columnheader', { name: 'Viajes' })).toHaveAttribute('aria-sort', 'ascending')
    expect(barriosEnOrden()).toEqual(['Staten Island', 'Bronx', 'Queens', 'Manhattan'])

    await usuario.click(screen.getByRole('button', { name: 'Barrio de origen' }))
    expect(barriosEnOrden()).toEqual(['Bronx', 'Manhattan', 'Queens', 'Staten Island'])
    expect(screen.getByRole('columnheader', { name: 'Viajes' })).toHaveAttribute('aria-sort', 'none')
  })

  it('el total del pie suma solo los grupos visibles y cuenta los enmascarados', () => {
    render(<TablaAgregados filas={FILAS_BARRIOS} nivel="dia_barrio" conTotal />)

    const pie = screen.getAllByRole('rowgroup')[2]
    expect(pie).toHaveTextContent('Total de los grupos visibles (3 grupos)')
    expect(pie).toHaveTextContent('1 enmascarado no incluidos')
    expect(within(pie).getByText('216.244')).toBeInTheDocument()
  })

  it('muestra el contenido de «vacío» cuando no hay filas', () => {
    render(<TablaAgregados filas={[]} nivel="hora_zona" vacio={<p>No hay grupos en esa ventana</p>} />)
    expect(screen.getByText('No hay grupos en esa ventana')).toBeInTheDocument()
    expect(screen.queryByRole('table')).not.toBeInTheDocument()
  })

  it('en el nivel por hora muestra la fecha y hora, la zona con su id y el barrio', () => {
    const filas: Fila[] = [
      { hora: '2020-01-15T08:00:00', zona_origen: 132, zona_origen_nombre: 'JFK Airport', barrio_origen: 'Queens', n_viajes: 145, suprimido: false },
    ]
    render(<TablaAgregados filas={filas} nivel="hora_zona" />)
    expect(screen.getAllByRole('columnheader').map((c) => c.textContent)).toEqual(['Hora', 'Zona de origen', 'Barrio', 'Viajes'])
    expect(screen.getByText('15/01/2020 08:00')).toBeInTheDocument()
    expect(screen.getByText('JFK Airport')).toBeInTheDocument()
    expect(screen.getByText('#132')).toBeInTheDocument()
  })
})
