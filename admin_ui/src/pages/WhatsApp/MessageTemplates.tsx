import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  Accordion,
  AccordionDetails,
  AccordionSummary,
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  IconButton,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
  ToggleButton,
  ToggleButtonGroup,
  Tooltip,
  Typography,
  Paper,
} from '@mui/material'
import ExpandMoreIcon from '@mui/icons-material/ExpandMore'
import EditOutlinedIcon from '@mui/icons-material/EditOutlined'
import { useEffectiveTenant } from '../../hooks/useEffectiveTenant'
import { useAuth } from '../../contexts/AuthContext'
import {
  getWhatsAppTemplateBundle,
  putDefaultMessagesAdmin,
  putTenantMessageTemplates,
  type MessageCategorySection,
  type WhatsAppTemplateBundle,
} from '@api/tenants'

function deriveCategories(keys: string[]): MessageCategorySection[] {
  const buckets: Record<string, string[]> = {}
  for (const key of keys) {
    let id = 'application_other'
    if (key.startsWith('wa_')) id = 'whatsapp_wa'
    else if (key.startsWith('whatsapp_')) id = 'whatsapp_general'
    else if (key.startsWith('followup_')) id = 'followups'
    else if (
      key.startsWith('booking_') ||
      key.startsWith('reschedule_') ||
      key === 'goodbye' ||
      key === 'welcome' ||
      key === 'workflow_complete'
    )
      id = 'booking_workflow'
    if (!buckets[id]) buckets[id] = []
    buckets[id].push(key)
  }
  for (const k of Object.keys(buckets)) buckets[k].sort()
  const order = ['whatsapp_wa', 'whatsapp_general', 'booking_workflow', 'followups', 'application_other']
  const titles: Record<string, string> = {
    whatsapp_wa: 'WhatsApp — wa_* (workflow, salon, core strings)',
    whatsapp_general: 'WhatsApp — whatsapp_* (generic)',
    booking_workflow: 'Booking & workflow',
    followups: 'Follow-ups',
    application_other: 'Application & other',
  }
  return order
    .filter((id) => buckets[id]?.length)
    .map((id) => ({ id, title: titles[id] || id, keys: buckets[id]! }))
}

function normalizeBundle(raw: Partial<WhatsAppTemplateBundle> | null): WhatsAppTemplateBundle | null {
  if (!raw?.keys?.length) return null
  const keys = raw.keys
  const z = (x: Record<string, string> | undefined) => x || {}
  const b = z(raw.templates)
  const d = z(raw.defaults)
  const labels: Record<string, string> = { ...z(raw.labels) }
  const customized: Record<string, boolean> = {}
  for (const k of keys) {
    if (!labels[k]) labels[k] = k
    customized[k] = Boolean(raw.customized?.[k])
  }
  const categories =
    raw.categories && raw.categories.length > 0 ? raw.categories : deriveCategories(keys)
  return {
    keys,
    categories,
    labels,
    defaults: d,
    templates: b,
    customized,
  }
}

function previewText(s: string, max = 72) {
  const t = (s || '').replace(/\s+/g, ' ').trim()
  if (t.length <= max) return t || '—'
  return `${t.slice(0, max)}…`
}

const CACHE_PREFIX = 'wa_msg_bundle:'

function CategoryTable(props: {
  catKeys: string[]
  bundle: WhatsAppTemplateBundle
  onEdit: (key: string) => void
}) {
  const { catKeys, bundle, onEdit } = props
  return (
    <TableContainer component={Paper} variant="outlined" sx={{ boxShadow: 'none' }}>
      <Table size="small">
        <TableHead>
          <TableRow>
            <TableCell sx={{ fontWeight: 600, width: 200 }}>Label</TableCell>
            <TableCell sx={{ fontWeight: 600, width: 220 }}>Key</TableCell>
            <TableCell sx={{ fontWeight: 600 }}>Preview (effective)</TableCell>
            <TableCell sx={{ fontWeight: 600, width: 120 }}>Status</TableCell>
            <TableCell align="right" sx={{ fontWeight: 600, width: 88 }}>
              Edit
            </TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {catKeys.map((key) => {
            const label = bundle.labels[key] || key
            const text = bundle.templates[key] || ''
            const isCustom = bundle.customized[key]
            return (
              <TableRow key={key} hover>
                <TableCell sx={{ verticalAlign: 'top' }}>{label}</TableCell>
                <TableCell
                  sx={{
                    verticalAlign: 'top',
                    fontFamily: 'ui-monospace, monospace',
                    fontSize: '0.8rem',
                    wordBreak: 'break-all',
                  }}
                >
                  {key}
                </TableCell>
                <TableCell sx={{ verticalAlign: 'top', color: 'text.secondary', whiteSpace: 'pre-wrap' }}>
                  {previewText(text, 96)}
                </TableCell>
                <TableCell sx={{ verticalAlign: 'top' }}>
                  {isCustom ? (
                    <Chip label="Tenant override" size="small" color="primary" variant="outlined" />
                  ) : (
                    <Chip label="Default" size="small" variant="outlined" />
                  )}
                </TableCell>
                <TableCell align="right" sx={{ verticalAlign: 'top' }}>
                  <Tooltip title="Edit message">
                    <IconButton size="small" color="primary" onClick={() => onEdit(key)} aria-label="Edit">
                      <EditOutlinedIcon fontSize="small" />
                    </IconButton>
                  </Tooltip>
                </TableCell>
              </TableRow>
            )
          })}
        </TableBody>
      </Table>
    </TableContainer>
  )
}

