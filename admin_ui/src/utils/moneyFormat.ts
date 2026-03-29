/** Format amounts using tenant payment_config.currency (ISO 4217). */
export function formatMoney(amount: number, currency: string = 'INR'): string {
  const c = (currency || 'INR').toUpperCase()
  const n = Number(amount) || 0
  try {
    return new Intl.NumberFormat(undefined, {
      style: 'currency',
      currency: c,
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(n)
  } catch {
    return `${c} ${n.toFixed(2)}`
  }
}
