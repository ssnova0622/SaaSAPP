import { ReactNode } from 'react'

interface AppTableProps {
  children: ReactNode
  className?: string
}

export function AppTable({ children, className = '' }: AppTableProps) {
  return <table className={`w-full text-left text-sm ${className}`}>{children}</table>
}

export function AppTableHead({ children }: { children: ReactNode }) {
  return <thead className="bg-[#334155] text-[#cbd5e1]">{children}</thead>
}

export function AppTableBody({ children }: { children: ReactNode }) {
  return <tbody className="text-[#e2e8f0]">{children}</tbody>
}

export function AppTableRow({
  children,
  className = '',
  ...rest
}: {
  children: ReactNode
  className?: string
} & React.HTMLAttributes<HTMLTableRowElement>) {
  return <tr className={`border-t border-[#334155] ${className}`} {...rest}>{children}</tr>
}

export function AppTh({
  children,
  className = '',
  align,
  ...rest
}: {
  children: ReactNode
  className?: string
  align?: 'left' | 'center' | 'right' | 'justify'
} & React.ThHTMLAttributes<HTMLTableCellElement>) {
  return (
    <th className={`px-4 py-3 ${className}`} style={align ? { textAlign: align } : undefined} {...rest}>
      {children}
    </th>
  )
}

export function AppTd({
  children,
  className = '',
  ...rest
}: { children: ReactNode; className?: string } & React.TdHTMLAttributes<HTMLTableCellElement>) {
  return (
    <td className={`px-4 py-3 ${className}`} {...rest}>
      {children}
    </td>
  )
}
