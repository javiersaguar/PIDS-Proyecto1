/**
 * Estado de una conversación con el asistente: sesión en el BFF, hilo de mensajes y flujo SSE de cada turno.
 *
 *   const conversacion = useConversacion('ollama')
 *   conversacion.enviar('¿Cuántos viajes salieron de JFK el 15 de enero?')
 *
 * - Al cambiar de motor (o con `reiniciar`) se cierra la sesión anterior y se crea otra; al desmontar, se cierra.
 * - Cada turno añade el mensaje del usuario y un mensaje del asistente «en curso» que se va rellenando con los
 *   eventos `paso` y termina con `respuesta` (o `error`).
 * - Un 401 en cualquier punto es una sesión del portal caducada: se marca en la caché y se navega a `/acceso`,
 *   lo mismo que hace la guardia de sesión con los 401 del cliente HTTP.
 */
import { useQueryClient } from '@tanstack/react-query'
import { useCallback, useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router'

import { cerrarSesion, crearSesion, enviarMensaje, pedirAlternativa, type AlRecibirEvento, type SesionChat } from '@/api/chat'
import { marcarChatActivo } from '@/api/chatActivo'
import { ErrorApi, mensajeDeError } from '@/api/cliente'
import { CLAVE_SESION } from '@/api/sesion'
import type { EstadoSesion, Motor } from '@/api/tipos'

import { esAsistente, type MensajeAsistente, type MensajeChat } from './tipos'

interface SesionConClave extends SesionChat {
  clave: string
}
interface ErrorConClave {
  clave: string
  error: unknown
}

type Ejecutar = (alRecibir: AlRecibirEvento, señal: AbortSignal) => Promise<void>

export interface Conversacion {
  mensajes: MensajeChat[]
  /** Sesión viva en el BFF para el motor actual (null mientras se crea o si falló). */
  sesion: SesionChat | null
  creandoSesion: boolean
  errorSesion: unknown
  /** Hay una respuesta en camino. */
  enCurso: boolean
  enviar: (texto: string) => void
  aceptarAlternativa: (idMensaje: string) => void
  cancelarAlternativa: (idMensaje: string) => void
  /** Corta la respuesta en curso. */
  detener: () => void
  /** Vacía el hilo y abre una sesión nueva con el mismo motor. */
  reiniciar: () => void
  reintentarSesion: () => void
}

function mensajeAsistenteVacio(id: string): MensajeAsistente {
  return { id, rol: 'asistente', texto: '', pasos: [], respuesta: null, enCurso: true, error: null, alternativaResuelta: null }
}

/** Las alternativas anteriores dejan de estar pendientes cuando llega un turno nuevo (el agente las sustituye). */
function cerrarAlternativasPendientes(lista: MensajeChat[]): MensajeChat[] {
  return lista.map((m) =>
    esAsistente(m) && m.respuesta?.alternativa && !m.alternativaResuelta ? { ...m, alternativaResuelta: 'cancelada' } : m,
  )
}

export function useConversacion(motor: Motor['id'] | null): Conversacion {
  const [mensajes, setMensajes] = useState<MensajeChat[]>([])
  const [generacion, setGeneracion] = useState(0)
  const [sesionGuardada, setSesionGuardada] = useState<SesionConClave | null>(null)
  const [errorGuardado, setErrorGuardado] = useState<ErrorConClave | null>(null)
  const contador = useRef(0)
  const controlador = useRef<AbortController | null>(null)
  const clienteConsultas = useQueryClient()
  const navegar = useNavigate()

  const clave = motor ? `${motor}#${generacion}` : null
  const sesion = sesionGuardada && sesionGuardada.clave === clave ? sesionGuardada : null
  const errorSesion = errorGuardado && errorGuardado.clave === clave ? errorGuardado.error : null
  const creandoSesion = clave !== null && sesion === null && errorSesion === null
  const enCurso = mensajes.some((m) => esAsistente(m) && m.enCurso)

  // Sesión en el BFF: una por motor y generación; la anterior se cierra al cambiar y al desmontar.
  useEffect(() => {
    if (!motor || !clave) return
    let cancelado = false
    let idCreado: string | null = null
    crearSesion(motor)
      .then((creada) => {
        if (cancelado) {
          void cerrarSesion(creada.id).catch(() => undefined)
          return
        }
        idCreado = creada.id
        setSesionGuardada({ ...creada, clave })
      })
      .catch((error: unknown) => {
        if (!cancelado) setErrorGuardado({ clave, error })
      })
    return () => {
      cancelado = true
      controlador.current?.abort()
      if (idCreado) void cerrarSesion(idCreado).catch(() => undefined)
    }
  }, [motor, clave])

  const nuevoId = useCallback(() => {
    contador.current += 1
    return `m${contador.current}`
  }, [])

  const actualizar = useCallback((id: string, cambio: (m: MensajeAsistente) => MensajeAsistente) => {
    setMensajes((lista) => lista.map((m) => (m.id === id && esAsistente(m) ? cambio(m) : m)))
  }, [])

  const sesionPerdida = useCallback(() => {
    clienteConsultas.setQueryData<EstadoSesion>(CLAVE_SESION, { autenticado: false })
    void navegar('/acceso', { replace: true, state: { caducada: true } })
  }, [clienteConsultas, navegar])

  const transmitir = useCallback(
    async (idAsistente: string, ejecutar: Ejecutar) => {
      const propio = new AbortController()
      controlador.current = propio
      let terminado = false
      if (motor) marcarChatActivo(motor)
      try {
        await ejecutar((evento) => {
          if (evento.tipo === 'paso') {
            actualizar(idAsistente, (m) => ({ ...m, pasos: [...m.pasos, evento.datos] }))
          } else if (evento.tipo === 'respuesta') {
            terminado = true
            actualizar(idAsistente, (m) => ({ ...m, texto: evento.datos.respuesta, respuesta: evento.datos, enCurso: false }))
          } else {
            terminado = true
            actualizar(idAsistente, (m) => ({ ...m, error: evento.datos.detail, enCurso: false }))
          }
        }, propio.signal)
        if (!terminado) {
          actualizar(idAsistente, (m) => ({ ...m, error: 'El asistente ha cerrado la conexión sin responder', enCurso: false }))
        }
      } catch (error) {
        if (error instanceof DOMException && error.name === 'AbortError') {
          actualizar(idAsistente, (m) => ({ ...m, enCurso: false, error: m.respuesta ? m.error : 'Respuesta detenida' }))
        } else if (error instanceof ErrorApi && error.status === 401) {
          actualizar(idAsistente, (m) => ({ ...m, enCurso: false, error: error.detail }))
          sesionPerdida()
        } else {
          actualizar(idAsistente, (m) => ({ ...m, enCurso: false, error: mensajeDeError(error) }))
        }
      } finally {
        marcarChatActivo(null)
        if (controlador.current === propio) controlador.current = null
      }
    },
    [actualizar, motor, sesionPerdida],
  )

  const enviar = useCallback(
    (texto: string) => {
      const limpio = texto.trim()
      if (!limpio || !sesion || enCurso) return
      const idAsistente = nuevoId()
      const mensajeUsuario: MensajeChat = { id: nuevoId(), rol: 'usuario', texto: limpio }
      setMensajes((lista) => [...cerrarAlternativasPendientes(lista), mensajeUsuario, mensajeAsistenteVacio(idAsistente)])
      void transmitir(idAsistente, (alRecibir, señal) => enviarMensaje(sesion.id, limpio, alRecibir, señal))
    },
    [sesion, enCurso, transmitir, nuevoId],
  )

  const aceptarAlternativa = useCallback(
    (idMensaje: string) => {
      const origen = mensajes.find((m) => m.id === idMensaje)
      if (!origen || !esAsistente(origen) || !origen.respuesta?.alternativa || !sesion || enCurso) return
      const descripcion = origen.respuesta.alternativa_descripcion
      const idAsistente = nuevoId()
      const mensajeUsuario: MensajeChat = {
        id: nuevoId(),
        rol: 'usuario',
        texto: descripcion ? `✅ Consultar la alternativa: ${descripcion}` : '✅ Consultar la alternativa',
      }
      setMensajes((lista) => [
        ...lista.map((m) => (m.id === idMensaje && esAsistente(m) ? { ...m, alternativaResuelta: 'aceptada' as const } : m)),
        mensajeUsuario,
        mensajeAsistenteVacio(idAsistente),
      ])
      void transmitir(idAsistente, (alRecibir, señal) => pedirAlternativa(sesion.id, alRecibir, señal))
    },
    [mensajes, sesion, enCurso, transmitir, nuevoId],
  )

  const cancelarAlternativa = useCallback((idMensaje: string) => {
    const idAviso = nuevoId()
    setMensajes((lista) => [
      ...lista.map((m) => (m.id === idMensaje && esAsistente(m) ? { ...m, alternativaResuelta: 'cancelada' as const } : m)),
      { ...mensajeAsistenteVacio(idAviso), texto: 'De acuerdo, consulta cancelada.', enCurso: false, local: true },
    ])
  }, [nuevoId])

  const detener = useCallback(() => {
    controlador.current?.abort()
  }, [])

  const reiniciar = useCallback(() => {
    controlador.current?.abort()
    setMensajes([])
    setGeneracion((g) => g + 1)
  }, [])

  const reintentarSesion = useCallback(() => {
    setGeneracion((g) => g + 1)
  }, [])

  return {
    mensajes,
    sesion,
    creandoSesion,
    errorSesion,
    enCurso,
    enviar,
    aceptarAlternativa,
    cancelarAlternativa,
    detener,
    reiniciar,
    reintentarSesion,
  }
}
