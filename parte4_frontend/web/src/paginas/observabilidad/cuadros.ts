/** Los ocho cuadros que provisiona Grafana (`observabilidad/grafana/dashboards`). El uid es el de cada JSON. */
export interface Cuadro {
  uid: string
  titulo: string
  texto: string
}

export const CUADROS: readonly Cuadro[] = [
  { uid: 'pids-plataforma', titulo: 'Plataforma', texto: 'Servicios, frescura, cola y alertas' },
  { uid: 'pids-privacidad', titulo: 'Privacidad', texto: 'Permitidas, enmascaradas y rechazadas' },
  { uid: 'pids-chatbots', titulo: 'Chatbots', texto: 'Ollama, DeepSeek y el asistente de esta web' },
  { uid: 'pids-kafka', titulo: 'Kafka', texto: 'Viajes, gestos y la captura' },
  { uid: 'pids-spark', titulo: 'Spark', texto: 'Workers, núcleos y memoria' },
  { uid: 'pids-mongo', titulo: 'MongoDB', texto: 'Agregados publicados, no viajes sueltos' },
  { uid: 'pids-s3', titulo: 'S3', texto: 'El crudo y el disco de SeaweedFS' },
  { uid: 'pids-tiempo-real', titulo: 'Tiempo real', texto: 'De la entrada a la tabla' },
]

export function urlCuadro(base: string, uid: string): string {
  const raiz = base.replace(/\/$/, '')
  return `${raiz}/d/${uid}?orgId=1&kiosk&theme=light`
}

const LOCALES = new Set(['localhost', '127.0.0.1', '[::1]'])

/**
 * ¿Se puede incrustar Grafana aquí? Solo cuando Grafana y la página están en este mismo equipo: Grafana se publica
 * en 127.0.0.1, así que desde la web pública (Vercel, túnel) el marco apuntaría al equipo de quien mira, y además una
 * página https no puede cargar un marco http. En la demostración el enlace ni siquiera es un Grafana.
 */
export function incrustable(base: string, paginaHost: string = window.location.hostname): boolean {
  try {
    return LOCALES.has(new URL(base).hostname) && LOCALES.has(paginaHost)
  } catch {
    return false
  }
}
