/**
 * Tarjeta «Simulador de tiempo real»: envía los viajes de un fichero de prueba al ritmo pedido,
 * para que la página Tiempo real se vaya llenando. Solo puede haber una simulación a la vez.
 *
 * Con «Inventar más viajes» el BFF no envía el fichero, sino los que se le piden, generados a partir
 * de él (la muestra tiene 999 y se agota en segundos). Cumplen las mismas reglas de validación.
 */
import { LoaderCircle, Play, Radio, Square, TriangleAlert } from 'lucide-react'
import { useState, type FormEvent } from 'react'
import { toast } from 'sonner'

import { ErrorApi, mensajeDeError } from '@/api/cliente'
import {
  MAXIMO_SINTETICOS,
  useFicherosSimulacion,
  useIniciarSimulacion,
  usePararSimulacion,
  useSimulacion,
} from '@/api/operaciones'
import type { Simulacion } from '@/api/tipos'
import { formatearFecha, formatearFechaHora, formatearNumero } from '@/componentes/chat/formato'
import { EstadoCargando, EstadoError } from '@/componentes/shell'
import { Button } from '@/componentes/ui/button'
import { Card, CardContent, CardHeader } from '@/componentes/ui/card'
import { Input } from '@/componentes/ui/input'
import { Label } from '@/componentes/ui/label'
import { Progress } from '@/componentes/ui/progress'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/componentes/ui/select'
import { Switch } from '@/componentes/ui/switch'

const RITMO_POR_DEFECTO = 50
const SINTETICOS_POR_DEFECTO = 20000

const NOMBRES_FICHERO: Record<string, string> = {
  'yellow_tripdata_2020_muestra.csv': 'Taxis amarillos, muestra de 2020',
  'exportacion_formato_europeo.csv': 'Muestra en formato europeo',
}

function nombreFichero(fichero: string): string {
  return NOMBRES_FICHERO[fichero] ?? fichero.replace(/\.csv$/i, '').replaceAll('_', ' ')
}

/** Qué viajes lleva la simulación: el fichero, o los inventados a partir de él. */
function origen(simulacion: Simulacion): string {
  if (!simulacion.fichero) return '—'
  const fichero = nombreFichero(simulacion.fichero)
  return simulacion.sinteticos ? `inventados a partir de ${fichero}` : fichero
}

function Progreso({ simulacion }: { simulacion: Simulacion }) {
  const porcentaje = simulacion.total > 0 ? Math.min(100, Math.round((simulacion.enviados / simulacion.total) * 100)) : 0
  return (
    <div className="space-y-3 rounded-xl border border-sky-200 bg-sky-50/70 p-4" aria-live="polite">
      <div className="flex flex-wrap items-center justify-between gap-2 text-sm">
        <span className="inline-flex items-center gap-2 font-medium text-slate-900">
          <LoaderCircle className="size-4 animate-spin text-sky-600" aria-hidden />
          Simulación en marcha
        </span>
        <span className="cifra text-slate-700">
          {formatearNumero(simulacion.enviados)} / {formatearNumero(simulacion.total)} viajes enviados ({porcentaje} %)
        </span>
      </div>
      {/* El envoltorio de shadcn no reenvía `value` a Radix, así que los atributos ARIA se ponen aquí. */}
      <Progress
        value={porcentaje}
        className="h-2.5 bg-white"
        aria-label="Viajes enviados"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={porcentaje}
        aria-valuetext={`${porcentaje} %: ${formatearNumero(simulacion.enviados)} de ${formatearNumero(simulacion.total)} viajes`}
      />
      {simulacion.lote && <span className="sr-only">{simulacion.lote}</span>}
      {simulacion.dia && (
        <p className="text-sm text-slate-600">
          Van fechados el <span className="cifra font-medium text-slate-900">{formatearFecha(simulacion.dia)}</span>, el día
          siguiente al último que ya muestra Tiempo real: con su fecha original, el tiempo real los descartaría.
        </p>
      )}
      <dl className="grid gap-3 text-sm sm:grid-cols-3">
        <div className="min-w-0">
          <dt className="text-slate-500">{simulacion.sinteticos ? 'Viajes' : 'Fichero'}</dt>
          <dd className="mt-0.5 text-slate-900">{origen(simulacion)}</dd>
        </div>
        <div>
          <dt className="text-slate-500">Velocidad</dt>
          <dd className="cifra mt-0.5 text-slate-900">{formatearNumero(simulacion.ritmo)} viajes por segundo</dd>
        </div>
        <div>
          <dt className="text-slate-500">Empezó</dt>
          <dd className="cifra mt-0.5 text-slate-900">{formatearFechaHora(simulacion.inicio)}</dd>
        </div>
      </dl>
    </div>
  )
}

