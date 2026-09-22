import { act, renderHook } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { useCambioDe } from './useCambioDe'
import { interpolar, suavizar, useNumeroAnimado, useValoresAnimados } from './useNumeroAnimado'

describe('suavizado', () => {
  it('empieza en 0, acaba en 1 y frena al final', () => {
    expect(suavizar(0)).toBe(0)
    expect(suavizar(1)).toBe(1)
    expect(suavizar(0.5)).toBeGreaterThan(0.5)
    expect(suavizar(2)).toBe(1)
    expect(interpolar(100, 200, 0)).toBe(100)
    expect(interpolar(100, 200, 1)).toBe(200)
  })
})

describe('useValoresAnimados', () => {
  let ahora = 0
  beforeEach(() => {
    ahora = 0
    vi.useFakeTimers()
    vi.spyOn(performance, 'now').mockImplementation(() => ahora)
    // un fotograma cada 16 ms, con el reloj simulado
    vi.stubGlobal('requestAnimationFrame', (cb: FrameRequestCallback) => setTimeout(() => cb((ahora += 16)), 16) as unknown as number)
    vi.stubGlobal('cancelAnimationFrame', (id: number) => clearTimeout(id))
  })
  afterEach(() => {
    vi.useRealTimers()
  })

  it('en el primer render muestra los valores tal cual', () => {
    const { result } = renderHook(() => useValoresAnimados([10, 20]))
    expect(result.current).toEqual([10, 20])
  })

  it('al cambiar, recorre el camino y termina exactamente en el valor nuevo', () => {
    const { result, rerender, unmount } = renderHook(({ valores }: { valores: number[] }) => useValoresAnimados(valores, 100), {
      initialProps: { valores: [100] },
    })
    rerender({ valores: [200] })
    act(() => vi.advanceTimersByTime(48))
    const intermedio = result.current[0]
    expect(intermedio).toBeGreaterThan(100)
    expect(intermedio).toBeLessThan(200)
    act(() => vi.advanceTimersByTime(200))
    expect(result.current).toEqual([200])
    unmount()
  })

  it('un array nuevo con los mismos valores no reinicia nada', () => {
    const { result, rerender } = renderHook(({ valores }: { valores: number[] }) => useValoresAnimados(valores, 100), {
      initialProps: { valores: [1, 2, 3] },
    })
    rerender({ valores: [1, 2, 3] })
    act(() => vi.advanceTimersByTime(50))
    expect(result.current).toEqual([1, 2, 3])
  })

  it('si cambia la longitud, salta sin recorrido', () => {
    const { result, rerender } = renderHook(({ valores }: { valores: number[] }) => useValoresAnimados(valores, 100), {
      initialProps: { valores: [5, 6] },
    })
    rerender({ valores: [7] })
    act(() => vi.advanceTimersByTime(1))
    expect(result.current).toEqual([7])
  })

  it('useNumeroAnimado devuelve null sin dato y el número al final', () => {
    const { result, rerender, unmount } = renderHook(({ valor }: { valor: number | null }) => useNumeroAnimado(valor, 100), {
      initialProps: { valor: null as number | null },
    })
    expect(result.current).toBeNull()
    rerender({ valor: 50 })
    act(() => vi.advanceTimersByTime(1))
    expect(result.current).toBe(50)
    rerender({ valor: 80 })
    act(() => vi.advanceTimersByTime(300))
    expect(result.current).toBe(80)
    unmount()
  })
})

describe('useCambioDe', () => {
  it('no anota nada hasta que el valor cambia con la misma clave', () => {
    const { result, rerender } = renderHook(({ valor, clave }: { valor: number; clave: string }) => useCambioDe(valor, clave), {
      initialProps: { valor: 10, clave: 'a' },
    })
    expect(result.current).toBeNull()
    rerender({ valor: 10, clave: 'a' })
    expect(result.current).toBeNull()
    rerender({ valor: 15, clave: 'a' })
    expect(result.current).toEqual({ anterior: 10, actual: 15, n: 1 })
    rerender({ valor: 15, clave: 'a' })
    expect(result.current).toEqual({ anterior: 10, actual: 15, n: 1 })
    rerender({ valor: 30, clave: 'a' })
    expect(result.current).toEqual({ anterior: 15, actual: 30, n: 2 })
  })

  it('cambiar la clave empieza de cero', () => {
    const { result, rerender } = renderHook(({ valor, clave }: { valor: number; clave: string }) => useCambioDe(valor, clave), {
      initialProps: { valor: 10, clave: 'historico' },
    })
    rerender({ valor: 20, clave: 'historico' })
    expect(result.current?.n).toBe(1)
    rerender({ valor: 99, clave: 'tiempo_real' })
    expect(result.current).toBeNull()
  })
})
