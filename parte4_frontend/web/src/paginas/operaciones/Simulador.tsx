/**
 * Tarjeta «Simulador de tiempo real»: el BFF reenvía los viajes de un CSV de `data/muestra` a la API de captura al
 * ritmo pedido (lotes de 100). Aquí se elige el fichero, el ritmo y un máximo opcional, se inicia o se para, y se
 * sigue el progreso (enviados/total, lote) refrescado cada 2 s mientras está activo.
 */
import { LoaderCircle, Play, Square, TriangleAlert } from 'lucide-react'
import { useState, type FormEvent } from 'react'
import { toast } from 'sonner'

import { ErrorApi, mensajeDeError } from '@/api/cliente'
import { useFicherosSimulacion, useIniciarSimulacion, usePararSimulacion, useSimulacion } from '@/api/operaciones'
import type { Simulacion } from '@/api/tipos'
import { formatearFechaHora, formatearNumero } from '@/componentes/chat/formato'
import { EstadoCargando, EstadoError } from '@/componentes/shell'
import { Badge } from '@/componentes/ui/badge'
import { Button } from '@/componentes/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/componentes/ui/card'
import { Input } from '@/componentes/ui/input'
import { Label } from '@/componentes/ui/label'
import { Progress } from '@/componentes/ui/progress'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/componentes/ui/select'

const RITMO_POR_DEFECTO = 50

function Progreso({ simulacion }: { simulacion: Simulacion }) {
  const porcentaje = simulacion.total > 0 ? Math.min(100, Math.round((simulacion.enviados / simulacion.total) * 100)) : 0
  return (
    <div className="space-y-2 rounded-lg border border-acento/40 bg-acento-suave/40 p-3" aria-live="polite">
      <div className="flex flex-wrap items-center justify-between gap-2 text-xs">
        <span className="inline-flex items-center gap-1.5 font-medium">
          <LoaderCircle className="size-3.5 animate-spin text-primario" aria-hidden />
          Simulación en marcha
        </span>
        <span className="cifra">
          {formatearNumero(simulacion.enviados)} / {formatearNumero(simulacion.total)} viajes enviados ({porcentaje} %)
        </span>
      </div>
      {/* El envoltorio de shadcn no reenvía `value` a Radix, así que los atributos ARIA se ponen aquí. */}
      <Progress
        value={porcentaje}
        className="h-2 bg-superficie"
        aria-label="Viajes enviados"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={porcentaje}
        aria-valuetext={`${porcentaje} %: ${formatearNumero(simulacion.enviados)} de ${formatearNumero(simulacion.total)} viajes`}
      />
      <dl className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs sm:grid-cols-4">
        <dt className="text-texto-suave">Lote</dt>
        <dd className="truncate font-mono" title={simulacion.lote ?? undefined}>
          {simulacion.lote ?? '—'}
        </dd>
        <dt className="text-texto-suave">Fichero</dt>
        <dd className="truncate font-mono" title={simulacion.fichero ?? undefined}>
          {simulacion.fichero ?? '—'}
        </dd>
        <dt className="text-texto-suave">Ritmo</dt>
        <dd className="cifra">{formatearNumero(simulacion.ritmo)} viajes/s</dd>
        <dt className="text-texto-suave">Inicio</dt>
        <dd className="cifra">{formatearFechaHora(simulacion.inicio)}</dd>
      </dl>
    </div>
  )
}

function UltimaSimulacion({ simulacion }: { simulacion: Simulacion }) {
  if (!simulacion.lote && !simulacion.fichero && simulacion.enviados === 0) {
    return <p className="text-xs text-texto-suave">Ninguna simulación en marcha. La última no ha dejado rastro en esta sesión del BFF.</p>
  }
  return (
    <p className="cifra text-xs text-texto-suave">
      Última simulación: <span className="font-mono text-foreground">{simulacion.lote ?? simulacion.fichero ?? '—'}</span> ·{' '}
      {formatearNumero(simulacion.enviados)} de {formatearNumero(simulacion.total)} viajes enviados
      {simulacion.inicio && <> · iniciada el {formatearFechaHora(simulacion.inicio)}</>}
    </p>
  )
}

