/**
 * Frases en español para una decisión de auditoría: qué se preguntó, por qué quedó así
 * y qué consulta se propuso en su lugar. La fila enseña el resumen; el detalle, el resto.
 */
import type { Consulta, DecisionAuditada, Nivel } from '@/api/tipos'
import { abreviar, formatearFechaHora, formatearNumero } from '@/componentes/chat/formato'

import { NOMBRE_NIVEL } from './etiquetas'

function leer(origen: object, clave: string): unknown {
  return (origen as Record<string, unknown>)[clave]
}

function unir(partes: string[]): string {
  if (partes.length <= 1) return partes[0] ?? ''
  return `${partes.slice(0, -1).join(', ')} y ${partes[partes.length - 1]}`
}

function textoLibre(consulta: object): string | null {
  for (const clave of ['texto', 'individual', 'descripcion']) {
    const valor = leer(consulta, clave)
    if (typeof valor === 'string' && valor.trim()) return valor.trim()
  }
  return null
}

/** Cómo se pidió la consulta, en una frase, sin identificadores técnicos. */
export function describirConsulta(consulta: object): { libre: string | null; agregada: string | null } {
  const libre = textoLibre(consulta)
  const nivelBruto = leer(consulta, 'nivel')
  const nivel = typeof nivelBruto === 'string' ? (NOMBRE_NIVEL[nivelBruto as Nivel] ?? nivelBruto.replaceAll('_', ' ')) : null
  const desde = typeof leer(consulta, 'desde') === 'string' ? formatearFechaHora(leer(consulta, 'desde') as string) : null
  const hasta = typeof leer(consulta, 'hasta') === 'string' ? formatearFechaHora(leer(consulta, 'hasta') as string) : null
  const filtros: string[] = []
  const barrioOrigen = leer(consulta, 'barrio_origen')
  const barrioDestino = leer(consulta, 'barrio_destino')
  const zona = leer(consulta, 'zona_origen')
  if (typeof barrioOrigen === 'string' && barrioOrigen) filtros.push(`desde ${barrioOrigen}`)
  if (typeof barrioDestino === 'string' && barrioDestino) filtros.push(`hacia ${barrioDestino}`)
  if (typeof zona === 'number') filtros.push(`zona de origen ${zona}`)
  const trozos = [
    nivel ? nivel.charAt(0).toLowerCase() + nivel.slice(1) : null,
    desde && hasta && desde !== '—' && hasta !== '—' ? `del ${desde} al ${hasta}` : null,
    filtros.length ? unir(filtros) : null,
  ].filter((trozo): trozo is string => Boolean(trozo))
  return { libre, agregada: trozos.length ? trozos.join(', ') : null }
}

/** El motivo guardado en la auditoría, dicho como se lo explicarías a alguien. */
export function humanizarMotivo(motivo: string): string {
  const tipo = motivo.split(':')[0]?.trim().toLowerCase() ?? ''
  if (!tipo) return 'No cumplía las reglas de privacidad.'
  if (tipo.startsWith('petición de datos individuales') || tipo.startsWith('pide campos individuales')) {
    return 'Pedía datos de un viaje concreto, y eso no se publica.'
  }
  if (tipo.startsWith('campos no publicados')) return 'Pedía campos que la API no publica.'
  if (tipo.startsWith('métricas no publicadas')) return 'Pedía una métrica que no está publicada.'
  if (tipo.startsWith('el destino solo se publica')) return 'El destino solo se puede consultar por barrio y por día.'
  if (tipo.includes('no filtra por barrio')) return 'Ese agrupamiento no se puede filtrar por barrio.'
  if (tipo.includes('desconocido')) return 'El barrio pedido no existe.'
  if (tipo.includes('no tiene zona')) return 'Ese agrupamiento no distingue zonas; se agrupa por barrio.'
  if (tipo.startsWith('la ventana temporal está vacía')) return 'El periodo pedido estaba vacío.'
  if (tipo.startsWith('la granularidad mínima')) return 'Pedía un instante más fino que una hora o un día completos.'
  if (tipo.startsWith('el rango máximo') || tipo.startsWith('ventana demasiado corta')) {
    return 'El periodo pedido supera lo que se puede consultar de una vez.'
  }
  if (tipo.startsWith('la plataforma solo publica agregados')) return 'Solo se publican grupos de al menos 10 viajes.'
  return /[.!?]$/.test(motivo.trim()) ? motivo.trim() : `${motivo.trim()}.`
}

/** Una línea para la fila: qué ocurrió, sin volcar la consulta. */
export function resumenDecision(decision: DecisionAuditada): string {
  const { libre, agregada } = describirConsulta(decision.consulta)
  const asunto = libre ? `la pregunta «${abreviar(libre, 90)}»` : agregada ? `una consulta ${agregada}` : 'la consulta'
  if (decision.resultado === 'rechazada') {
    return `Se rechazó ${asunto}. ${humanizarMotivo(decision.motivos[0] ?? '')}`
  }
  if (decision.resultado === 'enmascarada') {
    const n = decision.grupos_enmascarados ?? 0
    const grupos = n === 1 ? 'grupo' : 'grupos'
    return `Se respondió ${asunto}, ocultando ${formatearNumero(n)} ${grupos} con pocos viajes.`
  }
  if (decision.filas_devueltas !== undefined) {
    const filas = decision.filas_devueltas === 1 ? 'fila' : 'filas'
    return `Se respondió ${asunto}. ${formatearNumero(decision.filas_devueltas)} ${filas}.`
  }
  return `Se respondió ${asunto}.`
}

const NOMBRE_CLIENTE: Record<string, string> = {
  chatbot: 'Chatbot',
  frontend: 'Este portal',
  equipo: 'El equipo',
  airflow: 'Airflow',
}

/** Quién hizo la consulta, con un nombre y no con el identificador. */
export function nombreCliente(cliente: string): string {
  return NOMBRE_CLIENTE[cliente] ?? cliente
}

/** La alternativa que propuso la API, en la misma forma que la consulta. */
export function describirAlternativa(alternativa: Consulta): string {
  const { agregada } = describirConsulta(alternativa)
  if (!agregada) return 'Hay una consulta agregada que sí se puede responder.'
  return `${agregada.charAt(0).toUpperCase()}${agregada.slice(1)}.`
}
