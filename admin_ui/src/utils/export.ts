/**
 * Client-side export utilities: CSV, XLSX, PDF.
 * Use with list data (array of objects) and a column definition.
 */
import * as XLSX from 'xlsx'
import { jsPDF } from 'jspdf'
import autoTable from 'jspdf-autotable'

export type ExportColumn = { key: string; label: string }

function getCellValue(row: Record<string, unknown>, key: string): string {
  const v = row[key]
  if (v == null) return ''
  if (typeof v === 'object') return JSON.stringify(v)
  return String(v)
}

function escapeCsvCell(s: string): string {
  if (/[",\n\r]/.test(s)) return `"${s.replace(/"/g, '""')}"`
  return s
}

/** Export data to CSV and trigger download */
export function exportToCSV(
  data: Record<string, unknown>[],
  columns: ExportColumn[],
  filename: string
): void {
  const headers = columns.map((c) => escapeCsvCell(c.label))
  const rows = data.map((row) =>
    columns.map((c) => escapeCsvCell(getCellValue(row, c.key))).join(',')
  )
  const bom = '\uFEFF'
  const csv = bom + [headers.join(','), ...rows].join('\r\n')
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `${filename}.csv`
  a.click()
  URL.revokeObjectURL(url)
}

/** Export data to XLSX and trigger download */
export function exportToXLSX(
  data: Record<string, unknown>[],
  columns: ExportColumn[],
  filename: string,
  sheetName = 'Sheet1'
): void {
  const headerRow = columns.map((c) => c.label)
  const dataRows = data.map((row) =>
    columns.map((c) => getCellValue(row, c.key))
  )
  const ws = XLSX.utils.aoa_to_sheet([headerRow, ...dataRows])
  const wb = XLSX.utils.book_new()
  XLSX.utils.book_append_sheet(wb, ws, sheetName)
  XLSX.writeFile(wb, `${filename}.xlsx`)
}

/** Export data to PDF (table) and trigger download */
export function exportToPDF(
  data: Record<string, unknown>[],
  columns: ExportColumn[],
  filename: string,
  title?: string
): void {
  const doc = new jsPDF({ orientation: 'landscape', unit: 'mm', format: 'a4' })
  if (title) {
    doc.setFontSize(14)
    doc.text(title, 14, 12)
  }
  const head = [columns.map((c) => c.label)]
  const body = data.map((row) => columns.map((c) => getCellValue(row, c.key)))
  autoTable(doc, {
    head,
    body,
    startY: title ? 18 : 10,
    margin: { left: 14 },
    styles: { fontSize: 8 },
    headStyles: { fillColor: [37, 99, 235] },
  })
  doc.save(`${filename}.pdf`)
}
