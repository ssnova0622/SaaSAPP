import { useEffect, useMemo, useState } from 'react'
import { Box, Button, Card, CardContent, Chip, Dialog, DialogActions, DialogContent, DialogTitle, FormControlLabel, MenuItem, Stack, Table, TableBody, TableCell, TableHead, TableRow, TextField, Typography, Alert, Autocomplete, CircularProgress, Switch } from '@mui/material'
import { listOrders, getOrder, updateOrderStatus, updateOrderItems, Order, type OrderItem } from '@api/store'
import { listProducts, getProductBySku, Product } from '@api/catalog'
import { listOffers, type Offer } from '@api/offers'
import { useEffectiveTenant } from '../../hooks/useEffectiveTenant'
import { useCapabilities } from '../../hooks/useCapabilities'
import { useAlert } from '@contexts/AlertContext'
import { useDebounce } from '../../hooks/useDebounce'
import { useTenantDateFormat } from '../../hooks/useTenantDateFormat'
import { formatPhoneForDisplay } from '../../utils/phone'
import { formatDateForDisplay } from '../../utils/dateFormat'
import ExportMenu from '@components/ExportMenu'

const ALL_STATUSES: Order['status'][] = ['placed','confirmed','picking','ready_for_pickup','out_for_delivery','delivered','canceled']

type EditItem = { sku: string; qty: number; price_snapshot: number; name?: string; manual?: boolean; offer_applied?: boolean; price_before_offer?: number }

