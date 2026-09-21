/**
 * Semáforo de frescura del tiempo real: verde si la última escritura de Spark tiene menos de 2 min, ámbar si
 * menos de 10 min, rojo si más o si no hay dato.
 */
export type NivelFrescura = 'ok' | 'aviso' | 'peligro'

export const UMBRALES_FRESCURA = { ok: 2 * 60, aviso: 10 * 60 } as const

export const TEXTO_FRESCURA: Record<NivelFrescura, string> = {
  ok: 'al día',
  aviso: 'con retraso',
  peligro: 'sin datos recientes',
}

export function nivelFrescura(segundos: number | null | undefined): NivelFrescura {
  if (segundos == null || !Number.isFinite(segundos) || segundos < 0) return 'peligro'
  if (segundos < UMBRALES_FRESCURA.ok) return 'ok'
  if (segundos < UMBRALES_FRESCURA.aviso) return 'aviso'
  return 'peligro'
}
