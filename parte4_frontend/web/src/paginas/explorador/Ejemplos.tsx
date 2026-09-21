/**
 * Ejemplos fijos y vistas guardadas en este navegador. Pulsar una lanza la consulta;
 * «Guardar esta consulta» añade la que está en los filtros, con el nombre que se quiera.
 */
import { BookmarkPlus, X } from 'lucide-react'
import { useState } from 'react'
import { toast } from 'sonner'

import type { Consulta } from '@/api/tipos'
import { Button } from '@/componentes/ui/button'
import { Input } from '@/componentes/ui/input'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/componentes/ui/tooltip'
import { cn } from '@/lib/utils'

import { describirConsulta, EJEMPLOS } from './consulta'
import { crearVista, guardarVistas, leerVistas, MAX_VISTAS, type VistaGuardada } from './vistas'

interface Props {
  onElegir: (consulta: Consulta) => void
  disabled?: boolean
  /** Consulta que saldría ahora de los filtros; `null` si no es válida y no se puede guardar. */
  borrador: Consulta | null
}

export function Ejemplos({ onElegir, disabled, borrador }: Props) {
  const [vistas, setVistas] = useState<VistaGuardada[]>(() => leerVistas())
  const [editando, setEditando] = useState(false)
  const [nombre, setNombre] = useState('')

  const persistir = (siguientes: VistaGuardada[]) => {
    setVistas(siguientes)
    try {
      guardarVistas(siguientes)
    } catch {
      toast.error('No se ha podido guardar la vista en este navegador')
    }
  }

  const abrir = () => {
    if (!borrador) return
    setNombre(describirConsulta(borrador).slice(0, 72))
    setEditando(true)
  }

  const confirmar = () => {
    const titulo = nombre.trim()
    if (!titulo || !borrador) return
    if (vistas.length >= MAX_VISTAS) {
      toast.error(`Quita alguna vista para guardar otra (máximo ${MAX_VISTAS}).`)
      return
    }
    persistir([...vistas, crearVista(titulo, borrador)])
    setEditando(false)
    setNombre('')
  }

  const quitar = (id: string) => {
    persistir(vistas.filter((vista) => vista.id !== id))
  }

  return (
    <section aria-label="Ejemplos y vistas guardadas" className="rounded-2xl border border-slate-200/80 bg-white px-4 py-3 shadow-[0_1px_2px_rgba(15,23,42,0.04)]">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-sm font-medium text-slate-800">Ejemplos</h2>
        {editando ? (
          <div className="flex items-center gap-1.5">
            <Input
              aria-label="Nombre de la vista"
              value={nombre}
              autoFocus
              placeholder="Nombre de la vista"
              className="h-8 w-56 bg-white text-xs"
              onChange={(e) => setNombre(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  e.preventDefault()
                  confirmar()
                } else if (e.key === 'Escape') {
                  setEditando(false)
                }
              }}
            />
            <Button type="button" size="sm" onClick={confirmar} disabled={!nombre.trim() || !borrador}>
              Guardar
            </Button>
            <Button type="button" size="sm" variant="ghost" onClick={() => setEditando(false)}>
              Cancelar
            </Button>
          </div>
        ) : (
          <button
            type="button"
            disabled={disabled || !borrador}
            onClick={abrir}
            title="Guarda estos filtros en este navegador para volver a verlos"
            className={cn(
              'inline-flex h-8 items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 text-xs font-medium text-slate-600 transition-colors hover:border-blue-200 hover:bg-blue-50 hover:text-blue-700 disabled:opacity-50',
            )}
          >
            <BookmarkPlus className="size-3.5" aria-hidden />
            Guardar esta consulta
          </button>
        )}
      </div>

      <ul className="mt-3 flex flex-wrap gap-1.5" aria-label="Ejemplos rápidos">
        {EJEMPLOS.map((ejemplo) => (
          <li key={ejemplo.titulo}>
            <Tooltip>
              <TooltipTrigger asChild>
                <button
                  type="button"
                  disabled={disabled}
                  onClick={() => onElegir(ejemplo.consulta)}
                  className="inline-flex h-7 items-center rounded-full border border-slate-200 bg-slate-50 px-3 text-xs font-medium text-slate-700 transition-colors hover:border-blue-200 hover:bg-blue-50 disabled:opacity-50"
                >
                  {ejemplo.titulo}
                </button>
              </TooltipTrigger>
              <TooltipContent>{ejemplo.descripcion}</TooltipContent>
            </Tooltip>
          </li>
        ))}
      </ul>

      {vistas.length > 0 && (
        <ul className="mt-2 flex flex-wrap gap-1.5" aria-label="Vistas guardadas">
          {vistas.map((vista) => (
            <li key={vista.id} className="inline-flex h-7 items-center rounded-full border border-blue-200 bg-blue-50 text-xs font-medium text-blue-800">
              <button type="button" disabled={disabled} onClick={() => onElegir(vista.consulta)} className="px-3 disabled:opacity-50">
                {vista.titulo}
              </button>
              <button
                type="button"
                onClick={() => quitar(vista.id)}
                className="mr-1 inline-flex size-5 items-center justify-center rounded-full text-blue-500 hover:bg-blue-100 hover:text-blue-800"
                aria-label={`Quitar ${vista.titulo}`}
              >
                <X className="size-3" aria-hidden />
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}
