import { useState, useRef, useEffect } from 'react'
import { Box, Button, Card, CardContent, MenuItem, Stack, TextField, Typography, IconButton, Dialog, DialogTitle, DialogContent, DialogActions, List, ListItem, ListItemText, ListItemSecondaryAction, CircularProgress, Grid, Alert, Divider, Tab, Tabs, FormControlLabel, Checkbox, Switch, Tooltip } from '@mui/material'
import { Delete as DeleteIcon, Add as AddIcon, Link as LinkIcon, Image as ImageIcon, Movie as MovieIcon, PictureAsPdf as PdfIcon } from '@mui/icons-material'
import { createPromotion, uploadFile, Attachment, Button as WaButton, ListSection as WaListSection, CtaEntry } from '@api/promotions'
import { getWhatsAppConfig } from '@api/tenants'
import { promotionMessageWithLinks } from './messagePreviewUtils'
import { resolveUploadUrl } from '@api/config'
import { useNavigate, useLocation } from 'react-router-dom'
import { useEffectiveTenant } from '../../hooks/useEffectiveTenant'
import { parsePhoneList, findInvalidPhones } from '../../utils/phone'
import WhatsAppPreview from '../../components/WhatsAppPreview'
import { useAlert } from '@contexts/AlertContext'

/** Composer tabs: some map to Meta interactive types; others are layout hints only (document / media). */
type WaComposerTab =
  | 'none'
  | 'button'
  | 'list'
  | 'cta_url'
  | 'document'
  | 'media'
  | 'location'
  | 'flow'
  | 'catalog'

function getEffectiveInteractive(
  waTab: WaComposerTab,
  payloadEnabled: boolean,
): 'button' | 'list' | 'cta_url' | undefined {
  if (!payloadEnabled) return undefined
  if (waTab === 'button' || waTab === 'list' || waTab === 'cta_url') return waTab
  return undefined
}

