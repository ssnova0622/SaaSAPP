import { useMemo, useState } from 'react'
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Divider,
  IconButton,
  Stack,
  Tooltip,
  Typography,
} from '@mui/material'
import ContentCopyIcon from '@mui/icons-material/ContentCopy'
import OpenInNewIcon from '@mui/icons-material/OpenInNew'
import RefreshIcon from '@mui/icons-material/Refresh'
import StorefrontIcon from '@mui/icons-material/Storefront'
import { useEffectiveTenant } from '../../hooks/useEffectiveTenant'

/** Derive the catalog URL for the tenant based on the current window origin. */
function getCatalogUrl(tenant: string): string {
  const origin = typeof window !== 'undefined' ? window.location.origin : ''
  return `${origin}/ss-business/${encodeURIComponent(tenant)}/catalog`
}

export default function StoreCatalogPage() {
  const { effectiveTenant: tenant } = useEffectiveTenant()
  const [copied, setCopied] = useState(false)
  const [iframeKey, setIframeKey] = useState(0)

  const catalogUrl = useMemo(() => (tenant ? getCatalogUrl(tenant) : ''), [tenant])

  function copyLink() {
    if (!catalogUrl) return
    navigator.clipboard.writeText(catalogUrl).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    })
  }

  function openInNew() {
    if (catalogUrl) window.open(catalogUrl, '_blank', 'noopener,noreferrer')
  }

  function refreshPreview() {
    setIframeKey((k) => k + 1)
  }

  if (!tenant) {
    return (
      <Box sx={{ p: 2 }}>
        <Alert severity="info">Select a tenant to view the catalog.</Alert>
      </Box>
    )
  }

  return (
    <Box sx={{ p: 1 }}>
      <Stack direction="row" alignItems="center" spacing={1.5} sx={{ mb: 2 }}>
        <StorefrontIcon sx={{ color: 'primary.main', fontSize: 28 }} />
        <Typography variant="h5" fontWeight={700}>
          Store — Catalog Preview
        </Typography>
      </Stack>

      <Alert severity="info" sx={{ mb: 2 }}>
        This is the customer-facing catalog for <strong>{tenant}</strong>. Share the link below with your
        customers so they can browse products, view offers, and place orders via WhatsApp.
      </Alert>

      {/* Shareable link card */}
      <Card variant="outlined" sx={{ mb: 2 }}>
        <CardContent sx={{ py: 1.5, '&:last-child': { pb: 1.5 } }}>
          <Typography variant="subtitle2" color="text.secondary" sx={{ mb: 1 }}>
            Customer catalog link
          </Typography>
          <Stack direction="row" alignItems="center" spacing={1} flexWrap="wrap">
            <Box
              sx={{
                flex: 1,
                minWidth: 0,
                px: 1.5,
                py: 0.75,
                bgcolor: 'action.hover',
                borderRadius: 1,
                border: '1px solid',
                borderColor: 'divider',
                fontFamily: 'monospace',
                fontSize: '0.8125rem',
                color: 'text.primary',
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
              }}
              title={catalogUrl}
            >
              {catalogUrl}
            </Box>
            <Tooltip title={copied ? 'Copied!' : 'Copy link'}>
              <IconButton onClick={copyLink} color={copied ? 'success' : 'default'} size="small">
                <ContentCopyIcon fontSize="small" />
              </IconButton>
            </Tooltip>
            <Button
              variant="contained"
              size="small"
              startIcon={<OpenInNewIcon />}
              onClick={openInNew}
              sx={{ whiteSpace: 'nowrap' }}
            >
              Open
            </Button>
          </Stack>
        </CardContent>
      </Card>

      {/* Live preview */}
      <Card variant="outlined">
        <CardContent sx={{ py: 1, '&:last-child': { pb: 1 } }}>
          <Stack direction="row" alignItems="center" justifyContent="space-between" sx={{ mb: 1 }}>
            <Typography variant="subtitle2" color="text.secondary">
              Live preview
            </Typography>
            <Tooltip title="Refresh preview">
              <IconButton size="small" onClick={refreshPreview}>
                <RefreshIcon fontSize="small" />
              </IconButton>
            </Tooltip>
          </Stack>
          <Divider sx={{ mb: 1 }} />
          <Box
            sx={{
              width: '100%',
              height: { xs: 480, sm: 600, md: 720 },
              borderRadius: 1,
              overflow: 'hidden',
              border: '1px solid',
              borderColor: 'divider',
              bgcolor: 'background.default',
            }}
          >
            <iframe
              key={iframeKey}
              src={catalogUrl}
              title="Customer catalog preview"
              style={{ width: '100%', height: '100%', border: 'none' }}
              sandbox="allow-scripts allow-same-origin allow-forms allow-popups"
            />
          </Box>
        </CardContent>
      </Card>
    </Box>
  )
}