export function Simulador() {
  const simulacion = useSimulacion()
  const ficheros = useFicherosSimulacion()
  const iniciar = useIniciarSimulacion()
  const parar = usePararSimulacion()
  const [ficheroElegido, setFicheroElegido] = useState<string | null>(null)
  const [ritmo, setRitmo] = useState(String(RITMO_POR_DEFECTO))
  const [maximo, setMaximo] = useState('')

  const listaFicheros = ficheros.data ?? []
  const fichero = ficheroElegido && listaFicheros.includes(ficheroElegido) ? ficheroElegido : listaFicheros[0] ?? null
  const activa = simulacion.data?.activa === true
  const ocupado = iniciar.isPending || parar.isPending
  const ritmoNumero = Number(ritmo)
  const maximoNumero = maximo.trim() === '' ? undefined : Number(maximo)
  const ritmoValido = Number.isFinite(ritmoNumero) && ritmoNumero > 0
  const maximoValido = maximoNumero === undefined || (Number.isInteger(maximoNumero) && maximoNumero > 0)

  const enviar = (evento: FormEvent<HTMLFormElement>) => {
    evento.preventDefault()
    if (!fichero || !ritmoValido || !maximoValido || activa || ocupado) return
    iniciar.mutate(
      { fichero, ritmo: ritmoNumero, maximo: maximoNumero },
      {
        onSuccess: (estado) => toast.success('Simulación iniciada', { description: `Lote ${estado.lote ?? ''}`.trim() }),
        onError: (error) => {
          if (error instanceof ErrorApi && error.status === 409) {
            toast.error('Ya hay una simulación activa', { description: 'Párala antes de iniciar otra.' })
          } else {
            toast.error('No se ha podido iniciar la simulación', { description: mensajeDeError(error) })
          }
        },
      },
    )
  }

  const detener = () => {
    parar.mutate(undefined, {
      onSuccess: () => toast.success('Simulación parada'),
      onError: (error) => toast.error('No se ha podido parar la simulación', { description: mensajeDeError(error) }),
    })
  }

  return (
    <Card className="sombra-tarjeta">
      <CardHeader>
        <CardTitle>Simulador de tiempo real</CardTitle>
        <CardDescription>
          Envía los viajes de un CSV de <code className="font-mono text-[11px]">data/muestra</code> a la API de captura, ordenados por hora de
          recogida y en lotes de 100, para alimentar el flujo de tiempo real (Redpanda → Spark → <code className="font-mono text-[11px]">tr_*</code>).
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {simulacion.isPending ? (
          <EstadoCargando lineas={3} etiqueta="Consultando el simulador…" />
        ) : simulacion.isError ? (
          <EstadoError
            titulo="No se ha podido consultar el simulador"
            error={simulacion.error}
            alReintentar={() => void simulacion.refetch()}
            reintentando={simulacion.isFetching}
          />
        ) : activa ? (
          <Progreso simulacion={simulacion.data} />
        ) : (
          <UltimaSimulacion simulacion={simulacion.data} />
        )}

        {simulacion.data?.error && (
          <p role="alert" className="flex items-start gap-2 rounded-lg border border-peligro/30 bg-peligro/5 px-3 py-2 text-xs text-peligro">
            <TriangleAlert className="mt-0.5 size-3.5 shrink-0" aria-hidden />
            <span>
              <span className="font-medium">Error del simulador:</span> {simulacion.data.error}
            </span>
          </p>
        )}

        <form onSubmit={enviar} className="flex flex-wrap items-end gap-4" noValidate>
          <div className="min-w-56 flex-1 space-y-1.5">
            <Label htmlFor="fichero-simulacion">Fichero</Label>
            {ficheros.isError ? (
              <p className="text-xs text-peligro">No se ha podido leer la lista de ficheros: {mensajeDeError(ficheros.error)}</p>
            ) : (
              <Select value={fichero ?? ''} onValueChange={setFicheroElegido} disabled={activa || ficheros.isPending || listaFicheros.length === 0}>
                <SelectTrigger id="fichero-simulacion" className="w-full" aria-label="Fichero">
                  <SelectValue placeholder={ficheros.isPending ? 'Cargando…' : 'Sin ficheros en data/muestra'} />
                </SelectTrigger>
                <SelectContent>
                  {listaFicheros.map((f) => (
                    <SelectItem key={f} value={f}>
                      <span className="font-mono text-xs">{f}</span>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            )}
          </div>
          <div className="w-32 space-y-1.5">
            <Label htmlFor="ritmo-simulacion">Ritmo (viajes/s)</Label>
            <Input
              id="ritmo-simulacion"
              type="number"
              min={1}
              step={1}
              inputMode="numeric"
              value={ritmo}
              onChange={(e) => setRitmo(e.target.value)}
              disabled={activa}
              aria-invalid={!ritmoValido || undefined}
            />
          </div>
          <div className="w-36 space-y-1.5">
            <Label htmlFor="maximo-simulacion">
              Máximo <span className="text-texto-suave">(opcional)</span>
            </Label>
            <Input
              id="maximo-simulacion"
              type="number"
              min={1}
              step={1}
              inputMode="numeric"
              placeholder="todos"
              value={maximo}
              onChange={(e) => setMaximo(e.target.value)}
              disabled={activa}
              aria-invalid={!maximoValido || undefined}
            />
          </div>
          {activa ? (
            <Button type="button" variant="destructive" onClick={detener} disabled={ocupado}>
              {parar.isPending ? <LoaderCircle className="animate-spin" aria-hidden /> : <Square aria-hidden />}
              Parar
            </Button>
          ) : (
            <Button type="submit" disabled={!fichero || !ritmoValido || !maximoValido || ocupado || simulacion.isPending}>
              {iniciar.isPending ? <LoaderCircle className="animate-spin" aria-hidden /> : <Play aria-hidden />}
              Iniciar
            </Button>
          )}
        </form>
        <p className="flex flex-wrap items-center gap-1.5 text-xs text-texto-suave">
          <Badge variant="outline" className="h-5 font-normal">
            una a la vez
          </Badge>
          Solo puede haber una simulación activa en el portal; las cifras llegan a Tiempo real en cuanto Spark publica el siguiente micro-lote
          (unos 30 s).
        </p>
      </CardContent>
    </Card>
  )
}
