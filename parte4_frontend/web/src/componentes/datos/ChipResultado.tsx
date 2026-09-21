/**
 * Chips de estado de las consultas (§7): resultado de una decisión (permitida / enmascarada / rechazada) y la
 * marca violeta «enmascarado por privacidad» de los grupos con menos de k viajes.
 */
import { Lock } from 'lucide-react'

import { Badge } from '@/componentes/ui/badge'
import { cn } from '@/lib/utils'

import { TEXTO_RESULTADO, type Resultado } from './agregados'

const ESTILO_RESULTADO: Record<Resultado, string> = {
  permitida: 'border-ok/30 bg-ok/10 text-ok',
  enmascarada: 'border-enmascarado/30 bg-enmascarado-suave text-enmascarado',
  rechazada: 'border-peligro/30 bg-peligro/10 text-peligro',
}

interface PropsResultado {
  resultado: Resultado
  /** Cifra opcional delante del texto (por ejemplo, el número de decisiones de las últimas 24 h). */
  cantidad?: string | number
  className?: string
}

export function ChipResultado({ resultado, cantidad, className }: PropsResultado) {
  return (
    <Badge variant="outline" className={cn('capitalize', ESTILO_RESULTADO[resultado], className)}>
      {cantidad !== undefined && <span className="cifra font-semibold">{cantidad}</span>}
      {TEXTO_RESULTADO[resultado]}
    </Badge>
  )
}

interface PropsEnmascarado {
  /** `corto` muestra solo «enmascarado»; por defecto, «enmascarado por privacidad». */
  corto?: boolean
  className?: string
}

export function ChipEnmascarado({ corto = false, className }: PropsEnmascarado) {
  return (
    <Badge
      variant="outline"
      className={cn('border-enmascarado/30 bg-enmascarado-suave text-enmascarado', className)}
      title="Grupo con menos de 10 viajes: no se muestran sus cifras ni se suman a ningún total"
    >
      <Lock aria-hidden />
      {corto ? 'enmascarado' : 'enmascarado por privacidad'}
    </Badge>
  )
}
