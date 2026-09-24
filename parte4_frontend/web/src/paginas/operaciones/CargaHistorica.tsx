/**
 * Tarjeta «Carga histórica»: elige un mes de 2020 (o solo la muestra de 999 viajes), confirma lo que va a pasar
 * y pide la carga. Debajo, las últimas cargas con su resultado, refrescadas cada 15 s.
 *
 * Con el histórico ya cargado, la muestra no puede volver a cargarse (sustituiría los grupos del 1 de enero, T19):
 * en lugar del interruptor apagado aparece «Enviar los 999 al tiempo real», que usa el simulador del portal.
 */
import { differenceInSeconds, parseISO } from 'date-fns'
import { CalendarDays, ExternalLink, LoaderCircle, Play, Radio, RefreshCw } from 'lucide-react'
import { useState } from 'react'
import { toast } from 'sonner'

import { ErrorApi, mensajeDeError } from '@/api/cliente'
import {
  MESES_2020,
  useEjecucionesAirflow,
  useEnlaces,
  useEstadoMuestra,
  useIniciarSimulacion,
  useLanzarCarga,
  useSimulacion,
} from '@/api/operaciones'
import type { EjecucionAirflow } from '@/api/tipos'
import { formatearFecha, formatearFechaHora, formatearSegundos } from '@/componentes/chat/formato'
import { EstadoCargando, EstadoError, EstadoVacio } from '@/componentes/shell'
import { Badge } from '@/componentes/ui/badge'
import { Button } from '@/componentes/ui/button'
import { Card, CardContent, CardHeader } from '@/componentes/ui/card'
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/componentes/ui/dialog'
import { Label } from '@/componentes/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/componentes/ui/select'
import { Switch } from '@/componentes/ui/switch'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/componentes/ui/table'
import { cn } from '@/lib/utils'

const NOMBRE_MES = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre']

function etiquetaMes(mes: string): string {
  const indice = Number(mes.slice(5, 7)) - 1
  return `${NOMBRE_MES[indice] ?? mes} de 2020`
}

const CLASE_ESTADO: Record<string, string> = {
  success: 'bg-ok/10 text-ok border-ok/30',
  running: 'bg-aviso/10 text-aviso border-aviso/30',
  queued: 'bg-aviso/10 text-aviso border-aviso/30',
  scheduled: 'bg-aviso/10 text-aviso border-aviso/30',
  failed: 'bg-peligro/10 text-peligro border-peligro/30',
}
const TEXTO_ESTADO: Record<string, string> = {
  success: 'correcta',
  running: 'en ejecución',
  queued: 'en cola',
  scheduled: 'programada',
  failed: 'fallida',
}

export function ChipEstadoAirflow({ estado }: { estado: string }) {
  const enMarcha = estado === 'running' || estado === 'queued'
  return (
    <Badge variant="outline" className={cn('gap-1 font-medium', CLASE_ESTADO[estado] ?? 'bg-muted text-texto-suave')}>
      {enMarcha && <LoaderCircle className="animate-spin" aria-hidden />}
      {TEXTO_ESTADO[estado] ?? estado}
    </Badge>
  )
}

function duracion(ejecucion: EjecucionAirflow): string {
  if (!ejecucion.inicio || !ejecucion.fin) return '—'
  return formatearSegundos(differenceInSeconds(parseISO(ejecucion.fin), parseISO(ejecucion.inicio)))
}

function descripcionConf(conf: Record<string, unknown>): string {
  const mes = typeof conf.mes === 'string' ? etiquetaMes(conf.mes) : null
  const muestra = conf.muestra === true
  if (muestra) return mes ? `Muestra de prueba, ${mes}` : 'Muestra de prueba'
  return mes ?? '—'
}

const FICHERO_MUESTRA = 'yellow_tripdata_2020_muestra.csv'

/** Los 999 viajes de prueba al tiempo real (simulador del portal): lo que sí se puede hacer con el año cargado. */
function MuestraAlTiempoReal() {
  const simulacion = useSimulacion()
  const iniciar = useIniciarSimulacion()
  const activa = simulacion.data?.activa === true

  const enviar = () => {
    iniciar.mutate(
      { fichero: FICHERO_MUESTRA },
      {
        onSuccess: (estado) =>
          toast.success('Los 999 viajes de prueba van al tiempo real', {
            description: estado.dia
              ? `Aparecerán en Tiempo real como viajes del ${formatearFecha(estado.dia)} en unos 30 segundos.`
              : 'Aparecerán en Tiempo real en unos 30 segundos.',
          }),
        onError: (error) =>
          toast.error(
            error instanceof ErrorApi && error.status === 409 ? 'Ya hay una simulación activa' : 'No se han podido enviar',
            { description: error instanceof ErrorApi && error.status === 409 ? 'Párala abajo, en el simulador.' : mensajeDeError(error) },
          ),
      },
    )
  }

  return (
    <Button variant="outline" className="bg-white" onClick={enviar} disabled={activa || iniciar.isPending || simulacion.isPending}>
      {iniciar.isPending ? <LoaderCircle className="animate-spin" aria-hidden /> : <Radio aria-hidden />}
      {activa ? 'Simulación en marcha' : 'Enviar los 999 al tiempo real'}
    </Button>
  )
}

