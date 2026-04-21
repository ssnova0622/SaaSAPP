import { useEffect, useMemo, useState } from 'react'
import { Box, Button, Card, CardContent, Chip, Grid, IconButton, MenuItem, Select, Stack, Table, TableBody, TableCell, TableHead, TableRow, TextField, Typography, Alert, Autocomplete, CircularProgress, Avatar, Divider, Switch, FormControlLabel } from '@mui/material'
import DeleteIcon from '@mui/icons-material/Delete'
import AddIcon from '@mui/icons-material/Add'
import ContentCopyIcon from '@mui/icons-material/ContentCopy'
import { Cart, CartItem, CheckoutPayload, CheckoutResult, putCart, checkout, listOrders, getOrder } from '@api/store'
import { listProducts, Product, getProductBySku } from '@api/catalog'
import { listOffers, type Offer } from '@api/offers'
import { fullUrlForMedia } from '@api/upload'
import { getTenantSettings } from '@api/tenants'
import { useEffectiveTenant } from '../../hooks/useEffectiveTenant'
import { useAlert } from '@contexts/AlertContext'

export default function CartsPage(){
  const { effectiveTenant } = useEffectiveTenant()
  const { showConfirm } = useAlert()
  const tenant = effectiveTenant
  const [phone,setPhone]=useState<string>(()=>localStorage.getItem('store_last_phone')||'')
  const [loadQuery, setLoadQuery] = useState<string>(()=>localStorage.getItem('store_last_phone')||'')
  const [cart,setCart]=useState<Cart|null>(null)
  const [items,setItems]=useState<CartRow[]>([])
  const [loading,setLoading]=useState(false)
  const [error,setError]=useState<string|null>(null)
  const [result,setResult]=useState<CheckoutResult|null>(null)
  const [mode,setMode]=useState<'delivery'|'pickup'>('delivery')
  const [address,setAddress]=useState({ label:'Home', line1:'', city:'', pincode:'' })
  // Default to COD to avoid out-of-range value when ONLINE payments capability is not enabled
  const [payMethod,setPayMethod]=useState<'ONLINE'|'COD'>('COD')
  const [capabilities, setCapabilities] = useState<string[]>([])
  const [showAddress, setShowAddress] = useState(true)
  // Autocomplete state per row: options and loading indicators
  const [skuOpts, setSkuOpts] = useState<Record<number, Product[]>>({})
  const [skuLoadingIdx, setSkuLoadingIdx] = useState<number|null>(null)
  // Product cache to avoid repeated lookups for the same SKU
  const [productCache, setProductCache] = useState<Record<string, Product>>({})
  const [activeOffers, setActiveOffers] = useState<Offer[]>([])
  // Cart-level coupon / discount (percent or amount off subtotal)
  const [couponType, setCouponType] = useState<'percent' | 'amount' | ''>('')
  const [couponValue, setCouponValue] = useState<string>('')
  const [couponCode, setCouponCode] = useState<string>('')
  type CartRow = CartItem & { apply_offer?: boolean }

  const isOrderId = (s: string) => /^ORD-/i.test(String(s || '').trim())

  // clear state when tenant changes
  useEffect(() => {
    setCart(null)
    setItems([])
    setResult(null)
    setError(null)
    setProductCache({})
    setActiveOffers([])
    setMode('delivery')
    setShowAddress(true)
    setCouponType('')
    setCouponValue('')
    setCouponCode('')
    setLoadQuery('')
  }, [tenant])

  // Load capabilities for current tenant to decide if ONLINE payments should be shown
  useEffect(()=>{
    let mounted = true
    const init = async ()=>{
      if(!tenant){ 
        if(mounted){ setCapabilities([]) }
        return 
      }
      try{
        const s = await getTenantSettings(tenant)
        if(!mounted) return
        const caps = (s.capabilities||[]).map((c: string)=>c.toLowerCase())
        setCapabilities(caps)
        // Keep selection consistent with capabilities
        if(!caps.includes('store.payments')){
          // Payments not enabled: ensure value is COD to match available options
          setPayMethod('COD')
        } else {
          // Payments enabled: if current is not a valid option, switch to ONLINE by default
          setPayMethod(prev => (prev === 'ONLINE' || prev === 'COD') ? prev : 'ONLINE')
        }
      }catch(err){
        console.error('Failed to load tenant settings:', err)
        if(mounted){ setCapabilities([]) }
      }
    }
    init()
    return () => { mounted = false }
  },[tenant])

  useEffect(()=>{ if(phone) localStorage.setItem('store_last_phone', phone) },[phone])
  useEffect(() => { if (loadQuery && !isOrderId(loadQuery)) setPhone(loadQuery) }, [loadQuery])

  // Load active offers when tenant is available so the offer popup works when adding products (even before Load cart)
  useEffect(() => {
    if (!tenant) return
    let mounted = true
    listOffers(tenant, { active_only: true, page: 1, size: 100 })
      .then((res) => { if (mounted) setActiveOffers(res.items || []) })
      .catch(() => { if (mounted) setActiveOffers([]) })
    return () => { mounted = false }
  }, [tenant])

  const subtotal = useMemo(()=> items.reduce((s,it)=> s + (Number(it.qty)||0) * (Number(it.price_snapshot)||0), 0), [items])

  // Compute final subtotal from backend if available, otherwise frontend fallback
  const displaySubtotal = cart?.totals?.subtotal != null ? Number(cart.totals.subtotal) : subtotal

  // Cart-level discount (coupon): percent or amount off subtotal
  const couponDiscountAmount = useMemo(() => {
    if (!couponType || couponValue === '' || couponValue === undefined) return 0
    const v = Number(couponValue)
    if (Number.isNaN(v) || v <= 0) return 0
    if (couponType === 'percent') return Math.min(displaySubtotal * (v / 100), displaySubtotal)
    return Math.min(v, displaySubtotal)
  }, [couponType, couponValue, displaySubtotal])
  const displayTotal = Math.max(0, displaySubtotal - couponDiscountAmount)

  function addRow(){ setItems(prev=>[...prev, { sku:'', qty:1, price_snapshot:0, manual: false }]) }
  /** Add a row for manual entry when product is not in the product catalog */
  function addManualEntryRow(){ setItems(prev=>[...prev, { sku:'', qty:1, price_snapshot:0, manual: true }]) }
  function updateRow(idx:number, patch: Partial<CartRow>){ setItems(prev=> prev.map((it,i)=> i===idx? { ...it, ...patch }: it)) }
  function removeRow(idx:number){ setItems(prev=> prev.filter((_,i)=> i!==idx)) }

  // Compute product discounted price (fallback when final_selling_price not set)
  function computeUnitPrice(p: Product): number {
    const price = Number(p.price) || 0
    const t = p.discount_type as ('amount'|'percent'|null|undefined)
    const v = Number(p.discount_value || 0)
    if (t === 'amount') return Math.max(0, price - v)
    if (t === 'percent') return Math.max(0, price - (price * (v/100)))
    return price
  }

  // Selling price from product: use final_selling_price (Product page) when available
  function getBaseSellingPrice(p: Product): number {
    if (p.final_selling_price != null && p.final_selling_price !== undefined) return Number(p.final_selling_price)
    return computeUnitPrice(p)
  }

  function offerPriceForSku(basePrice: number, sku: string): number {
    if (!activeOffers.length || !sku) return basePrice
    const offer = activeOffers.find((o) => o.product_skus?.includes(sku))
    if (!offer?.discount_info) return basePrice
    const t = (offer.discount_info as { type?: string })?.type
    const v = Number((offer.discount_info as { value?: number })?.value ?? 0)
    if (t === 'amount') return Math.max(0, basePrice - v)
    if (t === 'percent') return Math.max(0, basePrice - (basePrice * (v / 100)))
    return basePrice
  }

  function hasOfferForSku(sku: string): boolean {
    return !!sku && activeOffers.some((o) => o.product_skus?.includes(sku))
  }

  async function autofillPriceFromSku(idx: number, sku: string){
    try{
      if(!tenant || !sku) return
      const trimmedSku = String(sku).trim()
      if (!trimmedSku) return
      let match = productCache[trimmedSku]
      if(!match) {
        match = await getProductBySku(tenant, trimmedSku)
        if(match) setProductCache(prev => ({ ...prev, [trimmedSku]: match }))
      }
      if(match){
        const base = getBaseSellingPrice(match)
        const hasOffer = hasOfferForSku(match.sku)
        // On blur/autofill we do not show the offer popup (avoids multiple popups when tabbing through rows).
        // Use offer price by default when product has an offer; user can change via the row toggle.
        const applyOffer = hasOffer
        const price = hasOffer ? offerPriceForSku(base, match.sku) : base
        setItems(prev => prev.map((item, i) =>
          i === idx
            ? { ...item, sku: match!.sku, price_snapshot: Number(price), unit: match!.unit ?? undefined, name: match!.name ?? undefined, apply_offer: applyOffer }
            : item
        ))
      }
    }catch{
      // ignore lookup failures; keep user-entered price
    }
  }

  async function searchSkuOptions(idx: number, term: string){
    try{
      if(!tenant || !term){ setSkuOpts(prev=> ({ ...prev, [idx]: [] })); return }
      setSkuLoadingIdx(idx)
      const res = await listProducts(tenant, { search: term, page: 1, size: 20, flatten_variants: true })
      setSkuOpts(prev=> ({ ...prev, [idx]: res.items || [] }))
    }catch{
      setSkuOpts(prev=> ({ ...prev, [idx]: [] }))
    }finally{
      setSkuLoadingIdx(prev => (prev===idx? null : prev))
    }
  }

  /** Populate product cache for given SKUs so unit dropdowns and labels work after loading by phone/order */
  async function fillProductCacheForSkus(skus: string[]) {
    if (!tenant) return
    const unique = [...new Set((skus || []).map(s => String(s || '').trim()).filter(Boolean))]
    const next: Record<string, Product> = {}
    await Promise.all(
      unique.map(async (sku) => {
        try {
          const p = await getProductBySku(tenant, sku)
          if (p) next[sku] = p
        } catch {
          // skip failed lookups
        }
      })
    )
    if (Object.keys(next).length) setProductCache(prev => ({ ...prev, ...next }))
  }

  /** Load: fetch last recent order by phone, or fetch by order number. Single textbox: store owner enters mobile or order number. */
  async function load(clearResult = true){
    if (!tenant) return
    const trimmed = loadQuery.trim()
    if (!trimmed) {
      setResult(null)
      setError('Enter customer phone')
      return
    }
    setLoading(true); setError(null)
    if (clearResult) setResult(null)
    setCart(null)
    try {
      if (isOrderId(trimmed)) {
        const order = await getOrder(tenant, trimmed)
        const rows: CartRow[] = (order.items || []).map((it: any) => ({
          sku: it.sku,
          qty: it.qty,
          price_snapshot: Number(it.price_snapshot) || 0,
          unit: it.unit,
          name: it.name,
          manual: !!it.manual,
          apply_offer: !!it.offer_applied,
        }))
        setItems(rows)
        fillProductCacheForSkus(rows.map(r => r.sku).filter(Boolean))
        const orderPhone = (order as any).customer?.phone || ''
        setPhone(orderPhone)
        setLoadQuery(orderPhone)
        setError(null)
        return
      }
      setPhone(trimmed)
      const res = await listOrders(tenant, { search: trimmed, page: 1, size: 25 })
      const orders = (res.items || []).slice()
      orders.sort((a, b) => {
        const ta = a.created_at ? new Date(a.created_at).getTime() : 0
        const tb = b.created_at ? new Date(b.created_at).getTime() : 0
        return tb - ta
      })
      const lastOrder = orders[0]
      if (!lastOrder || !lastOrder.items?.length) {
        setItems([])
        setError('No recent order found for this phone')
        return
      }
      const rows: CartRow[] = lastOrder.items.map((it: any) => ({
        sku: it.sku,
        qty: it.qty,
        price_snapshot: Number(it.price_snapshot) || 0,
        unit: it.unit,
        name: it.name,
        manual: !!it.manual,
        apply_offer: !!it.offer_applied,
      }))
      setItems(rows)
      fillProductCacheForSkus(rows.map(r => r.sku).filter(Boolean))
      setError(null)
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Failed to load order')
    } finally {
      setLoading(false)
    }
  }


  async function doCheckout(){
    if (!tenant) return
    const mobile = (phone || '').trim()
    if (!mobile) {
      setResult(null)
      setError('Enter customer phone')
      return
    }
    // No API calls below until after this point — order is never created without phone
    setLoading(true); setError(null); setResult(null)
    // Ensure the latest UI edits are persisted before checkout, otherwise
    // the order will be created from stale quantities in the backend cart.
    // 1) Validate items
    const invalid = items.find(it => !String(it.sku||'').trim() || (Number(it.qty) <= 0))
    if(invalid){
      setLoading(false)
      setError('Each item must have a SKU and quantity > 0 for checkout')
      return
    }
    // 2) Persist current items to cart (phone already validated above)
    try{
      const cartPayload: CartItem[] = items.map(({ apply_offer, ...rest }) => rest)
      await putCart(tenant, mobile, cartPayload)
    }catch(e:any){
      setLoading(false)
      setError(e?.response?.data?.detail || 'Failed to save cart before checkout')
      return
    }
    const allowOnline = capabilities.includes('store.payments')
    const method: 'ONLINE'|'COD' = allowOnline ? payMethod : 'COD'
    const discountInfo =
      couponType && couponValue !== '' && !Number.isNaN(Number(couponValue)) && Number(couponValue) > 0
        ? { type: couponType as 'percent' | 'amount', value: Number(couponValue), code: couponCode.trim() || undefined }
        : undefined
    const payload: CheckoutPayload = {
      fulfillment_mode: mode,
      payment_method: method,
      address: mode === 'delivery' ? { label: address.label, line1: address.line1, city: address.city, pincode: address.pincode } as any : undefined,
      discount_info: discountInfo,
    }
    try{ 
      const r = await checkout(tenant, mobile, payload)
      setResult(r)
      // Refresh cart to reflect checkout (status might change or items might be cleared)
      // Don't clear result here because we just set it above
      await load(false)
    } catch(e:any){ setError(e?.response?.data?.detail || 'Checkout failed') } finally{ setLoading(false) }
  }

  function copy(text:string){ navigator.clipboard?.writeText(text).catch(()=>{}) }

  function startNewOrder() {
    setItems([])
    setResult(null)
    setError(null)
    setCart(null)
    setPhone('')
    setLoadQuery('')
  }

  // Redesigned Card for better visual appeal
  return (
    <Box sx={{ p:2, maxWidth: 1400, mx: 'auto' }}>
      {result && (
        <Alert severity="success" icon={false} sx={{ mb: 2 }} onClose={() => setResult(null)}>
          <Typography variant="subtitle1" fontWeight="bold">Order Placed Successfully!</Typography>
          <Typography variant="body2">Order ID: <b>{result.order_id}</b></Typography>
          {result.payment_url && (
            <Stack direction="row" alignItems="center" spacing={1} sx={{ mt: 1 }}>
              <Button variant="contained" size="small" href={result.payment_url} target="_blank" rel="noreferrer">Pay Now</Button>
              <Button variant="outlined" size="small" onClick={() => copy(result.payment_url!)} startIcon={<ContentCopyIcon sx={{ fontSize: 14 }} />}>Copy payment link</Button>
            </Stack>
          )}
        </Alert>
      )}

      <Stack direction={{ xs:'column', md:'row' }} spacing={2} alignItems="center" justifyContent="space-between" sx={{ mb:3 }}>
        <Box>
          <Typography variant="h4" fontWeight="bold">Store — Cart & Checkout</Typography>
          <Typography variant="body2" color="text.secondary">Manage customer shopping carts and process orders</Typography>
        </Box>
        <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap">
          <Button variant="outlined" onClick={startNewOrder}>Add new order</Button>
          <Card sx={{ minWidth: 320 }}>
          <CardContent sx={{ py: '12px !important' }}>
            <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap" useFlexGap>
              <TextField 
                size="small" 
                required
                label="Customer phone or Order number" 
                value={loadQuery} 
                onChange={e => { const v = e.target.value; setLoadQuery(v); if (!isOrderId(v)) setPhone(v) }} 
                placeholder="Phone or e.g. ORD-XXXX"
                sx={{ minWidth: 220 }}
                error={!!(items.length > 0 && !(phone || '').trim())}
                helperText={items.length > 0 && !(phone || '').trim() ? 'Enter customer phone' : undefined}
              />
              <Button variant="contained" onClick={() => load(true)} disabled={!tenant || loading || !loadQuery?.trim()}>Load</Button>
            </Stack>
            <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 0.5 }}>Customer mobile is required to create/save cart. Load last order by phone, or by order number (e.g. ORD-XXXX).</Typography>
          </CardContent>
        </Card>
        </Stack>
      </Stack>

      {error && <Alert severity="error" sx={{ mb:3 }}>{error}</Alert>}

      <Grid container spacing={3}>
        <Grid item xs={12} lg={9}>
          <Card sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
            <CardContent sx={{ flex: 1 }}>
              <Stack direction="row" alignItems="center" justifyContent="space-between" sx={{ mb:2 }} flexWrap="wrap" gap={1}>
                <Typography variant="h6">Cart Items</Typography>
                <Stack direction="row" spacing={1}>
                  <Button variant="contained" size="small" startIcon={<AddIcon/>} onClick={addRow} disabled={!tenant || !phone}>Add Item</Button>
                  <Button variant="outlined" size="small" onClick={addManualEntryRow} disabled={!tenant || !phone}>Add manual entry</Button>
                </Stack>
              </Stack>
                              <Alert severity="info" sx={{ mb: 2 }} variant="outlined">
                                <Typography variant="body2">When you add an offer product, you can choose to continue with the offer or use the product final price. Use the toggle per product to turn the offer on or off.</Typography>
                              </Alert>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>Product / SKU</TableCell>
                    <TableCell width={120}>Qty</TableCell>
                    <TableCell width={120}>Unit</TableCell>
                    <TableCell width={140}>Selling price</TableCell>
                    <TableCell width={140}>Total Price</TableCell>
                    <TableCell width={64}></TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {items.map((it,idx)=> {
                    const cached = productCache[String(it.sku || '').trim()]
                    const units = (() => {
                      const u: string[] = []
                      if (it.unit && !u.includes(it.unit)) u.push(it.unit)
                      if (cached) {
                        if (cached.unit && !u.includes(cached.unit)) u.push(cached.unit)
                        if ((cached as any).unit_conversions) {
                          (cached as any).unit_conversions.forEach((uc: any) => {
                            if (uc.unit && uc.unit !== cached.unit && !u.includes(uc.unit)) u.push(uc.unit)
                          })
                        }
                      }
                      return u
                    })()

                    return (
                      <TableRow key={idx}>
                        <TableCell>
                          <Autocomplete
                            size="small"
                            freeSolo
                            options={skuOpts[idx] || []}
                            loading={skuLoadingIdx===idx}
                            getOptionLabel={(opt)=> {
                              if(!opt) return ''
                              if(typeof opt === 'string') return opt
                              const p = opt as Product
                              const attrs = p.attributes && Object.keys(p.attributes||{}).length ? ` (${Object.entries(p.attributes||{}).map(([k,v])=>`${k}: ${v}`).join(', ')})` : ''
                              return `${p.sku || ''} — ${p.name || ''}${attrs}`
                            }}
                            isOptionEqualToValue={(option, value) => {
                              if (!option || !value) return false
                              if (typeof value === 'string') return option.sku === value
                              return option.sku === value.sku
                            }}
                            filterOptions={(x)=>x} // server-side filtering
                            value={null as any}
                            inputValue={it.sku || ''}
                            onInputChange={(_, val)=>{
                              const trimmed = String(val || '').trim()
                              if (!trimmed) {
                                setItems(prev => prev.map((item, i) => i === idx ? { ...item, sku: val || '', price_snapshot: 0, name: undefined } : item))
                              } else {
                                updateRow(idx, { sku: val })
                              }
                              searchSkuOptions(idx, val)
                            }}
                            onChange={async (_, val)=>{
                              const p = val as unknown as Product | null
                              if(!p || !(p as any).sku) return
                              const sku = (p as any).sku as string
                              setProductCache(prev => ({ ...prev, [sku]: p }))
                              // If same product already in cart, increase its qty instead of adding a new row
                              const existingIdx = items.findIndex((it, i) => i !== idx && (it.sku || '').trim() === sku)
                              if (existingIdx !== -1) {
                                const addQty = Number(items[idx]?.qty) || 1
                                setItems(prev => {
                                  const next = prev.map((it, i) =>
                                    i === existingIdx ? { ...it, qty: (Number(it.qty) || 1) + addQty } : it
                                  )
                                  const withoutCurrent = next.filter((_, i) => i !== idx)
                                  return withoutCurrent
                                })
                                return
                              }
                              const base = getBaseSellingPrice(p)
                              const hasOffer = hasOfferForSku(sku)
                              if (hasOffer) {
                                const applyOffer = await showConfirm({
                                  title: 'Offer applied against this product',
                                  message: 'Do you want to continue with the offer? Yes = continue with offer. No = use final selling price from product.',
                                  confirmLabel: 'Yes',
                                  cancelLabel: 'No',
                                })
                                const price = applyOffer ? offerPriceForSku(base, sku) : base
                                setItems(prev => prev.map((item, i) =>
                                  i === idx
                                    ? { ...item, sku, price_snapshot: Number(price), unit: p.unit ?? undefined, name: p.name ?? undefined, apply_offer: applyOffer }
                                    : item
                                ))
                              } else {
                                setItems(prev => prev.map((item, i) =>
                                  i === idx
                                    ? { ...item, sku, price_snapshot: Number(base), unit: p.unit ?? undefined, name: p.name ?? undefined }
                                    : item
                                ))
                              }
                            }}
                            renderInput={(params)=> (
                              <TextField
                                {...params}
                                placeholder="Product / SKU"
                                onBlur={(e)=>{ const v = e.target.value; if(v && !it.manual) autofillPriceFromSku(idx, v) }}
                                InputProps={{
                                  ...params.InputProps,
                                  endAdornment: (
                                    <>
                                      {skuLoadingIdx===idx ? <CircularProgress color="inherit" size={16} /> : null}
                                      {params.InputProps.endAdornment}
                                    </>
                                  )
                                }}
                              />
                            )}
                            renderOption={(props, option)=>{
                              const p = option as Product
                              if (!p || !p.sku) return null
                              const { key, ...liProps } = props as any
                              return (
                                <li key={p.sku} {...liProps}>
                                  <Stack direction="row" spacing={1} alignItems="center">
                                    {p.image_url ? <Avatar src={fullUrlForMedia(p.image_url)} sx={{ width:24, height:24 }} /> : <Avatar sx={{ width:24, height:24 }}>{(p.name||p.sku||'?').slice(0,1)}</Avatar>}
                                    <Box>
                                      <Typography variant="body2">{p.name}</Typography>
                                      <Typography variant="caption" color="text.secondary">
                                        {p.sku}
                                        {p.attributes && Object.keys(p.attributes||{}).length ? ` — ${Object.entries(p.attributes||{}).map(([k,v])=>`${k}: ${v}`).join(', ')}` : ''}
                                      </Typography>
                                    </Box>
                                  </Stack>
                                </li>
                              )
                            }}
                          />
                          {cached && (
                            <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 0.5 }}>
                              Base: ₹{cached.price} / {cached.unit}
                              {cached.attributes && Object.keys(cached.attributes).length > 0 && (
                                <> — {Object.entries(cached.attributes).map(([k,v])=> `${k}: ${v}`).join(', ')}</>
                              )}
                            </Typography>
                          )}
                          {it.sku && hasOfferForSku(it.sku) && cached && (() => {
                            const base = getBaseSellingPrice(cached)
                            const offerP = offerPriceForSku(base, it.sku)
                            const applyOffer = (it as CartRow).apply_offer === true
                            return (
                              <Box sx={{ mt: 0.5 }}>
                                <Chip size="small" label="Offer available for this product" color="info" sx={{ mr: 0.5 }} />
                                <Typography variant="body2" sx={{ fontWeight: 500, color: 'text.primary', display: 'block', mt: 0.5 }}>
                                  Selling price ₹{base.toFixed(2)} | With offer ₹{offerP.toFixed(2)}
                                </Typography>
                                <FormControlLabel
                                  control={
                                    <Switch
                                      size="small"
                                      checked={applyOffer}
                                      onChange={(e) => {
                                        const on = e.target.checked
                                        const baseP = getBaseSellingPrice(cached)
                                        const price = on ? offerPriceForSku(baseP, it.sku) : baseP
                                        setItems(prev => prev.map((item, i) =>
                                          i === idx ? { ...item, apply_offer: on, price_snapshot: Number(price) } : item
                                        ))
                                      }}
                                    />
                                  }
                                  label={<Typography variant="body2" sx={{ fontWeight: 500, color: 'text.primary' }}>{applyOffer ? 'Offer on' : 'Offer off (final price)'}</Typography>}
                                  sx={{ ml: 0.5, mt: 0.5 }}
                                />
                              </Box>
                            )
                          })()}
                          {it.manual && (
                            <Chip size="small" label="Manual entry" color="default" sx={{ mt: 0.5 }} />
                          )}
                        </TableCell>
                        <TableCell>
                          <TextField
                            size="small"
                            type="number"
                            inputProps={{ min: 0.001, step: 0.001 }}
                            value={it.qty}
                            onChange={e=>{
                              const n = Math.max(0, Number(e.target.value))
                              updateRow(idx,{ qty: n })
                            }}
                          />
                        </TableCell>
                        <TableCell>
                          <Select
                            size="small"
                            fullWidth
                            value={it.unit || ''}
                            onChange={(e)=>{
                              const newUnit = e.target.value as string
                              updateRow(idx, { unit: newUnit })
                              // If we have the product, recalculate price based on unit factor
                              if (cached) {
                                let newPrice = getBaseSellingPrice(cached)
                                if (newUnit && newUnit !== cached.unit) {
                                  const conv = (cached.unit_conversions || []).find((c: any) => c.unit === newUnit)
                                  if (conv) {
                                    newPrice = newPrice * Number(conv.factor || 1)
                                  } else if (newUnit === 'gram' && cached.unit === 'kg') {
                                    newPrice = newPrice * 0.001
                                  } else if (newUnit === 'kg' && cached.unit === 'gram') {
                                    newPrice = newPrice * 1000
                                  } else if (['pc', 'pcs', 'piece'].includes(newUnit) && cached.unit === 'dozen') {
                                    newPrice = newPrice / 12.0
                                  } else if (newUnit === 'dozen' && ['pc', 'pcs', 'piece'].includes(cached.unit || '')) {
                                    newPrice = newPrice * 12.0
                                  } else if (['pc', 'pcs', 'piece'].includes(newUnit) && cached.unit === 'pack of 6') {
                                    newPrice = newPrice / 6.0
                                  } else if (newUnit === 'pack of 6' && ['pc', 'pcs', 'piece'].includes(cached.unit || '')) {
                                    newPrice = newPrice * 6.0
                                  }
                                }
                                const applyOffer = (it as CartRow).apply_offer
                                if (applyOffer) newPrice = offerPriceForSku(newPrice, it.sku)
                                updateRow(idx, { price_snapshot: newPrice })
                              }
                            }}
                            displayEmpty
                          >
                            <MenuItem value=""><em>Base</em></MenuItem>
                            {units.map(u => <MenuItem key={u} value={u}>{u}</MenuItem>)}
                          </Select>
                        </TableCell>
                        <TableCell>
                          <TextField 
                            size="small" 
                            type="number" 
                            value={it.price_snapshot} 
                            onChange={e=>updateRow(idx,{ price_snapshot: Number(e.target.value) })}
                            helperText={it.unit || ''}
                          />
                        </TableCell>
                        <TableCell>
                          <TextField
                            size="small"
                            type="number"
                            value={(Number(it.qty) * Number(it.price_snapshot)).toFixed(2)}
                            disabled
                          />
                        </TableCell>
                        <TableCell align="right"><IconButton onClick={()=>removeRow(idx)}><DeleteIcon/></IconButton></TableCell>
                      </TableRow>
                    )
                  })}
                  {!items.length && (
                    <TableRow><TableCell colSpan={6}><Typography variant="body2" color="text.secondary">No items</Typography></TableCell></TableRow>
                  )}
                </TableBody>
              </Table>
              <Stack direction="row" justifyContent="flex-end" sx={{ mt:3, pt: 2, borderTop: '1px solid #eee' }}>
                <Box sx={{ textAlign: 'right' }}>
                  <Typography variant="body2" color="text.secondary">Total Items: {items.length}</Typography>
                  <Typography variant="body1">Subtotal: ₹{displaySubtotal.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</Typography>
                </Box>
              </Stack>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} lg={3}>
          <Stack spacing={3}>
            <Card>
              <CardContent>
                <Typography variant="h6" sx={{ mb:2 }}>Checkout Information</Typography>
                <Stack spacing={2.5}>
                  <TextField select size="small" label="Fulfillment Mode" value={mode} onChange={(e)=>{
                    const m = e.target.value as 'delivery'|'pickup'
                    setMode(m)
                    setShowAddress(m === 'delivery')
                  }} fullWidth>
                    <MenuItem value="delivery">Home Delivery</MenuItem>
                    <MenuItem value="pickup">Store Pickup</MenuItem>
                  </TextField>
                  
                  {showAddress && (
                    <Card variant="outlined" sx={{ bgcolor: 'rgba(30, 41, 59, 0.6)', borderColor: '#334155' }}>
                      <CardContent sx={{ p: 2 }}>
                        <Typography variant="subtitle2" sx={{ mb: 1.5, color: '#f1f5f9', fontWeight: 600 }}>Delivery Address</Typography>
                        <Stack spacing={1.5}>
                          <TextField size="small" label="Label (Home/Work)" value={address.label} onChange={e=>setAddress(prev=>({...prev, label:e.target.value}))} fullWidth />
                          <TextField size="small" label="Street Address / Line 1" value={address.line1} onChange={e=>setAddress(prev=>({...prev, line1:e.target.value}))} fullWidth />
                          <Stack direction="row" spacing={1}>
                            <TextField size="small" label="City" value={address.city} onChange={e=>setAddress(prev=>({...prev, city:e.target.value}))} fullWidth />
                            <TextField size="small" label="Pincode" value={address.pincode} onChange={e=>setAddress(prev=>({...prev, pincode:e.target.value}))} fullWidth />
                          </Stack>
                        </Stack>
                      </CardContent>
                    </Card>
                  )}

                  <TextField
                    select
                    size="small"
                    label="Payment Method"
                    value={capabilities.includes('store.payments') ? payMethod : 'COD'}
                    onChange={(e)=>setPayMethod(e.target.value as any)}
                    fullWidth
                  >
                    {capabilities.includes('store.payments') && <MenuItem value="ONLINE">Online Payment</MenuItem>}
                    <MenuItem value="COD">Cash on Delivery (COD)</MenuItem>
                  </TextField>

                  <Divider />
                  <Box>
                    <Typography variant="subtitle2" sx={{ mb: 1 }}>Apply coupon or discount</Typography>
                    <Stack spacing={1.5}>
                      <TextField
                        size="small"
                        label="Coupon code (optional)"
                        value={couponCode}
                        onChange={(e)=>setCouponCode(e.target.value)}
                        fullWidth
                        placeholder="e.g. SAVE10"
                      />
                      <Stack direction="row" spacing={1}>
                        <Select
                          size="small"
                          value={couponType}
                          onChange={(e)=>setCouponType(e.target.value as 'percent' | 'amount' | '')}
                          displayEmpty
                          sx={{ minWidth: 100 }}
                        >
                          <MenuItem value="">None</MenuItem>
                          <MenuItem value="percent">Percent %</MenuItem>
                          <MenuItem value="amount">Amount ₹</MenuItem>
                        </Select>
                        <TextField
                          size="small"
                          type="number"
                          placeholder={couponType === 'percent' ? 'e.g. 10' : 'e.g. 50'}
                          value={couponValue}
                          onChange={(e)=>setCouponValue(e.target.value)}
                          disabled={!couponType}
                          inputProps={{ min: 0, step: couponType === 'percent' ? 1 : 0.01 }}
                          sx={{ flex: 1 }}
                        />
                      </Stack>
                      {couponDiscountAmount > 0 && (
                        <Typography variant="body2" color="success.main">
                          Discount: −₹{couponDiscountAmount.toFixed(2)}
                        </Typography>
                      )}
                    </Stack>
                  </Box>
                  <Box sx={{ py: 1, borderTop: '1px solid', borderColor: 'divider' }}>
                    <Typography variant="body2" color="text.secondary">Subtotal: ₹{displaySubtotal.toFixed(2)}</Typography>
                    {couponDiscountAmount > 0 && (
                      <Typography variant="body2" color="success.main">Discount: −₹{couponDiscountAmount.toFixed(2)}</Typography>
                    )}
                    <Typography variant="h6" fontWeight="bold" sx={{ mt: 0.5 }}>Total: ₹{displayTotal.toFixed(2)}</Typography>
                  </Box>

                  <Divider />
                  
                  <Box>
                    <Typography variant="caption" color="text.secondary" display="block" sx={{ mb: 1 }}>
                      By clicking checkout, an order will be created and inventory will be reserved.
                    </Typography>
                    <Button 
                      variant="contained" 
                      color="primary"
                      fullWidth 
                      size="large"
                      onClick={doCheckout} 
                      disabled={!tenant || !phone || loading || !items.length}
                      sx={{ py: 1.5, fontWeight: 600, color: '#fff' }}
                    >
                      Process Checkout — ₹{displayTotal.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                    </Button>
                  </Box>
                </Stack>
              </CardContent>
            </Card>

          </Stack>
        </Grid>
      </Grid>
    </Box>
  )
}
