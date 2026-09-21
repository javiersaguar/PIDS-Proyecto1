/**
 * Página de acceso (§4 y §6): formulario con la contraseña única del portal → `POST /api/sesion`.
 * Un 401 se muestra en el propio formulario; al entrar se navega a `/`.
 */
import { CarTaxiFront, KeyRound, LoaderCircle, Lock, ShieldCheck, TriangleAlert } from 'lucide-react'
import { useState, type FormEvent } from 'react'
import { Navigate, useLocation, useNavigate } from 'react-router'

import { mensajeDeError } from '@/api/cliente'
import { useIniciarSesion, useSesion } from '@/api/sesion'
import { AVISO_E3 } from '@/componentes/shell/Pie'
import { Button } from '@/componentes/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/componentes/ui/card'
import { Input } from '@/componentes/ui/input'
import { Label } from '@/componentes/ui/label'

const ARGUMENTOS = [
  { icono: Lock, texto: 'Solo agregados con al menos 10 viajes: los grupos pequeños se enmascaran, nunca se suman.' },
  { icono: ShieldCheck, texto: 'Cada consulta pasa por el filtro de privacidad de la API de acceso y queda auditada.' },
  { icono: KeyRound, texto: 'Las claves de las APIs viven en el servidor; el navegador solo tiene esta sesión.' },
]

interface EstadoNavegacion {
  caducada?: boolean
}

export default function PaginaAcceso() {
  const [clave, setClave] = useState('')
  const sesion = useSesion()
  const entrar = useIniciarSesion()
  const navegar = useNavigate()
  const { state } = useLocation() as { state: EstadoNavegacion | null }

  if (sesion.data?.autenticado) {
    return <Navigate to="/" replace />
  }

  const enviar = (evento: FormEvent<HTMLFormElement>) => {
    evento.preventDefault()
    if (!clave || entrar.isPending) return
    entrar.mutate(clave, {
      onSuccess: () => void navegar('/', { replace: true }),
    })
  }

  const mensajeError = entrar.isError ? mensajeDeError(entrar.error) : null

  return (
    <div className="grid min-h-svh lg:grid-cols-[minmax(0,5fr)_minmax(0,4fr)]">
      <section className="fondo-marino hidden flex-col justify-between p-10 text-white lg:flex">
        <div className="flex items-center gap-3">
          <span className="flex size-10 items-center justify-center rounded-xl bg-white text-[#1d4ed8]" aria-hidden>
            <CarTaxiFront className="size-6" strokeWidth={2.25} />
          </span>
          <div className="leading-tight">
            <p className="text-lg font-semibold text-white">PIDS · Taxis NYC</p>
            <p className="text-sm text-white/75">Plataforma de datos · Portal interno</p>
          </div>
        </div>
        <div className="max-w-lg space-y-6">
          <h1 className="text-3xl leading-tight text-white">
            Los datos de la flota, <span className="text-emerald-200">sin exponer a nadie</span>.
          </h1>
          <ul className="space-y-3">
            {ARGUMENTOS.map(({ icono: Icono, texto }) => (
              <li key={texto} className="flex items-start gap-3 text-sm text-white/90">
                <Icono className="mt-0.5 size-4 shrink-0 text-emerald-200" aria-hidden />
                <span>{texto}</span>
              </li>
            ))}
          </ul>
        </div>
        <p className="text-xs text-white/70">{AVISO_E3} · Escenario E3, privacidad total</p>
      </section>

      <section className="flex items-center justify-center bg-fondo p-6">
        <Card className="w-full max-w-sm sombra-tarjeta">
          <CardHeader>
            <div className="mb-2 flex items-center gap-2 lg:hidden">
              <span className="flex size-8 items-center justify-center rounded-lg bg-[#2563eb] text-white" aria-hidden>
                <CarTaxiFront className="size-4" strokeWidth={2.25} />
              </span>
              <span className="font-semibold text-primario">PIDS · Taxis NYC</span>
            </div>
            <CardTitle className="text-xl text-primario">Acceso al portal</CardTitle>
            <CardDescription>Introduce la contraseña del portal para consultar los agregados protegidos.</CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={enviar} className="space-y-4" noValidate>
              {state?.caducada && !mensajeError && (
                <p role="status" className="rounded-md border border-aviso/30 bg-aviso/5 px-3 py-2 text-aviso">
                  La sesión ha caducado. Vuelve a introducir la contraseña.
                </p>
              )}
              <div className="space-y-2">
                <Label htmlFor="clave">Contraseña</Label>
                <Input
                  id="clave"
                  name="clave"
                  type="password"
                  autoComplete="current-password"
                  autoFocus
                  required
                  value={clave}
                  onChange={(e) => setClave(e.target.value)}
                  aria-invalid={mensajeError ? true : undefined}
                  aria-describedby={mensajeError ? 'clave-error' : undefined}
                  disabled={entrar.isPending}
                />
              </div>
              {mensajeError && (
                <p id="clave-error" role="alert" className="flex items-start gap-2 text-peligro">
                  <TriangleAlert className="mt-0.5 size-4 shrink-0" aria-hidden />
                  <span>{mensajeError}</span>
                </p>
              )}
              <Button type="submit" className="w-full" disabled={!clave || entrar.isPending}>
                {entrar.isPending ? <LoaderCircle className="animate-spin" aria-hidden /> : <KeyRound aria-hidden />}
                {entrar.isPending ? 'Entrando…' : 'Entrar'}
              </Button>
            </form>
            <p className="mt-4 text-center text-xs text-texto-suave">
              Portal interno. La sesión dura 12 horas en este navegador; la contraseña la gestiona el equipo de la
              plataforma.
            </p>
          </CardContent>
        </Card>
      </section>
    </div>
  )
}
