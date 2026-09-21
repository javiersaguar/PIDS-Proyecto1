import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'

import { cuerpoEnviado, renderizarRutas, simularApi } from '@/pruebas/utilidades'

describe('PaginaAcceso', () => {
  it('muestra el detail del 401 cuando la clave es incorrecta', async () => {
    const espia = simularApi({
      'GET /api/sesion': { autenticado: false },
      'POST /api/sesion': { status: 401, json: { detail: 'Clave incorrecta' } },
    })
    renderizarRutas('/acceso')
    const usuario = userEvent.setup()

    await usuario.type(await screen.findByLabelText('Contraseña'), 'mala')
    await usuario.click(screen.getByRole('button', { name: 'Entrar' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('Clave incorrecta')
    expect(cuerpoEnviado(espia)).toEqual({ clave: 'mala' })
    expect(screen.getByLabelText('Contraseña')).toHaveAttribute('aria-invalid', 'true')
    // Sigue en la página de acceso: no se ha pintado el shell.
    expect(screen.queryByRole('navigation')).not.toBeInTheDocument()
  })

  it('con la clave correcta entra y navega al panel', async () => {
    simularApi({
      'GET /api/sesion': { autenticado: false },
      'POST /api/sesion': { status: 204 },
      'GET /api/panel': { status: 404, json: { detail: 'Recurso no encontrado' } },
    })
    renderizarRutas('/acceso')
    const usuario = userEvent.setup()

    await usuario.type(await screen.findByLabelText('Contraseña'), 'buena')
    await usuario.click(screen.getByRole('button', { name: 'Entrar' }))

    expect(await screen.findByRole('heading', { level: 1, name: 'Panel' })).toBeInTheDocument()
    expect(screen.getByText('En construcción')).toBeInTheDocument()
  })

  it('sin sesión, una ruta protegida redirige al acceso', async () => {
    simularApi({ 'GET /api/sesion': { autenticado: false } })
    renderizarRutas('/explorador')

    expect(await screen.findByText('Acceso al portal')).toBeInTheDocument()
    await waitFor(() => expect(screen.queryByRole('navigation')).not.toBeInTheDocument())
  })
})
