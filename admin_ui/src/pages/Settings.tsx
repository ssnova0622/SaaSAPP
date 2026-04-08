import { Box, Button, Card, CardContent, Grid, MenuItem, TextField, Typography, Stack, Switch, FormControlLabel, Checkbox, FormGroup, Tooltip, Alert, Tabs, Tab, Divider } from '@mui/material'
import { useEffect, useRef, useState } from 'react'
import { getTenantSettings, updateTenantSettings, TenantSettings, listPlans, getWhatsAppConfig, putWhatsAppConfig, WhatsAppConfig, clearTenantSettingsCache, type PlanInfo, type MessagingChannels } from '@api/tenants'
import { listCountries, type CountryOption } from '@api/meta'
import { listRegistry, RegistryItem } from '@api/modules'
import { listUsers, setPassword, type User } from '@api/users'
import { api } from '@api/axios'
import { getApiBaseURL } from '@api/config'
import { getLoginOtpEnabled, setLoginOtpEnabled as setLoginOtpEnabledApi } from '@api/auth'
import TimezoneSelect from '@components/TimezoneSelect'
import { useEffectiveTenant } from '../hooks/useEffectiveTenant'

export default function Settings() {
  const { effectiveTenant: tenantFromHook, isSuper } = useEffectiveTenant()
  const tenant = tenantFromHook || ''
  const [settings, setSettings] = useState<TenantSettings | null>(null)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [ok, setOk] = useState<string | null>(null)
  const [registry, setRegistry] = useState<RegistryItem[]>([])
  const [isSuperAdmin, setIsSuperAdmin] = useState<boolean>(false)
  const [me, setMe] = useState<{ id?: string|null, role?: string|null } | null>(null)
  const [pwd1, setPwd1] = useState('')
  const [pwd2, setPwd2] = useState('')
  const [pwdMsg, setPwdMsg] = useState<string|null>(null)
  // WhatsApp config state
  const [waCfg, setWaCfg] = useState<WhatsAppConfig | null>(null)
  const [waMsg, setWaMsg] = useState<string | null>(null)
  // Plans (for Plan & Access and Apply plan defaults)
  const [plans, setPlans] = useState<PlanInfo[]>([])
  const [channelsMsg, setChannelsMsg] = useState<string | null>(null)
  const [followupPrefsMsg, setFollowupPrefsMsg] = useState<string | null>(null)
  const [settingsTab, setSettingsTab] = useState(0)
  const [planAccessSubTab, setPlanAccessSubTab] = useState(0) // 0=Modules, 1=Core, 2=Salon, 3=Store, 4=AI
  const [planSaveMsg, setPlanSaveMsg] = useState<{ ok?: string; error?: string } | null>(null)
  const [modulesSaveMsg, setModulesSaveMsg] = useState<{ ok?: string; error?: string } | null>(null)
  const [capabilitiesSaveMsg, setCapabilitiesSaveMsg] = useState<{ ok?: string; error?: string } | null>(null)
  const [savingPlan, setSavingPlan] = useState(false)
  const [savingModules, setSavingModules] = useState(false)
  const [savingCapabilities, setSavingCapabilities] = useState(false)
  const [savedPlan, setSavedPlan] = useState<string>('basic') // last saved plan so we can revert dropdown when leaving tab
  const prevSettingsTabRef = useRef(0)
  // Super admin: change tenant admin password only (no user dropdown)
  const [tenantAdminUser, setTenantAdminUser] = useState<User | null>(null)
  const [pwdForUserNew, setPwdForUserNew] = useState('')
  const [pwdForUserConfirm, setPwdForUserConfirm] = useState('')
  const [pwdForUserMsg, setPwdForUserMsg] = useState<string | null>(null)
  const [loginOtpEnabled, setLoginOtpEnabled] = useState<boolean>(false)
  const [loginOtpSaving, setLoginOtpSaving] = useState(false)
  const [waTestFrom, setWaTestFrom] = useState('+911112223334')
  const [waTestTo, setWaTestTo] = useState('')
  const [waTestBody, setWaTestBody] = useState('1')
  const [waTestResp, setWaTestResp] = useState('')
  const [addressLocationMsg, setAddressLocationMsg] = useState<string | null>(null)
  const [countries, setCountries] = useState<CountryOption[]>([])
  const [ownerPhoneCode, setOwnerPhoneCode] = useState('+91')
  const [ownerPhoneMobile, setOwnerPhoneMobile] = useState('')

  useEffect(() => {
    listCountries().then(r => setCountries(r.items || [])).catch(() => setCountries([]))
  }, [])

  useEffect(() => {
    if (!settings || !countries.length) return
    const tc = (settings.tenant_country || 'IN').toUpperCase()
    const row = countries.find(c => c.iso2 === tc)
    const defDial = row?.dial || '91'
    const opn = (settings as TenantSettings & { owner_phone_number?: { code?: string; number?: string; mobile_number?: string } }).owner_phone_number
    const ownerNational = opn?.number ?? opn?.mobile_number
    if (ownerNational != null && String(ownerNational).length > 0) {
      const c = (opn?.code || `+${defDial}`).trim()
      setOwnerPhoneCode(c.startsWith('+') ? c : `+${c.replace(/\D/g, '')}`)
      setOwnerPhoneMobile(String(ownerNational).replace(/\D/g, ''))
    } else if (settings.owner_phone) {
      const digits = String(settings.owner_phone).replace(/\D/g, '')
      const dialDigits = defDial
      if (digits.startsWith(dialDigits) && digits.length > dialDigits.length) {
        setOwnerPhoneCode(`+${dialDigits}`)
        setOwnerPhoneMobile(digits.slice(dialDigits.length))
      } else {
        setOwnerPhoneCode(`+${defDial}`)
        setOwnerPhoneMobile(digits.startsWith(dialDigits) ? digits.slice(dialDigits.length) : digits.replace(/^0+/, ''))
      }
    } else {
      setOwnerPhoneCode(`+${defDial}`)
      setOwnerPhoneMobile('')
    }
  }, [settings, countries])

  useEffect(() => {
    if (!tenant) return
    ;(async () => {
      setError(null); setOk(null); setPlanSaveMsg(null); setModulesSaveMsg(null); setCapabilitiesSaveMsg(null)
      try {
        const s = await getTenantSettings(tenant)
        // Normalize modules/capabilities defensively to arrays of lowercase strings
        const normMods = Array.isArray((s as any).modules) ? (s as any).modules.map((m:any)=>String(m).toLowerCase()) : []
        const normCaps = Array.isArray((s as any).capabilities) ? (s as any).capabilities.map((c:any)=>String(c).toLowerCase()) : []
        setSettings({
          ...s,
          modules: normMods,
          capabilities: normCaps,
          tenant_country: (s as TenantSettings).tenant_country || 'IN',
        })
        setSavedPlan((s as any).plan || 'basic')
        // Try loading WhatsApp config (ignore if capability not enabled or forbidden)
        try {
          const cfg = await getWhatsAppConfig(tenant)
          // Normalize from_numbers to array of strings
          const list = Array.isArray(cfg?.from_numbers) ? cfg.from_numbers.map((n:any)=>String(n)) : []
          setWaCfg({
            provider: (cfg.provider||'twilio') as any,
            from_numbers: list,
            webhook_secret: cfg.webhook_secret||'',
            account_sid: cfg.account_sid||'',
            auth_token: cfg.auth_token||'',
            locale_default: cfg.locale_default||'en',
            phone_number_id: cfg.phone_number_id||'',
            access_token: cfg.access_token||'',
            active_menu_id: cfg.active_menu_id||'',
          })
          setWaTestTo(list[0] || '')
        } catch {
          setWaCfg({ provider: 'twilio', from_numbers: [], webhook_secret: 'dev', account_sid: '', auth_token: '', locale_default: 'en', phone_number_id: '', access_token: '', active_menu_id: '' })
        }
      } catch (e: any) {
        setError(e?.response?.data?.detail || 'Failed to load settings')
      }
    })()
  }, [tenant])

  // Fetch modules registry (Super Admin only API; if forbidden, treat as non-super)
  useEffect(() => {
    (async () => {
      try {
        const items = await listRegistry().then(r => r.items)
        setRegistry(items)
      } catch {
        setRegistry([])
      }
    })()
  }, [])

  useEffect(() => {
    listPlans().then(setPlans).catch(() => setPlans([]))
  }, [])

  useEffect(() => {
    // Reflect hook role
    setIsSuperAdmin(!!isSuper)
  }, [isSuper])

  useEffect(() => {
    if (!isSuperAdmin) return
    getLoginOtpEnabled().then(r => setLoginOtpEnabled(r.login_otp_enabled)).catch(() => {})
  }, [isSuperAdmin])

  // Load current user info for password change functionality
  useEffect(() => {
    (async () => {
      try {
        const res = await api.get('/auth/me')
        setMe({ id: res.data?.id || null, role: res.data?.role || null })
      } catch {
        setMe(null)
      }
    })()
  }, [])

  // Load tenant admin for selected tenant (super admin password tab: change tenant admin password only)
  useEffect(() => {
    if (!isSuperAdmin || !tenant) {
      setTenantAdminUser(null)
      return
    }
    listUsers({ tenant, role: 'tenant_admin', page: 1, size: 10 })
      .then(r => {
        const admin = (r.items || []).find(u => (u.role || '').toLowerCase() === 'tenant_admin') || (r.items || [])[0] || null
        setTenantAdminUser(admin || null)
      })
      .catch(() => setTenantAdminUser(null))
  }, [isSuperAdmin, tenant])

  // When leaving Plan & Access tab, revert plan dropdown to last saved value (discard unsaved selection)
  useEffect(() => {
    if (prevSettingsTabRef.current === 1 && settingsTab !== 1) {
      setSettings(prev => prev ? { ...prev, plan: savedPlan } : prev)
    }
    prevSettingsTabRef.current = settingsTab
  }, [settingsTab, savedPlan])


  async function onChangeTenantUserPassword() {
    setPwdForUserMsg(null)
    const userId = tenantAdminUser?.id
    if (!userId || !pwdForUserNew || pwdForUserNew.length < 8) {
      setPwdForUserMsg(tenantAdminUser ? 'Enter a password (min 8 characters)' : 'No tenant admin found for this tenant.')
      return
    }
    if (pwdForUserNew !== pwdForUserConfirm) {
      setPwdForUserMsg('Passwords do not match')
      return
    }
    try {
      await setPassword(userId, pwdForUserNew)
      setPwdForUserMsg('Password updated')
      setPwdForUserNew('')
      setPwdForUserConfirm('')
    } catch (e: any) {
      const d = e?.response?.data?.detail
      setPwdForUserMsg(typeof d === 'string' ? d : 'Failed to update password')
    }
  }

  async function onSave() {
    if (!tenant || !settings) return
    setSaving(true); setError(null); setOk(null)
    try {
      const mobDigits = ownerPhoneMobile.replace(/\D/g, '')
      let ownerPhoneNumber: { code: string; number: string } | null = null
      if (mobDigits.length > 0) {
        const c = ownerPhoneCode.trim()
        const cc = c.startsWith('+') ? c : `+${c.replace(/\D/g, '')}`
        ownerPhoneNumber = { code: cc, number: mobDigits }
      }
      const payload = {
        owner_email: settings.owner_email || '',
        tenant_country: (settings.tenant_country || 'IN').toUpperCase(),
        tz: settings.tz || 'Asia/Kolkata',
        date_format: settings.date_format || 'DD-MM-YYYY',
        currency: (settings.currency || 'INR').toUpperCase(),
        invoice_delivery: settings.invoice_delivery || 'both',
        ...(ownerPhoneNumber
          ? { owner_phone_number: ownerPhoneNumber }
          : { owner_phone_number: null, owner_phone: null }),
      } as Partial<TenantSettings>
      if (isSuperAdmin) payload.display_name = settings.display_name || ''
      clearTenantSettingsCache()
      const s = await updateTenantSettings(tenant, payload)
      setSettings({ ...s, date_format: s?.date_format ?? payload.date_format })
      try { window.dispatchEvent(new CustomEvent('tenantSettingsChanged', { detail: { tenant } })) } catch { /* ignore */ }
      setOk('Saved')
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Save failed')
    } finally {
      setSaving(false)
    }
  }

  async function onSavePayments() {
    if (!tenant || !settings) return
    setSaving(true); setError(null); setOk(null)
    try {
      const s = await updateTenantSettings(tenant, {
        store_enabled: settings.store_enabled ?? true,
        payment_config: settings.payment_config,
      })
      setSettings(s)
      setOk('Payments saved')
    } catch (e:any) {
      setError(e?.response?.data?.detail || 'Save failed')
    } finally { setSaving(false) }
  }

  async function onSaveFulfillment() {
    if (!tenant || !settings) return
    setSaving(true); setError(null); setOk(null)
    try {
      const s = await updateTenantSettings(tenant, {
        delivery_config: settings.delivery_config,
      })
      setSettings(s)
      setOk('Fulfillment saved')
    } catch (e:any) {
      setError(e?.response?.data?.detail || 'Save failed')
    } finally { setSaving(false) }
  }

  async function onChangePassword() {
    setPwdMsg(null)
    if (!me?.id) { setPwdMsg('Cannot load current user'); return }
    if (!pwd1 || pwd1.length < 8) { setPwdMsg('Password must be at least 8 characters'); return }
    if (pwd1 !== pwd2) { setPwdMsg('Passwords do not match'); return }
    try {
      await api.patch(`/users/${encodeURIComponent(me.id)}/password`, { password: pwd1 })
      setPwdMsg('Password updated')
      setPwd1(''); setPwd2('')
    } catch (e:any) {
      const d = e?.response?.data?.detail
      let msg = 'Failed to change password'
      if (typeof d === 'string') msg = d
      else if (Array.isArray(d) && d.length) msg = d[0]?.msg || JSON.stringify(d[0])
      else if (d && typeof d === 'object') msg = d.msg || JSON.stringify(d)
      else if (e?.message) msg = e.message
      setPwdMsg(msg)
    }
  }

  /** Save only modules (no plan, no capabilities). Super Admin only. */
  async function onSaveModulesOnly() {
    if (!tenant || !settings || !isSuperAdmin) return
    setSavingModules(true); setPlanSaveMsg(null); setModulesSaveMsg(null); setCapabilitiesSaveMsg(null)
    try {
      const s = await updateTenantSettings(tenant, { modules: settings.modules || [] })
      setSettings(prev => prev ? { ...prev, ...s } : prev)
      try { clearTenantSettingsCache() } catch { /* ignore */ }
      try { window.dispatchEvent(new CustomEvent('tenantSettingsChanged', { detail: { tenant } })) } catch { /* ignore */ }
      setModulesSaveMsg({ ok: 'Modules saved' })
    } catch (e: any) {
      setModulesSaveMsg({ error: e?.response?.data?.detail || 'Save failed' })
    } finally { setSavingModules(false) }
  }

  /** Save only capabilities (no plan, no modules). Super Admin only. */
  async function onSaveCapabilitiesOnly() {
    if (!tenant || !settings || !isSuperAdmin) return
    setSavingCapabilities(true); setPlanSaveMsg(null); setModulesSaveMsg(null); setCapabilitiesSaveMsg(null)
    try {
      const s = await updateTenantSettings(tenant, { capabilities: settings.capabilities || [] })
      setSettings(prev => prev ? { ...prev, ...s } : prev)
      try { clearTenantSettingsCache() } catch { /* ignore */ }
      try { window.dispatchEvent(new CustomEvent('tenantSettingsChanged', { detail: { tenant } })) } catch { /* ignore */ }
      setCapabilitiesSaveMsg({ ok: 'Capabilities saved' })
    } catch (e: any) {
      setCapabilitiesSaveMsg({ error: e?.response?.data?.detail || 'Save failed' })
    } finally { setSavingCapabilities(false) }
  }

  /** Save only plan (no modules/capabilities). Super Admin only. Updates UI with saved plan. */
  async function onSavePlanOnly() {
    if (!tenant || !settings || !isSuperAdmin) return
    setSavingPlan(true); setPlanSaveMsg(null); setModulesSaveMsg(null); setCapabilitiesSaveMsg(null)
    try {
      const planValue = settings.plan || 'basic'
      const s = await updateTenantSettings(tenant, { plan: planValue })
      setSettings(prev => prev ? { ...prev, ...s, plan: (s as any).plan ?? planValue } : prev)
      try { clearTenantSettingsCache() } catch { /* ignore */ }
      try { window.dispatchEvent(new CustomEvent('tenantSettingsChanged', { detail: { tenant } })) } catch { /* ignore */ }
      setPlanSaveMsg({ ok: 'Plan saved' })
      setSavedPlan(planValue)
    } catch (e: any) {
      setPlanSaveMsg({ error: e?.response?.data?.detail || 'Save failed' })
    } finally { setSavingPlan(false) }
  }

  async function onSaveFollowupPrefs() {
    if (!tenant || !settings) return
    setFollowupPrefsMsg(null)
    setSaving(true)
    try {
      const prefs = (settings as any).followup_prefs || {}
      const payload = {
        confirm: prefs.confirm !== false,
        reminder24: prefs.reminder24 !== false,
        reminder2: prefs.reminder2 !== false,
        post: prefs.post !== false,
      }
      await updateTenantSettings(tenant, { followup_prefs: payload })
      setSettings(prev => prev ? { ...prev, followup_prefs: payload } : prev)
      setFollowupPrefsMsg('Follow-up events saved')
    } catch (e: any) {
      const d = e?.response?.data?.detail
      setFollowupPrefsMsg(typeof d === 'string' ? d : 'Failed to save')
    } finally {
      setSaving(false)
    }
  }

  async function onSaveChannels() {
    if (!tenant || !settings) return
    setChannelsMsg(null)
    setSaving(true)
    try {
      const ch: MessagingChannels = {
        email: settings.messaging_channels?.email ?? true,
        whatsapp: settings.messaging_channels?.whatsapp ?? true,
        sms: settings.messaging_channels?.sms ?? false,
      }
      const s = await updateTenantSettings(tenant, {
        messaging_channels: ch,
        sms_config: settings.sms_config || { enabled: ch.sms, provider: 'twilio', from_number: '', account_sid: '', auth_token: '' },
      })
      setSettings(s)
      setChannelsMsg('Notification channels saved')
    } catch (e: any) {
      const d = e?.response?.data?.detail
      setChannelsMsg(typeof d === 'string' ? d : 'Failed to save channels')
    } finally {
      setSaving(false)
    }
  }

  async function onTestWhatsAppWebhook() {
    setWaTestResp('')
    try {
      const res = await api.post('/integrations/twilio/whatsapp/webhook', { From: waTestFrom, To: waTestTo, Body: waTestBody }, { responseType: 'text' })
      setWaTestResp(String(res.data || ''))
    } catch (e: any) {
      setWaTestResp(String(e?.response?.data || e?.message || 'Request failed'))
    }
  }

  async function onSaveWhatsApp() {
    if (!tenant || !waCfg) return
    setWaMsg(null)
    try {
      const payload: WhatsAppConfig = {
        provider: (waCfg.provider || 'twilio') as any,
        from_numbers: Array.isArray(waCfg.from_numbers) ? waCfg.from_numbers.filter(Boolean) : [],
        webhook_secret: waCfg.webhook_secret || 'dev',
        account_sid: waCfg.account_sid || '',
        auth_token: waCfg.auth_token || '',
        locale_default: waCfg.locale_default || 'en',
        phone_number_id: (waCfg as any).phone_number_id || '',
        access_token: (waCfg as any).access_token || '',
        active_menu_id: (waCfg as any).active_menu_id || '',
      }
      const saved = await putWhatsAppConfig(tenant, payload)
      setWaCfg({ ...saved, from_numbers: Array.isArray(saved.from_numbers) ? saved.from_numbers : (waCfg.from_numbers || []) })
      setWaMsg('WhatsApp configuration saved')
    } catch (e:any) {
      const d = e?.response?.data?.detail
      let msg = 'Failed to save WhatsApp config'
      if (typeof d === 'string') msg = d
      else if (Array.isArray(d) && d.length) msg = d[0]?.msg || JSON.stringify(d[0])
      else if (d && typeof d === 'object') msg = d.msg || JSON.stringify(d)
      else if (e?.message) msg = e.message
      setWaMsg(msg)
    }
  }

  async function onSaveAddressLocation() {
    if (!tenant || !settings) return
    setAddressLocationMsg(null)
    setSaving(true)
    try {
      await updateTenantSettings(tenant, {
        address: settings.address ?? '',
        location: settings.location ?? '',
      })
      setSettings(prev => prev ? { ...prev, address: settings!.address ?? '', location: settings!.location ?? '' } : prev)
      try { clearTenantSettingsCache(); window.dispatchEvent(new CustomEvent('tenantSettingsChanged', { detail: { tenant } })) } catch { /* ignore */ }
      setAddressLocationMsg('Address & location saved')
    } catch (e: any) {
      setAddressLocationMsg(e?.response?.data?.detail || 'Save failed')
    } finally {
      setSaving(false)
    }
  }

  const tabIndexAddressLocation = 1
  const tabIndexPlanAccess = 2
  const tabIndexPayments = 3
  const tabIndexFulfillment = 4
  const tabIndexNotifications = 5
  const tabIndexPassword = 6
  const tabIndexWhatsAppConfig = 7

  return (
    <Box sx={{ p: 1 }}>
      <Typography variant="h5" sx={{ mb: 1 }}>Settings</Typography>

      {/* Tabs at top: General, Plan & Access (includes Modules & Capabilities), etc. */}
      <Tabs value={settingsTab} onChange={(_, v) => setSettingsTab(v)} sx={{ borderBottom: 1, borderColor: 'divider', mb: 0, mt: 1 }}>
        <Tab label="General" />
        <Tab label="Address & Location" />
        <Tab label="Plan & Access" />
        <Tab label="Payments" />
        <Tab label="Fulfillment" />
        <Tab label="Notifications" />
        <Tab label="Password" />
        {isSuperAdmin && (settings?.capabilities || []).map(c => String(c).toLowerCase()).includes('core.whatsapp_menu') && (
          <Tab label="WhatsApp Config" />
        )}
      </Tabs>

      <Card sx={{ mt: 0 }}>
        <CardContent>
              {settingsTab === 0 && (
                <Grid container spacing={2}>
                  <Grid item xs={12} md={6}>
                    <TextField fullWidth label="Tenant display name" value={settings?.display_name || ''} onChange={e=>setSettings(prev=>prev?{...prev, display_name:e.target.value}:prev)} placeholder="e.g. My Salon" helperText={isSuperAdmin ? 'Shown at the top of the page instead of tenant ID. Only Super Admin can edit.' : 'Shown at the top of the page. Editable by Super Admin only.'} disabled={!isSuperAdmin} />
                  </Grid>
                  <Grid item xs={12} md={6}>
                    <TimezoneSelect value={settings?.tz || ''} onChange={(tz) => setSettings(prev => prev ? { ...prev, tz } : prev)} label="Timezone (IANA)" placeholder="Asia/Kolkata" fullWidth />
                  </Grid>
                  <Grid item xs={12} md={6}>
                    <TextField fullWidth label="Owner Email" value={settings?.owner_email || ''} onChange={e=>setSettings(prev=>prev?{...prev, owner_email:e.target.value}:prev)} />
                  </Grid>
                  <Grid item xs={12} md={6}>
                    <TextField
                      select
                      fullWidth
                      label="Tenant country"
                      value={(settings?.tenant_country || 'IN').toUpperCase()}
                      onChange={e => {
                        const iso = e.target.value
                        const row = countries.find(c => c.iso2 === iso)
                        const d = row?.dial || '91'
                        setSettings(prev => prev ? { ...prev, tenant_country: iso } : prev)
                        setOwnerPhoneCode(`+${d}`)
                      }}
                      SelectProps={{ MenuProps: { PaperProps: { style: { maxHeight: 320 } } } }}
                    >
                      {countries.map(c => (
                        <MenuItem key={c.iso2} value={c.iso2}>{c.name} (+{c.dial})</MenuItem>
                      ))}
                    </TextField>
                  </Grid>
                  <Grid item xs={12} md={6}>
                    <Stack direction="row" spacing={1} alignItems="flex-start">
                      <TextField
                        label="Owner dial code"
                        value={ownerPhoneCode}
                        onChange={e => setOwnerPhoneCode(e.target.value)}
                        sx={{ width: 120 }}
                        placeholder="+91"
                      />
                      <TextField
                        fullWidth
                        label="Owner mobile"
                        value={ownerPhoneMobile}
                        onChange={e => setOwnerPhoneMobile(e.target.value)}
                        placeholder="National number (no +). Use Tenant country for default code."
                      />
                    </Stack>
                  </Grid>
                  <Grid item xs={12} md={6}>
                    <TextField select fullWidth label="Date Format" value={settings?.date_format ?? 'DD-MM-YYYY'} onChange={e=>setSettings(prev=>prev?{...prev, date_format:e.target.value as any}:prev)}>
                      <MenuItem value="DD-MM-YYYY">DD-MM-YYYY</MenuItem>
                      <MenuItem value="DD/MM/YYYY">DD/MM/YYYY</MenuItem>
                      <MenuItem value="MM/DD/YYYY">MM/DD/YYYY</MenuItem>
                      <MenuItem value="YYYY-MM-DD">YYYY-MM-DD</MenuItem>
                    </TextField>
                  </Grid>
                  <Grid item xs={12} md={6}>
                    <TextField
                      select
                      fullWidth
                      label="Currency"
                      value={settings?.currency || 'INR'}
                      onChange={e => setSettings(prev => prev ? { ...prev, currency: e.target.value } : prev)}
                      helperText="Currency shown across all pages — dashboard, reports, orders, products, catalog."
                      SelectProps={{ MenuProps: { PaperProps: { style: { maxHeight: 320 } } } }}
                    >
                      {[
                        { code: 'INR', label: 'INR — Indian Rupee (₹)' },
                        { code: 'USD', label: 'USD — US Dollar ($)' },
                        { code: 'EUR', label: 'EUR — Euro (€)' },
                        { code: 'GBP', label: 'GBP — British Pound (£)' },
                        { code: 'AED', label: 'AED — UAE Dirham (د.إ)' },
                        { code: 'SAR', label: 'SAR — Saudi Riyal (﷼)' },
                        { code: 'KWD', label: 'KWD — Kuwaiti Dinar (KD)' },
                        { code: 'QAR', label: 'QAR — Qatari Riyal (ر.ق)' },
                        { code: 'OMR', label: 'OMR — Omani Rial (ر.ع.)' },
                        { code: 'BHD', label: 'BHD — Bahraini Dinar (.د.ب)' },
                        { code: 'MYR', label: 'MYR — Malaysian Ringgit (RM)' },
                        { code: 'SGD', label: 'SGD — Singapore Dollar (S$)' },
                        { code: 'AUD', label: 'AUD — Australian Dollar (A$)' },
                        { code: 'CAD', label: 'CAD — Canadian Dollar (C$)' },
                        { code: 'JPY', label: 'JPY — Japanese Yen (¥)' },
                        { code: 'CNY', label: 'CNY — Chinese Yuan (¥)' },
                        { code: 'KRW', label: 'KRW — South Korean Won (₩)' },
                        { code: 'THB', label: 'THB — Thai Baht (฿)' },
                        { code: 'IDR', label: 'IDR — Indonesian Rupiah (Rp)' },
                        { code: 'PHP', label: 'PHP — Philippine Peso (₱)' },
                        { code: 'BDT', label: 'BDT — Bangladeshi Taka (৳)' },
                        { code: 'PKR', label: 'PKR — Pakistani Rupee (₨)' },
                        { code: 'LKR', label: 'LKR — Sri Lankan Rupee (Rs)' },
                        { code: 'NGN', label: 'NGN — Nigerian Naira (₦)' },
                        { code: 'ZAR', label: 'ZAR — South African Rand (R)' },
                        { code: 'EGP', label: 'EGP — Egyptian Pound (E£)' },
                        { code: 'TRY', label: 'TRY — Turkish Lira (₺)' },
                        { code: 'BRL', label: 'BRL — Brazilian Real (R$)' },
                        { code: 'CHF', label: 'CHF — Swiss Franc (Fr)' },
                      ].map(c => (
                        <MenuItem key={c.code} value={c.code}>{c.label}</MenuItem>
                      ))}
                    </TextField>
                  </Grid>
                  {isSuperAdmin && (
                    <Grid item xs={12}>
                      <Typography variant="subtitle2" fontWeight={600} color="text.primary" sx={{ mb: 1 }}>Security (Super Admin)</Typography>
                      <FormControlLabel
                        control={
                          <Switch
                            checked={loginOtpEnabled}
                            disabled={loginOtpSaving}
                            onChange={async (e) => {
                              const v = e.target.checked
                              setLoginOtpSaving(true)
                              try {
                                await setLoginOtpEnabledApi(v)
                                setLoginOtpEnabled(v)
                              } finally {
                                setLoginOtpSaving(false)
                              }
                            }}
                          />
                        }
                        label="Require OTP after login for Tenant Admins and Staff (OTP sent to mobile; Super Admin is never required to enter OTP)"
                      />
                    </Grid>
                  )}
                  <Grid item xs={12}>
                    <Button variant="contained" disabled={saving || !tenant} onClick={onSave}>Save</Button>
                    {error && <Typography color="error" variant="body2" sx={{ ml: 2 }}>{error}</Typography>}
                    {ok && <Typography color="success.main" variant="body2" sx={{ ml: 2 }}>{ok}</Typography>}
                  </Grid>
                </Grid>
              )}

              {settingsTab === tabIndexAddressLocation && (
                <Grid container spacing={2}>
                  <Typography variant="h6" sx={{ mb: 1 }}>Address &amp; Location</Typography>
                  <Grid item xs={12}>
                    <TextField
                      fullWidth
                      multiline
                      minRows={2}
                      label="Business address"
                      value={settings?.address ?? ''}
                      onChange={e => setSettings(prev => prev ? { ...prev, address: e.target.value } : prev)}
                      placeholder="e.g. 123 Main St, City, State"
                      helperText="Shown in booking confirmation and other messages (e.g. Location line)."
                    />
                  </Grid>
                  <Grid item xs={12}>
                    <TextField
                      fullWidth
                      label="Map link"
                      value={settings?.location ?? ''}
                      onChange={e => setSettings(prev => prev ? { ...prev, location: e.target.value } : prev)}
                      placeholder="e.g. https://maps.google.com/... or Google Maps share URL"
                      helperText="Optional. Paste a Google Maps (or other) link so customers can open directions."
                    />
                  </Grid>
                  <Grid item xs={12}>
                    <Button variant="contained" disabled={saving || !tenant} onClick={onSaveAddressLocation}>Save</Button>
                    {addressLocationMsg && (
                      <Typography variant="body2" sx={{ ml: 2 }} color={addressLocationMsg.includes('Saved') ? 'success.main' : 'error'}>{addressLocationMsg}</Typography>
                    )}
                  </Grid>
                </Grid>
              )}

              {settingsTab === tabIndexPlanAccess && (
                <Box>
                  <Typography variant="h6" sx={{ mb: 1 }}>Plan &amp; Access</Typography>
                  <Grid container spacing={2}>
                    <Grid item xs={12} md={6}>
                      {isSuperAdmin ? (
                        <TextField select fullWidth label="Plan" value={settings?.plan || 'basic'} onChange={(e) => setSettings(prev => prev ? { ...prev, plan: e.target.value } : prev)} helperText="Save Plan to persist. Modules/capabilities have a separate save below.">
                          {(plans.length ? plans : [{ id: 'basic', label: 'Basic' }, { id: 'enterprise', label: 'Enterprise' }, { id: 'pro', label: 'Pro' }]).map((p) => (
                            <MenuItem key={p.id} value={p.id}>{p.label}</MenuItem>
                          ))}
                        </TextField>
                      ) : (
                        <Alert severity="info" icon={false}>Current plan: <strong>{(plans.find(p => p.id === (settings?.plan || 'basic'))?.label || (settings?.plan || 'Basic'))}</strong></Alert>
                      )}
                    </Grid>
                    {isSuperAdmin && (
                      <>
                        <Grid item xs={12}>
                          <Button variant="contained" disabled={savingPlan || !tenant} onClick={onSavePlanOnly}>Save Plan</Button>
                          {planSaveMsg?.error && <Typography color="error" variant="body2" sx={{ ml: 2 }} component="span">{planSaveMsg.error}</Typography>}
                          {planSaveMsg?.ok && <Typography color="success.main" variant="body2" sx={{ ml: 2 }} component="span">{planSaveMsg.ok}</Typography>}
                        </Grid>
                      </>
                    )}
                  </Grid>
                  {isSuperAdmin && (
                    <>
                      <Divider sx={{ my: 3 }} />
                      <Typography variant="subtitle1" fontWeight={600} color="text.primary" sx={{ mb: 1 }}>Modules &amp; Capabilities</Typography>
                      <Tabs value={planAccessSubTab} onChange={(_, v) => setPlanAccessSubTab(v)} sx={{ borderBottom: 1, borderColor: 'divider', mb: 2 }}>
                        <Tab label="Modules" />
                        <Tab label="Core" />
                        <Tab label="Salon" />
                        <Tab label="Store" />
                        <Tab label="AI" />
                      </Tabs>
                      {planAccessSubTab === 0 && (() => {
                        const moduleItems = registry.filter(r => r.type === 'module')
                        const selected = new Set((settings?.modules || []).map(m => m.toLowerCase()))
                        function toggleModule(id: string, on: boolean) {
                          setSettings(prev => {
                            if (!prev) return prev
                            const baseMods: string[] = Array.isArray((prev as any).modules) ? (prev as any).modules.map((m: any) => String(m).toLowerCase()) : []
                            const idL = String(id).toLowerCase()
                            const modsSet = new Set(baseMods)
                            if (on) modsSet.add(idL); else modsSet.delete(idL)
                            return { ...prev, modules: Array.from(modsSet).sort() }
                          })
                        }
                        return (
                          <Box>
                            <Divider sx={{ mb: 2 }} />
                            <Typography variant="subtitle2" fontWeight={600} color="text.primary" sx={{ mb: 1 }}>Enable modules for this tenant</Typography>
                            <FormGroup>
                              {moduleItems.map(m => (
                                <FormControlLabel key={m.id} control={<Checkbox checked={selected.has(m.id.toLowerCase())} onChange={(e) => toggleModule(m.id, e.target.checked)} />} label={<Typography variant="body2" color="text.primary">{m.label} ({m.id})</Typography>} />
                              ))}
                            </FormGroup>
                            <Divider sx={{ my: 2 }} />
                            <Button variant="contained" disabled={savingModules || !tenant} onClick={onSaveModulesOnly}>Save Modules</Button>
                            {modulesSaveMsg?.error && <Typography color="error" variant="body2" sx={{ ml: 2 }} component="span">{modulesSaveMsg.error}</Typography>}
                            {modulesSaveMsg?.ok && <Typography color="success.main" variant="body2" sx={{ ml: 2 }} component="span">{modulesSaveMsg.ok}</Typography>}
                          </Box>
                        )
                      })()}
                      {[1, 2, 3, 4].indexOf(planAccessSubTab) !== -1 && (() => {
                        const groupNames = ['Core', 'Salon', 'Store', 'AI']
                        const currentGroup = groupNames[planAccessSubTab - 1]
                        const caps = new Set((settings?.capabilities || []).map(c => c.toLowerCase()))
                        const enabledModules = new Set((settings?.modules || []).map(m => m.toLowerCase()))
                        function toggleCapability(id: string, on: boolean) {
                          setSettings(prev => {
                            if (!prev) return prev
                            const baseCaps: string[] = Array.isArray((prev as any).capabilities) ? (prev as any).capabilities.map((c: any) => String(c).toLowerCase()) : []
                            const idL = String(id).toLowerCase()
                            if (idL.startsWith('ai.')) return prev
                            const capsSet = new Set(baseCaps)
                            if (on) capsSet.add(idL); else capsSet.delete(idL)
                            return { ...prev, capabilities: Array.from(capsSet).sort() }
                          })
                        }
                        const items = registry.filter(r => r.type === 'capability' && (r.group || 'Core').toLowerCase() === currentGroup.toLowerCase()).sort((a, b) => a.label.localeCompare(b.label))
                        return (
                          <Box>
                            <Divider sx={{ mb: 2 }} />
                            <Typography variant="subtitle2" fontWeight={600} color="text.primary" sx={{ mb: 1 }}>{currentGroup} capabilities</Typography>
                            <FormGroup>
                              {items.map(item => {
                                const id = item.id
                                const checked = caps.has(id.toLowerCase())
                                const itemModule = (item as any).module as string | undefined
                                const moduleEnabled = itemModule ? enabledModules.has(itemModule.toLowerCase()) : true
                                return (
                                  <Tooltip key={id} title={item.description || ''} placement="right" arrow>
                                    <FormControlLabel control={<Checkbox checked={checked && moduleEnabled} disabled={!moduleEnabled || id.toLowerCase().startsWith('ai.')} onChange={(e) => toggleCapability(id, e.target.checked)} />} label={<Typography variant="body2" color="text.primary" sx={{ opacity: moduleEnabled ? 1 : 0.5 }}>{item.label} ({id}){id.toLowerCase().startsWith('ai.') ? ' — managed by AI' : (moduleEnabled ? '' : ' — enable module first')}</Typography>} />
                                  </Tooltip>
                                )
                              })}
                            </FormGroup>
                            {items.length === 0 && <Typography variant="body2" color="text.secondary">No capabilities in this group.</Typography>}
                            <Divider sx={{ my: 2 }} />
                            <Stack direction="row" spacing={1} sx={{ mb: 1 }}>
                              <Button size="small" variant="outlined" onClick={() => { const enabled = new Set((settings?.modules || []).map(m => m.toLowerCase())); const defaults = registry.filter(r => r.type === 'capability' && r.default && (!('module' in r) || enabled.has((r as any).module?.toLowerCase?.() || ''))).map(r => r.id.toLowerCase()); setSettings(prev => prev ? { ...prev, capabilities: Array.from(new Set([...(prev.capabilities || []).map(c => c.toLowerCase()), ...defaults])).sort() } : prev) }}>Select defaults</Button>
                              <Button size="small" variant="outlined" onClick={() => setSettings(prev => prev ? { ...prev, modules: [], capabilities: [] } : prev)}>Clear all</Button>
                            </Stack>
                            <Button variant="contained" disabled={savingCapabilities || !tenant} onClick={onSaveCapabilitiesOnly}>Save Capabilities</Button>
                            {capabilitiesSaveMsg?.error && <Typography color="error" variant="body2" sx={{ ml: 2 }} component="span">{capabilitiesSaveMsg.error}</Typography>}
                            {capabilitiesSaveMsg?.ok && <Typography color="success.main" variant="body2" sx={{ ml: 2 }} component="span">{capabilitiesSaveMsg.ok}</Typography>}
                          </Box>
                        )
                      })()}
                    </>
                  )}
                </Box>
              )}

              {settingsTab === tabIndexPayments && (
                Array.isArray(settings?.modules) && settings!.modules!.map(m=>m.toLowerCase()).includes('store') ? (
                <Grid container spacing={2}>
                  <Typography variant="h6" sx={{ mb: 1 }}>Payments</Typography>
                  <Grid item xs={12}><FormControlLabel control={<Switch checked={settings?.store_enabled ?? true} onChange={(e)=>setSettings(prev=>prev?{...prev, store_enabled:e.target.checked}:prev)} />} label="Store enabled" /></Grid>
                  <Grid item xs={12} md={6}><TextField select fullWidth label="Provider" value={settings?.payment_config?.provider || 'dummy'} onChange={(e)=>setSettings(prev=>prev?{...prev, payment_config:{...prev.payment_config, provider:e.target.value as any}}:prev)}><MenuItem value="dummy">Dummy (dev)</MenuItem><MenuItem value="stripe" disabled>Stripe (coming soon)</MenuItem><MenuItem value="razorpay" disabled>Razorpay (coming soon)</MenuItem></TextField></Grid>
                  <Grid item xs={12} md={6}><TextField fullWidth label="Methods (comma separated)" placeholder="ONLINE,COD" value={(settings?.payment_config?.methods||['ONLINE','COD']).join(',')} onChange={(e)=>{ const arr = e.target.value.split(',').map(s=>s.trim().toUpperCase()).filter(Boolean) as any; setSettings(prev=>prev?{...prev, payment_config:{...prev.payment_config, methods: arr}}:prev) }} /></Grid>
                  <Grid item xs={12} md={6}><FormControlLabel control={<Switch checked={!!settings?.payment_config?.test_mode} onChange={(e)=>setSettings(prev=>prev?{...prev, payment_config:{...prev.payment_config, test_mode:e.target.checked}}:prev)} />} label="Test mode" /></Grid>
                  <Grid item xs={12}><TextField fullWidth type="password" label="Webhook secret (dev)" value={settings?.payment_config?.webhook_secret || ''} onChange={(e)=>setSettings(prev=>prev?{...prev, payment_config:{...prev.payment_config, webhook_secret:e.target.value}}:prev)} /></Grid>
                  <Grid item xs={12}><Button variant="contained" disabled={saving || !tenant} onClick={onSavePayments}>Save Payments</Button></Grid>
                </Grid>
                ) : (
                <Typography variant="body2" color="text.secondary">Enable the Store module in Plan &amp; Access to configure payments.</Typography>
                )
              )}

              {settingsTab === tabIndexFulfillment && Array.isArray(settings?.modules) && settings!.modules!.map(m=>m.toLowerCase()).includes('store') && (
                <Grid container spacing={2}>
                  <Grid item xs={12} md={6}>
                    <FormControlLabel control={<Switch checked={!!settings?.delivery_config?.delivery_enabled} onChange={(e)=>setSettings(prev=>prev?{...prev, delivery_config:{...(prev.delivery_config||{}), delivery_enabled:e.target.checked, pickup_enabled: prev?.delivery_config?.pickup_enabled ?? true, service_areas: prev?.delivery_config?.service_areas || [], store_hours: prev?.delivery_config?.store_hours || []}}:prev)} />} label="Delivery enabled" />
                  </Grid>
                  <Grid item xs={12} md={6}>
                    <FormControlLabel control={<Switch checked={!!settings?.delivery_config?.pickup_enabled} onChange={(e)=>setSettings(prev=>prev?{...prev, delivery_config:{...(prev.delivery_config||{}), pickup_enabled:e.target.checked, delivery_enabled: prev?.delivery_config?.delivery_enabled ?? true, service_areas: prev?.delivery_config?.service_areas || [], store_hours: prev?.delivery_config?.store_hours || []}}:prev)} />} label="Pickup enabled" />
                  </Grid>
                  <Grid item xs={12}><TextField fullWidth multiline minRows={2} label="Service areas (one per line)" value={(settings?.delivery_config?.service_areas||[]).join('\n')} onChange={(e)=>{ const list = e.target.value.split(/\n|,/).map(s=>s.trim()).filter(Boolean); setSettings(prev=>prev?{...prev, delivery_config:{...(prev.delivery_config||{}), service_areas:list}}:prev) }} /></Grid>
                  <Grid item xs={12}><TextField fullWidth multiline minRows={2} label="Store hours (e.g., Mon-Fri 9-18)" value={(settings?.delivery_config?.store_hours||[]).join('\n')} onChange={(e)=>{ const list = e.target.value.split(/\n|,/).map(s=>s.trim()).filter(Boolean); setSettings(prev=>prev?{...prev, delivery_config:{...(prev.delivery_config||{}), store_hours:list}}:prev) }} /></Grid>
                  <Grid item xs={12}><Button variant="contained" disabled={saving || !tenant} onClick={onSaveFulfillment}>Save Fulfillment</Button></Grid>
                </Grid>
              )}
              {settingsTab === tabIndexFulfillment && (!Array.isArray(settings?.modules) || !settings?.modules?.map(m=>m.toLowerCase()).includes('store')) && (
                <Typography variant="body2" color="text.secondary">Enable the Store module in Plan &amp; Access to configure fulfillment.</Typography>
              )}
              {settingsTab === tabIndexNotifications && (
                <Grid container spacing={2}>
                  <Typography variant="subtitle1" sx={{ mb: 1 }}>Notification Channel</Typography>
                  <Grid item xs={12}><FormGroup row>
                    <FormControlLabel control={<Switch checked={settings?.messaging_channels?.email !== false} onChange={(e) => setSettings(prev => prev ? { ...prev, messaging_channels: { ...prev.messaging_channels, email: e.target.checked } } : prev)} />} label="Email" />
                    <FormControlLabel control={<Switch checked={settings?.messaging_channels?.whatsapp !== false} onChange={(e) => setSettings(prev => prev ? { ...prev, messaging_channels: { ...prev.messaging_channels, whatsapp: e.target.checked } } : prev)} />} label="WhatsApp" />
                    <FormControlLabel control={<Switch checked={!!settings?.messaging_channels?.sms} onChange={(e) => setSettings(prev => prev ? { ...prev, messaging_channels: { ...prev.messaging_channels, sms: e.target.checked } } : prev)} />} label="SMS" />
                  </FormGroup></Grid>
                  {settings?.messaging_channels?.sms && (<><Grid item xs={12} md={6}><TextField fullWidth label="SMS From number" placeholder="+1234567890" value={settings?.sms_config?.from_number || ''} onChange={(e) => setSettings(prev => prev ? { ...prev, sms_config: { ...prev.sms_config, from_number: e.target.value } } : prev)} /></Grid>
                  <Grid item xs={12} md={6}><TextField select fullWidth label="SMS Provider" value={settings?.sms_config?.provider || 'twilio'} onChange={(e) => setSettings(prev => prev ? { ...prev, sms_config: { ...prev.sms_config, provider: e.target.value } } : prev)}><MenuItem value="twilio">Twilio</MenuItem><MenuItem value="other">Other</MenuItem></TextField></Grid></>)}
                  <Grid item xs={12}><Button variant="contained" disabled={saving || !tenant} onClick={onSaveChannels}>Save channels</Button>{channelsMsg && <Typography variant="body2" sx={{ ml: 2 }} color={channelsMsg.includes('Failed') ? 'error' : 'success.main'}>{channelsMsg}</Typography>}</Grid>
                  <Grid item xs={12}><Divider sx={{ my: 2 }} /></Grid>
                  <Typography variant="subtitle1" sx={{ mb: 1 }}>Follow-up events</Typography>
                  <Grid item xs={12}><FormGroup row>
                    <FormControlLabel control={<Checkbox checked={(settings as any)?.followup_prefs?.confirm !== false} onChange={(e) => setSettings(prev => prev ? { ...prev, followup_prefs: { ...(prev as any).followup_prefs, confirm: e.target.checked } } : prev)} />} label="Confirm (immediate)" />
                    <FormControlLabel control={<Checkbox checked={(settings as any)?.followup_prefs?.reminder24 !== false} onChange={(e) => setSettings(prev => prev ? { ...prev, followup_prefs: { ...(prev as any).followup_prefs, reminder24: e.target.checked } } : prev)} />} label="Reminder 24h before" />
                    <FormControlLabel control={<Checkbox checked={(settings as any)?.followup_prefs?.reminder2 !== false} onChange={(e) => setSettings(prev => prev ? { ...prev, followup_prefs: { ...(prev as any).followup_prefs, reminder2: e.target.checked } } : prev)} />} label="Reminder 2h before" />
                    <FormControlLabel control={<Checkbox checked={(settings as any)?.followup_prefs?.post !== false} onChange={(e) => setSettings(prev => prev ? { ...prev, followup_prefs: { ...(prev as any).followup_prefs, post: e.target.checked } } : prev)} />} label="Post-visit (thanks)" />
                  </FormGroup></Grid>
                  <Grid item xs={12}><Button variant="contained" disabled={saving || !tenant} onClick={onSaveFollowupPrefs}>Save follow-up options</Button>{followupPrefsMsg && <Typography variant="body2" sx={{ ml: 2 }} color={followupPrefsMsg.includes('Failed') ? 'error' : 'success.main'}>{followupPrefsMsg}</Typography>}</Grid>
                </Grid>
              )}
              {settingsTab === tabIndexPassword && (
                <Grid container spacing={2}>
                  {!isSuperAdmin ? (
                    <>
                      <Grid item xs={12}><Typography variant="h6" sx={{ mb: 1 }}>Change my password</Typography></Grid>
                      <Grid item xs={12} md={6}><TextField fullWidth type="password" label="New Password" value={pwd1} onChange={e=>setPwd1(e.target.value)} placeholder="min 8 characters" /></Grid>
                      <Grid item xs={12} md={6}><TextField fullWidth type="password" label="Confirm Password" value={pwd2} onChange={e=>setPwd2(e.target.value)} /></Grid>
                      <Grid item xs={12}><Button variant="contained" disabled={!me?.id} onClick={onChangePassword}>Update Password</Button>{pwdMsg && <Typography variant="body2" sx={{ ml: 2 }} color={pwdMsg.includes('Failed') || pwdMsg.toLowerCase().includes('error') ? 'error' : 'success.main'}>{pwdMsg}</Typography>}</Grid>
                    </>
                  ) : (
                    <>
                      <Grid item xs={12}><Typography variant="h6" sx={{ mb: 1 }}>Change tenant admin password</Typography></Grid>
                      <Grid item xs={12}><Typography variant="body2" color="text.secondary">Only the tenant admin for the selected tenant. No other roles.</Typography></Grid>
                      {tenantAdminUser ? (
                        <>
                          <Grid item xs={12} md={6}><TextField fullWidth type="password" label="New password" value={pwdForUserNew} onChange={e=>setPwdForUserNew(e.target.value)} placeholder="min 8 characters" /></Grid>
                          <Grid item xs={12} md={6}><TextField fullWidth type="password" label="Confirm password" value={pwdForUserConfirm} onChange={e=>setPwdForUserConfirm(e.target.value)} /></Grid>
                          <Grid item xs={12}><Button variant="contained" disabled={!pwdForUserNew || pwdForUserNew.length < 8 || pwdForUserNew !== pwdForUserConfirm} onClick={onChangeTenantUserPassword}>Set password</Button>{pwdForUserMsg && <Typography variant="body2" sx={{ ml: 2 }} color={pwdForUserMsg.includes('Failed') || pwdForUserMsg.includes('match') || pwdForUserMsg.includes('No tenant') ? 'error' : 'success.main'}>{pwdForUserMsg}</Typography>}</Grid>
                        </>
                      ) : (
                        <Grid item xs={12}><Typography variant="body2" color="text.secondary">No tenant admin found for the selected tenant.</Typography></Grid>
                      )}
                    </>
                  )}
                </Grid>
              )}

              {settingsTab === tabIndexWhatsAppConfig && isSuperAdmin && (
                <Box>
                  <Typography variant="h6" sx={{ mb: 2 }}>WhatsApp Config</Typography>
                  {waMsg && <Alert severity="success" sx={{ mb: 2 }}>{waMsg}</Alert>}
                  <Grid container spacing={2}>
                    <Grid item xs={12} md={6}>
                      <TextField select fullWidth label="Provider" value={waCfg?.provider || 'twilio'} onChange={e=>setWaCfg(prev=>prev?{ ...prev, provider: e.target.value as any }:prev)}>
                        <MenuItem value="twilio">Twilio (dummy/dev)</MenuItem>
                        <MenuItem value="meta_cloud">Meta Cloud (dummy interactive)</MenuItem>
                      </TextField>
                    </Grid>
                    <Grid item xs={12} md={6}>
                      <TextField fullWidth label="Default Locale" value={waCfg?.locale_default || 'en'} onChange={e=>setWaCfg(prev=>prev?{ ...prev, locale_default: e.target.value }:prev)} placeholder="en" />
                    </Grid>
                    <Grid item xs={12}>
                      <TextField fullWidth multiline minRows={2} label="From numbers (one per line, E.164 e.g., +911234567890)" value={(waCfg?.from_numbers || []).join('\n')} onChange={e=>setWaCfg(prev=>prev?{ ...prev, from_numbers: e.target.value.split(/\n|,/).map(s=>s.trim()).filter(Boolean) }:prev)} helperText="Accepts optional 'whatsapp:+..' prefix; we will normalize to +E.164" />
                    </Grid>
                    <Grid item xs={12} md={6}>
                      <TextField fullWidth label="Webhook secret (dev)" value={waCfg?.webhook_secret || ''} onChange={e=>setWaCfg(prev=>prev?{ ...prev, webhook_secret: e.target.value }:prev)} helperText="Used to sign bot requests; keep 'dev' for local tests" />
                    </Grid>
                    <Grid item xs={12} md={6}>
                      <TextField fullWidth label="Account SID (optional)" value={waCfg?.account_sid || ''} onChange={e=>setWaCfg(prev=>prev?{ ...prev, account_sid: e.target.value }:prev)} />
                    </Grid>
                    <Grid item xs={12} md={6}>
                      <TextField fullWidth type="password" label="Auth token (optional)" value={waCfg?.auth_token || ''} onChange={e=>setWaCfg(prev=>prev?{ ...prev, auth_token: e.target.value }:prev)} />
                    </Grid>
                    {String(waCfg?.provider || 'twilio') === 'meta_cloud' && (
                      <>
                        <Grid item xs={12} md={6}>
                          <TextField fullWidth label="Meta phone_number_id" value={(waCfg as any)?.phone_number_id || ''} onChange={e=>setWaCfg(prev=>prev?{ ...prev, phone_number_id: e.target.value }:prev)} helperText="Dummy mode: any value allowed" />
                        </Grid>
                        <Grid item xs={12} md={6}>
                          <TextField fullWidth type="password" label="Meta access_token" value={(waCfg as any)?.access_token || ''} onChange={e=>setWaCfg(prev=>prev?{ ...prev, access_token: e.target.value }:prev)} helperText="Dummy mode: any value allowed" />
                        </Grid>
                        <Grid item xs={12} md={6}>
                          <TextField fullWidth label="Active menu id (optional)" value={(waCfg as any)?.active_menu_id || ''} onChange={e=>setWaCfg(prev=>prev?{ ...prev, active_menu_id: e.target.value }:prev)} helperText="If empty, latest published menu will be used" />
                        </Grid>
                      </>
                    )}
                    <Grid item xs={12}>
                      <Button variant="contained" onClick={onSaveWhatsApp} disabled={saving || !tenant || !waCfg}>Save</Button>
                      <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>Webhook URL: {getApiBaseURL()}/integrations/twilio/whatsapp/webhook</Typography>
                    </Grid>
                  </Grid>
                  <Divider sx={{ my: 3 }} />
                  <Typography variant="h6" sx={{ mb: 1 }}>Test webhook (dummy/dev)</Typography>
                  <Grid container spacing={2}>
                    <Grid item xs={12} md={4}>
                      <TextField fullWidth label="From" value={waTestFrom} onChange={e=>setWaTestFrom(e.target.value)} placeholder="+911112223334" />
                    </Grid>
                    <Grid item xs={12} md={4}>
                      <TextField select fullWidth label="To (tenant number)" value={waTestTo} onChange={e=>setWaTestTo(e.target.value)}>
                        {(waCfg?.from_numbers || []).map((n: string)=>(<MenuItem key={n} value={n}>{n}</MenuItem>))}
                      </TextField>
                    </Grid>
                    <Grid item xs={12} md={4}>
                      <TextField fullWidth label="Body" value={waTestBody} onChange={e=>setWaTestBody(e.target.value)} placeholder="1" />
                    </Grid>
                    <Grid item xs={12}>
                      <Button variant="outlined" onClick={onTestWhatsAppWebhook} disabled={!tenant || !waTestTo}>Send test</Button>
                    </Grid>
                    {waTestResp && (
                      <Grid item xs={12}>
                        <Typography variant="subtitle2" sx={{ mb: 1 }}>Response (TwiML/XML)</Typography>
                        <Box sx={{ p: 1, bgcolor: '#fafafa', border: '1px solid #eee', borderRadius: 1, fontFamily: 'monospace', whiteSpace: 'pre-wrap' }}>{waTestResp}</Box>
                      </Grid>
                    )}
                  </Grid>
                </Box>
              )}
            </CardContent>
          </Card>
    </Box>
  )
}
