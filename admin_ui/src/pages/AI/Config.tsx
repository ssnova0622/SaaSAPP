import { useEffect, useState } from 'react'
import {
  Box,
  Button,
  Card,
  CardContent,
  TextField,
  Typography,
  Alert,
  Stack,
  Divider,
  FormControlLabel,
  Switch,
  InputAdornment,
} from '@mui/material'
import { getTenantSettings, TenantSettings } from '@api/tenants'
import { getAiConfig, putAiConfig, type AIConfig } from '@api/ai'
import { useEffectiveTenant } from '../../hooks/useEffectiveTenant'

export default function AIConfigPage() {
  const { effectiveTenant: tenant } = useEffectiveTenant()
  const [settings, setSettings] = useState<TenantSettings | null>(null)
  const [config, setConfig] = useState<AIConfig | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)

  const modules = (settings?.modules || []).map((m) => String(m).toLowerCase())
  const hasSalon = modules.includes('salon') || modules.includes('clinic')
  const hasStore = modules.includes('store')

  useEffect(() => {
    if (!tenant) {
      setLoading(false)
      setConfig(null)
      setSettings(null)
      return
    }
    setLoading(true)
    setError(null)
    getTenantSettings(tenant)
      .then((s) => {
        setSettings(s)
        const hasAI = (s.modules || []).map((m: string) => String(m).toLowerCase()).includes('ai')
        if (!hasAI) {
          setConfig({})
          return
        }
        return getAiConfig(tenant).then((r) => r.ai_config)
      })
      .then((cfg) => {
        if (cfg !== undefined) setConfig(typeof cfg === 'object' && cfg !== null ? cfg : {})
      })
      .catch((e: any) => setError(e?.response?.data?.detail || 'Failed to load'))
      .finally(() => setLoading(false))
  }, [tenant])

  const update = (key: keyof AIConfig, value: number | boolean | string | undefined) => {
    setConfig((prev) => (prev ? { ...prev, [key]: value } : prev))
  }

  async function onSave() {
    if (!tenant || !config) return
    setSaving(true)
    setError(null)
    setSuccess(null)
    try {
      await putAiConfig(tenant, config)
      setSuccess('AI config saved.')
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Failed to save')
    } finally {
      setSaving(false)
    }
  }

  if (loading || !tenant) {
    return (
      <Box sx={{ p: 2 }}>
        <Typography variant="h5" sx={{ mb: 2 }}>AI Config</Typography>
        {!tenant && <Alert severity="info">Select a tenant.</Alert>}
        {tenant && loading && <Typography color="text.secondary">Loading...</Typography>}
      </Box>
    )
  }

  const c = config || {}

  return (
    <Box sx={{ p: 2 }}>
      <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 2 }}>
        <Typography variant="h5">AI Config</Typography>
        <Button variant="contained" disabled={saving || !config} onClick={onSave}>
          {saving ? 'Saving...' : 'Save'}
        </Button>
      </Stack>
      {error && <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>{error}</Alert>}
      {success && <Alert severity="success" sx={{ mb: 2 }} onClose={() => setSuccess(null)}>{success}</Alert>}

      {!settings?.modules?.includes('ai') && (
        <Alert severity="warning" sx={{ mb: 2 }}>
          AI module is not enabled for this tenant. Enable it in Settings → Modules to use AI features and thresholds.
        </Alert>
      )}

      {hasSalon && (
        <Card sx={{ mb: 2 }}>
          <CardContent>
            <Typography variant="h6" sx={{ mb: 2 }}>No-Show (Salon / Clinic)</Typography>
            <Stack spacing={2}>
              <TextField
                type="number"
                label="No-show block threshold"
                value={c.no_show_block_threshold ?? 3}
                onChange={(e) => update('no_show_block_threshold', e.target.value === '' ? undefined : parseInt(e.target.value, 10))}
                helperText="Block booking when customer no-show count ≥ this (0 = disabled)"
                inputProps={{ min: 0, max: 20 }}
                InputProps={{ endAdornment: <InputAdornment position="end">no-shows</InputAdornment> }}
                fullWidth
              />
              <TextField
                type="number"
                label="No-show reminder threshold"
                value={c.no_show_reminder_threshold ?? 0.5}
                onChange={(e) => update('no_show_reminder_threshold', e.target.value === '' ? undefined : parseFloat(e.target.value))}
                helperText="Suggest reminder when risk score ≥ this (0–1)"
                inputProps={{ min: 0, max: 1, step: 0.1 }}
                fullWidth
              />
              <TextField
                type="number"
                label="No-show high-risk threshold"
                value={c.no_show_high_risk_threshold ?? 0.7}
                onChange={(e) => update('no_show_high_risk_threshold', e.target.value === '' ? undefined : parseFloat(e.target.value))}
                helperText="Mark as high risk when score ≥ this (0–1)"
                inputProps={{ min: 0, max: 1, step: 0.1 }}
                fullWidth
              />
              <TextField
                type="number"
                label="No-show reminder lead (hours)"
                value={c.no_show_reminder_lead_hours ?? 24}
                onChange={(e) => update('no_show_reminder_lead_hours', e.target.value === '' ? undefined : parseInt(e.target.value, 10))}
                helperText="Suggest reminder this many hours before appointment"
                inputProps={{ min: 1, max: 168 }}
                InputProps={{ endAdornment: <InputAdornment position="end">hours</InputAdornment> }}
                fullWidth
              />
            </Stack>
          </CardContent>
        </Card>
      )}

      {hasStore && (
        <Card sx={{ mb: 2 }}>
          <CardContent>
            <Typography variant="h6" sx={{ mb: 2 }}>Store: Low-stock &amp; Cart recovery</Typography>
            <Stack spacing={2}>
              <TextField
                type="number"
                label="Low-stock default days"
                value={c.low_stock_days_default ?? 30}
                onChange={(e) => update('low_stock_days_default', e.target.value === '' ? undefined : parseInt(e.target.value, 10))}
                inputProps={{ min: 7, max: 120 }}
                fullWidth
              />
              <TextField
                type="number"
                label="Low-stock lead time (days)"
                value={c.low_stock_lead_time_days ?? 3}
                onChange={(e) => update('low_stock_lead_time_days', e.target.value === '' ? undefined : parseInt(e.target.value, 10))}
                inputProps={{ min: 0, max: 30 }}
                fullWidth
              />
              <TextField
                type="number"
                label="Low-stock safety days"
                value={c.low_stock_safety_days ?? 2}
                onChange={(e) => update('low_stock_safety_days', e.target.value === '' ? undefined : parseInt(e.target.value, 10))}
                inputProps={{ min: 0, max: 30 }}
                fullWidth
              />
              <TextField
                type="number"
                label="Low-stock alert when days to stockout &lt;"
                value={c.low_stock_alert_days ?? 7}
                onChange={(e) => update('low_stock_alert_days', e.target.value === '' ? undefined : parseInt(e.target.value, 10))}
                helperText="Alert when days_to_stockout is below this"
                inputProps={{ min: 1, max: 30 }}
                fullWidth
              />
              <Divider />
              <TextField
                type="number"
                label="Cart recovery window (hours)"
                value={c.cart_recovery_window_hours ?? 24}
                onChange={(e) => update('cart_recovery_window_hours', e.target.value === '' ? undefined : parseInt(e.target.value, 10))}
                inputProps={{ min: 1, max: 168 }}
                fullWidth
              />
              <TextField
                type="number"
                label="Cart recovery max messages per cart"
                value={c.cart_recovery_max_messages_per_cart ?? 2}
                onChange={(e) => update('cart_recovery_max_messages_per_cart', e.target.value === '' ? undefined : parseInt(e.target.value, 10))}
                inputProps={{ min: 1, max: 10 }}
                fullWidth
              />
            </Stack>
          </CardContent>
        </Card>
      )}

      {(hasSalon || hasStore) && (
        <Card sx={{ mb: 2 }}>
          <CardContent>
            <Typography variant="h6" sx={{ mb: 2 }}>Dynamic pricing (Store / Salon)</Typography>
            <Stack spacing={2}>
              <TextField
                type="number"
                label="Min price multiplier"
                value={c.dynamic_pricing_min_multiplier ?? 0.8}
                onChange={(e) => update('dynamic_pricing_min_multiplier', e.target.value === '' ? undefined : parseFloat(e.target.value))}
                inputProps={{ min: 0.5, max: 1, step: 0.1 }}
                fullWidth
              />
              <TextField
                type="number"
                label="Max price multiplier"
                value={c.dynamic_pricing_max_multiplier ?? 1.2}
                onChange={(e) => update('dynamic_pricing_max_multiplier', e.target.value === '' ? undefined : parseFloat(e.target.value))}
                inputProps={{ min: 1, max: 2, step: 0.1 }}
                fullWidth
              />
              <TextField
                type="number"
                label="Max discount %"
                value={c.dynamic_pricing_max_discount_pct ?? 20}
                onChange={(e) => update('dynamic_pricing_max_discount_pct', e.target.value === '' ? undefined : parseFloat(e.target.value))}
                InputProps={{ endAdornment: <InputAdornment position="end">%</InputAdornment> }}
                inputProps={{ min: 0, max: 100 }}
                fullWidth
              />
            </Stack>
          </CardContent>
        </Card>
      )}

      {!hasSalon && !hasStore && config && (
        <Alert severity="info">Enable Salon/Clinic or Store module for this tenant to see related thresholds.</Alert>
      )}
    </Box>
  )
}
