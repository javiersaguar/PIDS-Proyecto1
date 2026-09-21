/**
 * Tarjeta «Carga histórica»: elige un mes de 2020 (o solo la muestra), confirma en un diálogo lo que va a pasar
 * (descarga de ~90 MB, minutos de Spark) y lanza el DAG `pids_carga_historica` en Airflow. Debajo, las últimas
 * ejecuciones del DAG con su estado, refrescadas cada 15 s, y el enlace a la interfaz de Airflow.
 */
import { differenceInSeconds, parseISO } from 'date-fns'
import { ExternalLink, LoaderCircle, Play, RefreshCw } from 'lucide-react'
import { useState } from 'react'
import { toast } from 'sonner'

import { mensajeDeError } from '@/api/cliente'
import { MESES_2020, useEjecucionesAirflow, useEnlaces, useLanzarCarga } from '@/api/operaciones'
import type { EjecucionAirflow } from '@/api/tipos'
import { formatearFechaHora, formatearSegundos } from '@/componentes/chat/formato'
import { EstadoCargando, EstadoError, EstadoVacio } from '@/componentes/shell'
import { Badge } from '@/componentes/ui/badge'
import { Button } from '@/componentes/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/componentes/ui/card'
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
    <Badge variant="outline" className={cn('h-5 gap-1 px-1.5 font-medium', CLASE_ESTADO[estado] ?? 'bg-muted text-texto-suave')}>
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
  if (muestra) return mes ? `muestra (${mes})` : 'muestra'
  return mes ?? '—'
}

