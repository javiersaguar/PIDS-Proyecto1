/**
 * Barra sobre el lienzo: qué está haciendo la plataforma ahora (una frase por proceso) y, si no hay nada,
 * cuál fue la última carga y desde dónde se lanza algo. Es la explicación de los tramos que se iluminan.
 */
import { Activity, CalendarClock, MessageSquareText, Radio, Workflow, type LucideIcon } from 'lucide-react'
import { Link } from 'react-router'

import { describirActividad, describirCarga, type Actividad } from '@/api/actividad'
import { describirAntiguedad } from '@/componentes/datos/formato'
import { cn } from '@/lib/utils'

const ICONO: Record<'carga' | 'simulacion' | 'publicando' | 'chat', { icono: LucideIcon; clase: string }> = {
  carga: { icono: Workflow, clase: 'bg-[#fff6e4] text-[#b7791f]' },
  simulacion: { icono: Radio, clase: 'bg-[#e8faf2] text-[#17875a]' },
  publicando: { icono: Activity, clase: 'bg-[#f3eeff] text-[#6d4eae]' },
  chat: { icono: MessageSquareText, clase: 'bg-[#e7f8f8] text-[#0e7c7c]' },
}

function ultimaCarga(actividad: Actividad): string | null {
  const ultima = actividad.ultimaCarga
  if (!ultima) return null
  const resultado = ultima.estado === 'success' ? 'correcta' : ultima.estado === 'failed' ? 'fallida' : ultima.estado
  const cuando = ultima.segundos == null ? '' : `, ${describirAntiguedad(ultima.segundos)}`
  return `Última carga: ${describirCarga(ultima.mes, ultima.muestra)}, ${resultado}${cuando}`
}

export function BarraActividad({ actividad, className }: { actividad: Actividad; className?: string }) {
  const frases = describirActividad(actividad)
  const claves = ([['carga', actividad.carga], ['simulacion', actividad.simulacion], ['publicando', actividad.publicando], ['chat', actividad.chatOllama], ['chat', actividad.chatHelmcode]] as const)
    .filter(([, hay]) => !!hay)
    .map(([clave]) => clave)

  return (
    <div
      role="status"
      aria-label="Actividad de la plataforma"
      className={cn('flex flex-wrap items-center gap-x-4 gap-y-2 rounded-2xl border border-[#e6edf5] bg-white/90 px-4 py-2.5 text-[13px] shadow-[0_1px_2px_rgba(15,23,42,0.04)]', className)}
    >
      <span className="flex items-center gap-2 font-semibold text-slate-700">
        <span className="relative flex size-2.5" aria-hidden>
          {actividad.enMarcha && <span className="punto-vivo absolute inset-0 rounded-full bg-emerald-400/60" />}
          <span className={cn('relative size-2.5 rounded-full', actividad.enMarcha ? 'bg-emerald-500' : 'bg-slate-300')} />
        </span>
        {actividad.enMarcha ? 'En marcha ahora' : 'Sin procesos en marcha'}
      </span>

      {frases.map((frase, indice) => {
        const { icono: Icono, clase } = ICONO[claves[indice] ?? 'publicando']
        return (
          <span key={frase} className="flex items-center gap-1.5 text-slate-600">
            <span className={cn('flex size-6 items-center justify-center rounded-lg', clase)} aria-hidden>
              <Icono className="size-3.5" />
            </span>
            {frase}
          </span>
        )
      })}

      {!actividad.enMarcha && (
        <>
          {ultimaCarga(actividad) && (
            <span className="flex items-center gap-1.5 text-slate-500">
              <CalendarClock className="size-3.5 text-slate-400" aria-hidden />
              {ultimaCarga(actividad)}
            </span>
          )}
          <Link to="/operaciones" className="ml-auto rounded-full bg-[#eaf2ff] px-3 py-1 text-xs font-semibold text-[#2f62c4] hover:bg-[#dce9ff]">
            Lanzar una carga o el simulador
          </Link>
        </>
      )}
      {actividad.enMarcha && (
        <span className="ml-auto text-xs text-slate-400">Los tramos iluminados son los que están trabajando</span>
      )}
    </div>
  )
}
