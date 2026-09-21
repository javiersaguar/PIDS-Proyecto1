/**
 * Markdown de las respuestas del agente (react-markdown + remark-gfm): tablas con estilo, negritas, listas,
 * enlaces en pestaña nueva y el pie «_Datos históricos, solo agregados._» en gris.
 * El texto se muestra tal cual lo produce el agente (§5): aquí no se filtra ni se reescribe nada.
 */
import ReactMarkdown, { type Components } from 'react-markdown'
import remarkGfm from 'remark-gfm'

import { cn } from '@/lib/utils'

const COMPONENTES: Components = {
  p: ({ children }) => <p className="my-1.5 leading-relaxed first:mt-0 last:mb-0">{children}</p>,
  strong: ({ children }) => <strong className="font-semibold text-foreground">{children}</strong>,
  em: ({ children }) => <em className="text-texto-suave">{children}</em>,
  ul: ({ children }) => <ul className="my-1.5 list-disc space-y-0.5 pl-5">{children}</ul>,
  ol: ({ children }) => <ol className="my-1.5 list-decimal space-y-0.5 pl-5">{children}</ol>,
  li: ({ children }) => <li className="leading-relaxed">{children}</li>,
  h1: ({ children }) => <p className="my-1.5 text-base font-semibold text-primario">{children}</p>,
  h2: ({ children }) => <p className="my-1.5 text-[15px] font-semibold text-primario">{children}</p>,
  h3: ({ children }) => <p className="my-1.5 font-semibold text-primario">{children}</p>,
  h4: ({ children }) => <p className="my-1 font-semibold">{children}</p>,
  a: ({ href, children }) => (
    <a href={href} target="_blank" rel="noreferrer" className="text-primario underline underline-offset-2 hover:text-primario-claro">
      {children}
    </a>
  ),
  code: ({ children, className }) => (
    <code className={cn('rounded bg-muted px-1 py-0.5 font-mono text-[12.5px]', className)}>{children}</code>
  ),
  pre: ({ children }) => <pre className="my-2 overflow-x-auto rounded-lg bg-muted p-3 text-xs leading-relaxed">{children}</pre>,
  blockquote: ({ children }) => <blockquote className="my-2 border-l-2 border-acento pl-3 text-texto-suave">{children}</blockquote>,
  hr: () => <hr className="my-3 border-borde" />,
  table: ({ children }) => (
    <div className="my-2 overflow-x-auto rounded-lg border">
      <table className="cifra w-full text-[13px]">{children}</table>
    </div>
  ),
  thead: ({ children }) => <thead className="bg-superficie-alterna text-left text-texto-suave">{children}</thead>,
  tbody: ({ children }) => <tbody>{children}</tbody>,
  tr: ({ children }) => <tr className="border-t first:border-t-0">{children}</tr>,
  th: ({ children, style }) => (
    <th scope="col" style={style} className="px-2.5 py-1.5 font-medium whitespace-nowrap">
      {children}
    </th>
  ),
  td: ({ children, style }) => (
    <td style={style} className="px-2.5 py-1.5 whitespace-nowrap">
      {children}
    </td>
  ),
}

interface Props {
  texto: string
  className?: string
}

export function Markdown({ texto, className }: Props) {
  return (
    <div className={cn('markdown-chat min-w-0 wrap-break-word', className)}>
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={COMPONENTES}>
        {texto}
      </ReactMarkdown>
    </div>
  )
}