export default function OrdersPage(){
  const { effectiveTenant } = useEffectiveTenant()
  const { canEditOrders, canEditSensitiveOrders } = useCapabilities()
  const { showConfirm } = useAlert()
  const dateFormat = useTenantDateFormat()
  const tenant = effectiveTenant
  const [statusFilter,setStatusFilter]=useState<string>('')
  const [searchQuery, setSearchQuery] = useState<string>('')
  const debouncedSearch = useDebounce(searchQuery.trim(), 400)
  const [items,setItems]=useState<Order[]>([])
  const [page,setPage]=useState(1)
  const [size,setSize]=useState(50)
  const [total,setTotal]=useState(0)
  const [loading,setLoading]=useState(false)
  const [detail,setDetail]=useState<Order|null>(null)
  const [statusChange,setStatusChange]=useState<Order['status']>('confirmed')
  const [editOpen, setEditOpen] = useState(false)
  const [editItems, setEditItems] = useState<EditItem[]>([])
  const [productCache, setProductCache] = useState<Record<string, Product>>({})
  const [editError, setEditError] = useState<string|null>(null)
  const [skuOpts, setSkuOpts] = useState<Record<number, Product[]>>({})
  const [skuLoadingIdx, setSkuLoadingIdx] = useState<number|null>(null)
  const [activeOffers, setActiveOffers] = useState<Offer[]>([])

  async function load(){
    if(!tenant) return
    const rid = ++(load as any).__rid || (((load as any).__rid = 1))
    setLoading(true)
    try{
      const res = await listOrders(tenant, { status: statusFilter || undefined, search: debouncedSearch || undefined, page, size })
      if (rid !== (load as any).__rid) return
      setItems(res.items); setTotal(res.total)
    } finally{ if (rid === (load as any).__rid) setLoading(false) }
  }
  useEffect(()=>{ load() // eslint-disable-next-line
  }, [tenant, statusFilter, debouncedSearch, page, size])

  async function openDetail(o: Order){
    if(!tenant) return
    const rid = ++(openDetail as any).__rid || (((openDetail as any).__rid = 1))
    const fresh = await getOrder(tenant, o.id)
    if (rid !== (openDetail as any).__rid) return
    setDetail(fresh)
    setStatusChange(fresh.status)
    setEditOpen(false)
    setEditError(null)
  }

  const statusList = useMemo(()=> ALL_STATUSES, [])

  async function applyStatus(){
    if(!tenant || !detail) return
    const rid = ++(applyStatus as any).__rid || (((applyStatus as any).__rid = 1))
    const updated = await updateOrderStatus(tenant, detail.id, statusChange)
    if (rid !== (applyStatus as any).__rid) return
    setDetail(updated)
    setStatusChange(updated.status)
    await load()
  }

  // Helpers: selling price from product (use final_selling_price from Product page when available)
  function computeUnitPrice(p: Product): number {
    const price = Number(p.price) || 0
    const t = p.discount_type as ('amount'|'percent'|null|undefined)
    const v = Number(p.discount_value || 0)
    if (t === 'amount') return Math.max(0, price - v)
    if (t === 'percent') return Math.max(0, price - (price * (v/100)))
    return price
  }
  function getBaseSellingPrice(p: Product): number {
    if (p.final_selling_price != null && p.final_selling_price !== undefined) return Number(p.final_selling_price)
    return computeUnitPrice(p)
  }

  function hasOfferForSku(sku: string): boolean {
    return !!sku && activeOffers.some((o) => o.product_skus?.includes(sku))
  }

  // Apply active offer discount for a SKU (if any). Per-product choice (like Cart page).
  function priceWithOffer(basePrice: number, sku: string, offers?: Offer[]): number {
    const list = offers ?? activeOffers
    if (!list.length || !sku) return basePrice
    const offer = list.find((o) => o.product_skus?.includes(sku))
    if (!offer?.discount_info) return basePrice
    const t = (offer.discount_info as { type?: string })?.type
    const v = Number((offer.discount_info as { value?: number })?.value ?? 0)
    if (t === 'amount') return Math.max(0, basePrice - v)
    if (t === 'percent') return Math.max(0, basePrice - (basePrice * (v / 100)))
    return basePrice
  }

  function canEditOrder(o?: Order|null): boolean {
    if(!o || !canEditOrders) return false
    const editableStatuses: Order['status'][] = ['placed','confirmed','picking']
    const statusOk = editableStatuses.includes(o.status)
    const onlinePaid = (o.payment?.method === 'ONLINE' && o.payment?.status === 'paid')
    return statusOk && !onlinePaid
  }

  async function startEditItems(){
    if(!detail || !tenant) return
    setSkuOpts({})
    setEditError(null)
    setEditOpen(true)
    try {
      const res = await listOffers(tenant, { active_only: true, page: 1, size: 100 })
      setActiveOffers(res.items || [])
    } catch {
      setActiveOffers([])
    }
    // Preserve existing order item prices (same validation as Cart: per-product offer choice)
    const next: EditItem[] = await Promise.all((detail.items || []).map(async (it) => {
      const row: EditItem = {
        sku: it.sku,
        qty: Number(it.qty) || 1,
        price_snapshot: Number(it.price_snapshot) || 0,
        name: it.name,
        manual: !!it.manual,
        offer_applied: !!(it as OrderItem).offer_applied,
        price_before_offer: (it as OrderItem).price_before_offer,
      }
      if (!it.sku) return row
      try {
        const match = await getProductBySku(tenant, it.sku)
        if (match) setProductCache(prev => ({ ...prev, [it.sku]: match }))
      } catch { /* keep existing row */ }
      return row
    }))
    setEditItems(next)
  }

  function addRow(){ setEditItems(prev=> [...prev, { sku:'', qty:1, price_snapshot:0, manual: false }]) }
  /** Add a row for manual entry when product is not in the catalog (no availability check) */
  function addManualEntryRow(){ setEditItems(prev=> [...prev, { sku:'', qty:1, price_snapshot:0, manual: true }]) }
  function updateRow(idx:number, patch: Partial<EditItem>) { setEditItems(prev=> prev.map((it,i)=> i===idx? { ...it, ...patch }: it)) }
  function removeRow(idx:number){ setEditItems(prev=> prev.filter((_,i)=> i!==idx)) }

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

  async function autofillPriceFromSku(idx: number, sku: string){
    try{
      if(!tenant || !sku) return
      let match = productCache[sku]
      if(!match) {
        match = await getProductBySku(tenant, sku)
        if(match) setProductCache(prev => ({ ...prev, [sku]: match }))
      }
      if (match) {
        const base = getBaseSellingPrice(match)
        const finalPrice = priceWithOffer(base, sku)
        const hadOffer = finalPrice < base && base > 0
        updateRow(idx, {
          price_snapshot: finalPrice,
          name: match.name,
          offer_applied: hadOffer,
          price_before_offer: hadOffer ? base : undefined,
        })
      }
    }catch{ /* ignore */ }
  }

  const editSubtotal = useMemo(()=> editItems.reduce((s,it)=> s + (Number(it.qty)||0) * (Number(it.price_snapshot)||0), 0), [editItems])

  async function saveItems(){
    if(!tenant || !detail) return
    const invalid = editItems.find(it=> !String(it.sku||'').trim() || !(Number(it.qty)||0))
    if(invalid){ setEditError('Each item must have a SKU and quantity > 0'); return }
    const withOffers = editItems.filter(it => it.offer_applied && it.price_before_offer != null)
    const notesParts: string[] = []
    if (withOffers.length) {
      notesParts.push('Offer applied. Order value is after discount.')
      withOffers.forEach(it => {
        const was = Number(it.price_before_offer).toFixed(2)
        const now = Number(it.price_snapshot).toFixed(2)
        notesParts.push(`${it.name || it.sku}: Was ₹${was}, Now ₹${now}`)
      })
      const subtotal = editItems.reduce((s, it) => s + (Number(it.qty) || 0) * (Number(it.price_snapshot) || 0), 0)
      notesParts.push(`Customer pays: ₹${subtotal.toFixed(2)} (after offers).`)
    }
    const notes = notesParts.length ? notesParts.join('\n') : undefined
    const payload = {
      items: editItems.map(it => ({
        sku: it.sku,
        qty: it.qty,
        price_snapshot: it.price_snapshot,
        name: it.name,
        manual: it.manual || undefined,
        offer_applied: it.offer_applied || undefined,
        price_before_offer: it.price_before_offer,
      })),
      notes,
    }
    try{
      const updated = await updateOrderItems(tenant, detail.id, payload)
      setDetail(updated)
      setEditOpen(false)
    }catch(e:any){ setEditError(e?.response?.data?.detail || 'Failed to update items') }
  }

  return (
    <Box sx={{ p:1 }}>
      <Stack direction={{ xs:'column', md:'row' }} spacing={2} alignItems="center" justifyContent="space-between" sx={{ mb:2 }}>
        <Typography variant="h5">Store — Orders</Typography>
        <Stack direction="row" spacing={1}>
          <TextField 
            size="small" 
            label="Search orders..." 
            value={searchQuery} 
            onChange={(e)=>{ setSearchQuery(e.target.value); setPage(1) }} 
            sx={{ minWidth: 250 }} 
            placeholder="ID, Phone, Name..."
          />
          <TextField size="small" select label="Status" value={statusFilter} onChange={(e)=>{ setStatusFilter(e.target.value); setPage(1) }} sx={{ minWidth: 200 }}>
            <MenuItem value="">All Statuses</MenuItem>
            {statusList.map(s=> <MenuItem key={s} value={s}>{s}</MenuItem>)}
          </TextField>
          <ExportMenu
            data={items.map((o) => ({
              id: o.id,
              created_at: o.created_at ? formatDateForDisplay(o.created_at, dateFormat) : '',
              customer_phone: o.customer?.phone ?? '',
              customer_name: o.customer?.name ?? '',
              fulfillment_mode: o.fulfillment_mode,
              item_count: o.items?.length ?? 0,
              total: (o.totals?.grand_total != null ? Number(o.totals.grand_total) : o.totals?.subtotal != null ? Number(o.totals.subtotal) : 0).toFixed(2),
              status: o.status,
              payment: `${o.payment?.method ?? ''}/${o.payment?.status ?? ''}`,
            }))}
            columns={[
              { key: 'id', label: 'Order ID' },
              { key: 'created_at', label: 'Created' },
              { key: 'customer_phone', label: 'Customer Phone' },
              { key: 'customer_name', label: 'Customer Name' },
              { key: 'fulfillment_mode', label: 'Mode' },
              { key: 'item_count', label: 'Items' },
              { key: 'total', label: 'Total' },
              { key: 'status', label: 'Status' },
              { key: 'payment', label: 'Payment' },
            ]}
            filename="orders"
            title="Store Orders"
            disabled={loading}
            size="small"
          />
        </Stack>
      </Stack>

      <Card>
        <CardContent>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Order</TableCell>
                <TableCell>Created</TableCell>
                <TableCell>Customer</TableCell>
                <TableCell>Mode</TableCell>
                <TableCell>Items</TableCell>
                <TableCell>Total</TableCell>
                <TableCell>Status</TableCell>
                <TableCell>Payment</TableCell>
                <TableCell align="right">Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {items.map(o=> (
                <TableRow key={o.id} hover>
                  <TableCell sx={{ fontFamily:'monospace', maxWidth: 180 }} title={o.id}>
                    <Typography variant="body2" noWrap sx={{ fontFamily: 'monospace' }}>{o.id}</Typography>
                  </TableCell>
                  <TableCell>{o.created_at ? formatDateForDisplay(o.created_at, dateFormat) : '-'}</TableCell>
                  <TableCell>{formatPhoneForDisplay(o.customer?.phone) || '-'}</TableCell>
                  <TableCell>{o.fulfillment_mode}</TableCell>
                  <TableCell>{o.items?.length || 0}</TableCell>
                  <TableCell>{(o.totals?.grand_total ?? o.totals?.subtotal) != null ? Number(o.totals?.grand_total ?? o.totals?.subtotal).toFixed(2) : '—'}</TableCell>
                  <TableCell>
                    <Chip size="small" label={o.status} color={o.status==='delivered'?'success':o.status==='canceled'?'default':'primary'} />
                  </TableCell>
                  <TableCell>
                    <Chip size="small" label={`${o.payment?.method}/${o.payment?.status}`} color={o.payment?.status==='paid'?'success':o.payment?.status==='failed'?'default':'warning'} />
                  </TableCell>
                  <TableCell align="right">
                    <Button size="small" onClick={()=>openDetail(o)}>View</Button>
                  </TableCell>
                </TableRow>
              ))}
              {!items.length && (
                <TableRow><TableCell colSpan={9}><Typography variant="body2" color="text.secondary">{loading ? 'Loading...' : 'No orders'}</Typography></TableCell></TableRow>
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      <Dialog open={!!detail} onClose={()=>setDetail(null)} maxWidth="md" fullWidth>
        <DialogTitle>Order {detail?.id}</DialogTitle>
        <DialogContent dividers>
          {detail && (
            <Stack spacing={2}>
              <Typography variant="subtitle2">Customer: {formatPhoneForDisplay(detail.customer?.phone) || '-'}</Typography>
              <Typography variant="subtitle2">Mode: {detail.fulfillment_mode}</Typography>
              {/* Edit guard notice for ONLINE paid orders */}
              {detail.payment?.method==='ONLINE' && detail.payment?.status==='paid' && (
                <Alert severity='info'>
                  This order was paid online. Editing items is disabled to preserve transaction integrity.
                  <br/>
                  A Refund option will be available when payment provider integration is added.
                </Alert>
              )}
              {detail.address && (
                <Typography variant="body2">Address: {detail.address.line1}, {detail.address.city} {detail.address.pincode}</Typography>
              )}
              <Typography variant="subtitle2">Items</Typography>
              {!editOpen ? (
                  <Table size="small">
                    <TableHead><TableRow><TableCell>SKU / Name</TableCell><TableCell>Qty</TableCell><TableCell>Unit</TableCell><TableCell>Selling price</TableCell><TableCell>Total Price</TableCell></TableRow></TableHead>
                    <TableBody>
                      {detail.items.map((it,idx)=> (
                        <TableRow key={idx}>
                          <TableCell>
                            <Typography variant="body2">{it.sku}{it.manual ? ' [MANUAL]' : ''}</Typography>
                            {it.name && <Typography variant="caption" color="text.secondary" display="block">{it.name}</Typography>}
                            {it.offer_applied && (
                              <Chip size="small" label="Offer applied" color="success" sx={{ mt: 0.5 }} />
                            )}
                          </TableCell>
                          <TableCell>{it.qty}</TableCell>
                          <TableCell>{it.unit || '—'}</TableCell>
                          <TableCell>₹{Number(it.price_snapshot).toFixed(2)}</TableCell>
                          <TableCell>₹{(Number(it.qty) * Number(it.price_snapshot)).toFixed(2)}</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
              ) : (
                <>
                  {editError && <Alert severity='error'>{editError}</Alert>}
                  <Stack direction="row" alignItems="center" justifyContent="space-between" sx={{ mb:1 }} flexWrap="wrap" gap={1}>
                    <Typography variant="subtitle2">Edit Items</Typography>
                    <Stack direction="row" spacing={1}>
                      <Button size="small" onClick={addRow}>Add</Button>
                      <Button size="small" variant="outlined" onClick={addManualEntryRow}>Add manual entry</Button>
                    </Stack>
                  </Stack>
                  <Table size="small">
                    <TableHead>
                      <TableRow>
                        <TableCell>SKU / Name</TableCell>
                        <TableCell width={100}>Qty</TableCell>
                        <TableCell width={120}>Selling price</TableCell>
                        <TableCell width={120}>Total Price</TableCell>
                        <TableCell width={60}></TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {editItems.map((it,idx)=> (
                        <TableRow key={idx}>
                          <TableCell>
                            <Autocomplete
                              size="small"
                              freeSolo
                              options={skuOpts[idx] || []}
                              loading={skuLoadingIdx===idx}
                              getOptionLabel={(opt)=>{
                                if(typeof opt === 'string') return opt
                                const p = opt as Product
                                const attrs = p.attributes && Object.keys(p.attributes||{}).length ? ` (${Object.entries(p.attributes||{}).map(([k,v])=>`${k}: ${v}`).join(', ')})` : ''
                                return `${p.sku} — ${p.name}${attrs}`
                              }}
                              filterOptions={(x)=>x}
                              value={null as any}
                              inputValue={it.sku || ''}
                              onInputChange={(_, val)=>{ updateRow(idx, { sku: val }); searchSkuOptions(idx, val) }}
                              onChange={async (_, val)=>{
                                const p = val as unknown as Product | null
                                if(p && (p as any).sku){
                                  setProductCache(prev => ({ ...prev, [p.sku]: p }))
                                  const base = getBaseSellingPrice(p)
                                  const hasOffer = hasOfferForSku(p.sku)
                                  if (hasOffer) {
                                    const applyOffer = await showConfirm({
                                      title: 'Offer applied against this product',
                                      message: 'Do you want to continue with the offer? Yes = continue with offer. No = use final selling price from product.',
                                      confirmLabel: 'Yes',
                                      cancelLabel: 'No',
                                    })
                                    const price = applyOffer ? priceWithOffer(base, p.sku) : base
                                    updateRow(idx, {
                                      sku: p.sku,
                                      price_snapshot: price,
                                      name: p.name,
                                      offer_applied: applyOffer,
                                      price_before_offer: applyOffer ? base : undefined,
                                    })
                                  } else {
                                    updateRow(idx, { sku: p.sku, price_snapshot: base, name: p.name, offer_applied: false, price_before_offer: undefined })
                                  }
                                }
                              }}
                              renderInput={(params)=> (
                                <TextField
                                  {...params}
                                  placeholder="Product / SKU"
                                  onBlur={(e)=>{ const v = e.target.value; if(v && !it.manual) autofillPriceFromSku(idx, v) }}
                                  InputProps={{
                                    ...params.InputProps,
                                    endAdornment: (<>{skuLoadingIdx===idx ? <CircularProgress color="inherit" size={16} /> : null}{params.InputProps.endAdornment}</>)
                                  }}
                                />
                              )}
                            />
                            {it.offer_applied && (
                              <Chip size="small" label="Offer applied" color="success" sx={{ mt: 0.5 }} />
                            )}
                            {it.sku && hasOfferForSku(it.sku) && productCache[it.sku] && (() => {
                              const cached = productCache[it.sku]
                              const base = getBaseSellingPrice(cached)
                              const offerP = priceWithOffer(base, it.sku)
                              const applyOffer = it.offer_applied === true
                              return (
                                <Box sx={{ mt: 0.5 }}>
                                  <Typography variant="caption" color="text.secondary" sx={{ display: 'block' }}>
                                    Final price: ₹{base.toFixed(2)} | With offer: ₹{offerP.toFixed(2)}
                                  </Typography>
                                  <FormControlLabel
                                    control={
                                      <Switch
                                        size="small"
                                        checked={applyOffer}
                                        onChange={(e) => {
                                          const on = e.target.checked
                                          const price = on ? priceWithOffer(base, it.sku) : base
                                          updateRow(idx, { offer_applied: on, price_snapshot: price, price_before_offer: on ? base : undefined })
                                        }}
                                      />
                                    }
                                    label={<Typography variant="caption" color="text.secondary">{applyOffer ? 'Offer on' : 'Offer off (final price)'}</Typography>}
                                  />
                                </Box>
                              )
                            })()}
                            {productCache[it.sku] && !hasOfferForSku(it.sku) && (
                              <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 0.5 }}>
                                Base: ₹{productCache[it.sku].price} / {productCache[it.sku].unit}
                                {productCache[it.sku].attributes && Object.keys(productCache[it.sku].attributes||{}).length > 0 && (
                                  <> — {Object.entries(productCache[it.sku].attributes||{}).map(([k,v])=> `${k}: ${v}`).join(', ')}</>
                                )}
                              </Typography>
                            )}
                            {it.manual && (
                              <Chip size="small" label="Manual entry" color="default" sx={{ mt: 0.5 }} />
                            )}
                          </TableCell>
                          <TableCell>
                            <TextField size="small" type="number" value={it.qty} onChange={e=> updateRow(idx, { qty: Number(e.target.value)||0 })} inputProps={{ min:0.001, step: 0.001 }} />
                          </TableCell>
                          <TableCell>
                            <TextField 
                              size="small" 
                              type="number" 
                              value={it.price_snapshot} 
                              onChange={e=> updateRow(idx, { price_snapshot: Number(e.target.value)||0 })} 
                              helperText={productCache[it.sku]?.unit || ''}
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
                          <TableCell>
                            <Button size="small" onClick={()=>removeRow(idx)}>Remove</Button>
                          </TableCell>
                        </TableRow>
                      ))}
                      {!editItems.length && (
                        <TableRow><TableCell colSpan={5}><Typography variant='body2' color='text.secondary'>No items. Click Add to insert a new line.</Typography></TableCell></TableRow>
                      )}
                    </TableBody>
                  </Table>
                  <Typography variant="subtitle2">Subtotal: {editSubtotal.toFixed(2)}</Typography>
                </>
              )}
              {/* Totals breakdown: subtotal, store discount (if any), total collected */}
              {detail.totals && (
                <Stack spacing={0.5} sx={{ mt: 0.5 }}>
                  <Typography variant="subtitle2">Subtotal (items): ₹{(Number(detail.totals.subtotal) || 0).toFixed(2)}</Typography>
                  {(Number(detail.totals?.discount) || 0) > 0 && (
                    <Typography variant="body2" color="text.secondary">Store discount (applied by store owner): −₹{Number(detail.totals.discount).toFixed(2)}{detail.discount_info?.code ? ` (${detail.discount_info.code})` : ''}</Typography>
                  )}
                  <Typography variant="subtitle2" fontWeight="bold">Total collected from customer: ₹{(detail.totals?.grand_total != null ? Number(detail.totals.grand_total) : detail.totals?.subtotal != null ? Number(detail.totals.subtotal) : 0).toFixed(2)}</Typography>
                </Stack>
              )}
              {!detail.totals && <Typography variant="subtitle2">Totals: —</Typography>}
              {detail.notes && (
                <Alert severity="info" sx={{ mt: 1 }}>
                  <Typography variant="subtitle2" gutterBottom>Order summary / notes</Typography>
                  <Typography variant="body2" component="pre" sx={{ whiteSpace: 'pre-wrap', fontFamily: 'inherit' }}>{detail.notes}</Typography>
                </Alert>
              )}
              <Typography variant="subtitle2">Payment: {detail.payment?.method} / {detail.payment?.status} {detail.payment?.intent_id ? `(intent ${detail.payment.intent_id})` : ''}</Typography>
              <Stack direction="row" spacing={2} alignItems="center">
                {canEditOrders && (
                  <>
                    <TextField select size="small" label="Status" value={statusChange} onChange={(e)=>setStatusChange(e.target.value as Order['status'])}>
                      {ALL_STATUSES.map(s=> <MenuItem key={s} value={s}>{s}</MenuItem>)}
                    </TextField>
                    <Button variant="contained" onClick={applyStatus}>Apply</Button>
                  </>
                )}
                {canEditOrder(detail) && !editOpen && (
                  <Button variant="outlined" onClick={startEditItems}>Edit items</Button>
                )}
                {canEditSensitiveOrders && !canEditOrder(detail) && detail.payment?.method==='ONLINE' && detail.payment?.status==='paid' && (
                  <Button variant="outlined" disabled title="Coming soon: Refund via provider">Refund</Button>
                )}
                {editOpen && (
                  <>
                    <Button variant="outlined" color='inherit' onClick={()=>{ setEditOpen(false); setEditError(null) }}>Cancel edit</Button>
                    <Button variant="contained" onClick={saveItems}>Save items</Button>
                  </>
                )}
              </Stack>
            </Stack>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={()=>setDetail(null)}>Close</Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}
