export const SERIES_COLORS = ['#1976d2', '#2e7d32', '#ed6c02', '#9c27b0', '#d32f2f', '#455a64', '#6d4c41']

export function colorAt(index: number): string {
  return SERIES_COLORS[index % SERIES_COLORS.length]
}

export function categoryColor(index: number): string {
  return SERIES_COLORS[index % SERIES_COLORS.length]
}