export default function WhatsAppMessageTemplatesPage() {
  const { effectiveTenant: tenant } = useEffectiveTenant()
  const { isSuperAdmin } = useAuth()
  const [bundle, setBundle] = useState<WhatsAppTemplateBundle | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [message, setMessage] = useState<string | null>(null)
  const [search, setSearch] = useState('')
  const [editKey, setEditKey] = useState<string | null>(null)
  const [draft, setDraft] = useState('')
  const [dialogSaving, setDialogSaving] = useState(false)
  const [saveTarget, setSaveTarget] = useState<'tenant' | 'platform'>('tenant')

  const load = useCallback(async () => {
    if (!tenant) return
    setLoading(true)
    setError(null)
    setMessage(null)
    try {
      const b = await getWhatsAppTemplateBundle(tenant)
      const n = normalizeBundle(b)
      setBundle(n)
      if (n) {
        try {
          sessionStorage.setItem(`${CACHE_PREFIX}${tenant}`, JSON.stringify(b))
        } catch {
          /* ignore */
        }
      }
    } catch (e: unknown) {
      const err = e as { response?: { data?: { detail?: string } } }
      setError(err?.response?.data?.detail || 'Failed to load message templates')
    } finally {
      setLoading(false)
    }
  }, [tenant])

  useEffect(() => {
    if (!tenant) return
    try {
      const raw = sessionStorage.getItem(`${CACHE_PREFIX}${tenant}`)
      if (raw) {
        const parsed = JSON.parse(raw) as Partial<WhatsAppTemplateBundle>
        const n = normalizeBundle(parsed)
        if (n) setBundle(n)
      }
    } catch {
      /* ignore */
    }
    void load()
  }, [tenant, load])

  const filteredCategories = useMemo(() => {
    if (!bundle) return []
    const q = search.trim().toLowerCase()
    if (!q) return bundle.categories
    return bundle.categories
      .map((c) => ({
        ...c,
        keys: c.keys.filter((key) => {
          const label = (bundle.labels[key] || '').toLowerCase()
          return (
            key.toLowerCase().includes(q) ||
            label.includes(q) ||
            (bundle.templates[key] || '').toLowerCase().includes(q) ||
            (bundle.defaults[key] || '').toLowerCase().includes(q)
          )
        }),
      }))
      .filter((c) => c.keys.length > 0)
  }, [bundle, search])

  const openEdit = (key: string) => {
    if (!bundle) return
    setEditKey(key)
    setSaveTarget('tenant')
    setDraft(bundle.templates[key] ?? '')
  }

  const closeEdit = () => {
    setEditKey(null)
    setDraft('')
    setSaveTarget('tenant')
  }

  const saveOne = async () => {
    if (!bundle || !editKey) return
    if (saveTarget === 'platform' && !isSuperAdmin) return
    setDialogSaving(true)
    setError(null)
    setMessage(null)
    try {
      if (saveTarget === 'platform' && isSuperAdmin) {
        await putDefaultMessagesAdmin({ templates: { [editKey]: draft } })
        setMessage('Platform default updated (all tenants unless they override).')
      } else {
        if (!tenant) return
        await putTenantMessageTemplates(tenant, { [editKey]: draft })
        setMessage('Tenant message saved.')
      }
      closeEdit()
      await load()
    } catch (e: unknown) {
      const err = e as { response?: { data?: { detail?: string } } }
      setError(err?.response?.data?.detail || 'Save failed')
    } finally {
      setDialogSaving(false)
    }
  }

  const resetDraftToDefault = () => {
    if (!bundle || !editKey) return
    setDraft(bundle.defaults[editKey] ?? '')
  }

  if (!tenant) {
    return <Typography sx={{ p: 2 }}>Select a tenant to edit messages.</Typography>
  }

  if (loading && !bundle) {
    return (
      <Box sx={{ p: 4, display: 'flex', justifyContent: 'center' }}>
        <CircularProgress />
      </Box>
    )
  }

  const editingLabel = editKey && bundle ? bundle.labels[editKey] || editKey : ''

  return (
    <Box sx={{ p: 2, maxWidth: 1200 }}>
      <Typography variant="h5" gutterBottom fontWeight={600}>
        Default messages
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        Platform defaults and labels are stored in the <code>default_message</code> collection (cached on the server).
        Messages are grouped by key prefix (for example <code>wa_*</code> for WhatsApp-related copy). Tenant-specific
        changes are stored only in <code>tenant_message_templates</code> and apply to the selected tenant.
        {isSuperAdmin ? ' Super Admins can also update the platform default for all tenants.' : ''}
      </Typography>
      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}
      {message && (
        <Alert severity="success" sx={{ mb: 2 }} onClose={() => setMessage(null)}>
          {message}
        </Alert>
      )}
      <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2} sx={{ mb: 2 }} alignItems={{ sm: 'center' }}>
        <TextField
          size="small"
          label="Search label, key, or text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          sx={{ minWidth: 280 }}
        />
        <Button variant="outlined" onClick={() => void load()} disabled={loading}>
          Reload from server
        </Button>
      </Stack>

      <Stack spacing={1}>
        {filteredCategories.map((cat) => (
          <Accordion key={cat.id} defaultExpanded disableGutters>
            <AccordionSummary expandIcon={<ExpandMoreIcon />}>
              <Typography fontWeight={600}>{cat.title}</Typography>
              <Typography variant="caption" color="text.secondary" sx={{ ml: 2 }}>
                {cat.keys.length} message{cat.keys.length === 1 ? '' : 's'}
              </Typography>
            </AccordionSummary>
            <AccordionDetails sx={{ pt: 0 }}>
              {bundle && <CategoryTable catKeys={cat.keys} bundle={bundle} onEdit={openEdit} />}
            </AccordionDetails>
          </Accordion>
        ))}
      </Stack>

      <Dialog open={Boolean(editKey)} onClose={closeEdit} fullWidth maxWidth="md">
        <DialogTitle>{editingLabel}</DialogTitle>
        <DialogContent>
          {editKey && bundle && (
            <Stack spacing={2} sx={{ mt: 1 }}>
              <Typography variant="caption" color="text.secondary" sx={{ fontFamily: 'monospace' }}>
                {editKey}
              </Typography>
              {isSuperAdmin && (
                <>
                  <Typography variant="body2" fontWeight={600}>
                    Save to
                  </Typography>
                  <ToggleButtonGroup
                    exclusive
                    size="small"
                    value={saveTarget}
                    onChange={(_, v) => v && setSaveTarget(v)}
                    color="primary"
                  >
                    <ToggleButton value="tenant">This tenant only</ToggleButton>
                    <ToggleButton value="platform">Platform default (all tenants)</ToggleButton>
                  </ToggleButtonGroup>
                </>
              )}
              <Typography variant="body2" color="text.secondary">
                Platform default (reference)
              </Typography>
              <Paper variant="outlined" sx={{ p: 1.5, bgcolor: 'action.hover', whiteSpace: 'pre-wrap' }}>
                {bundle.defaults[editKey] || '—'}
              </Paper>
              <TextField
                label={saveTarget === 'platform' && isSuperAdmin ? 'Platform message' : 'Effective / tenant message'}
                value={draft}
                onChange={(e) => setDraft(e.target.value)}
                multiline
                minRows={6}
                fullWidth
                helperText={
                  saveTarget === 'tenant'
                    ? 'Matching the platform default removes the tenant override.'
                    : 'Updates default_message in the database (invalidates caches).'
                }
              />
              <Button size="small" variant="outlined" onClick={resetDraftToDefault}>
                Reset draft to current platform default
              </Button>
            </Stack>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={closeEdit}>Cancel</Button>
          <Button variant="contained" onClick={() => void saveOne()} disabled={dialogSaving}>
            {dialogSaving ? 'Saving…' : 'Save'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}