function UltimaSimulacion({ simulacion }: { simulacion: Simulacion }) {
  if (!simulacion.lote && !simulacion.fichero && simulacion.enviados === 0) return null
  return (
    <p className="text-sm text-slate-600">
      La última simulación envió{' '}
      <span className="cifra font-medium text-slate-900">
        {formatearNumero(simulacion.enviados)} de {formatearNumero(simulacion.total)}
      </span>{' '}
      viajes
      {simulacion.fichero && (
        <>
          {' '}
          {simulacion.sinteticos ? 'inventados a partir de' : 'del fichero'}{' '}
          <span className="font-medium text-slate-900">{nombreFichero(simulacion.fichero)}</span>
        </>
      )}
      {simulacion.inicio && (
        <>
          . Empezó el <span className="cifra">{formatearFechaHora(simulacion.inicio)}</span>
        </>
      )}
      .
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
  const [inventar, setInventar] = useState(false)
  const [cuantos, setCuantos] = useState(String(SINTETICOS_POR_DEFECTO))

  const listaFicheros = ficheros.data ?? []
  const fichero = ficheroElegido && listaFicheros.includes(ficheroElegido) ? ficheroElegido : listaFicheros[0] ?? null
  const activa = simulacion.data?.activa === true
  const ocupado = iniciar.isPending || parar.isPending
  const ritmoNumero = Number(ritmo)
  const maximoNumero = maximo.trim() === '' ? undefined : Number(maximo)
  const cuantosNumero = Number(cuantos)
  const ritmoValido = Number.isFinite(ritmoNumero) && ritmoNumero > 0
  const maximoValido = inventar
    ? Number.isInteger(cuantosNumero) && cuantosNumero > 0 && cuantosNumero <= MAXIMO_SINTETICOS
    : maximoNumero === undefined || (Number.isInteger(maximoNumero) && maximoNumero > 0)

  const enviar = (evento: FormEvent<HTMLFormElement>) => {
    evento.preventDefault()
    if (!fichero || !ritmoValido || !maximoValido || activa || ocupado) return
    iniciar.mutate(
      inventar
        ? { fichero, ritmo: ritmoNumero, sinteticos: cuantosNumero }
        : { fichero, ritmo: ritmoNumero, maximo: maximoNumero },
      {
        onSuccess: () => toast.success('Simulación empezada', { description: 'Los viajes ya se están enviando.' }),
        onError: (error) => {
          if (error instanceof ErrorApi && error.status === 409) {
            toast.error('Ya hay una simulación activa', { description: 'Párala antes de empezar otra.' })
          } else {
            toast.error('No se ha podido empezar la simulación', { description: mensajeDeError(error) })
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
    <Card className="sombra-tarjeta gap-0 overflow-hidden rounded-2xl border border-slate-200/80 bg-white py-0 text-slate-900 ring-0">
      <CardHeader className="gap-0 px-5 pt-4 pb-0">
        <div className="flex items-start gap-2.5">
          <span className="flex size-9 shrink-0 items-center justify-center rounded-xl bg-emerald-50 text-emerald-600" aria-hidden>
            <Radio className="size-4" strokeWidth={2.25} />
          </span>
          <div className="min-w-0 space-y-1">
            <h2 className="text-[15px] leading-none text-slate-900">Simulador de tiempo real</h2>
            <p className="max-w-3xl text-sm text-slate-500">
              Imita los taxis circulando ahora mismo. Coge viajes de prueba y los envía poco a poco, para que la página Tiempo real vaya mostrando cifras. Tardan unos 30 segundos en aparecer.
            </p>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-4 px-5 pt-4 pb-5">
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
          <p role="alert" className="flex items-start gap-2 rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
            <TriangleAlert className="mt-0.5 size-4 shrink-0" aria-hidden />
            <span>
              <span className="font-medium">Algo ha fallado:</span> {simulacion.data.error}
            </span>
          </p>
        )}

        <form onSubmit={enviar} className="grid gap-4 rounded-xl bg-slate-50 p-4 md:grid-cols-[minmax(0,1.4fr)_11rem_12rem_auto] md:items-end" noValidate>
          <div className="min-w-0 space-y-2">
            <Label htmlFor="fichero-simulacion">{inventar ? 'De qué viajes copiar el estilo' : 'Qué viajes enviar'}</Label>
            {ficheros.isError ? (
              <p className="text-sm text-rose-700">No se ha podido leer la lista de ficheros: {mensajeDeError(ficheros.error)}</p>
            ) : (
              <Select value={fichero ?? ''} onValueChange={setFicheroElegido} disabled={activa || ficheros.isPending || listaFicheros.length === 0}>
                <SelectTrigger id="fichero-simulacion" className="w-full" aria-label="Qué viajes enviar">
                  <SelectValue placeholder={ficheros.isPending ? 'Cargando…' : 'No hay ficheros de prueba'} />
                </SelectTrigger>
                <SelectContent>
                  {listaFicheros.map((f) => (
                    <SelectItem key={f} value={f}>
                      {nombreFichero(f)}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            )}
          </div>
          <div className="space-y-2">
            <Label htmlFor="ritmo-simulacion">Cuántos por segundo</Label>
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
          <div className="space-y-2">
            <Label htmlFor="maximo-simulacion">{inventar ? 'Cuántos inventar' : 'Máximo de viajes'}</Label>
            <Input
              id="maximo-simulacion"
              type="number"
              min={1}
              max={inventar ? MAXIMO_SINTETICOS : undefined}
              step={1}
              inputMode="numeric"
              placeholder={inventar ? String(SINTETICOS_POR_DEFECTO) : 'todos'}
              value={inventar ? cuantos : maximo}
              onChange={(e) => (inventar ? setCuantos(e.target.value) : setMaximo(e.target.value))}
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
              Empezar
            </Button>
          )}
          <div className="flex flex-wrap items-center gap-3 md:col-span-full">
            <Switch id="inventar-simulacion" checked={inventar} onCheckedChange={setInventar} disabled={activa} />
            <Label htmlFor="inventar-simulacion" className="font-normal text-slate-600">
              Inventar más viajes a partir de ese fichero, para que la demo no se quede en los{' '}
              {formatearNumero(999)} de la muestra. Son datos falsos con las mismas reglas: nadie real detrás.
            </Label>
          </div>
        </form>
      </CardContent>
    </Card>
  )
}
