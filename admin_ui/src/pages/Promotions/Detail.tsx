import { useEffect, useState, useRef } from 'react'
import { useParams, useNavigate, Link as RouterLink } from 'react-router-dom'
import { Alert, Box, Button, Card, CardContent, Grid, Stack, Table, TableBody, TableCell, TableHead, TableRow, Typography, IconButton, TextField, Dialog, DialogTitle, DialogContent, DialogActions, Link, CircularProgress, List, ListItem, ListItemText, ListItemSecondaryAction, Chip, Divider, MenuItem } from '@mui/material'
import { Delete as DeleteIcon, Add as AddIcon, Link as LinkIcon, Image as ImageIcon, Movie as MovieIcon, PictureAsPdf as PdfIcon, Sms as SmsIcon } from '@mui/icons-material'
import { getPromotion, sendPromotion, getPromotionLogs, Promotion, updatePromotion, Attachment } from '@api/promotions'
import { uploadFile } from '@api/upload'
import { getWhatsAppConfig } from '@api/tenants'
import { promotionMessageWithLinks, promotionCtaEntriesForPreview } from './messagePreviewUtils'
import { resolveUploadUrl } from '@api/config'
import { useWebSocket } from '@hooks/useWebSocket'
import { useEffectiveTenant } from '../../hooks/useEffectiveTenant'
import { useTenantDisplayPreferences } from '../../hooks/useTenantDateFormat'
import { formatDateTimeForDisplay } from '../../utils/dateFormat'
import WhatsAppPreview from '../../components/WhatsAppPreview'
import { useAlert } from '@contexts/AlertContext'
import { parsePhoneList, findInvalidPhones } from '../../utils/phone'

function includesWhatsApp(ch?: string | null): boolean {
  return ['whatsapp', 'both', 'sms+whatsapp', 'all'].includes(ch ?? '')
}

function includesSms(ch?: string | null): boolean {
  return ['sms', 'sms+email', 'sms+whatsapp', 'all'].includes(ch ?? '')
}

type AttachmentLike = { type?: string; url?: string; name?: string }

function buildSmsBody(message: string, attachments?: AttachmentLike[] | null, offerCode?: string | null): string {
  const linkLines = (attachments ?? [])
    .filter(a => a.type === 'link' && a.url)
    .map(a => (a.name && a.name !== a.url ? `${a.name}: ${a.url}` : a.url!))
  const parts: string[] = [message]
  if (linkLines.length) parts.push(linkLines.join('\n'))
  if (offerCode?.trim()) parts.push(`Code: ${offerCode.trim()}`)
  return parts.filter(Boolean).join('\n')
}

function SmsPreview({ message, attachments, offerCode }: { message: string; attachments?: AttachmentLike[] | null; offerCode?: string | null }) {
  const body = buildSmsBody(message, attachments, offerCode)
  const chars = body.length
  const segments = Math.max(1, Math.ceil(chars / 160))
  const linkAtts = (attachments ?? []).filter(a => a.type === 'link' && a.url)
  return (
    <Box sx={{ border: '2px solid #cbd5e1', borderRadius: 3, p: 2, bgcolor: '#f8fafc' }}>
      <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 1.5, pb: 1, borderBottom: '1px solid #e2e8f0' }}>
        <SmsIcon sx={{ color: '#16a34a', fontSize: 18 }} />
        <Typography variant="caption" color="text.secondary" fontWeight={600}>SMS Preview</Typography>
        {linkAtts.length > 0 && (
          <Chip size="small" label={`${linkAtts.length} link${linkAtts.length > 1 ? 's' : ''}`} color="success" variant="outlined" />
        )}
      </Stack>
      <Box sx={{ bgcolor: '#dcfce7', borderRadius: '12px 12px 2px 12px', p: 1.5, maxWidth: '90%', ml: 'auto' }}>
        <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap', fontSize: 13, color: '#111827' }}>
          {body || '(no message)'}
        </Typography>
      </Box>
      <Stack direction="row" spacing={1} sx={{ mt: 1.5, pt: 1, borderTop: '1px solid #e2e8f0' }} flexWrap="wrap">
        <Chip size="small" icon={<SmsIcon fontSize="small" />} label={`${chars} chars`} color={chars > 160 ? 'warning' : 'default'} variant="outlined" />
        <Chip size="small" label={`${segments} segment${segments > 1 ? 's' : ''}`} color={segments > 1 ? 'warning' : 'default'} variant="outlined" />
      </Stack>
    </Box>
  )
}

