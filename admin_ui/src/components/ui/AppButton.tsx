import { ButtonHTMLAttributes, ReactNode } from 'react'

type Variant = 'primary' | 'secondary' | 'danger' | 'ghost'

const variantClasses: Record<Variant, string> = {
  primary: 'bg-[#3b82f6] text-white hover:bg-[#2563eb] disabled:opacity-50',
  secondary: 'border border-[#334155] bg-[#1e293b] text-[#e2e8f0] hover:bg-[#334155] disabled:opacity-50',
  danger: 'bg-[#ef4444] text-white hover:bg-[#dc2626] disabled:opacity-50',
  ghost: 'text-[#cbd5e1] hover:bg-[#334155] hover:text-white disabled:opacity-50',
}

interface AppButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant
  children: ReactNode
}

/**
 * Consistent button styling. Use instead of raw <button> for primary/secondary/danger actions.
 */
export function AppButton({
  variant = 'primary',
  className = '',
  children,
  ...props
}: AppButtonProps) {
  return (
    <button
      type="button"
      className={`rounded-lg px-4 py-2 text-sm font-medium transition-colors ${variantClasses[variant]} ${className}`}
      {...props}
    >
      {children}
    </button>
  )
}
