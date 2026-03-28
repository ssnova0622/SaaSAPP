import { Box, Paper, Typography, Stack, Button, Divider, Alert } from '@mui/material'
import { Attachment, Button as WaButton, ListSection as WaListSection, CtaEntry } from '@api/promotions'
import { Link as LinkIcon, List as ListIcon, PictureAsPdf as PdfIcon, OpenInNew as OpenInNewIcon } from '@mui/icons-material'

function isMetaWhatsappProvider(p: string | null | undefined): boolean {
  const x = String(p || '').toLowerCase()
  return x === 'meta' || x === 'meta_cloud'
}

interface WhatsAppPreviewProps {
  message: string
  attachments?: Attachment[] | null
  getFullUrl: (url: string) => string
  interactive_type?: 'button' | 'list' | 'cta_url' | null
  buttons?: WaButton[] | null
  list_sections?: WaListSection[] | null
  /** CTA rows with URLs; all are shown as stacked action rows in preview (WhatsApp sends one native CTA; rest via text if enabled on promotion). */
  cta_entries?: CtaEntry[] | null
  cta_display_text?: string | null
  cta_footer?: string | null
  /**
   * Tenant WhatsApp provider from Settings (``twilio`` vs ``meta_cloud``).
   * Twilio cannot send Meta interactive CTA bubbles; backend falls back to plain text + link.
   */
  whatsappProvider?: string | null
}