export default function PromotionNew(){
  const { effectiveTenant } = useEffectiveTenant()
  const tenant = effectiveTenant
  const { showAlert } = useAlert()
  const nav = useNavigate()
  const location = useLocation()
  const [name,setName]=useState('')
  const [channel,setChannel]=useState<'whatsapp'|'email'|'both'>('both')
  const [message,setMessage]=useState('')
  const [audType,setAudType]=useState<'all'|'tags'|'custom'|'segment'>('all')
  const [tags,setTags]=useState('')
  const [segment, setSegment]=useState<{type: string, days?: number}|null>(null)
  const [phones,setPhones]=useState('')
  const [emails,setEmails]=useState('')
  /** Send later: separate date + time avoids flaky `datetime-local` in some browsers. */
  const [scheduleSendLater, setScheduleSendLater] = useState(false)
  const [scheduleDate, setScheduleDate] = useState('')
  const [scheduleTime, setScheduleTime] = useState('09:00')
  const [attachments, setAttachments] = useState<Attachment[]>([])
  const [saving,setSaving]=useState(false)
  const [uploading, setUploading] = useState(false)
  const [linkDialogOpen, setLinkDialogOpen] = useState(false)
  const [newLink, setNewLink] = useState({ name: '', url: '' })
  const fileInputRef = useRef<HTMLInputElement>(null)

  const [waTab, setWaTab] = useState<WaComposerTab>('none')
  /** When off, Buttons / List / CTA are not sent as WhatsApp interactive (plain text + attachments only). */
  const [waInteractivePayloadEnabled, setWaInteractivePayloadEnabled] = useState(true)
  const [buttons, setButtons] = useState<WaButton[]>([])
  const [listSections, setListSections] = useState<WaListSection[]>([{ title: 'Options', rows: [] }])
  const [ctaEntries, setCtaEntries] = useState<CtaEntry[]>([
    { id: 'cta_1', display_text: 'Shop Now', url: '' },
  ])
  const [ctaFooter, setCtaFooter] = useState('')
  /** When false, URLs are not duplicated in the message bubble (only the CTA button / extra rows in preview). */
  const [ctaAppendUrlsInBody, setCtaAppendUrlsInBody] = useState(false)
  const [offerCode, setOfferCode] = useState('')
  const [waProvider, setWaProvider] = useState<string>('twilio')

  const sectionBoxSx = { p: 1, bgcolor: 'action.hover', border: 1, borderColor: 'divider', borderRadius: 1 } as const

  const phoneList = audType==='custom' ? parsePhoneList(phones) : []
  const invalidPhones = audType==='custom' ? findInvalidPhones(phoneList) : []
  const ctaFilled = ctaEntries.filter(e => (e.url || '').trim())
  const effectiveInteractive = getEffectiveInteractive(waTab, waInteractivePayloadEnabled)
  const disabled =
    !tenant ||
    !name ||
    !message ||
    (audType === 'custom' && invalidPhones.length > 0) ||
    (effectiveInteractive === 'cta_url' && ctaFilled.length === 0) ||
    (scheduleSendLater && (!scheduleDate || !scheduleTime))

  useEffect(() => {
    if (!tenant) return
    getWhatsAppConfig(tenant)
      .then(c => setWaProvider(String(c?.provider || 'twilio')))
      .catch(() => setWaProvider('twilio'))
  }, [tenant])

  useEffect(() => {
    const params = new URLSearchParams(location.search)
    const segType = params.get('segment')
    const segDays = params.get('days')
    if (segType) {
      setAudType('segment')
      setSegment({ type: segType, days: segDays ? parseInt(segDays) : undefined })
      setName(`Promotion for ${segType} customers`)
    }
  }, [location.search])

  async function handleFileUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file || !tenant) return
    setUploading(true)
    try {
      const res = await uploadFile(tenant, file)
      let type: Attachment['type'] = 'image'
      if (file.type.startsWith('video/')) type = 'video'
      else if (file.type === 'application/pdf' || file.name.toLowerCase().endsWith('.pdf')) type = 'document'
      const att: Attachment = { type, url: res.url, name: file.name }
      setAttachments([...attachments, att])
    } catch (err) {
      console.error('Upload failed', err)
      showAlert('Upload failed', 'error')
    } finally {
      setUploading(false)
      if (fileInputRef.current) fileInputRef.current.value = ''
    }
  }

  function handleAddLink() {
    if (!newLink.url) return
    const att: Attachment = { type: 'link', url: newLink.url, name: newLink.name || newLink.url }
    setAttachments([...attachments, att])
    setLinkDialogOpen(false)
    setNewLink({ name: '', url: '' })
  }

  function removeAttachment(idx: number) {
    setAttachments(attachments.filter((_, i) => i !== idx))
  }

  const getFullUrl = (url: string) => resolveUploadUrl(url)

  function addButton() {
    if (buttons.length >= 3) return
    setButtons([...buttons, { id: `btn_${buttons.length + 1}`, title: `Button ${buttons.length + 1}` }])
  }

  function updateButton(idx: number, field: keyof WaButton, val: string) {
    const newBtns = [...buttons]
    newBtns[idx] = { ...newBtns[idx], [field]: val }
    setButtons(newBtns)
  }

  function removeButton(idx: number) {
    setButtons(buttons.filter((_, i) => i !== idx))
  }

  function addListRow(secIdx: number) {
    const newSections = [...listSections]
    newSections[secIdx].rows.push({ id: `item_${newSections[secIdx].rows.length + 1}`, title: `Item ${newSections[secIdx].rows.length + 1}` })
    setListSections(newSections)
  }

  function updateListRow(secIdx: number, rowIdx: number, field: keyof any, val: string) {
    const newSections = [...listSections]
    newSections[secIdx].rows[rowIdx] = { ...newSections[secIdx].rows[rowIdx], [field]: val }
    setListSections(newSections)
  }

  function removeListRow(secIdx: number, rowIdx: number) {
    const newSections = [...listSections]
    newSections[secIdx].rows = newSections[secIdx].rows.filter((_, i) => i !== rowIdx)
    setListSections(newSections)
  }

  function addCtaRow() {
    const n = ctaEntries.length + 1
    setCtaEntries([...ctaEntries, { id: `cta_${n}`, display_text: `Link ${n}`, url: '' }])
  }

  function updateCtaRow(idx: number, field: keyof CtaEntry, val: string) {
    const next = [...ctaEntries]
    next[idx] = { ...next[idx], [field]: val }
    setCtaEntries(next)
  }

  function removeCtaRow(idx: number) {
    if (ctaEntries.length <= 1) return
    setCtaEntries(ctaEntries.filter((_, i) => i !== idx))
  }

  async function onCreate(){
    if(!tenant) return
    setSaving(true)
    const audience:any = { type: audType }
    if(audType==='tags') audience.tags = tags.split(',').map(t=>t.trim()).filter(Boolean)
    if(audType==='custom') {
      audience.phones = phoneList
      audience.emails = emails.split(',').map(t=>t.trim()).filter(Boolean)
    }
    if(audType==='segment' && segment) {
      audience.segment = segment
    }
    try {
      let schedule_at: string | undefined
      if (scheduleSendLater && scheduleDate && scheduleTime) {
        const when = new Date(`${scheduleDate}T${scheduleTime}:00`)
        if (!Number.isNaN(when.getTime())) {
          schedule_at = when.toISOString()
        }
      }
      const filledCta = ctaEntries.map((e, i) => ({
        id: e.id || `cta_${i + 1}`,
        display_text: (e.display_text || 'Link').trim() || 'Link',
        url: (e.url || '').trim(),
      })).filter(e => e.url)
      const doc = await createPromotion(tenant, { 
        name, 
        channel, 
        message, 
        audience, 
        attachments,
        schedule_at,
        interactive_type: effectiveInteractive,
        buttons: effectiveInteractive === 'button' ? buttons : undefined,
        list_sections: effectiveInteractive === 'list' ? listSections : undefined,
        cta_entries: effectiveInteractive === 'cta_url' && filledCta.length ? filledCta : undefined,
        cta_url: effectiveInteractive === 'cta_url' && filledCta[0] ? filledCta[0].url : undefined,
        cta_display_text: effectiveInteractive === 'cta_url' && filledCta[0] ? filledCta[0].display_text : undefined,
        cta_footer: effectiveInteractive === 'cta_url' && ctaFooter.trim() ? ctaFooter.trim() : undefined,
        cta_append_urls_to_body: effectiveInteractive === 'cta_url' ? ctaAppendUrlsInBody : undefined,
        offer_code: offerCode.trim() ? offerCode.trim() : undefined,
      })
      nav(`/promotions/${doc.id}`)
    } catch (err) {
      console.error('Creation failed', err)
      showAlert('Failed to create promotion', 'error')
    } finally {
      setSaving(false)
    }
  }

  const previewBody = promotionMessageWithLinks({
    message,
    interactive_type: effectiveInteractive ?? null,
    buttons,
    list_sections: listSections,
    cta_entries: ctaEntries,
    cta_url: null,
    cta_display_text: ctaEntries[0]?.display_text,
    cta_append_urls_to_body: effectiveInteractive === 'cta_url' ? ctaAppendUrlsInBody : undefined,
    offer_code: offerCode.trim() || undefined,
  })

  return (
    <Box sx={{ p:1 }}>
      <Typography variant="h5" sx={{ mb:2 }}>New Promotion</Typography>
      <Grid container spacing={2}>
        <Grid item xs={12} md={7}>
          <Card>
            <CardContent>
              <Stack spacing={2}>
                <TextField label="Name" value={name} onChange={e=>setName(e.target.value)} size="small" />
                <TextField select label="Channel" value={channel} onChange={e=>setChannel(e.target.value as any)} size="small">
                  <MenuItem value="both">both</MenuItem>
                  <MenuItem value="whatsapp">whatsapp</MenuItem>
                  <MenuItem value="email">email</MenuItem>
                </TextField>
                <TextField label="Message" value={message} onChange={e=>setMessage(e.target.value)} multiline minRows={3} size="small" />
                {(channel === 'whatsapp' || channel === 'both') && (
                  <TextField
                    label="Offer code (optional)"
                    value={offerCode}
                    onChange={e => setOfferCode(e.target.value)}
                    size="small"
                    helperText="Appended to WhatsApp and email; users can copy from the message (native “copy code” needs a Meta marketing template)."
                  />
                )}

                <Box sx={{ border: 1, borderColor: 'divider', borderRadius: 1, p: 1.5 }}>
                  <FormControlLabel
                    control={
                      <Checkbox
                        checked={scheduleSendLater}
                        onChange={e => {
                          const on = e.target.checked
                          setScheduleSendLater(on)
                          if (on && !scheduleDate) {
                            const t = new Date()
                            setScheduleDate(t.toISOString().slice(0, 10))
                          }
                        }}
                        size="small"
                      />
                    }
                    label={<Typography variant="body2">Schedule send for later</Typography>}
                  />
                  <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 1, pl: 4 }}>
                    Times use your computer&apos;s local timezone and are stored in UTC. Leave unchecked to save as draft or send manually.
                  </Typography>
                  {scheduleSendLater && (
                    <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1} sx={{ pl: { xs: 0, sm: 4 } }}>
                      <TextField
                        label="Send date"
                        type="date"
                        value={scheduleDate}
                        onChange={e => setScheduleDate(e.target.value)}
                        size="small"
                        InputLabelProps={{ shrink: true }}
                        inputProps={{
                          min: new Date().toISOString().slice(0, 10),
                        }}
                        sx={{ minWidth: 160 }}
                      />
                      <TextField
                        label="Send time"
                        type="time"
                        value={scheduleTime}
                        onChange={e => setScheduleTime(e.target.value)}
                        size="small"
                        InputLabelProps={{ shrink: true }}
                        sx={{ minWidth: 140 }}
                      />
                    </Stack>
                  )}
                </Box>

                {(channel === 'whatsapp' || channel === 'both') && (
                  <Box sx={{ border: 1, borderColor: 'divider', p: 2, borderRadius: 1 }}>
                    <Typography variant="subtitle2" gutterBottom>
                      WhatsApp message type
                    </Typography>
                    <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 1 }}>
                      Tabs cover session-message styles we can send today. Disabled tabs are on the roadmap; toggle interactive payload off to force plain text with attachments.
                    </Typography>
                    <Tabs value={waTab} onChange={(_, v) => setWaTab(v)} sx={{ mb: 2 }} variant="scrollable" scrollButtons="auto">
                      <Tab label="None" value="none" />
                      <Tab label="Buttons" value="button" />
                      <Tab label="List" value="list" />
                      <Tab label="CTA links" value="cta_url" />
                      <Tab label="Document" value="document" />
                      <Tab label="Photo / video" value="media" />
                      <Tooltip title="Location request messages are not available in promotions yet.">
                        <span>
                          <Tab label="Location" value="location" disabled />
                        </span>
                      </Tooltip>
                      <Tooltip title="WhatsApp Flows require a separate Flow setup in Meta Business.">
                        <span>
                          <Tab label="Flow" value="flow" disabled />
                        </span>
                      </Tooltip>
                      <Tooltip title="Product / catalog messages need catalog API integration.">
                        <span>
                          <Tab label="Catalog" value="catalog" disabled />
                        </span>
                      </Tooltip>
                    </Tabs>

                    {(waTab === 'button' || waTab === 'list' || waTab === 'cta_url') && (
                      <FormControlLabel
                        sx={{ mb: 1, alignItems: 'flex-start' }}
                        control={
                          <Switch
                            size="small"
                            checked={waInteractivePayloadEnabled}
                            onChange={e => setWaInteractivePayloadEnabled(e.target.checked)}
                          />
                        }
                        label={
                          <Box>
                            <Typography variant="body2">Enable WhatsApp interactive payload</Typography>
                            <Typography variant="caption" color="text.secondary">
                              Off = send as plain text (and attachments) only; URLs in buttons/list still appended below if you configured them.
                            </Typography>
                          </Box>
                        }
                      />
                    )}

                    {waTab === 'document' && (
                      <Box sx={sectionBoxSx}>
                        <Typography variant="body2" color="text.secondary" sx={{ mb: 0 }}>
                          Sends your{' '}
                          <Box component="span" sx={{ fontWeight: 700 }}>message as the caption</Box>
                          {' '}with the first PDF in Attachments as a WhatsApp document. Add a link in the body or switch to CTA links for a native link button.
                        </Typography>
                      </Box>
                    )}

                    {waTab === 'media' && (
                      <Box sx={sectionBoxSx}>
                        <Typography variant="body2" color="text.secondary" sx={{ mb: 0 }}>
                          Upload an image or video under{' '}
                          <Box component="span" sx={{ fontWeight: 700 }}>Attachments</Box>
                          . Caption = your message; first image or video wins. Document + interactive types are separate sends from this composer.
                        </Typography>
                      </Box>
                    )}

                    {waTab === 'button' && (
                      <Stack spacing={1}>
                        {buttons.map((btn, idx) => (
                          <Stack key={idx} direction="row" spacing={1} alignItems="center">
                            <TextField label="Button Text" size="small" value={btn.title} onChange={e => updateButton(idx, 'title', e.target.value)} sx={{ flex: 1 }} />
                            <TextField label="URL (optional)" size="small" value={btn.url || ''} onChange={e => updateButton(idx, 'url', e.target.value)} sx={{ flex: 1 }} />
                            <TextField label="ID" size="small" value={btn.id} onChange={e => updateButton(idx, 'id', e.target.value)} sx={{ width: 80 }} />
                            <IconButton onClick={() => removeButton(idx)} color="error" size="small"><DeleteIcon /></IconButton>
                          </Stack>
                        ))}
                        {buttons.length < 3 && (
                          <Button startIcon={<AddIcon />} onClick={addButton} size="small">Add Button</Button>
                        )}
                        <Typography variant="caption" color="text.secondary">Max 3 buttons allowed by WhatsApp. If URL is provided, it will be included in the message.</Typography>
                      </Stack>
                    )}

                    {waTab === 'cta_url' && (
                      <Stack spacing={1}>
                        <Box sx={sectionBoxSx}>
                          <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 1 }}>
                            Link rows: WhatsApp opens the <Box component="span" sx={{ fontWeight: 700 }}>first URL</Box> as the main button. Add more rows and enable &quot;Include CTA URLs in message text&quot; to show extra links in the bubble.
                          </Typography>
                          <Stack spacing={1} sx={{ pl: { xs: 0, sm: 1 } }}>
                            {ctaEntries.map((row, idx) => (
                              <Stack key={row.id || idx} direction="row" spacing={1} alignItems="center">
                                <TextField
                                  label="Button / line label"
                                  size="small"
                                  value={row.display_text}
                                  onChange={e => updateCtaRow(idx, 'display_text', e.target.value)}
                                  sx={{ flex: 1 }}
                                  helperText={idx === 0 ? 'First row: primary CTA label' : undefined}
                                />
                                <TextField
                                  label="URL"
                                  size="small"
                                  value={row.url}
                                  onChange={e => updateCtaRow(idx, 'url', e.target.value)}
                                  sx={{ flex: 1.2 }}
                                />
                                <IconButton onClick={() => removeCtaRow(idx)} color="error" size="small" disabled={ctaEntries.length <= 1}>
                                  <DeleteIcon />
                                </IconButton>
                              </Stack>
                            ))}
                            <Button startIcon={<AddIcon />} onClick={addCtaRow} size="small">
                              Add link
                            </Button>
                          </Stack>
                        </Box>
                        <TextField label="Footer (optional)" value={ctaFooter} onChange={e => setCtaFooter(e.target.value)} size="small" fullWidth />
                        <FormControlLabel
                          control={
                            <Checkbox
                              checked={ctaAppendUrlsInBody}
                              onChange={e => setCtaAppendUrlsInBody(e.target.checked)}
                              size="small"
                            />
                          }
                          label="Include CTA URLs in message text"
                        />
                        <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: -1 }}>
                          Turn off to match WhatsApp (link only on the button). Email sends always include links for click-through.
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                          Add an image, video, or PDF in Attachments to use as the message header (first matching attachment is used).
                        </Typography>
                      </Stack>
                    )}

                    {waTab === 'list' && (
                      <Stack spacing={1}>
                        {listSections.map((sec, sIdx) => (
                          <Box key={sIdx} sx={sectionBoxSx}>
                            <TextField label="Section Title" size="small" fullWidth value={sec.title} onChange={e => {
                                const ns = [...listSections]; ns[sIdx].title = e.target.value; setListSections(ns);
                            }} sx={{ mb: 1 }} />
                            <Stack spacing={1} sx={{ pl: 2 }}>
                                {sec.rows.map((row, rIdx) => (
                                    <Stack key={rIdx} direction="row" spacing={1} alignItems="center">
                                        <TextField label="Item Title" size="small" value={row.title} onChange={e => updateListRow(sIdx, rIdx, 'title', e.target.value)} sx={{ flex: 1 }} />
                                        <TextField label="Description" size="small" value={row.description} onChange={e => updateListRow(sIdx, rIdx, 'description', e.target.value)} sx={{ flex: 1 }} />
                                        <TextField label="URL" size="small" value={row.url || ''} onChange={e => updateListRow(sIdx, rIdx, 'url', e.target.value)} sx={{ flex: 1 }} />
                                        <IconButton onClick={() => removeListRow(sIdx, rIdx)} color="error" size="small"><DeleteIcon /></IconButton>
                                    </Stack>
                                ))}
                                <Button startIcon={<AddIcon />} onClick={() => addListRow(sIdx)} size="small">Add Item</Button>
                            </Stack>
                          </Box>
                        ))}
                      </Stack>
                    )}
                  </Box>
                )}

                <Box>
                  <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 1 }}>
                    <Typography variant="subtitle2">Attachments</Typography>
                    <input type="file" hidden ref={fileInputRef} onChange={handleFileUpload} accept="image/*,video/*,.pdf,application/pdf" />
                    <Button size="small" startIcon={<AddIcon />} onClick={() => fileInputRef.current?.click()} disabled={uploading}>
                      Upload
                    </Button>
                    <Button size="small" startIcon={<LinkIcon />} onClick={() => setLinkDialogOpen(true)}>
                      Link
                    </Button>
                    {uploading && <CircularProgress size={20} />}
                  </Stack>
                  {attachments.length > 0 && (
                    <List dense sx={{ border: '1px solid #eee', borderRadius: 1 }}>
                      {attachments.map((att, idx) => (
                        <ListItem key={idx}>
                          <ListItemText
                            primary={
                              <Stack direction="row" spacing={1} alignItems="center">
                                {att.type === 'image' && <ImageIcon fontSize="small" color="primary" />}
                                {att.type === 'video' && <MovieIcon fontSize="small" color="primary" />}
                                {att.type === 'link' && <LinkIcon fontSize="small" color="primary" />}
                                {att.type === 'document' && <PdfIcon fontSize="small" color="primary" />}
                                <Typography variant="body2" sx={{ 
                                  maxWidth: 300, 
                                  overflow: 'hidden', 
                                  textOverflow: 'ellipsis', 
                                  whiteSpace: 'nowrap',
                                  cursor: 'pointer',
                                  textDecoration: 'underline',
                                  color: 'primary.main'
                                }} onClick={() => window.open(getFullUrl(att.url), '_blank')}>
                                  {att.name || att.url}
                                </Typography>
                              </Stack>
                            }
                          />
                          <ListItemSecondaryAction>
                            <IconButton edge="end" size="small" onClick={() => removeAttachment(idx)}>
                              <DeleteIcon fontSize="small" />
                            </IconButton>
                          </ListItemSecondaryAction>
                        </ListItem>
                      ))}
                    </List>
                  )}
                </Box>

                <TextField select label="Audience" value={audType} onChange={e=>setAudType(e.target.value as any)} size="small">
                  <MenuItem value="all">all</MenuItem>
                  <MenuItem value="tags">tags</MenuItem>
                  <MenuItem value="custom">custom</MenuItem>
                  <MenuItem value="segment">segment</MenuItem>
                </TextField>
                {audType==='tags' && (
                  <TextField label="Tags (comma separated)" value={tags} onChange={e=>setTags(e.target.value)} size="small" />
                )}
                {audType==='segment' && segment && (
                   <Alert severity="info">
                     Targeting <strong>{segment.type}</strong> customers {segment.days ? `(>${segment.days} days)` : ''}
                   </Alert>
                )}
                {audType==='custom' && (
                  <>
                    <TextField label="Phones (comma/newline separated, E.164 e.g., +911234567890)" value={phones} onChange={e=>setPhones(e.target.value)} error={invalidPhones.length>0} helperText={invalidPhones.length>0?`Invalid: ${invalidPhones.join(', ')}`:'Enter one or more phone numbers'} size="small" />
                    <TextField label="Emails (comma separated)" value={emails} onChange={e=>setEmails(e.target.value)} size="small" />
                  </>
                )}
                <Stack direction="row" spacing={2}>
                  <Button variant="contained" disabled={disabled || saving || uploading} onClick={onCreate}>Create</Button>
                  <Button onClick={()=>nav(-1)}>Cancel</Button>
                </Stack>
              </Stack>
            </CardContent>
          </Card>
        </Grid>

        {(channel === 'whatsapp' || channel === 'both') && (
          <Grid item xs={12} md={5}>
            <Typography variant="subtitle2" sx={{ mb: 1 }}>WhatsApp Preview</Typography>
            <WhatsAppPreview 
                message={previewBody} 
                attachments={attachments} 
                getFullUrl={getFullUrl} 
                interactive_type={effectiveInteractive === undefined ? undefined : effectiveInteractive}
                buttons={buttons}
                list_sections={listSections}
                cta_entries={effectiveInteractive === 'cta_url' ? ctaFilled : undefined}
                cta_display_text={
                  effectiveInteractive === 'cta_url'
                    ? (ctaFilled[0]?.display_text || ctaEntries[0]?.display_text || 'Shop Now')
                    : undefined
                }
                cta_footer={effectiveInteractive === 'cta_url' ? ctaFooter : undefined}
                whatsappProvider={waProvider}
            />
          </Grid>
        )}
      </Grid>

      <Dialog open={linkDialogOpen} onClose={() => setLinkDialogOpen(false)}>
        <DialogTitle>Add Link</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ mt: 1, minWidth: 300 }}>
            <TextField label="Name (optional)" fullWidth value={newLink.name} onChange={e => setNewLink({ ...newLink, name: e.target.value })} />
            <TextField label="URL" fullWidth value={newLink.url} onChange={e => setNewLink({ ...newLink, url: e.target.value })} />
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setLinkDialogOpen(false)}>Cancel</Button>
          <Button onClick={handleAddLink} variant="contained" disabled={!newLink.url}>Add</Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}
