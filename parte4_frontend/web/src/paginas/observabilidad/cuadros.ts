/**
 * Los ocho cuadros que provisiona Grafana (`observabilidad/grafana/dashboards`). El uid es el de cada JSON. La lista
 * de verdad la da el BFF; esta sirve para las pestañas mientras llega y para el subtítulo de cada una.
 */
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

/** El cuadro en Grafana, para abrirlo en otra pestaña (alertas, edición, cambiar el periodo). */
export function urlCuadro(base: string, uid: string): string {
  const raiz = base.replace(/\/$/, '')
  return `${raiz}/d/${uid}?orgId=1`
}

const LOCALES = new Set(['localhost', '127.0.0.1', '[::1]'])

/**
 * ¿Se puede abrir Grafana desde aquí? Solo cuando Grafana y la página están en este mismo equipo: Grafana se publica
 * en 127.0.0.1, así que desde la web pública (Vercel, túnel) el enlace apuntaría al equipo de quien mira. En la
 * demostración el enlace ni siquiera es un Grafana. Los cuadros del portal se ven en todos los casos.
 */
export function incrustable(base: string, paginaHost: string = window.location.hostname): boolean {
  try {
    return LOCALES.has(new URL(base).hostname) && LOCALES.has(paginaHost)
  } catch {
    return false
  }
}
