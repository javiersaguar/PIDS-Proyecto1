/**
 * Datos del modo demostración: la instantánea que graba `parte4_frontend/demo/instantanea.py` en `public/demo/`.
 * Son respuestas de la API de acceso con el filtro de privacidad ya aplicado (los grupos de menos de 10 viajes
 * vienen como `"oculto"`, sin cifras), más el estado de los servicios, la auditoría y conversaciones grabadas del
 * asistente. Cada fichero se descarga la primera vez que hace falta.
 */
import type { Zona } from '@/api/tipos'

import { aIso, aMilisegundos, campoTiempo, type ConsultaApi, type FilaGuardada } from './privacidad'

export interface Manifiesto {
  generado: string
  dias_hora_zona: string[]
  zonas_todo_el_anio: number[]
  dia_tiempo_real: string
}

interface Columnas {
  columnas: string[]
  filas: unknown[][]
}

/** Cómo se lee un fichero de la instantánea (en el navegador, `fetch`; en los tests, `import.meta.glob`). */
export type Lector = (ruta: string) => Promise<unknown>

const DIA = 86_400_000

export class Instantanea {
  private readonly lector: Lector
  private readonly cache = new Map<string, Promise<unknown>>()

  constructor(lector: Lector) {
    this.lector = lector
  }

  leer<T>(ruta: string): Promise<T> {
    let promesa = this.cache.get(ruta)
    if (!promesa) {
      promesa = this.lector(ruta)
      promesa.catch(() => this.cache.delete(ruta))      // que un fallo de red no quede cacheado
      this.cache.set(ruta, promesa)
    }
    return promesa as Promise<T>
  }

  manifiesto(): Promise<Manifiesto> {
    return this.leer<Manifiesto>('manifiesto.json')
  }

  zonas(): Promise<Zona[]> {
    return this.leer<Zona[]>('zonas.json')
  }

  private async tabla(ruta: string): Promise<FilaGuardada[]> {
    const { columnas, filas } = await this.leer<Columnas>(ruta)
    return filas.map((fila) => Object.fromEntries(columnas.map((c, i) => [c, fila[i]])))
  }

  /** Filas `hora_zona` con el nombre y el barrio de la zona, que la instantánea no repite en cada fila. */
  private async tablaHoraZona(ruta: string): Promise<FilaGuardada[]> {
    const [filas, zonas] = await Promise.all([this.tabla(ruta), this.zonas()])
    const porId = new Map(zonas.map((z) => [z._id, z]))
    return filas.map((fila) => {
      const zona = porId.get(fila.zona_origen as number)
      return { ...fila, zona_origen_nombre: zona?.nombre, barrio_origen: zona?.barrio }
    })
  }

  /**
   * Las filas publicadas que puede necesitar la consulta (antes de filtrarlas) y si falta alguna parte de su ventana
   * en la instantánea. El «tiempo real» de la demostración es la reproducción de un día histórico.
   */
  async candidatas(consulta: ConsultaApi): Promise<{ filas: FilaGuardada[]; incompleta: boolean }> {
    const manifiesto = await this.manifiesto()
    let desde = aMilisegundos(consulta.desde)!
    let hasta = aMilisegundos(consulta.hasta)!
    if (consulta.fuente === 'tiempo_real') {
      const dia = aMilisegundos(manifiesto.dia_tiempo_real)!
      desde = Math.max(desde, dia)
      hasta = Math.min(hasta, dia + DIA)
      if (desde >= hasta) return { filas: [], incompleta: false }
    }
    const { filas, incompleta } = await this.porNivel(consulta, manifiesto, desde, hasta)
    const tiempo = campoTiempo(consulta.nivel)
    const [inicio, fin] = [aIso(desde), aIso(hasta)]
    return { filas: filas.filter((f) => String(f[tiempo]) >= inicio && String(f[tiempo]) < fin), incompleta }
  }

  private async porNivel(consulta: ConsultaApi, manifiesto: Manifiesto, desde: number, hasta: number) {
    const dias: string[] = []
    for (let t = Math.floor(desde / DIA) * DIA; t < hasta; t += DIA) dias.push(aIso(t).slice(0, 10))
    const de2020 = dias.filter((d) => d.startsWith('2020-'))
    if (consulta.nivel === 'dia_barrio') return { filas: await this.tabla('dia_barrio.json'), incompleta: false }
    if (consulta.nivel === 'od_dia_barrio') {
      const meses = [...new Set(de2020.map((d) => d.slice(0, 7)))]
      const partes = await Promise.all(meses.map((m) => this.tabla(`od/${m}.json`)))
      return { filas: partes.flat(), incompleta: false }
    }
    if (consulta.zona_origen !== null && manifiesto.zonas_todo_el_anio.includes(consulta.zona_origen)) {
      return { filas: await this.tablaHoraZona(`zona/${consulta.zona_origen}.json`), incompleta: false }
    }
    const grabados = de2020.filter((d) => manifiesto.dias_hora_zona.includes(d))
    const partes = await Promise.all(grabados.map((d) => this.tablaHoraZona(`hora_zona/${d}.json`)))
    return { filas: partes.flat(), incompleta: grabados.length < de2020.length }
  }
}

/** Nota que se añade cuando la instantánea no tiene todo el detalle por hora y zona que pide la consulta. */
export function notaIncompleta(manifiesto: Manifiesto): string {
  const dias = manifiesto.dias_hora_zona.map((d) => `${d.slice(8, 10)}/${d.slice(5, 7)}`).join(', ')
  return (
    `Demostración: el detalle por hora y zona solo está grabado para el ${dias} de 2020 y, todo el año, para ` +
    'JFK, LaGuardia, Times Square y Stapleton. El resto de horas de esta consulta no está en la demostración.'
  )
}
