/** 👌: la última respuesta del asistente, leída en voz alta con la síntesis de voz del navegador (sin servidor). */

/** Markdown → texto que se puede leer: cada fila de una tabla como una frase; sin enlaces, negritas ni código. */
export function textoParaLeer(markdown: string, maximo = 700): string {
  const partes: string[] = []
  for (const linea of markdown.replace(/```[\s\S]*?```/g, ' ').split(/\r?\n/)) {
    const limpia = linea.trim()
    if (!limpia || /^\|?\s*:?-{3,}/.test(limpia)) continue          // vacías y separadores de tablas
    if (limpia.includes('|')) {
      const celdas = limpia.replace(/^\||\|$/g, '').split('|').map((c) => c.trim()).filter(Boolean)
      if (celdas.length) partes.push(`${celdas.join(', ')}.`)
    } else {
      partes.push(limpia)
    }
  }
  const texto = partes.join(' ')
    .replace(/!\[[^\]]*\]\([^)]*\)/g, ' ')
    .replace(/\[([^\]]+)\]\([^)]*\)/g, '$1')
    .replace(/[*_`#>]+/g, '')
    .replace(/\s+/g, ' ')
    .trim()
  return texto.length > maximo ? `${texto.slice(0, maximo).replace(/\s+\S*$/, '')}…` : texto
}

export function vozDisponible(): boolean {
  return typeof window !== 'undefined' && 'speechSynthesis' in window && typeof SpeechSynthesisUtterance !== 'undefined'
}

export function leerEnVozAlta(markdown: string): boolean {
  if (!vozDisponible()) return false
  const texto = textoParaLeer(markdown)
  if (!texto) return false
  window.speechSynthesis.cancel()
  const frase = new SpeechSynthesisUtterance(texto)
  frase.lang = 'es-ES'
  const voz = window.speechSynthesis.getVoices().find((v) => v.lang.startsWith('es'))
  if (voz) frase.voice = voz
  window.speechSynthesis.speak(frase)
  return true
}

/** Calla la lectura en curso. Devuelve `true` si estaba hablando. */
export function callar(): boolean {
  if (!vozDisponible()) return false
  const hablaba = window.speechSynthesis.speaking || window.speechSynthesis.pending
  window.speechSynthesis.cancel()
  return hablaba
}