export default function WhatsAppPreview({
  message,
  attachments,
  getFullUrl,
  interactive_type,
  buttons,
  list_sections,
  cta_entries,
  cta_display_text,
  cta_footer,
  whatsappProvider,
}: WhatsAppPreviewProps) {
  const ctaWithUrl = (cta_entries || []).filter(e => (e.url || '').trim())
  const metaInteractive = isMetaWhatsappProvider(whatsappProvider)
  const twilioStyleCta = interactive_type === 'cta_url' && !metaInteractive

  return (
    <Box sx={{ 
      p: 2, 
      backgroundColor: '#e5ddd5',
      backgroundImage: 'url("https://user-images.githubusercontent.com/15075759/28719144-86dc0f70-73b1-11e7-911d-60d70fcded21.png")',
      borderRadius: 2,
      minHeight: 200,
      display: 'flex',
      flexDirection: 'column',
      maxWidth: 400
    }}>
      {twilioStyleCta && (
        <Alert severity="info" sx={{ mb: 1, py: 0.25, fontSize: '0.75rem' }}>
          Preview matches <strong>Twilio</strong>: CTA URL promos are sent as plain text with a link, not a separate tap button.
          Use <strong>Meta Cloud</strong> in WhatsApp settings for native CTA URL messages.
        </Alert>
      )}
      <Paper sx={{ 
        p: 0, 
        backgroundColor: '#fff', 
        borderRadius: '8px 8px 8px 0', 
        position: 'relative',
        maxWidth: '90%',
        alignSelf: 'flex-start',
        boxShadow: '0 1px 0.5px rgba(0,0,0,0.13)',
        overflow: 'hidden'
      }}>
        {attachments && attachments.length > 0 && (
          <Stack spacing={0}>
            {attachments.map((att, idx) => {
              const url = getFullUrl(att.url)
              if (att.type === 'image') {
                return (
                  <Box key={idx} component="img" src={url} sx={{ width: '100%', maxHeight: 200, objectFit: 'cover' }} />
                )
              }
              if (att.type === 'video') {
                return (
                  <Box key={idx} component="video" src={url} sx={{ width: '100%', maxHeight: 200 }} controls />
                )
              }
              if (att.type === 'document') {
                return (
                  <Box key={idx} sx={{ p: 2, bgcolor: '#f5f5f5', display: 'flex', alignItems: 'center', gap: 1 }}>
                    <PdfIcon color="action" />
                    <Typography variant="caption">{att.name || 'Document'}</Typography>
                  </Box>
                )
              }
              return null
            })}
          </Stack>
        )}
        
        <Box sx={{ p: 1.5 }}>
            {attachments?.some(a => a.type === 'link') && (
                <Stack spacing={1} sx={{ mb: 1 }}>
                    {attachments.filter(a => a.type === 'link').map((att, idx) => (
                        <Box key={idx} sx={{ p: 1, bgcolor: '#f0f0f0', borderRadius: 1, borderLeft: '4px solid #25D366' }}>
                            <Stack direction="row" spacing={1} alignItems="center">
                                <LinkIcon fontSize="small" color="action" />
                                <Typography variant="caption" sx={{ color: '#075E54', fontWeight: 'bold' }}>{att.name || 'Link'}</Typography>
                            </Stack>
                            <Typography variant="caption" noWrap display="block" color="text.secondary">{att.url}</Typography>
                        </Box>
                    ))}
                </Stack>
            )}

            <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word', color: '#303030' }}>
            {message || 'Type a message...'}
            </Typography>
            {interactive_type === 'cta_url' && cta_footer && (
              <Typography variant="caption" sx={{ display: 'block', color: 'rgba(0, 0, 0, 0.5)', mt: 0.5 }}>
                {cta_footer}
              </Typography>
            )}
            <Typography variant="caption" sx={{ display: 'block', textAlign: 'right', color: 'rgba(0, 0, 0, 0.45)', mt: 0.5, fontSize: '0.7rem' }}>
            {new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
            </Typography>
        </Box>

        {interactive_type === 'cta_url' && metaInteractive && ctaWithUrl.length > 0 && (
            <Box sx={{ bgcolor: '#fff', borderTop: '1px solid #f0f0f0' }}>
                {ctaWithUrl.map((e, idx) => (
                    <Box key={e.id || idx}>
                        {idx > 0 && <Divider />}
                        <Button
                            fullWidth
                            endIcon={<OpenInNewIcon sx={{ fontSize: 16 }} />}
                            sx={{ py: 1, color: '#008069', textTransform: 'none', fontWeight: 500, borderRadius: 0 }}
                        >
                            {(e.display_text || '').trim() || (idx === 0 ? cta_display_text : null) || 'Open link'}
                        </Button>
                    </Box>
                ))}
                {ctaWithUrl.length > 1 && (
                    <Typography variant="caption" sx={{ display: 'block', px: 1.5, py: 0.75, bgcolor: '#f9f9f9', color: 'text.secondary' }}>
                        Preview only: Meta sends one link button per message; enable &quot;Include CTA URLs in message text&quot; to add the other links as plain text in chat.
                    </Typography>
                )}
            </Box>
        )}

        {interactive_type === 'cta_url' && metaInteractive && ctaWithUrl.length === 0 && (
            <Box sx={{ bgcolor: '#fff', borderTop: '1px solid #f0f0f0', px: 1.5, py: 1 }}>
                <Typography variant="caption" color="warning.main">
                  Add a CTA URL (or legacy CTA URL field). Without it, WhatsApp only sends plain text — no tap button.
                </Typography>
            </Box>
        )}

        {interactive_type === 'button' && buttons && buttons.length > 0 && (
            <Box sx={{ bgcolor: '#fff', borderTop: '1px solid #f0f0f0' }}>
                {buttons.map((btn, idx) => (
                    <Box key={idx}>
                        <Button fullWidth sx={{ py: 1, color: '#008069', textTransform: 'none', fontWeight: 500, borderRadius: 0 }}>
                            {btn.title}
                            {btn.url && <LinkIcon fontSize="inherit" sx={{ ml: 0.5 }} />}
                        </Button>
                        {idx < buttons.length - 1 && <Divider />}
                    </Box>
                ))}
            </Box>
        )}

        {interactive_type === 'list' && (
            <Box sx={{ bgcolor: '#fff', borderTop: '1px solid #f0f0f0' }}>
                <Button fullWidth startIcon={<ListIcon />} sx={{ py: 1, color: '#008069', textTransform: 'none', fontWeight: 500, borderRadius: 0 }}>
                    View Options
                </Button>
            </Box>
        )}

        {interactive_type === 'list' && list_sections && list_sections.some(s => s.rows.some(r => r.url)) && (
            <Box sx={{ p: 1, bgcolor: '#f0f0f0', borderTop: '1px solid #ddd' }}>
                <Typography variant="caption" color="text.secondary">Links in options:</Typography>
                {list_sections.map(s => s.rows.filter(r => r.url).map(r => (
                    <Typography key={r.id} variant="caption" display="block" color="primary" sx={{ textDecoration: 'underline' }}>
                        {r.title}: {r.url}
                    </Typography>
                )))}
            </Box>
        )}
      </Paper>
    </Box>
  )
}