export default function PromotionDetail(){
  const { effectiveTenant } = useEffectiveTenant()
  const { dateFormat, timeZone } = useTenantDisplayPreferences()
  const tenant = effectiveTenant
  const { showAlert } = useAlert()
  const { id = '' } = useParams()
  const nav = useNavigate()
  const [doc,setDoc]=useState<Promotion|undefined>()
  const [stats,setStats]=useState<{total:number;sent:number;failed:number}>({total:0,sent:0,failed:0})
  const [logs,setLogs]=useState<any[]>([])
  const [loading,setLoading]=useState(false)
  const [uploading, setUploading] = useState(false)
  const [linkDialogOpen, setLinkDialogOpen] = useState(false)
  const [newLink, setNewLink] = useState({ name: '', url: '' })
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [waProvider, setWaProvider] = useState<string>('twilio')
  const [resendOpen, setResendOpen] = useState(false)
  const [resendSending, setResendSending] = useState(false)
  const [resendAudType, setResendAudType] = useState<'all' | 'tags' | 'custom' | 'segment'>('all')
  const [resendTags, setResendTags] = useState('')
  const [resendPhones, setResendPhones] = useState('')
  const [resendEmails, setResendEmails] = useState('')
  const [resendSegType, setResendSegType] = useState('active')
  const [resendSegDays, setResendSegDays] = useState('')
  const { lastEvent } = useWebSocket(tenant)

  async function load(){
    if(!tenant || !id) return
    const rid = ++(load as any).__rid || (((load as any).__rid = 1))
    setLoading(true)
    try{
      const d = await getPromotion(tenant, id)
      const lg = await getPromotionLogs(tenant, id, { page:1, size:50 })
      if (rid !== (load as any).__rid) return
      setDoc(d)
      setLogs(lg.items)
    } finally{ if (rid === (load as any).__rid) setLoading(false) }
  }
  useEffect(()=>{ load() // eslint-disable-next-line
  },[tenant, id])

  useEffect(() => {
    if (!tenant) return
    getWhatsAppConfig(tenant)
      .then(c => setWaProvider(String(c?.provider || 'twilio')))
      .catch(() => setWaProvider('twilio'))
  }, [tenant])

  useEffect(()=>{
    if(!lastEvent) return
    if(lastEvent.type==='promotion.progress' && lastEvent.promotion_id===id){
      setStats({ total:lastEvent.total||0, sent:lastEvent.sent||0, failed:lastEvent.failed||0 })
    }
    if(lastEvent.type==='promotion.completed' && lastEvent.promotion_id===id){
      setStats({ total:lastEvent.total||0, sent:lastEvent.sent||0, failed:lastEvent.failed||0 })
      load()
    }
  },[lastEvent])

  async function onSend(){
    if(!tenant || !id) return
    try {
      const res = await sendPromotion(tenant, id, {})
      setStats({ total:res.total, sent:res.sent, failed:res.failed })
      load()
    } catch (err: any) {
      console.error('Send failed', err)
      showAlert(err?.response?.data?.detail || 'Failed to send promotion', 'error')
    }
  }

  function openResendDialog() {
    const a = doc?.audience
    if (!a || typeof a !== 'object') {
      setResendAudType('all')
      setResendTags('')
      setResendPhones('')
      setResendEmails('')
      setResendSegType('active')
      setResendSegDays('')
    } else {
      const t = (a.type || 'all') as string
      setResendAudType(['all', 'tags', 'custom', 'segment'].includes(t) ? (t as typeof resendAudType) : 'all')
      setResendTags(Array.isArray(a.tags) ? a.tags.join(', ') : '')
      setResendPhones(Array.isArray(a.phones) ? a.phones.join('\n') : '')
      setResendEmails(Array.isArray(a.emails) ? a.emails.join(', ') : '')
      const seg = a.segment as { type?: string; days?: number } | undefined
      setResendSegType(typeof seg?.type === 'string' ? seg.type : 'active')
      setResendSegDays(seg?.days != null ? String(seg.days) : '')
    }
    setResendOpen(true)
  }

  function buildResendAudience(): Record<string, unknown> {
    const audience: Record<string, unknown> = { type: resendAudType }
    if (resendAudType === 'tags') {
      audience.tags = resendTags.split(',').map(s => s.trim()).filter(Boolean)
    }
    if (resendAudType === 'custom') {
      audience.phones = parsePhoneList(resendPhones)
      audience.emails = resendEmails.split(',').map(s => s.trim()).filter(Boolean)
    }
    if (resendAudType === 'segment') {
      const days = resendSegDays.trim() ? parseInt(resendSegDays, 10) : undefined
      audience.segment = {
        type: resendSegType,
        ...(days != null && !Number.isNaN(days) ? { days } : {}),
      }
    }
    return audience
  }

  const resendInvalidPhones =
    resendAudType === 'custom' ? findInvalidPhones(parsePhoneList(resendPhones)) : []

  async function onResendConfirm() {
    if (!tenant || !id) return
    if (resendInvalidPhones.length) {
      showAlert(`Invalid phone(s): ${resendInvalidPhones.join(', ')}`, 'error')
      return
    }
    setResendSending(true)
    try {
      const res = await sendPromotion(tenant, id, { resend: true, audience: buildResendAudience() })
      setResendOpen(false)
      if (res.source_promotion_id && res.id !== id) {
        showAlert('Created a new promotion and sent it; opening that record.', 'success')
        nav(`/promotions/${res.id}`)
        return
      }
      setStats({ total: res.total, sent: res.sent, failed: res.failed })
      load()
    } catch (err: any) {
      console.error('Resend failed', err)
      showAlert(err?.response?.data?.detail || 'Failed to resend promotion', 'error')
    } finally {
      setResendSending(false)
    }
  }

  async function handleFileUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file || !tenant || !id || !doc) return
    setUploading(true)
    try {
      const res = await uploadFile(tenant, file)
      let type: Attachment['type'] = 'image'
      if (file.type.startsWith('video/')) type = 'video'
      else if (file.type === 'application/pdf' || file.name.toLowerCase().endsWith('.pdf')) type = 'document'
      const att: Attachment = { type, url: res.url, name: file.name }
      const newAttachments = [...(doc.attachments || []), att]
      const updated = await updatePromotion(tenant, id, { attachments: newAttachments })
      setDoc(updated)
    } catch (err) {
      console.error('Upload failed', err)
      showAlert('Upload failed', 'error')
    } finally {
      setUploading(false)
      if (fileInputRef.current) fileInputRef.current.value = ''
    }
  }

  async function handleAddLink() {
    if (!tenant || !id || !doc || !newLink.url) return
    const att: Attachment = { type: 'link', url: newLink.url, name: newLink.name || newLink.url }
    const newAttachments = [...(doc.attachments || []), att]
    try {
      const updated = await updatePromotion(tenant, id, { attachments: newAttachments })
      setDoc(updated)
      setLinkDialogOpen(false)
      setNewLink({ name: '', url: '' })
    } catch (err) {
      console.error('Update failed', err)
      showAlert('Failed to add link', 'error')
    }
  }

  async function removeAttachment(idx: number) {
    if (!tenant || !id || !doc || !doc.attachments) return
    const newAttachments = doc.attachments.filter((_, i) => i !== idx)
    try {
      const updated = await updatePromotion(tenant, id, { attachments: newAttachments })
      setDoc(updated)
    } catch (err) {
      console.error('Update failed', err)
      showAlert('Failed to remove attachment', 'error')
    }
  }

  const getFullUrl = (url: string) => resolveUploadUrl(url)

  function formatTs(iso?: string | null): string {
    if (!iso) return '—'
    const s = formatDateTimeForDisplay(iso, dateFormat, timeZone)
    return s || String(iso)
  }

  function formatUtc(iso?: string | null): string {
    if (!iso) return ''
    try {
      const d = new Date(iso)
      if (Number.isNaN(d.getTime())) return ''
      return d.toUTCString()
    } catch {
      return ''
    }
  }

  function audienceSummary(aud: Promotion['audience']): string {
    if (!aud || typeof aud !== 'object') return '—'
    const t = aud.type || 'all'
    if (t === 'all') return 'All active customers'
    if (t === 'tags') {
      const tags = Array.isArray(aud.tags) ? aud.tags.filter(Boolean) : []
      return tags.length ? `Tags: ${tags.join(', ')}` : 'Tags (none)'
    }
    if (t === 'segment') {
      const s = aud.segment || {}
      return `Segment: ${s.type || '?'}${s.days != null ? ` (${s.days} days)` : ''}`
    }
    if (t === 'custom') {
      const phones = (aud.phones || []).length
      const emails = (aud.emails || []).length
      return `Custom: ${phones} phone(s), ${emails} email(s)`
    }
    return String(t)
  }

  return (
    <Box sx={{ p:1 }}>
      <Typography variant="h5" sx={{ mb:2 }}>Promotion Details</Typography>
      <Grid container spacing={2}>
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="subtitle2" color="text.secondary">Summary</Typography>
              <Stack spacing={1} sx={{ mt:1 }}>
                <div><b>Name:</b> {doc?.name}</div>
                <Stack direction="row" alignItems="center" spacing={1} flexWrap="wrap">
                  <b>Status:</b>
                  <Chip
                    size="small"
                    label={doc?.status || '—'}
                    color={
                      doc?.status === 'completed' ? 'success' :
                      doc?.status === 'running' ? 'warning' :
                      doc?.status === 'scheduled' ? 'info' :
                      'default'
                    }
                    variant="outlined"
                  />
                </Stack>
                <div><b>Channel:</b> {doc?.channel}</div>
                {doc?.message && (
                  <Box>
                    <b>Message:</b>
                    <Typography variant="body2" color="text.secondary" sx={{ whiteSpace: 'pre-wrap', mt: 0.5 }}>
                      {doc.message.length > 400 ? `${doc.message.slice(0, 400)}…` : doc.message}
                    </Typography>
                  </Box>
                )}
                <div><b>Audience:</b> {audienceSummary(doc?.audience)}</div>
                {doc?.resend_of ? (
                  <div>
                    <b>Resent from:</b>{' '}
                    <RouterLink to={`/promotions/${doc.resend_of}`}>{doc.resend_of}</RouterLink>
                  </div>
                ) : null}
                {(doc?.interactive_type || doc?.offer_code) && (
                  <div>
                    <b>WhatsApp extras:</b>{' '}
                    {doc?.interactive_type ? <Chip size="small" sx={{ mr: 0.5 }} label={doc.interactive_type} /> : null}
                    {doc?.offer_code ? <Chip size="small" label={`Code: ${doc.offer_code}`} variant="outlined" /> : null}
                  </div>
                )}
                <Divider sx={{ my: 0.5 }} />
                <Typography variant="caption" color="text.secondary" display="block" fontWeight={600}>
                  Scheduling
                </Typography>
                {doc?.schedule_at ? (
                  <>
                    <div><b>Scheduled send:</b> {formatTs(doc.schedule_at)}</div>
                    <Typography variant="caption" color="text.secondary" display="block">
                      UTC: {formatUtc(doc.schedule_at)}
                    </Typography>
                    {doc.status === 'scheduled' && (
                      <Typography variant="caption" color="info.main" display="block">
                        This promotion will go out automatically when the time is reached (scheduler must be running).
                      </Typography>
                    )}
                  </>
                ) : (
                  <Typography variant="body2" color="text.secondary">
                    Not scheduled — use <b>Send now</b> or set a time when creating a promotion.
                  </Typography>
                )}
                {(doc?.started_at || doc?.completed_at) && (
                  <>
                    <Typography variant="caption" color="text.secondary" display="block" fontWeight={600} sx={{ pt: 0.5 }}>
                      Send run
                    </Typography>
                    {doc.started_at && <div><b>Started:</b> {formatTs(doc.started_at)}</div>}
                    {doc.completed_at && <div><b>Completed:</b> {formatTs(doc.completed_at)}</div>}
                  </>
                )}
                {(doc?.stats && (doc.stats.total != null || doc.stats.sent != null)) && (
                  <div>
                    <b>Last run stats:</b> total {doc.stats.total ?? '—'} · sent {doc.stats.sent ?? '—'} · failed {doc.stats.failed ?? '—'}
                  </div>
                )}
                <div><b>Live progress:</b> {stats.total} total · {stats.sent} sent · {stats.failed} failed</div>
                {(doc?.created_at || doc?.updated_at) && (
                  <Typography variant="caption" color="text.secondary" display="block">
                    Created {doc.created_at ? formatTs(doc.created_at) : '—'}
                    {doc.updated_at ? ` · Updated ${formatTs(doc.updated_at)}` : ''}
                  </Typography>
                )}
                <Stack direction="row" spacing={2} sx={{ mt:1 }} flexWrap="wrap">
                  {doc?.status === 'completed' ? (
                    <Button variant="contained" onClick={openResendDialog} disabled={!tenant}>
                      Resend promotion…
                    </Button>
                  ) : (
                    <Button
                      variant="contained"
                      onClick={onSend}
                      disabled={!tenant || doc?.status === 'running'}
                    >
                      Send now
                    </Button>
                  )}
                </Stack>
              </Stack>
            </CardContent>
          </Card>

          <Card sx={{ mt: 2 }}>
            <CardContent>
              <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 1 }}>
                <Typography variant="subtitle2" color="text.secondary">Attachments</Typography>
                <Stack direction="row" spacing={1}>
                  <input
                    type="file"
                    hidden
                    ref={fileInputRef}
                    onChange={handleFileUpload}
                    accept="image/*,video/*,.pdf,application/pdf"
                  />
                  <Button
                    size="small"
                    startIcon={uploading ? <CircularProgress size={16} /> : <AddIcon />}
                    onClick={() => fileInputRef.current?.click()}
                    disabled={uploading}
                  >
                    Upload
                  </Button>
                  <Button
                    size="small"
                    startIcon={<LinkIcon />}
                    onClick={() => setLinkDialogOpen(true)}
                  >
                    Link
                  </Button>
                </Stack>
              </Stack>

              <List>
                {(doc?.attachments || []).map((a, i) => (
                  <ListItem key={i} divider>
                    <Box sx={{ mr: 2, display: 'flex', alignItems: 'center' }}>
                      {a.type === 'image' && <ImageIcon color="primary" />}
                      {a.type === 'video' && <MovieIcon color="primary" />}
                      {a.type === 'link' && <LinkIcon color="primary" />}
                      {a.type === 'document' && <PdfIcon color="primary" />}
                    </Box>
                    <ListItemText
                      primary={<Link href={getFullUrl(a.url)} target="_blank" rel="noopener">{a.name || a.url}</Link>}
                      secondary={a.type}
                    />
                    <ListItemSecondaryAction>
                      <IconButton edge="end" size="small" onClick={() => removeAttachment(i)}>
                        <DeleteIcon fontSize="small" />
                      </IconButton>
                    </ListItemSecondaryAction>
                  </ListItem>
                ))}
                {!(doc?.attachments?.length) && (
                  <Typography variant="body2" color="text.secondary" sx={{ py: 2, textAlign: 'center' }}>
                    No attachments yet
                  </Typography>
                )}
              </List>
            </CardContent>
          </Card>
        </Grid>

        <Dialog open={resendOpen} onClose={() => !resendSending && setResendOpen(false)} fullWidth maxWidth="sm">
          <DialogTitle>Resend promotion</DialogTitle>
          <DialogContent>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
              Creates a <strong>new</strong> promotion (name gets a “(resend)” suffix), sends it, and leaves this original record unchanged. Audience below is stored on the new row only; adjust it if you want a different group.
            </Typography>
            <Stack spacing={2} sx={{ mt: 1 }}>
              <TextField
                select
                label="Audience"
                value={resendAudType}
                onChange={e => setResendAudType(e.target.value as typeof resendAudType)}
                size="small"
                fullWidth
              >
                <MenuItem value="all">All active customers</MenuItem>
                <MenuItem value="tags">Tags</MenuItem>
                <MenuItem value="custom">Custom phones / emails</MenuItem>
                <MenuItem value="segment">Retention segment</MenuItem>
              </TextField>
              {resendAudType === 'tags' && (
                <TextField
                  label="Tags (comma separated)"
                  value={resendTags}
                  onChange={e => setResendTags(e.target.value)}
                  size="small"
                  fullWidth
                />
              )}
              {resendAudType === 'segment' && (
                <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1}>
                  <TextField
                    select
                    label="Segment"
                    value={resendSegType}
                    onChange={e => setResendSegType(e.target.value)}
                    size="small"
                    fullWidth
                  >
                    <MenuItem value="active">active</MenuItem>
                    <MenuItem value="at_risk">at_risk</MenuItem>
                    <MenuItem value="churned">churned</MenuItem>
                  </TextField>
                  <TextField
                    label="Days (optional)"
                    value={resendSegDays}
                    onChange={e => setResendSegDays(e.target.value)}
                    size="small"
                    fullWidth
                    helperText="Used by segment rules when applicable"
                  />
                </Stack>
              )}
              {resendAudType === 'custom' && (
                <>
                  <TextField
                    label="Phones (comma or newline, E.164)"
                    value={resendPhones}
                    onChange={e => setResendPhones(e.target.value)}
                    size="small"
                    fullWidth
                    multiline
                    minRows={2}
                    error={resendInvalidPhones.length > 0}
                    helperText={
                      resendInvalidPhones.length
                        ? `Invalid: ${resendInvalidPhones.join(', ')}`
                        : 'One or more numbers required for WhatsApp when channel includes WhatsApp'
                    }
                  />
                  <TextField
                    label="Emails (comma separated)"
                    value={resendEmails}
                    onChange={e => setResendEmails(e.target.value)}
                    size="small"
                    fullWidth
                  />
                </>
              )}
            </Stack>
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setResendOpen(false)} disabled={resendSending}>
              Cancel
            </Button>
            <Button
              variant="contained"
              onClick={onResendConfirm}
              disabled={resendSending || resendInvalidPhones.length > 0}
            >
              {resendSending ? <CircularProgress size={22} /> : 'Send now'}
            </Button>
          </DialogActions>
        </Dialog>

        <Dialog open={linkDialogOpen} onClose={() => setLinkDialogOpen(false)} fullWidth maxWidth="xs">
          <DialogTitle>Add Link</DialogTitle>
          <DialogContent>
            <Stack spacing={2} sx={{ mt: 1 }}>
              <TextField
                label="Name (optional)"
                fullWidth
                size="small"
                value={newLink.name}
                onChange={(e) => setNewLink({ ...newLink, name: e.target.value })}
              />
              <TextField
                label="URL"
                fullWidth
                size="small"
                value={newLink.url}
                onChange={(e) => setNewLink({ ...newLink, url: e.target.value })}
                placeholder="https://..."
              />
            </Stack>
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setLinkDialogOpen(false)}>Cancel</Button>
            <Button onClick={handleAddLink} variant="contained" disabled={!newLink.url}>Add</Button>
          </DialogActions>
        </Dialog>
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="subtitle2" color="text.secondary">Logs (latest)</Typography>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>Channel</TableCell>
                    <TableCell>To</TableCell>
                    <TableCell>Status</TableCell>
                    <TableCell>When</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {logs.map(l=> (
                    <TableRow key={l.id}>
                      <TableCell>{l.channel}</TableCell>
                      <TableCell>{l.to}</TableCell>
                      <TableCell>{l.status}</TableCell>
                      <TableCell>{l.sent_at || '-'}</TableCell>
                    </TableRow>
                  ))}
                  {!logs.length && (
                    <TableRow><TableCell colSpan={4}><Typography variant="body2" color="text.secondary">{loading? 'Loading...' : 'No logs yet'}</Typography></TableCell></TableRow>
                  )}
                </TableBody>
              </Table>
            </CardContent>
          </Card>

          {includesWhatsApp(doc?.channel) && (
            <Box sx={{ mt: 2 }}>
              <Typography variant="subtitle2" sx={{ mb: 1 }} color="text.secondary">WhatsApp Preview</Typography>
              <WhatsAppPreview
                message={doc ? promotionMessageWithLinks(doc) : ''}
                attachments={doc?.attachments}
                getFullUrl={getFullUrl}
                interactive_type={doc?.interactive_type}
                buttons={doc?.buttons}
                list_sections={doc?.list_sections}
                cta_entries={
                  doc?.interactive_type === 'cta_url'
                    ? promotionCtaEntriesForPreview(doc)
                    : undefined
                }
                cta_display_text={
                  doc?.interactive_type === 'cta_url'
                    ? (doc.cta_entries?.find(e => (e.url || '').trim())?.display_text ||
                        doc.cta_display_text ||
                        'Shop Now')
                    : undefined
                }
                cta_footer={doc?.interactive_type === 'cta_url' ? (doc.cta_footer || undefined) : undefined}
                whatsappProvider={waProvider}
              />
            </Box>
          )}
          {includesSms(doc?.channel) && (
            <Box sx={{ mt: 2 }}>
              <Typography variant="subtitle2" sx={{ mb: 1 }} color="text.secondary">SMS Preview</Typography>
              <SmsPreview message={doc?.message ?? ''} attachments={doc?.attachments} offerCode={doc?.offer_code} />
              <Alert severity="info" sx={{ mt: 1, fontSize: 12 }}>
                SMS sends as plain text. Link attachments are appended to the message body automatically.
              </Alert>
            </Box>
          )}
        </Grid>
      </Grid>
    </Box>
  )
}
