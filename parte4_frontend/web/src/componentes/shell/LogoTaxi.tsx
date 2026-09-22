/**
 * Logotipo del portal: un taxi de Nueva York visto de frente (amarillo, con el letrero del techo, el parabrisas,
 * la banda ajedrezada, la rejilla y las ruedas en negro) sobre el recuadro azul de la marca.
 *
 * El mismo dibujo está en `public/favicon.svg`: si cambias uno, cambia el otro. Es decorativo (`aria-hidden`); el
 * nombre del portal va siempre en el texto de al lado.
 */
import { cn } from '@/lib/utils'

const AMARILLO = '#F7B500'
const NEGRO = '#111827'

export function TaxiNuevaYork({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 32 32" className={className} aria-hidden focusable="false">
      <rect x="11" y="3" width="10" height="4.5" rx="1.3" fill={NEGRO} />
      <rect x="12.6" y="4.4" width="6.8" height="1.7" rx="0.6" fill={AMARILLO} />
      <rect x="1.5" y="13" width="3.5" height="2.6" rx="0.9" fill={NEGRO} />
      <rect x="27" y="13" width="3.5" height="2.6" rx="0.9" fill={NEGRO} />
      <path
        d="M8.5 8.5 Q9.2 7.5 10.5 7.5 H21.5 Q22.8 7.5 23.5 8.5 L26.5 14.5 Q27.5 15 27.5 16.5 V24.5 Q27.5 26 26 26 H6 Q4.5 26 4.5 24.5 V16.5 Q4.5 15 5.5 14.5 Z"
        fill={AMARILLO}
      />
      <path d="M9.6 9.3 H22.4 L25 14.6 H7 Z" fill={NEGRO} />
      <rect x="4.5" y="16.6" width="23" height="2.8" fill={NEGRO} />
      <g fill="#FFFFFF">
        <rect x="7.3" y="16.6" width="2.8" height="1.4" />
        <rect x="12.9" y="16.6" width="2.8" height="1.4" />
        <rect x="18.5" y="16.6" width="2.8" height="1.4" />
        <rect x="24.1" y="16.6" width="2.8" height="1.4" />
        <rect x="4.5" y="18" width="2.8" height="1.4" />
        <rect x="10.1" y="18" width="2.8" height="1.4" />
        <rect x="15.7" y="18" width="2.8" height="1.4" />
        <rect x="21.3" y="18" width="2.8" height="1.4" />
        <rect x="26.9" y="18" width="0.6" height="1.4" />
      </g>
      <circle cx="9" cy="22.2" r="2.1" fill="#FFF6D5" stroke={NEGRO} strokeWidth="1.1" />
      <circle cx="23" cy="22.2" r="2.1" fill="#FFF6D5" stroke={NEGRO} strokeWidth="1.1" />
      <rect x="13" y="21" width="6" height="2.6" rx="0.9" fill={NEGRO} />
      <rect x="4.5" y="24.6" width="23" height="1.6" fill={NEGRO} />
      <rect x="6" y="25.4" width="5.4" height="4.2" rx="1.3" fill={NEGRO} />
      <rect x="20.6" y="25.4" width="5.4" height="4.2" rx="1.3" fill={NEGRO} />
    </svg>
  )
}

/** El recuadro azul con el taxi. `className` fija el tamaño y el radio (`size-9 rounded-xl`, `size-8 rounded-lg`…). */
export function LogoTaxi({ className }: { className?: string }) {
  return (
    <span className={cn('flex shrink-0 items-center justify-center bg-[#2563eb] shadow-sm', className)} aria-hidden>
      <TaxiNuevaYork className="size-[76%]" />
    </span>
  )
}
