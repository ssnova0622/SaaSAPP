import { useState } from 'react'
import { Button, Menu, MenuItem, ListItemIcon, ListItemText } from '@mui/material'
import FileDownloadIcon from '@mui/icons-material/FileDownload'
import TableChartIcon from '@mui/icons-material/TableChart'
import PictureAsPdfIcon from '@mui/icons-material/PictureAsPdf'
import TextSnippetIcon from '@mui/icons-material/TextSnippet'
import { exportToCSV, exportToXLSX, exportToPDF, type ExportColumn } from '../utils/export'

export type ExportMenuProps = {
  /** Current data to export (array of objects) */
  data: Record<string, unknown>[]
  /** Column definitions: key = field name, label = header */
  columns: ExportColumn[]
  /** Filename prefix (e.g. "customers" -> customers.csv) */
  filename: string
  /** Optional title for PDF */
  title?: string
  /** Disable when no data or loading */
  disabled?: boolean
  /** Button size */
  size?: 'small' | 'medium' | 'large'
}

export default function ExportMenu({
  data,
  columns,
  filename,
  title,
  disabled = false,
  size = 'medium',
}: ExportMenuProps) {
  const [anchor, setAnchor] = useState<null | HTMLElement>(null)

  const handleExport = (format: 'csv' | 'xlsx' | 'pdf') => {
    setAnchor(null)
    if (!data.length) return
    const base = `${filename}_${new Date().toISOString().slice(0, 10)}`
    try {
      if (format === 'csv') exportToCSV(data, columns, base)
      else if (format === 'xlsx') exportToXLSX(data, columns, base)
      else exportToPDF(data, columns, base, title || filename)
    } catch (e) {
      console.error('Export failed', e)
    }
  }

  return (
    <>
      <Button
        size={size}
        variant="outlined"
        startIcon={<FileDownloadIcon />}
        onClick={(e) => setAnchor(e.currentTarget)}
        disabled={disabled || !data.length}
      >
        Export
      </Button>
      <Menu
        anchorEl={anchor}
        open={!!anchor}
        onClose={() => setAnchor(null)}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
        transformOrigin={{ vertical: 'top', horizontal: 'right' }}
      >
        <MenuItem onClick={() => handleExport('csv')}>
          <ListItemIcon><TextSnippetIcon fontSize="small" /></ListItemIcon>
          <ListItemText>CSV</ListItemText>
        </MenuItem>
        <MenuItem onClick={() => handleExport('xlsx')}>
          <ListItemIcon><TableChartIcon fontSize="small" /></ListItemIcon>
          <ListItemText>Excel (XLSX)</ListItemText>
        </MenuItem>
        <MenuItem onClick={() => handleExport('pdf')}>
          <ListItemIcon><PictureAsPdfIcon fontSize="small" /></ListItemIcon>
          <ListItemText>PDF</ListItemText>
        </MenuItem>
      </Menu>
    </>
  )
}