function TablaEjecuciones() {
  const ejecuciones = useEjecucionesAirflow()
  if (ejecuciones.isPending) return <EstadoCargando lineas={4} etiqueta="Cargando las ejecuciones de Airflow…" />
  if (ejecuciones.isError) {
    return (
      <EstadoError
        titulo="No se han podido leer las ejecuciones de Airflow"
        error={ejecuciones.error}
        alReintentar={() => void ejecuciones.refetch()}
        reintentando={ejecuciones.isFetching}
      />
    )
  }
  if (ejecuciones.data.length === 0) {
    return <EstadoVacio titulo="Sin ejecuciones" descripcion="El DAG pids_carga_historica todavía no se ha lanzado nunca." />
  }
  return (
    <Table>
      <TableHeader>
        <TableRow className="bg-superficie-alterna/60 hover:bg-superficie-alterna/60">
          <TableHead scope="col">Ejecución</TableHead>
          <TableHead scope="col">Estado</TableHead>
          <TableHead scope="col">Carga</TableHead>
          <TableHead scope="col">Inicio</TableHead>
          <TableHead scope="col">Fin</TableHead>
          <TableHead scope="col" className="text-right">
            Duración
          </TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {ejecuciones.data.map((ejecucion) => (
          <TableRow key={ejecucion.dag_run_id}>
            <TableCell className="max-w-64 truncate font-mono text-xs" title={ejecucion.dag_run_id}>
              {ejecucion.dag_run_id}
            </TableCell>
            <TableCell>
              <ChipEstadoAirflow estado={ejecucion.estado} />
            </TableCell>
            <TableCell>{descripcionConf(ejecucion.conf ?? {})}</TableCell>
            <TableCell className="cifra text-texto-suave">{formatearFechaHora(ejecucion.inicio)}</TableCell>
            <TableCell className="cifra text-texto-suave">{formatearFechaHora(ejecucion.fin)}</TableCell>
            <TableCell className="cifra text-right">{duracion(ejecucion)}</TableCell>
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
  const ejecuciones = useEjecucionesAirflow()
  const { enlaces } = useEnlaces()

  const confirmar = () => {
    lanzar.mutate(
      { mes, muestra },
      {
        onSuccess: (ejecucion) => {
          setConfirmando(false)
          toast.success('Carga lanzada en Airflow', { description: `Ejecución ${ejecucion.dag_run_id}` })
        },
        onError: (error) => {
          toast.error('No se ha podido lanzar la carga', { description: mensajeDeError(error) })
        },
      },
    )
  }

  return (
    <Card className="sombra-tarjeta">
      <CardHeader>
        <CardTitle>Carga histórica</CardTitle>
        <CardDescription>
          Lanza el DAG <code className="font-mono text-[11px]">pids_carga_historica</code>: Airflow descarga el mes de la TLC a S3, Spark
          valida, archiva y publica los agregados protegidos, y el resumen queda en <code className="font-mono text-[11px]">auditoria.cargas</code>.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-5">
        <div className="flex flex-wrap items-end gap-4">
          <div className="space-y-1.5">
            <Label htmlFor="mes-carga">Mes de 2020</Label>
            <Select value={mes} onValueChange={setMes} disabled={muestra}>
              <SelectTrigger id="mes-carga" className="min-w-44" aria-label="Mes de 2020">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {MESES_2020.map((m) => (
                  <SelectItem key={m} value={m}>
                    {etiquetaMes(m)} <span className="font-mono text-xs text-texto-suave">({m})</span>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="flex h-8 items-center gap-2">
            <Switch id="solo-muestra" checked={muestra} onCheckedChange={setMuestra} />
            <Label htmlFor="solo-muestra" className="font-normal">
              Solo la muestra <span className="text-texto-suave">(999 viajes de data/muestra, sin descargar nada)</span>
            </Label>
          </div>
          <Button className="ml-auto" onClick={() => setConfirmando(true)} disabled={lanzar.isPending}>
            <Play aria-hidden />
            Lanzar en Airflow
          </Button>
        </div>

        <Dialog open={confirmando} onOpenChange={(abierto) => !lanzar.isPending && setConfirmando(abierto)}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>{muestra ? 'Cargar la muestra' : `Cargar ${etiquetaMes(mes)}`}</DialogTitle>
              <DialogDescription>
                {muestra
                  ? 'Airflow lanzará el trabajo de Spark con los 999 viajes de data/muestra, sin descargar nada. Tarda alrededor de un minuto y vuelve a publicar los agregados de esa muestra.'
                  : `Airflow descargará el fichero Parquet de ${etiquetaMes(mes)} de la web de la TLC (~90 MB), lo dejará en S3 y lanzará el trabajo de Spark en modo cluster. Suele tardar varios minutos y ocupa la CPU y la memoria de la plataforma mientras dura.`}
              </DialogDescription>
            </DialogHeader>
            <p className="text-texto-suave">
              La ejecución quedará registrada en Airflow y, al terminar, el resumen de la carga aparecerá en Privacidad → Cargas.
            </p>
            <DialogFooter>
              <DialogClose asChild>
                <Button variant="outline" disabled={lanzar.isPending}>
                  Cancelar
                </Button>
              </DialogClose>
              <Button onClick={confirmar} disabled={lanzar.isPending}>
                {lanzar.isPending ? <LoaderCircle className="animate-spin" aria-hidden /> : <Play aria-hidden />}
                {lanzar.isPending ? 'Lanzando…' : 'Confirmar y lanzar'}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        <div className="space-y-2">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h3 className="text-sm font-semibold">Últimas ejecuciones</h3>
            <div className="flex items-center gap-1">
              <Button variant="ghost" size="sm" onClick={() => void ejecuciones.refetch()} disabled={ejecuciones.isFetching}>
                <RefreshCw className={cn(ejecuciones.isFetching && 'animate-spin')} aria-hidden />
                Actualizar
              </Button>
              <Button asChild variant="outline" size="sm">
                <a href={enlaces.airflow} target="_blank" rel="noreferrer">
                  <ExternalLink aria-hidden />
                  Abrir Airflow
                </a>
              </Button>
            </div>
          </div>
          <TablaEjecuciones />
        </div>
      </CardContent>
    </Card>
  )
}
