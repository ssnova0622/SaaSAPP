import { ReactNode } from 'react'

type AlertVariant = 'error' | 'success' | 'warning' | 'info'

const variantClasses: Record<AlertVariant, string> = {
  error: 'border-[#ef4444]/50 bg-[#ef4444]/10 text-[#fca5a5]',
  success: 'border-[#22c55e]/50 bg-[#22c55e]/10 text-[#86efac]',
  warning: 'border-[#eab308]/50 bg-[#eab308]/10 text-[#fde047]',
  info: 'border-[#3b82f6]/50 bg-[#3b82f6]/10 text-[#93c5fd]',
}

interface AlertProps {
  variant?: AlertVariant
  children: ReactNode
  className?: string
}

export function Alert({ variant = 'info', children, className = '' }: AlertProps) {
  return (
    <div
      className={`rounded-lg border px-4 py-3 text-sm ${variantClasses[variant]} ${className}`}
      role="alert"
    >
      {children}
    </div>
  )
}
