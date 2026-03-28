import { useState, useEffect } from 'react'
import { Box, Card, CardContent, Grid, Stack, TextField, Typography, Button, MenuItem, Paper, Avatar, Divider, CircularProgress } from '@mui/material'
import { Send as SendIcon, SmartToy as BotIcon, Person as PersonIcon } from '@mui/icons-material'
import { listPromotions, Promotion } from '@api/promotions'
import { getWhatsAppConfig } from '@api/tenants'
import { promotionMessageWithLinks, promotionCtaEntriesForPreview } from './messagePreviewUtils'
import { resolveUploadUrl } from '@api/config'
import { useEffectiveTenant } from '../../hooks/useEffectiveTenant'
import WhatsAppPreview from '../../components/WhatsAppPreview'

export default function PromotionSimulator() {
  const { effectiveTenant } = useEffectiveTenant()
  const tenant = effectiveTenant
  const [promotions, setPromotions] = useState<Promotion[]>([])
  const [selectedId, setSelectedId] = useState<string>('')
  const [loading, setLoading] = useState(false)
  const [chat, setChat] = useState<{ role: 'bot' | 'user', content: string, promotion?: Promotion }[]>([])
  const [waProvider, setWaProvider] = useState<string>('twilio')

  useEffect(() => {
    if (tenant) {
      loadPromotions()
      getWhatsAppConfig(tenant)
        .then(c => setWaProvider(String(c?.provider || 'twilio')))
        .catch(() => setWaProvider('twilio'))
    }
  }, [tenant])

  async function loadPromotions() {
    try {
      const list = await listPromotions(tenant)
      setPromotions(list)
      if (list.length > 0) {
          setSelectedId(list[0].id)
      }
    } catch (err) {
      console.error('Failed to load promotions', err)
    }
  }

  const getFullUrl = (url: string) => resolveUploadUrl(url)

  function simulateReceive() {
    const promo = promotions.find(p => p.id === selectedId)
    if (!promo) return

    setChat(prev => [...prev, { 
        role: 'bot', 
        content: promo.message,
        promotion: promo
    }])
  }

  return (
    <Box sx={{ p: 2, height: 'calc(100vh - 100px)', display: 'flex', flexDirection: 'column' }}>
      <Typography variant="h5" sx={{ mb: 2, color: '#f1f5f9', fontFamily: '"DM Sans", "Inter", system-ui, sans-serif' }}>WhatsApp Promotion Simulator</Typography>
      
      <Grid container spacing={2} sx={{ flex: 1, minHeight: 0 }}>
        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Typography variant="subtitle2" gutterBottom sx={{ color: '#94a3b8', fontFamily: 'inherit' }}>Test Configuration</Typography>
              <Stack spacing={2}>
                <TextField 
                    select 
                    fullWidth 
                    label="Select Promotion" 
                    value={selectedId} 
                    onChange={e => setSelectedId(e.target.value)}
                    size="small"
                >
                  {promotions.map(p => (
                    <MenuItem key={p.id} value={p.id}>{p.name} ({p.status})</MenuItem>
                  ))}
                  {promotions.length === 0 && <MenuItem disabled>No promotions found</MenuItem>}
                </TextField>
                
                <Button 
                    variant="contained" 
                    startIcon={<SendIcon />} 
                    onClick={simulateReceive}
                    disabled={!selectedId}
                >
                  Simulate Receive
                </Button>
                
                <Divider />
                
                <Typography variant="caption" sx={{ color: '#94a3b8', fontFamily: 'inherit' }}>
                    Preview follows your tenant WhatsApp provider (Twilio vs Meta Cloud). Twilio sends CTA URL promos as text + link; Meta Cloud can send a native tap button.
                </Typography>
              </Stack>
            </CardContent>
          </Card>
        </Grid>
        
        <Grid item xs={12} md={8} sx={{ height: '100%' }}>
          <Box sx={{ 
            height: '100%', 
            display: 'flex', 
            flexDirection: 'column',
            bgcolor: '#e5ddd5',
            backgroundImage: 'url("https://user-images.githubusercontent.com/15075759/28719144-86dc0f70-73b1-11e7-911d-60d70fcded21.png")',
            borderRadius: 2,
            border: '1px solid #ccc',
            overflow: 'hidden'
          }}>
            {/* Header */}
            <Box sx={{ bgcolor: '#075e54', p: 1, color: '#fff', display: 'flex', alignItems: 'center', gap: 1 }}>
                <Avatar sx={{ bgcolor: '#128c7e' }}><BotIcon /></Avatar>
                <Box>
                    <Typography variant="subtitle1" sx={{ lineHeight: 1.2, color: '#fff', fontFamily: 'inherit' }}>WhatsApp Simulator</Typography>
                    <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.9)', fontFamily: 'inherit' }}>Online</Typography>
                </Box>
            </Box>

            {/* Chat Area */}
            <Box sx={{ flex: 1, p: 2, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 2 }}>
                {chat.length === 0 && (
                    <Box sx={{ alignSelf: 'center', bgcolor: 'rgba(255,255,255,0.7)', p: 1, borderRadius: 1, mt: 4 }}>
                        <Typography variant="caption" sx={{ color: '#1e293b', fontFamily: 'inherit' }}>Select a promotion and click 'Simulate Receive'</Typography>
                    </Box>
                )}
                {chat.map((msg, i) => (
                    <Box key={i} sx={{ 
                        alignSelf: msg.role === 'bot' ? 'flex-start' : 'flex-end',
                        maxWidth: '85%'
                    }}>
                        {msg.promotion ? (
                            <WhatsAppPreview 
                                message={promotionMessageWithLinks(msg.promotion)}
                                attachments={msg.promotion.attachments}
                                getFullUrl={getFullUrl}
                                interactive_type={msg.promotion.interactive_type}
                                buttons={msg.promotion.buttons}
                                list_sections={msg.promotion.list_sections}
                                cta_entries={
                                  msg.promotion.interactive_type === 'cta_url'
                                    ? promotionCtaEntriesForPreview(msg.promotion)
                                    : undefined
                                }
                                cta_display_text={
                                  msg.promotion.interactive_type === 'cta_url'
                                    ? (msg.promotion.cta_entries?.find(e => (e.url || '').trim())?.display_text ||
                                        msg.promotion.cta_display_text ||
                                        'Shop Now')
                                    : undefined
                                }
                                cta_footer={msg.promotion.interactive_type === 'cta_url' ? (msg.promotion.cta_footer || undefined) : undefined}
                                whatsappProvider={waProvider}
                            />
                        ) : (
                            <Paper sx={{ 
                                p: 1, 
                                bgcolor: msg.role === 'bot' ? '#fff' : '#dcf8c6',
                                borderRadius: msg.role === 'bot' ? '0 8px 8px 8px' : '8px 0 8px 8px',
                                position: 'relative'
                            }}>
                                <Typography variant="body2" sx={{ color: '#1e293b', fontFamily: 'inherit' }}>{msg.content}</Typography>
                            </Paper>
                        )}
                    </Box>
                ))}
            </Box>

            {/* Input Area (Static) */}
            <Box sx={{ p: 1, bgcolor: '#f0f0f0', display: 'flex', gap: 1 }}>
                <TextField 
                    fullWidth 
                    size="small" 
                    placeholder="Type a message..." 
                    disabled
                    sx={{ bgcolor: '#fff', borderRadius: 1 }}
                />
                <Button variant="contained" disabled sx={{ minWidth: 0, p: 1, borderRadius: '50%' }}>
                    <SendIcon />
                </Button>
            </Box>
          </Box>
        </Grid>
      </Grid>
    </Box>
  )
}