function TablaEjecuciones() {
  const ejecuciones = useEjecucionesAirflow()
  if (ejecuciones.isPending) return <EstadoCargando lineas={4} etiqueta="Cargando las cargas anteriores…" />
  if (ejecuciones.isError) {
    return (
      <EstadoError
        titulo="No se han podido ver las cargas anteriores"
        error={ejecuciones.error}
        alReintentar={() => void ejecuciones.refetch()}
        reintentando={ejecuciones.isFetching}
      />
    )
  }
  if (ejecuciones.data.length === 0) {
    return (
      <EstadoVacio
        titulo="Todavía no hay cargas"
        descripcion="Elige un mes arriba y pulsa Cargar viajes. Cuando termine, aparecerá en esta lista."
      />
    )
  }
  return (
    <Table className="min-w-[44rem]">
      <TableHeader>
        <TableRow className="bg-slate-50 hover:bg-slate-50">
          <TableHead scope="col" className="px-4 text-xs font-medium text-slate-500">
            Qué se cargó
          </TableHead>
          <TableHead scope="col" className="px-4 text-xs font-medium text-slate-500">
            Cómo va
          </TableHead>
          <TableHead scope="col" className="px-4 text-xs font-medium text-slate-500">
            Empezó
          </TableHead>
          <TableHead scope="col" className="px-4 text-xs font-medium text-slate-500">
            Terminó
          </TableHead>
          <TableHead scope="col" className="px-4 text-right text-xs font-medium text-slate-500">
            Cuánto tardó
          </TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {ejecuciones.data.map((ejecucion) => (
          <TableRow key={ejecucion.dag_run_id}>
            <TableCell className="px-4 py-3">{descripcionConf(ejecucion.conf ?? {})}</TableCell>
            <TableCell className="px-4 py-3">
              <ChipEstadoAirflow estado={ejecucion.estado} />
            </TableCell>
            <TableCell className="cifra px-4 py-3 whitespace-nowrap text-slate-600">
              {formatearFechaHora(ejecucion.inicio)}
            </TableCell>
            <TableCell className="cifra px-4 py-3 whitespace-nowrap text-slate-600">
              {formatearFechaHora(ejecucion.fin)}
            </TableCell>
            <TableCell className="cifra px-4 py-3 text-right whitespace-nowrap">{duracion(ejecucion)}</TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  )
}

export function CargaHistorica() {
  const [mes, setMes] = useState(MESES_2020[0])
  const [muestra, setMuestra] = useState(false)
  const [confirmando, setConfirmando] = useState(false)
  const lanzar = useLanzarCarga()
  const estadoMuestra = useEstadoMuestra()
  const historicoCargado = estadoMuestra.data?.bloqueada === true
  const bloqueada = estadoMuestra.isPending || estadoMuestra.isError || historicoCargado
  const motivo = historicoCargado
    ? 'El histórico de 2020 ya está cargado: los 999 viajes de prueba no se vuelven a cargar porque sustituirían los datos del 1 de enero. Se pueden enviar al tiempo real, que no toca el histórico.'
    : estadoMuestra.isError
      ? 'No se ha podido comprobar si el histórico ya está cargado. La muestra no se puede lanzar.'
      : estadoMuestra.isPending
        ? 'Comprobando si el histórico ya está cargado…'
        : null
  const usarMuestra = bloqueada ? false : muestra
  const ejecuciones = useEjecucionesAirflow()
  const { enlaces } = useEnlaces()

  const confirmar = () => {
    lanzar.mutate(
      { mes, muestra: usarMuestra },
      {
        onSuccess: () => {
          setConfirmando(false)
          toast.success('La carga ya ha empezado', {
            description: usarMuestra ? 'Se están usando los 999 viajes de prueba.' : `Se está cargando ${etiquetaMes(mes)}.`,
          })
        },
        onError: (error) => {
          toast.error('No se ha podido empezar la carga', { description: mensajeDeError(error) })
        },
      },
    )
  }

  return (
    <Card className="sombra-tarjeta gap-0 overflow-hidden rounded-2xl border border-slate-200/80 bg-white py-0 text-slate-900 ring-0">
      <CardHeader className="gap-0 px-5 pt-4 pb-0">
        <div className="flex items-start gap-2.5">
          <span className="flex size-9 shrink-0 items-center justify-center rounded-xl bg-sky-50 text-sky-600" aria-hidden>
            <CalendarDays className="size-4" strokeWidth={2.25} />
          </span>
          <div className="min-w-0 space-y-1">
            <h2 className="text-[15px] leading-none text-slate-900">Carga histórica</h2>
            <p className="max-w-3xl text-sm text-slate-500">
              Guarda los viajes de taxi de un mes de 2020 para poder consultarlos después. Tú eliges el mes; el sistema los descarga, los resume por barrio y por hora, y los deja listos en el portal.
            </p>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-5 px-5 pt-4 pb-5">
        <div className="flex flex-col gap-3 rounded-xl bg-slate-50 p-3 sm:flex-row sm:items-end">
          <div className="w-full space-y-1.5 sm:w-56">
            <Label htmlFor="mes-carga">Mes</Label>
            <Select value={mes} onValueChange={setMes} disabled={usarMuestra}>
              <SelectTrigger id="mes-carga" className="w-full bg-white" aria-label="Mes de 2020">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {MESES_2020.map((m) => (
                  <SelectItem key={m} value={m}>
                    {etiquetaMes(m)}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          {historicoCargado ? (
            <MuestraAlTiempoReal />
          ) : (
            <div className="flex h-8 items-center gap-2">
              <Switch
                id="solo-muestra"
                checked={usarMuestra}
                onCheckedChange={setMuestra}
                disabled={bloqueada}
                aria-describedby={motivo ? 'motivo-muestra' : undefined}
              />
              <Label htmlFor="solo-muestra" className="font-normal text-slate-600">
                Solo 999 viajes de prueba
              </Label>
            </div>
          )}
          <Button className="sm:ml-auto" onClick={() => setConfirmando(true)} disabled={lanzar.isPending}>
            <Play aria-hidden />
            Cargar viajes
          </Button>
        </div>
        {motivo && (
          <p id="motivo-muestra" className="text-sm text-slate-600">
            {motivo}
          </p>
        )}

        <Dialog open={confirmando} onOpenChange={(abierto) => !lanzar.isPending && setConfirmando(abierto)}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>{usarMuestra ? '¿Cargar los 999 viajes de prueba?' : `¿Cargar ${etiquetaMes(mes)}?`}</DialogTitle>
              <DialogDescription>
                {usarMuestra
                  ? 'Se usarán los 999 viajes de prueba que ya están guardados. No se descarga nada. Tarda alrededor de un minuto y se vuelven a calcular los resúmenes de esa muestra.'
                  : `Se descargarán los viajes de ${etiquetaMes(mes)} (unos 90 MB) y se prepararán los resúmenes por barrio y por hora. Suele tardar varios minutos. Mientras tanto, el ordenador de la plataforma estará ocupado.`}
              </DialogDescription>
            </DialogHeader>
            <p className="text-sm text-slate-600">
              Cuando termine, el resumen se podrá ver en Privacidad, en la pestaña Cargas.
            </p>
            <DialogFooter>
              <DialogClose asChild>
                <Button variant="outline" disabled={lanzar.isPending}>
                  Cancelar
                </Button>
              </DialogClose>
              <Button onClick={confirmar} disabled={lanzar.isPending}>
                {lanzar.isPending ? <LoaderCircle className="animate-spin" aria-hidden /> : <Play aria-hidden />}
                {lanzar.isPending ? 'Cargando…' : 'Sí, cargar'}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        <div className="space-y-3">
          <div className="flex flex-wrap items-end justify-between gap-3">
            <div className="min-w-0 space-y-1">
              <h3 className="text-[15px] leading-none text-slate-900">Cargas anteriores</h3>
              <p className="text-sm text-slate-500">
                Cada fila es una vez que pediste cargar viajes. Airflow es el programa que las ejecuta; ábrelo si quieres ver más detalle.
              </p>
            </div>
            <div className="flex items-center gap-2">
              <Button variant="ghost" onClick={() => void ejecuciones.refetch()} disabled={ejecuciones.isFetching}>
                <RefreshCw className={cn(ejecuciones.isFetching && 'animate-spin')} aria-hidden />
                Actualizar
              </Button>
              <Button asChild variant="outline">
                <a href={enlaces.airflow} target="_blank" rel="noreferrer">
                  <ExternalLink aria-hidden />
                  Abrir Airflow
                </a>
              </Button>
            </div>
          </div>
          <div className="overflow-hidden rounded-xl border border-slate-200">
            <TablaEjecuciones />
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
