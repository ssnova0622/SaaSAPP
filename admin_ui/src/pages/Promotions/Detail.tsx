import { useEffect, useState, useRef } from 'react'
import { useParams } from 'react-router-dom'
import { Box, Button, Card, CardContent, Grid, Stack, Table, TableBody, TableCell, TableHead, TableRow, Typography, IconButton, TextField, Dialog, DialogTitle, DialogContent, DialogActions, Link, CircularProgress, List, ListItem, ListItemText, ListItemSecondaryAction, Chip, Divider } from '@mui/material'
import { Delete as DeleteIcon, Add as AddIcon, Link as LinkIcon, Image as ImageIcon, Movie as MovieIcon, PictureAsPdf as PdfIcon } from '@mui/icons-material'
import { getPromotion, sendPromotion, getPromotionLogs, Promotion, updatePromotion, uploadFile, Attachment } from '@api/promotions'
import { getWhatsAppConfig } from '@api/tenants'
import { promotionMessageWithLinks, promotionCtaEntriesForPreview } from './messagePreviewUtils'
import { resolveUploadUrl } from '@api/config'
import { useWebSocket } from '@hooks/useWebSocket'
import { useEffectiveTenant } from '../../hooks/useEffectiveTenant'
import WhatsAppPreview from '../../components/WhatsAppPreview'
import { useAlert } from '@contexts/AlertContext'

export default function PromotionDetail(){
  const { effectiveTenant } = useEffectiveTenant()
  const tenant = effectiveTenant
  const { showAlert } = useAlert()
  const { id = '' } = useParams()
  const [doc,setDoc]=useState<Promotion|undefined>()
  const [stats,setStats]=useState<{total:number;sent:number;failed:number}>({total:0,sent:0,failed:0})
  const [logs,setLogs]=useState<any[]>([])
  const [loading,setLoading]=useState(false)
  const [uploading, setUploading] = useState(false)
  const [linkDialogOpen, setLinkDialogOpen] = useState(false)
  const [newLink, setNewLink] = useState({ name: '', url: '' })
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [waProvider, setWaProvider] = useState<string>('twilio')
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
      const res = await sendPromotion(tenant, id)
      setStats({ total:res.total, sent:res.sent, failed:res.failed })
      load()
    } catch (err: any) {
      console.error('Send failed', err)
      showAlert(err?.response?.data?.detail || 'Failed to send promotion', 'error')
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
    try {
      const d = new Date(iso)
      if (Number.isNaN(d.getTime())) return String(iso)
      const local = d.toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' })
      const tz = Intl.DateTimeFormat().resolvedOptions().timeZone || 'local'
      return `${local} (${tz})`
    } catch {
      return String(iso)
    }
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
                <Stack direction="row" spacing={2} sx={{ mt:1 }}>
                  <Button variant="contained" onClick={onSend} disabled={!tenant}>Send now</Button>
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

          {(doc?.channel === 'whatsapp' || doc?.channel === 'both') && (
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
        </Grid>
      </Grid>
    </Box>
  )
}
