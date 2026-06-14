import { useState, useEffect, useRef, useMemo } from 'react'
import { Box, Paper, TextField, IconButton, Typography, Stack, Avatar, Chip, Alert, Divider, CircularProgress, Button } from '@mui/material'
import SendIcon from '@mui/icons-material/Send'
import SmartToyIcon from '@mui/icons-material/SmartToy'
import PersonIcon from '@mui/icons-material/Person'
import { botNextStep, listAvailableActions } from '@api/whatsapp'
import { useEffectiveTenant } from '../../hooks/useEffectiveTenant'

interface Message {
  id: string
  text: string
  sender: 'user' | 'bot'
  timestamp: Date
  node?: string
}

export default function WhatsAppBotModule() {
  const { effectiveTenant: selectedTenant } = useEffectiveTenant()
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [currentNode, setCurrentNode] = useState<string | undefined>()
  const phone = useMemo(() => {
    if (!selectedTenant) return '+919999999999'
    let h = 0
    for (let i = 0; i < selectedTenant.length; i += 1) {
      h = (h * 31 + selectedTenant.charCodeAt(i)) >>> 0
    }
    return `+9199${String(h % 100000000).padStart(8, '0')}`
  }, [selectedTenant])
  const [availableActions, setAvailableActions] = useState<any[]>([])
  const scrollRef = useRef<HTMLDivElement>(null)

  // Fetch actions for the effective tenant
  useEffect(() => {
    (async () => {
      try {
        const actions = await listAvailableActions(selectedTenant || undefined)
        setAvailableActions(actions || [])
      } catch (e) {
        console.error('Failed to load actions', e)
      }
    })()
  }, [selectedTenant])

  // Reset chat when tenant changes; do not auto-send "menu" (avoids double main menu from
  // React Strict Mode double-mount or duplicate effects — user starts with one click).
  useEffect(() => {
    if (!selectedTenant) return
    setMessages([])
    setCurrentNode(undefined)
  }, [selectedTenant])

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [messages])

  const handleSend = async (text: string, options?: { resetSession?: boolean }) => {
    const activeTenant = selectedTenant
    const userText = text || input.trim()
    if (!userText || !activeTenant || loading) return

    if (!options?.resetSession) {
      const userMsg: Message = {
        id: Math.random().toString(36).substr(2, 9),
        text: userText,
        sender: 'user',
        timestamp: new Date()
      }
      setMessages(prev => [...prev, userMsg])
      setInput('')
    }
    
    setLoading(true)

    try {
      const res = await botNextStep(activeTenant, {
        phone,
        input: userText,
        node: options?.resetSession ? undefined : currentNode,
        reset_session: options?.resetSession,
      })

      const botMsg: Message = {
        id: Math.random().toString(36).substr(2, 9),
        text: res.reply,
        sender: 'bot',
        timestamp: new Date(),
        node: res.node
      }

      setMessages(prev => [...prev, botMsg])
      setCurrentNode(res.node)
    } catch (e: any) {
      const errorMsg: Message = {
        id: Math.random().toString(36).substr(2, 9),
        text: 'Error: ' + (e?.response?.data?.detail || e.message || 'Failed to get response'),
        sender: 'bot',
        timestamp: new Date()
      }
      setMessages(prev => [...prev, errorMsg])
    } finally {
      setLoading(false)
    }
  }

  if (!selectedTenant) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert severity="info">
          Select a tenant from the left panel to test the WhatsApp bot for that tenant.
        </Alert>
      </Box>
    )
  }

  return (
    <Box sx={{ height: 'calc(100vh - 120px)', display: 'flex', flexDirection: 'column', p: 2 }}>
      <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 2 }}>
        <Typography variant="h5" sx={{ color: '#f1f5f9', fontFamily: '"DM Sans", "Inter", system-ui, sans-serif' }}>WhatsApp AI Bot Simulator</Typography>
      </Stack>

      <Alert severity="info" sx={{ mb: 2 }}>
        This module allows you to test the AI appointment workflow for <strong>{selectedTenant}</strong> without using WhatsApp.
      </Alert>

      <Paper elevation={3} sx={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden', bgcolor: '#f5f5f5' }}>
        {/* Header */}
        <Box sx={{ p: 2, bgcolor: '#075E54', color: 'white', display: 'flex', alignItems: 'center', gap: 2 }}>
          <Avatar sx={{ bgcolor: '#128C7E' }}>
            <SmartToyIcon />
          </Avatar>
          <Box>
            <Typography variant="subtitle1" sx={{ color: '#fff', fontFamily: 'inherit' }}>WhatsApp AI Bot</Typography>
            <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.9)', fontFamily: 'inherit' }}>Testing workflow for {selectedTenant}</Typography>
          </Box>
          <Box sx={{ ml: 'auto' }}>
            {currentNode && <Chip label={`Node: ${currentNode}`} size="small" sx={{ color: 'white', borderColor: 'rgba(255,255,255,0.5)' }} variant="outlined" />}
          </Box>
        </Box>

        {/* Chat Area */}
        <Box 
          ref={scrollRef}
          sx={{ 
            flex: 1, 
            p: 2, 
            overflowY: 'auto', 
            display: 'flex', 
            flexDirection: 'column', 
            gap: 2,
            backgroundImage: 'url("https://user-images.githubusercontent.com/15075759/28719144-86dc0f70-73b1-11e7-911d-60d70fcded21.png")',
            backgroundRepeat: 'repeat'
          }}
        >
          {messages.length === 0 && !loading && (
            <Box sx={{ alignSelf: 'center', maxWidth: 360, textAlign: 'center', py: 4, px: 2 }}>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                Start a conversation — open the published WhatsApp main menu once (avoids loading it twice).
              </Typography>
              <Button variant="contained" color="success" size="small" onClick={() => handleSend('menu', { resetSession: true })} disabled={loading}>
                Main menu
              </Button>
            </Box>
          )}
          {messages.map((m) => (
            <Box 
              key={m.id} 
              sx={{ 
                alignSelf: m.sender === 'user' ? 'flex-end' : 'flex-start',
                maxWidth: '80%',
                display: 'flex',
                gap: 1,
                flexDirection: m.sender === 'user' ? 'row-reverse' : 'row'
              }}
            >
              <Avatar sx={{ width: 32, height: 32, bgcolor: m.sender === 'user' ? 'primary.main' : 'secondary.main' }}>
                {m.sender === 'user' ? <PersonIcon fontSize="small" /> : <SmartToyIcon fontSize="small" />}
              </Avatar>
              <Paper 
                sx={{ 
                  p: 1.5, 
                  borderRadius: 2, 
                  bgcolor: m.sender === 'user' ? '#DCF8C6' : 'white',
                  position: 'relative'
                }}
              >
                <Typography variant="body1" sx={{ whiteSpace: 'pre-wrap', color: '#1e293b', fontFamily: 'inherit' }}>{m.text}</Typography>
                <Typography variant="caption" sx={{ display: 'block', textAlign: 'right', mt: 0.5, opacity: 0.6, fontSize: '0.7rem', color: '#64748b', fontFamily: 'inherit' }}>
                  {m.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                </Typography>
              </Paper>
            </Box>
          ))}
          {loading && (
            <Box sx={{ alignSelf: 'flex-start', ml: 5 }}>
              <CircularProgress size={20} />
            </Box>
          )}
        </Box>

        <Divider />

        {/* Input Area */}
        <Box sx={{ p: 2, bgcolor: 'white', display: 'flex', gap: 1 }}>
          <TextField
            fullWidth
            size="small"
            placeholder="Type your message..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && handleSend('')}
            disabled={loading}
          />
          <IconButton color="primary" onClick={() => handleSend('')} disabled={!input.trim() || loading}>
            <SendIcon />
          </IconButton>
        </Box>
      </Paper>
      
      <Box sx={{ mt: 2, display: 'flex', gap: 1, flexWrap: 'wrap' }}>
        <Typography variant="caption" sx={{ width: '100%', mb: 0.5, color: '#94a3b8', fontFamily: 'inherit' }}>Quick actions:</Typography>
        <Chip label="Menu" size="small" onClick={() => handleSend('menu', { resetSession: true })} clickable disabled={loading} />
        {availableActions.filter(a => a.id.startsWith('salon.') || a.id.startsWith('clinic.') || a.id.startsWith('workflow.')).map(action => (
            <Chip 
                key={action.id} 
                label={action.label} 
                size="small" 
                color="primary" 
                variant="outlined"
                onClick={() => handleSend(action.id)} 
                clickable 
                disabled={loading} 
            />
        ))}
        <Chip label="Cancel" size="small" onClick={() => handleSend('cancel')} clickable disabled={loading} />
      </Box>
    </Box>
  )
}
