import { ReactNode } from 'react'

interface DataCardProps {
  children: ReactNode
  className?: string
}

/**
 * Standard card container for content (slate border, rounded). Use for tables, forms, sections.
 */
export function DataCard({ children, className = '' }: DataCardProps) {
  return (
    <div className={`rounded-xl border border-[#334155] bg-[#1e293b] overflow-hidden ${className}`}>
      {children}
    </div>
  )
}
