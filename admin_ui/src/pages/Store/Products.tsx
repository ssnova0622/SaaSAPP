import { useEffect, useMemo, useState } from 'react'
import { Alert, Box, Button, Card, CardContent, Chip, Dialog, DialogActions, DialogContent, DialogTitle, IconButton, MenuItem, Stack, Table, TableBody, TableCell, TableHead, TableRow, TextField, Typography, Avatar, Tooltip, Tabs, Tab, Divider, Grid } from '@mui/material'
import DeleteIcon from '@mui/icons-material/Delete'
import EditIcon from '@mui/icons-material/Edit'
import SaveIcon from '@mui/icons-material/Save'
import AddIcon from '@mui/icons-material/Add'
import ContentCopyIcon from '@mui/icons-material/ContentCopy'
import { listCategories, listProducts, upsertProduct, updateProduct, deleteProduct, getInventory, setInventory, Product, Category, getProductBySku } from '@api/catalog'
import { uploadProductMedia, fullUrlForMedia } from '@api/upload'
import { useDebounce } from '../../hooks/useDebounce'
import { getLowStockForecast, LowStockItem } from '@api/ai'
import { getTenantSettings, TenantSettings } from '@api/tenants'
import { useEffectiveTenant } from '../../hooks/useEffectiveTenant'
import { useAlert } from '@contexts/AlertContext'

type ProductForm = {
  sku: string
  name: string
  category?: string
  price: number
  mrp?: number
  tax?: number
  unit?: string
  active: boolean
  image_url?: string
  discount_type?: '' | 'amount' | 'percent'
  discount_value?: number
  /** Minimum selling price (MSP); alerts if selling price goes below this */
  minimum_selling_price?: number | null
  /** Final selling price (Selling − Discount + VAT), sent on save */
  final_selling_price?: number | null
  margin_type?: '' | 'percent' | 'amount'
  margin_value?: number | null
  stock_qty?: number
  variants?: VariantForm[]
  barcode?: string
  unit_conversions?: { unit: string, factor: number }[]
}

type VariantForm = {
  variant_sku: string
  // Common attributes helpers (mapped into attributes record)
  color?: string
  size?: string
  // Full attributes map (we synthesize from color/size on save)
  attributes?: Record<string, string>
  price?: number
  mrp?: number
  tax?: number
  discount_type?: '' | 'amount' | 'percent'
  discount_value?: number
  image_url?: string
  active?: boolean
}

export default function ProductsPage(){
  const { effectiveTenant: tenant, isSuper } = useEffectiveTenant()
  const { showConfirm } = useAlert()
  const [items, setItems] = useState<Product[]>([])
  const [categories, setCategories] = useState<Category[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string|null>(null)
  const [search, setSearch] = useState('')
  const debouncedSearch = useDebounce(search.trim(), 300)
  const [catFilter, setCatFilter] = useState<string>('')
  const [activeFilter, setActiveFilter] = useState<'all'|'active'|'inactive'>('all')
  const [page, setPage] = useState(1)
  const [size, setSize] = useState(50)
  // AI low-stock panel state
  const [aiEnabled, setAiEnabled] = useState<boolean>(false)
  const [lsLoading, setLsLoading] = useState<boolean>(false)
  const [lsError, setLsError] = useState<string|null>(null)
  const [lowStock, setLowStock] = useState<LowStockItem[]>([])

  // Dialog state
  const [open, setOpen] = useState(false)
  const [form, setForm] = useState<ProductForm>({ sku:'', name:'', price:0, unit:'', category:'', mrp: undefined, tax: undefined, active: true, image_url: '', discount_type: '', discount_value: undefined, minimum_selling_price: undefined, final_selling_price: undefined, margin_type: '', margin_value: undefined, stock_qty: undefined, variants: [], barcode: '', unit_conversions: [] })
  const [editMode, setEditMode] = useState(false)
  // Dialog-local error (so validation shows inside the dialog, not the main screen)
  const [dialogError, setDialogError] = useState<string|null>(null)
  const [activeTab, setActiveTab] = useState(0)

  // Inline stock editing
  const [stockSku, setStockSku] = useState<string>('')
  const [stockQty, setStockQty] = useState<string>('')
  const [savingStock, setSavingStock] = useState(false)
  // Variant available qty map
  const [variantAvail, setVariantAvail] = useState<Record<string, number>>({})

  async function loadCategories(){
    if(!tenant) return
    const rid = ++(loadCategories as any).__rid || (((loadCategories as any).__rid = 1))
    try{ 
      const list = await listCategories(tenant); 
      if (rid !== (loadCategories as any).__rid) return
      setCategories(list) 
    } catch {}
  }

  async function load(){
    if(!tenant) return
    const rid = ++(load as any).__rid || (((load as any).__rid = 1))
    setLoading(true); setError(null)
    try{
      const res = await listProducts(tenant, { search: debouncedSearch || undefined, category: (catFilter||undefined), active: activeFilter==='all' ? undefined : activeFilter==='active', page, size })
      if (rid !== (load as any).__rid) return
      setItems(res.items)
    }catch(e:any){ if (rid === (load as any).__rid) setError(e?.response?.data?.detail || 'Failed to load products') }
    finally{ if (rid === (load as any).__rid) setLoading(false) }
  }

  useEffect(()=>{ loadCategories() // eslint-disable-next-line
  },[tenant])
  useEffect(()=>{ load() // eslint-disable-next-line
  },[tenant, catFilter, activeFilter, page, size, debouncedSearch])

  // Load tenant AI feature flags
  useEffect(()=>{
    (async () => {
      if(!tenant){ setAiEnabled(false); return }
      try{
        const s: TenantSettings = await getTenantSettings(tenant)
        const on = !!(s as any)?.ai?.low_stock
        setAiEnabled(on)
      }catch{ setAiEnabled(false) }
    })()
  }, [tenant])

  // Fetch low-stock forecast when enabled
  useEffect(()=>{
    (async () => {
      if(!tenant || !aiEnabled){ setLowStock([]); return }
      setLsLoading(true); setLsError(null)
      try{
        const res = await getLowStockForecast(tenant, { days: 30, lead_time: 3, safety_days: 2, top: 20 })
        setLowStock(res.items || [])
      }catch(e:any){ setLsError(e?.response?.data?.detail || 'Failed to load low-stock forecast'); setLowStock([]) }
      finally{ setLsLoading(false) }
    })()
  }, [tenant, aiEnabled])

  function startCreate(){
    setEditMode(false)
    setForm({ sku:'', name:'', price:0, unit:'', category:'', mrp: undefined, tax: undefined, active: true, image_url:'', discount_type:'', discount_value: undefined, minimum_selling_price: undefined, final_selling_price: undefined, margin_type: '', margin_value: undefined, stock_qty: undefined, variants: [], barcode: '', unit_conversions: [] })
    setDialogError(null)
    setActiveTab(0)
    setOpen(true)
  }
  function startEdit(p: Product){
    setEditMode(true)
    setDialogError(null)
    setActiveTab(0)
    setOpen(true)
    if (!tenant) return
    getProductBySku(tenant, p.sku).then((full) => {
      const doc = full || p
      const vforms: VariantForm[] = (doc.variants||[]).map(v=>({
        variant_sku: v.variant_sku,
        color: v.attributes?.color,
        size: v.attributes?.size,
        attributes: v.attributes || {},
        price: v.price ?? undefined,
        mrp: v.mrp ?? undefined,
        tax: v.tax ?? undefined,
        discount_type: (v.discount_type as any) || '',
        discount_value: v.discount_value ?? undefined,
        image_url: v.image_url || undefined,
        active: v.active ?? true,
      }))
      setForm({
        sku: doc.sku,
        name: doc.name,
        price: doc.price,
        unit: doc.unit || '',
        category: doc.category || '',
        mrp: (doc as any).mrp ?? undefined,
        tax: doc.tax ?? undefined,
        active: !!doc.active,
        image_url: doc.image_url || '',
        discount_type: (doc.discount_type as any) || '',
        discount_value: doc.discount_value ?? undefined,
        minimum_selling_price: (doc as any).minimum_selling_price ?? (doc as any).final_price ?? undefined,
        final_selling_price: (doc as any).final_selling_price ?? undefined,
        margin_type: ((doc as any).margin_type as string) || '',
        margin_value: (doc as any).margin_value ?? undefined,
        stock_qty: undefined,
        variants: vforms,
        barcode: doc.barcode || '',
        unit_conversions: (doc as any).unit_conversions || [],
      })
      getInventory(tenant, doc.sku).then(inv=> setForm(prev=>({...prev, stock_qty: inv?.available_qty ?? 0}))).catch(()=>{})
      const variants = doc.variants || []
      if (variants.length) {
        Promise.all(variants.map(async (v)=>{
          const vs = v.variant_sku
          try { const inv = await getInventory(tenant, vs); return { sku: vs, available_qty: inv?.available_qty ?? 0 } } catch { return { sku: vs, available_qty: 0 } }
        })).then(list=>{
          const m: Record<string, number> = {}
          list.forEach(x=>{ m[x.sku] = Number(x.available_qty||0) })
          setVariantAvail(m)
        })
      }
    }).catch(() => {
      const vforms: VariantForm[] = (p.variants||[]).map(v=>({
        variant_sku: v.variant_sku,
        color: v.attributes?.color,
        size: v.attributes?.size,
        attributes: v.attributes || {},
        price: v.price ?? undefined,
        mrp: v.mrp ?? undefined,
        tax: v.tax ?? undefined,
        discount_type: (v.discount_type as any) || '',
        discount_value: v.discount_value ?? undefined,
        image_url: v.image_url || undefined,
        active: v.active ?? true,
      }))
      setForm({
        sku: p.sku, name: p.name, price: p.price, unit: p.unit || '', category: p.category || '',
        mrp: p.mrp || undefined, tax: p.tax || undefined, active: !!p.active,
        image_url: p.image_url || '', discount_type: (p.discount_type as any) || '',
        discount_value: p.discount_value ?? undefined,
        minimum_selling_price: (p as any).minimum_selling_price ?? (p as any).final_price ?? undefined,
        final_selling_price: (p as any).final_selling_price ?? undefined,
        margin_type: ((p as any).margin_type as string) || '',
        margin_value: (p as any).margin_value ?? undefined,
        stock_qty: undefined,
        variants: vforms, barcode: p.barcode || '',
        unit_conversions: (p as any).unit_conversions || [],
      })
    })
  }

  async function save(){
    if(!tenant) return
    if(!form.sku.trim() || !form.name.trim()) { 
      setDialogError('SKU and Name are required'); 
      setActiveTab(0);
      return 
    }
    // Validate variants (client-side)
    const hasVariants = !!(form.variants && form.variants.length)
    if(hasVariants){
      const seen = new Set<string>()
      for(const v of (form.variants||[])){
        const vs = (v.variant_sku||'').trim()
        if(!vs){ 
          setDialogError('Variant SKU is required for all variants'); 
          setActiveTab(2);
          return 
        }
        if(vs === form.sku.trim()){ 
          setDialogError('Variant SKU cannot be same as base SKU'); 
          setActiveTab(2);
          return 
        }
        if(seen.has(vs)){ 
          setDialogError(`Duplicate variant SKU '${vs}'`); 
          setActiveTab(2);
          return 
        }
        seen.add(vs)
        const attrCount = ((v.color?1:0) + (v.size?1:0)) || Object.keys(v.attributes||{}).length
        if(attrCount === 0){ 
          setDialogError(`Variant '${vs}' must have at least one attribute (e.g., color or size)`); 
          setActiveTab(2);
          return 
        }
      }
    }
    // Final Price (Selling Price after discount) must be >= Minimum Selling Price (MSP)
    const costPrice = Number(form.price) || 0
    const sellingPriceBase = Number(form.mrp ?? form.price) || 0
    const discT = form.discount_type
    const discV = Number(form.discount_value || 0)
    let finalSellingPrice = sellingPriceBase
    if (discT === 'amount') finalSellingPrice = Math.max(0, sellingPriceBase - discV)
    else if (discT === 'percent') finalSellingPrice = Math.max(0, sellingPriceBase - (sellingPriceBase * (discV / 100)))
    // MSP: when margin set = Cost + margin (markup); when None = Selling Price
    let effectiveMSP: number
    if (form.margin_type === 'percent' && form.margin_value != null) {
      const mv = Number(form.margin_value)
      effectiveMSP = costPrice + (costPrice * mv / 100)
    } else if (form.margin_type === 'amount' && form.margin_value != null) {
      effectiveMSP = costPrice + Number(form.margin_value)
    } else {
      effectiveMSP = sellingPriceBase
    }
    effectiveMSP = Math.max(0, effectiveMSP)
    if (finalSellingPrice < effectiveMSP - 0.01) {
      setDialogError('Final Price (Selling Price) should not be less than Minimum Selling Price')
      setActiveTab(1)
      return
    }
    setLoading(true); setError(null); setDialogError(null)
    try{
      // If creating a new product, prevent duplicate SKU
      if(!editMode){
        try{
          const existing = await getProductBySku(tenant, form.sku.trim())
          if(existing && existing.sku){
            setDialogError(`A product with SKU '${form.sku.trim()}' already exists`)
            setActiveTab(0)
            setLoading(false)
            return
          }
        }catch(err:any){
          // 404 means not found; proceed
        }
      }
      // Build variants payload
      const variantsPayload = (form.variants||[]).map(v=>{
        const attrs: Record<string,string> = { ...(v.attributes||{}) }
        if(v.color){ attrs['color'] = v.color }
        if(v.size){ attrs['size'] = v.size }
        // Remove empty string attributes
        Object.keys(attrs).forEach(k=>{ if(String(attrs[k]||'').trim()===''){ delete attrs[k] } })
        return {
          variant_sku: v.variant_sku.trim(),
          attributes: attrs,
          price: v.price!=null ? Number(v.price) : undefined,
          mrp: v.mrp!=null ? Number(v.mrp) : undefined,
          tax: v.tax!=null ? Number(v.tax) : undefined,
          discount_type: v.discount_type ? (v.discount_type as any) : undefined,
          discount_value: v.discount_value!=null ? Number(v.discount_value) : undefined,
          image_url: (v.image_url||'') || undefined,
          active: v.active!=null ? !!v.active : true,
        }
      })
      const cost = Number(form.price) || 0
      const selling = Number(form.mrp ?? form.price) || 0
      let msp = selling
      if (form.margin_type === 'percent' && form.margin_value != null) msp = cost + (cost * Number(form.margin_value) / 100)
      else if (form.margin_type === 'amount' && form.margin_value != null) msp = cost + Number(form.margin_value)
      const minimum_selling_price = Math.max(0, msp)
      let afterDiscount = selling
      if (form.discount_type === 'amount' && form.discount_value != null) afterDiscount = Math.max(0, selling - Number(form.discount_value))
      else if (form.discount_type === 'percent' && form.discount_value != null) afterDiscount = Math.max(0, selling - (selling * Number(form.discount_value) / 100))
      const taxPct = Number(form.tax) || 0
      const final_selling_price = Math.round(afterDiscount * (1 + taxPct / 100) * 100) / 100
      if(!editMode){
        await upsertProduct(tenant, {
          sku: form.sku.trim(), name: form.name.trim(), category: form.category || undefined,
          price: Number(form.price)||0, mrp: form.mrp!=null? Number(form.mrp): undefined,
          tax: form.tax!=null? Number(form.tax): undefined, unit: form.unit || undefined, active: form.active,
          image_url: (form.image_url||'') || undefined,
          discount_type: form.discount_type ? (form.discount_type as any) : undefined,
          discount_value: form.discount_value!=null ? Number(form.discount_value) : undefined,
          minimum_selling_price,
          final_selling_price,
          margin_type: form.margin_type ? (form.margin_type as any) : undefined,
          margin_value: form.margin_value != null ? Number(form.margin_value) : undefined,
          barcode: (form.barcode||'') || undefined,
          variants: variantsPayload,
          unit_conversions: (form.unit_conversions || []).filter(uc => uc.unit.trim() !== ''),
        })
      }else{
        await updateProduct(tenant, form.sku.trim(), {
          sku: form.sku.trim(), name: form.name.trim(), category: form.category || undefined,
          price: Number(form.price)||0, mrp: form.mrp!=null? Number(form.mrp): undefined,
          tax: form.tax!=null? Number(form.tax): undefined, unit: form.unit || undefined, active: form.active,
          image_url: (form.image_url||'') || undefined,
          discount_type: form.discount_type ? (form.discount_type as any) : undefined,
          discount_value: form.discount_value!=null ? Number(form.discount_value) : undefined,
          minimum_selling_price,
          final_selling_price,
          margin_type: form.margin_type ? (form.margin_type as any) : undefined,
          margin_value: form.margin_value != null ? Number(form.margin_value) : undefined,
          barcode: (form.barcode||'') || undefined,
          variants: variantsPayload,
          unit_conversions: (form.unit_conversions || []).filter(uc => uc.unit.trim() !== ''),
        })
      }
      // Set inventory if provided
      // If variants exist, set inventory for each variant too if it was modified in variantAvail
      if(hasVariants){
        for(const v of (form.variants||[])){
          const vs = v.variant_sku.trim()
          if(vs && variantAvail[vs] != null){
            try{ await setInventory(tenant, vs, Number(variantAvail[vs])||0) } catch{}
          }
        }
      } else if(form.stock_qty != null && !Number.isNaN(Number(form.stock_qty))){
        await setInventory(tenant, form.sku.trim(), Number(form.stock_qty)||0)
      }
      setOpen(false)
      await load()
    }catch(e:any){ setDialogError(e?.response?.data?.detail || 'Save failed') }
    finally{ setLoading(false) }
  }

  async function remove(p: Product){
    if(!tenant) return
    const ok = await showConfirm({ title: 'Delete product', message: `Delete product '${p.name}' (${p.sku})?` })
    if(!ok) return
    setLoading(true); setError(null)
    try{ await deleteProduct(tenant, p.sku); await load() } catch(e:any){ setError(e?.response?.data?.detail || 'Delete failed') } finally{ setLoading(false) }
  }

  /** Default image when product has no image_url (48x48 placeholder) */
  const DEFAULT_PRODUCT_IMAGE = 'data:image/svg+xml,' + encodeURIComponent(
    '<svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 48 48"><rect fill="#334155" width="48" height="48"/><text x="50%" y="50%" dominant-baseline="middle" text-anchor="middle" fill="#64748b" font-size="10" font-family="sans-serif">No image</text></svg>'
  )

  async function editStock(p: Product){
    if(!tenant) return
    try{
      const inv = await getInventory(tenant, p.sku)
      setStockSku(p.sku)
      setStockQty(String(inv.available_qty ?? 0))
    }catch{
      setStockSku(p.sku)
      setStockQty('0')
    }
  }

  async function saveStock(){
    if(!tenant || !stockSku) return
    setSavingStock(true)
    try{ await setInventory(tenant, stockSku, Number(stockQty)||0); setStockSku(''); setStockQty('') } finally{ setSavingStock(false) }
  }

  return (
    <Box sx={{ p:1 }}>
      <Stack direction={{ xs:'column', md:'row' }} spacing={2} alignItems="center" justifyContent="space-between" sx={{ mb:2 }}>
        <Typography variant="h5">Store — Products</Typography>
        <Stack direction='row' spacing={1}>
          <TextField size='small' placeholder='Search sku/name' value={search} onChange={e=>{ setSearch(e.target.value); setPage(1) }} sx={{ minWidth: 180 }} />
          <TextField size='small' select label='Category' value={catFilter} onChange={e=>setCatFilter(e.target.value)} sx={{ minWidth: 180 }}>
            <MenuItem value=''>All</MenuItem>
            {categories.map(c=> <MenuItem key={c.name} value={c.name}>{c.name}</MenuItem>)}
          </TextField>
          <TextField size='small' select label='Status' value={activeFilter} onChange={e=>setActiveFilter(e.target.value as any)} sx={{ minWidth: 160 }}>
            <MenuItem value='all'>All</MenuItem>
            <MenuItem value='active'>Active</MenuItem>
            <MenuItem value='inactive'>Inactive</MenuItem>
          </TextField>
          <Button variant='contained' onClick={startCreate} disabled={!tenant}>New Product</Button>
        </Stack>
      </Stack>

      {error && <Alert severity='error' sx={{ mb:2 }}>{error}</Alert>}

      {aiEnabled && (
        <Card sx={{ mb: 2 }}>
          <CardContent>
            <Stack direction="row" alignItems="center" justifyContent="space-between" sx={{ mb: 1 }}>
              <Typography variant="h6">AI — Low‑stock forecast</Typography>
              <Button size="small" onClick={()=>{
                // manual refresh
                if(!tenant) return;
                setLsLoading(true); setLsError(null);
                getLowStockForecast(tenant, { days:30, lead_time:3, safety_days:2, top:20 })
                  .then(res=> setLowStock(res.items||[]))
                  .catch(e=> setLsError(e?.response?.data?.detail || 'Failed to load low-stock forecast'))
                  .finally(()=> setLsLoading(false))
              }}>Refresh</Button>
            </Stack>
            {lsError && <Alert severity='error' sx={{ mb:1 }}>{lsError}</Alert>}
            <Table size='small'>
              <TableHead>
                <TableRow>
                  <TableCell>SKU</TableCell>
                  <TableCell>Name</TableCell>
                  <TableCell align='right'>Avail</TableCell>
                  <TableCell align='right'>Daily</TableCell>
                  <TableCell align='right'>Days to SO</TableCell>
                  <TableCell align='right'>Reorder Qty</TableCell>
                  <TableCell align='right'>Action</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {lsLoading && (
                  <TableRow><TableCell colSpan={7}><Typography variant='body2' color='text.secondary'>Loading…</Typography></TableCell></TableRow>
                )}
                {!lsLoading && (!lowStock || lowStock.length===0) && (
                  <TableRow><TableCell colSpan={7}><Typography variant='body2' color='text.secondary'>No low‑stock signals yet</Typography></TableCell></TableRow>
                )}
                {!lsLoading && lowStock.map(row => (
                  <TableRow key={row.sku}>
                    <TableCell>{row.sku}</TableCell>
                    <TableCell>{row.name}</TableCell>
                    <TableCell align='right'>{row.available_qty}</TableCell>
                    <TableCell align='right'>{row.daily_demand}</TableCell>
                    <TableCell align='right'>{row.days_to_stockout === 9999 ? '∞' : row.days_to_stockout}</TableCell>
                    <TableCell align='right'>{row.suggested_reorder_qty}</TableCell>
                    <TableCell align='right'>
                      <Button size='small' onClick={()=>{
                        // Prefill edit stock with suggested target (avail + reorder)
                        const target = Math.max(0, Number(row.available_qty||0) + Number(row.suggested_reorder_qty||0))
                        setStockSku(row.sku)
                        setStockQty(String(target))
                      }}>Set Inventory</Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardContent>
          <Table size='small'>
            <TableHead>
              <TableRow>
                <TableCell sx={{ width: 56 }}>Image</TableCell>
                <TableCell>SKU</TableCell>
                <TableCell>Name</TableCell>
                <TableCell>Category</TableCell>
                <TableCell>Price</TableCell>
                <TableCell>Unit</TableCell>
                <TableCell>Status</TableCell>
                <TableCell>Stock</TableCell>
                <TableCell>Staff (C/U)</TableCell>
                <TableCell align='right'>Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {items.map(p=> (
                <TableRow key={p.sku}>
                  <TableCell sx={{ width: 56, verticalAlign: 'middle' }}>
                    <Box
                      component="img"
                      src={p.image_url ? fullUrlForMedia(p.image_url) : DEFAULT_PRODUCT_IMAGE}
                      alt={p.name || p.sku}
                      onError={(e) => { (e.target as HTMLImageElement).src = DEFAULT_PRODUCT_IMAGE }}
                      sx={{ width: 40, height: 40, objectFit: 'cover', borderRadius: 1 }}
                    />
                  </TableCell>
                  <TableCell>{p.sku}</TableCell>
                  <TableCell>{p.name}</TableCell>
                  <TableCell>{p.category || '-'}</TableCell>
                  <TableCell>{p.price?.toFixed ? p.price.toFixed(2) : p.price}</TableCell>
                  <TableCell>{p.unit || '-'}</TableCell>
                  <TableCell>
                    <Chip size='small' label={p.active ? 'Active' : 'Inactive'} color={p.active ? 'success' : 'default'} />
                  </TableCell>
                  <TableCell>
                    {stockSku === p.sku ? (
                      <Stack direction='row' spacing={1} alignItems='center'>
                        <TextField size='small' type='number' value={stockQty} onChange={e=>setStockQty(e.target.value)} sx={{ width: 120 }} />
                        <IconButton size='small' onClick={saveStock} disabled={savingStock}><SaveIcon fontSize='small' /></IconButton>
                      </Stack>
                    ) : (
                      <Button size='small' onClick={()=>editStock(p)}>Edit</Button>
                    )}
                  </TableCell>
                  <TableCell>
                    <Typography variant="caption" display="block" color="text.secondary">
                      C: {p.created_by ?? '-'}
                    </Typography>
                    <Typography variant="caption" display="block" color="text.secondary">
                      U: {p.updated_by ?? '-'}
                    </Typography>
                  </TableCell>
                  <TableCell align='right'>
                    <IconButton size='small' onClick={()=>startEdit(p)}><EditIcon fontSize='small' /></IconButton>
                    <IconButton size='small' onClick={()=>remove(p)}><DeleteIcon fontSize='small' /></IconButton>
                  </TableCell>
                </TableRow>
              ))}
              {!items.length && (
                <TableRow><TableCell colSpan={10}><Typography variant='body2' color='text.secondary'>{loading? 'Loading...' : 'No products'}</Typography></TableCell></TableRow>
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      <Dialog open={open} onClose={()=>setOpen(false)} maxWidth='md' fullWidth>
        <DialogTitle>{editMode ? 'Edit Product' : 'New Product'}</DialogTitle>
        <Tabs value={activeTab} onChange={(_,v)=>setActiveTab(v)} sx={{ borderBottom: 1, borderColor: 'divider', px: 2 }}>
          <Tab label="General" />
          <Tab label="Pricing & Inventory" />
          <Tab label="Variants" />
          <Tab label="Units" />
        </Tabs>
        <DialogContent dividers>
          {dialogError && <Alert severity='error' sx={{ mb: 2 }}>{dialogError}</Alert>}
          
          {activeTab === 0 && (
            <Stack spacing={2.5} sx={{ mt: 1 }}>
              <Typography variant="subtitle2" color="primary">Basic Information</Typography>
              <Grid container spacing={2}>
                <Grid item xs={12} md={6}>
                  <TextField fullWidth size="small" label='Product SKU' value={form.sku} onChange={e=>setForm(prev=>({...prev, sku:e.target.value}))} disabled={editMode} helperText="Unique identifier (e.g. PRD-001)" />
                </Grid>
                <Grid item xs={12} md={6}>
                  <TextField fullWidth size="small" label='Product Name' value={form.name} onChange={e=>setForm(prev=>({...prev, name:e.target.value}))} placeholder="e.g. Men's Cotton T-Shirt" />
                </Grid>
                <Grid item xs={12} md={6}>
                  <TextField fullWidth size="small" select label='Category' value={form.category || ''} onChange={e=>setForm(prev=>({...prev, category:e.target.value||undefined}))}>
                    <MenuItem value=''>None</MenuItem>
                    {categories.map(c=> <MenuItem key={c.name} value={c.name}>{c.name}</MenuItem>)}
                  </TextField>
                </Grid>
                <Grid item xs={12} md={6}>
                  <TextField fullWidth size="small" label='Barcode / EAN' value={form.barcode || ''} onChange={e=>setForm(prev=>({...prev, barcode: e.target.value}))} placeholder="Scan or enter barcode" />
                </Grid>
              </Grid>

              <Divider />
              <Typography variant="subtitle2" color="primary">Product Media & Status</Typography>
              <Grid container spacing={2} alignItems="flex-start">
                <Grid item xs={12} sm={6} md={4}>
                  <Box>
                    <Avatar variant='rounded' src={form.image_url ? fullUrlForMedia(form.image_url) : undefined} sx={{ width: 120, height: 120, border: '1px solid', borderColor: 'divider' }}>{(form.name||'').slice(0,1)}</Avatar>
                    <Button component='label' variant='outlined' size='small' sx={{ mt: 1, width: '100%' }} disabled={!tenant}>
                      Upload
                      <input type='file' accept='image/*' hidden onChange={async (e)=>{
                        const f = e.target.files?.[0]; if(!f || !tenant) return;
                        try {
                          setDialogError(null);
                          const { url } = await uploadProductMedia(tenant, f);
                          setForm(prev=> ({ ...prev, image_url: url }));
                        } catch (err: any) {
                          setDialogError(err?.response?.data?.detail || err?.message || 'Upload failed');
                        }
                      }} />
                    </Button>
                  </Box>
                </Grid>
                <Grid item xs={12} sm={6} md={8}>
                  <Stack spacing={2}>
                    <TextField fullWidth size="small" label='Image URL' placeholder='https://example.com/image.jpg' value={form.image_url || ''} onChange={e=>setForm(prev=>({...prev, image_url: e.target.value || ''}))} />
                    <TextField fullWidth size="small" select label='Display Status' value={form.active? 'active':'inactive'} onChange={e=>setForm(prev=>({...prev, active: e.target.value==='active'}))}>
                      <MenuItem value='active'>Active (Visible in Catalog)</MenuItem>
                      <MenuItem value='inactive'>Inactive (Hidden)</MenuItem>
                    </TextField>
                  </Stack>
                </Grid>
              </Grid>
            </Stack>
          )}

          {activeTab === 1 && (
            <Stack spacing={2.5} sx={{ mt: 1, '& .MuiInputLabel-root': { fontSize: '0.875rem', fontWeight: 500 }, '& .MuiFormHelperText-root': { fontSize: '0.875rem', fontWeight: 500 } }}>
              <Typography variant="body2" sx={{ fontWeight: 600, color: 'text.primary' }}>Pricing</Typography>
              <Grid container spacing={2}>
                <Grid item xs={12} sm={6} md={3}>
                  <TextField fullWidth size="small" type="number" label="Cost Price (Supplier Price)" value={form.price} onChange={e=>setForm(prev=>({...prev, price: Number(e.target.value)}))} />
                </Grid>
                <Grid item xs={12} sm={6} md={3}>
                  <TextField fullWidth size="small" type="number" label="Selling Price" value={form.mrp ?? ''} onChange={e=>setForm(prev=>({...prev, mrp: e.target.value===''? undefined: Number(e.target.value)}))} />
                </Grid>
                <Grid item xs={6} sm={6} md={3}>
                  <TextField fullWidth size="small" type="number" label="Tax %" value={form.tax ?? ''} onChange={e=>setForm(prev=>({...prev, tax: e.target.value===''? undefined: Number(e.target.value)}))} />
                </Grid>
                <Grid item xs={6} sm={6} md={3}>
                  <TextField fullWidth size="small" label="Base Unit" value={form.unit || ''} onChange={e=>setForm(prev=>({...prev, unit: e.target.value||undefined}))} placeholder="kg, pc" />
                </Grid>
              </Grid>

              <Box sx={{ py: 1.5, px: 2, bgcolor: 'rgba(59, 130, 246, 0.1)', border: '1px solid rgba(59, 130, 246, 0.35)', borderRadius: 1.5 }}>
                <Typography variant="body2" sx={{ mb: 1.5, fontWeight: 600, color: 'text.primary' }}>Minimum selling price</Typography>
                <Grid container spacing={2} alignItems="center">
                  <Grid item xs={12} sm={6} md={4}>
                    <TextField fullWidth size="small" select label="Margin Type" value={form.margin_type || ''} onChange={e=>setForm(prev=>({...prev, margin_type: (e.target.value as any)||''}))}>
                      <MenuItem value="">None</MenuItem>
                      <MenuItem value="percent">Percentage %</MenuItem>
                      <MenuItem value="amount">Amount</MenuItem>
                    </TextField>
                  </Grid>
                  {(form.margin_type === 'percent' || form.margin_type === 'amount') && (
                    <Grid item xs={12} sm={6} md={4}>
                      <TextField fullWidth size="small" type="number" label="Margin Amount" value={form.margin_value ?? ''} onChange={e=>setForm(prev=>({...prev, margin_value: e.target.value===''? undefined : Number(e.target.value)}))} />
                      <Typography variant="body2" sx={{ mt: 0.5, fontWeight: 500, color: 'text.primary' }}>Markup on Cost Price (Supplier Price)</Typography>
                    </Grid>
                  )}
                  <Grid item xs={12} sm={6} md={form.margin_type ? 4 : 6}>
                    {(() => {
                      const cost = Number(form.price) || 0
                      const selling = Number(form.mrp ?? form.price) || 0
                      let msp = selling
                      if (form.margin_type === 'percent' && form.margin_value != null) msp = cost + (cost * Number(form.margin_value) / 100)
                      else if (form.margin_type === 'amount' && form.margin_value != null) msp = cost + Number(form.margin_value)
                      msp = Math.max(0, msp)
                      return (
                        <Box>
                          <TextField fullWidth size="small" label="Minimum Selling price" value={msp.toFixed(2)} disabled />
                          <Typography variant="body2" sx={{ mt: 0.5, fontWeight: 500, color: 'text.primary' }}>
                            Auto: Cost + margin, or Selling Price when Margin Type is None
                          </Typography>
                        </Box>
                      )
                    })()}
                  </Grid>
                </Grid>
              </Box>

              <Typography variant="body2" sx={{ fontWeight: 600, color: 'text.primary' }}>Discount</Typography>
              <Grid container spacing={2}>
                <Grid item xs={12} sm={6} md={6}>
                  <TextField fullWidth size="small" select label="Discount Type" value={form.discount_type || ''} onChange={e=>setForm(prev=>({...prev, discount_type: (e.target.value as any)||''}))}>
                    <MenuItem value="">None</MenuItem>
                    <MenuItem value="amount">Fixed Amount</MenuItem>
                    <MenuItem value="percent">Percentage %</MenuItem>
                  </TextField>
                </Grid>
                <Grid item xs={12} sm={6} md={6}>
                  <TextField fullWidth size="small" type="number" label="Discount Amount" value={form.discount_value ?? ''} onChange={e=>setForm(prev=>({...prev, discount_value: e.target.value===''? undefined : Number(e.target.value)}))} disabled={!form.discount_type} />
                </Grid>
              </Grid>

              <Typography variant="body2" sx={{ fontWeight: 600, color: 'text.primary' }}>Inventory</Typography>
              {(!form.variants || form.variants.length === 0) ? (
                <Grid container spacing={2}>
                  <Grid item xs={12} sm={6} md={6}>
                    <TextField fullWidth size="small" type="number" label="Current Stock Quantity" value={form.stock_qty ?? ''} onChange={e=>setForm(prev=>({...prev, stock_qty: e.target.value===''? undefined: Number(e.target.value)}))} />
                    <Typography variant="body2" sx={{ mt: 0.5, fontWeight: 500, color: 'text.primary' }}>{editMode ? `Available: ${form.stock_qty ?? 0}` : 'Initial stock'}</Typography>
                  </Grid>
                </Grid>
              ) : (
                <Alert severity="info" sx={{ py: 0.5 }}>Stock is managed per variant in the Variants tab.</Alert>
              )}

              {(() => {
                const sellingPrice = Number(form.mrp ?? form.price) || 0
                const discT = form.discount_type
                const discV = Number(form.discount_value || 0)
                let afterDiscount = sellingPrice
                if (discT === 'amount') afterDiscount = Math.max(0, sellingPrice - discV)
                else if (discT === 'percent') afterDiscount = Math.max(0, sellingPrice - (sellingPrice * (discV / 100)))
                const taxPct = Number(form.tax || 0) / 100
                const vat = afterDiscount * taxPct
                const finalPrice = afterDiscount + vat
                return (
                  <Box sx={{ py: 1.5, px: 2, width: '100%', bgcolor: 'rgba(220, 38, 38, 0.08)', border: '1px solid rgba(220, 38, 38, 0.4)', borderRadius: 1.5, display: 'flex', alignItems: 'center', flexWrap: 'wrap', gap: 2 }}>
                    <Typography variant="body2" sx={{ fontWeight: 600, color: 'text.primary' }}>Final Price</Typography>
                    <Typography variant="body2" sx={{ fontWeight: 500, color: 'text.primary' }}>Selling Price − Discount + VAT</Typography>
                    <Typography variant="h6" sx={{ color: '#dc2626', fontWeight: 700 }}>₹{finalPrice.toFixed(2)}</Typography>
                  </Box>
                )
              })()}
            </Stack>
          )}

          {activeTab === 2 && (
            <Box sx={{ mt: 1, width: '100%', overflow: 'auto' }}>
              <Grid container spacing={2} alignItems="center" sx={{ mb: 2 }}>
                <Grid item xs={12} sm>
                  <Typography variant="subtitle2" color="primary">Product Variants</Typography>
                  <Typography variant="caption" color="text.secondary">Add variants if this product has different colors, sizes, or materials.</Typography>
                </Grid>
                <Grid item xs={12} sm={6} md={4}>
                  <Button startIcon={<AddIcon />} variant="outlined" size='small' fullWidth sx={{ minWidth: 140 }} onClick={()=> setForm(prev=> ({...prev, variants: [...(prev.variants||[]), { variant_sku:'', color:'', size:'', price: undefined, mrp: undefined, tax: undefined, discount_type:'', discount_value: undefined, image_url:'', active: true }]}))}>Add Variant</Button>
                </Grid>
              </Grid>

              <Box sx={{ mb: 2, p: 2, bgcolor: 'rgba(30, 41, 59, 0.8)', borderRadius: 1, border: '1px solid #334155' }}>
                <Typography variant="caption" fontWeight="bold" sx={{ color: '#93c5fd', display: 'block', mb: 1 }}>How to use Variants (Examples):</Typography>
                <Grid container spacing={1} sx={{ mb: 2 }}>
                  {[
                    { label: 'Color + Size (Fashion)', example: 'shirt-red-m', attrs: { color: 'Red', size: 'M' } },
                    { label: 'Color Only (Phone)', example: 'iphone-black', attrs: { color: 'Black' } },
                    { label: 'Size Only (Shoes)', example: 'shoe-10', attrs: { size: '10' } },
                    { label: 'Material (Furniture)', example: 'table-wood', attrs: { material: 'Wood' } },
                  ].map((p, idx) => (
                    <Grid item key={idx}>
                      <Chip 
                        label={p.label} 
                        size="small" 
                        onClick={() => {
                          const vs = p.example + '-' + Math.floor(Math.random()*1000)
                          setForm(prev => ({ 
                            ...prev, 
                            variants: [...(prev.variants||[]), { 
                              variant_sku: vs, 
                              color: p.attrs.color, 
                              size: p.attrs.size,
                              attributes: Object.fromEntries(Object.entries(p.attrs).filter(([,v])=>v!=null)) as Record<string, string>,
                              active: true 
                            }] 
                          }));
                        }}
                        sx={{ bgcolor: '#334155', color: '#f1f5f9', border: '1px solid #475569', '&:hover': { bgcolor: '#475569' } }}
                      />
                    </Grid>
                  ))}
                </Grid>
                
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell sx={{ fontSize: '0.75rem', py: 0.5, color: '#e2e8f0' }}><b>Variant SKU</b></TableCell>
                      <TableCell sx={{ fontSize: '0.75rem', py: 0.5, color: '#e2e8f0' }}><b>Color</b></TableCell>
                      <TableCell sx={{ fontSize: '0.75rem', py: 0.5, color: '#e2e8f0' }}><b>Size</b></TableCell>
                      <TableCell sx={{ fontSize: '0.75rem', py: 0.5, color: '#e2e8f0' }}><b>Usage</b></TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    <TableRow>
                      <TableCell sx={{ fontSize: '0.75rem', py: 0.5, color: '#f1f5f9' }}>shirt-red-m</TableCell>
                      <TableCell sx={{ fontSize: '0.75rem', py: 0.5, color: '#f1f5f9' }}>Red</TableCell>
                      <TableCell sx={{ fontSize: '0.75rem', py: 0.5, color: '#f1f5f9' }}>M</TableCell>
                      <TableCell sx={{ fontSize: '0.75rem', py: 0.5, color: '#e2e8f0' }}>For Red color, Medium size</TableCell>
                    </TableRow>
                    <TableRow>
                      <TableCell sx={{ fontSize: '0.75rem', py: 0.5, color: '#f1f5f9' }}>iphone-15-black</TableCell>
                      <TableCell sx={{ fontSize: '0.75rem', py: 0.5, color: '#f1f5f9' }}>Black</TableCell>
                      <TableCell sx={{ fontSize: '0.75rem', py: 0.5, color: '#f1f5f9' }}>—</TableCell>
                      <TableCell sx={{ fontSize: '0.75rem', py: 0.5, color: '#e2e8f0' }}>For Black color variant</TableCell>
                    </TableRow>
                  </TableBody>
                </Table>
              </Box>

              <Box sx={{ overflowX: 'auto' }}>
              <Table size='small' sx={{ minWidth: 640 }}>
                <TableHead>
                  <TableRow sx={{ bgcolor: 'rgba(51, 65, 85, 0.5)' }}>
                    <TableCell sx={{ fontWeight: 'bold', color: '#e2e8f0' }}>SKU & Attributes</TableCell>
                    <TableCell sx={{ fontWeight: 'bold', color: '#e2e8f0' }}>Pricing (Optional)</TableCell>
                    <TableCell sx={{ fontWeight: 'bold', color: '#e2e8f0' }}>Stock & Status</TableCell>
                    <TableCell align='right'></TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {(form.variants||[]).map((v, i)=>{
                    const unitPrice = Number(v.price!=null? v.price : form.price)||0
                    const dt: string = (v.discount_type ?? '') || (form.discount_type ?? '')
                    const dv = (v.discount_value!=null? v.discount_value : form.discount_value)||0
                    const final = dt==='amount' ? Math.max(0, unitPrice - Number(dv||0)) : dt==='percent' ? Math.max(0, unitPrice - (unitPrice * (Number(dv||0)/100))) : unitPrice
                    return (
                      <TableRow key={i}>
                        <TableCell sx={{ verticalAlign: 'top', pt: 2 }}>
                          <Stack spacing={1}>
                            <TextField size='small' label="Variant SKU" value={v.variant_sku} onChange={e=> setForm(prev=> ({...prev, variants: (prev.variants||[]).map((vx,ix)=> ix===i? {...vx, variant_sku: e.target.value }: vx)}))} placeholder='e.g., tee-red-m' fullWidth />
                            <Stack direction="row" spacing={1}>
                              <TextField size='small' label="Color" value={v.color || ''} onChange={e=> setForm(prev=> ({...prev, variants: (prev.variants||[]).map((vx,ix)=> ix===i? {...vx, color: e.target.value }: vx)}))} placeholder='Red' />
                              <TextField size='small' label="Size" value={v.size || ''} onChange={e=> setForm(prev=> ({...prev, variants: (prev.variants||[]).map((vx,ix)=> ix===i? {...vx, size: e.target.value }: vx)}))} placeholder='M' />
                            </Stack>
                          </Stack>
                        </TableCell>
                        <TableCell sx={{ verticalAlign: 'top', pt: 2 }}>
                          <Stack spacing={1}>
                            <TextField size='small' type='number' label="Price" value={v.price ?? ''} onChange={e=> setForm(prev=> ({...prev, variants: (prev.variants||[]).map((vx,ix)=> ix===i? {...vx, price: (e.target.value===''?undefined:Number(e.target.value)) as any}: vx)}))} placeholder={String(form.price||0)} />
                            <Box sx={{ px: 1 }}>
                              <Typography variant="caption" color="text.secondary">Final: ₹{final.toFixed(2)}</Typography>
                            </Box>
                            <Stack direction="row" spacing={1}>
                              <TextField select size='small' label="Disc" value={v.discount_type || ''} onChange={e=> setForm(prev=> ({...prev, variants: (prev.variants||[]).map((vx,ix)=> ix===i? {...vx, discount_type: e.target.value as any }: vx)}))} sx={{ width: 100 }}>
                                <MenuItem value=''>Inherit</MenuItem>
                                <MenuItem value='amount'>₹</MenuItem>
                                <MenuItem value='percent'>%</MenuItem>
                              </TextField>
                              <TextField size='small' type='number' label="Val" value={v.discount_value ?? ''} onChange={e=> setForm(prev=> ({...prev, variants: (prev.variants||[]).map((vx,ix)=> ix===i? {...vx, discount_value: (e.target.value===''?undefined:Number(e.target.value)) as any}: vx)}))} disabled={!v.discount_type} />
                            </Stack>
                          </Stack>
                        </TableCell>
                        <TableCell sx={{ verticalAlign: 'top', pt: 2 }}>
                          <Stack spacing={1}>
                            <TextField size='small' type="number" label="Available Stock" value={String(variantAvail[v.variant_sku||''] ?? '')}
                              onChange={(e)=> setVariantAvail(prev => ({ ...prev, [v.variant_sku]: Number(e.target.value) }))}
                              placeholder='0'
                              helperText={form.unit === 'kg' ? 'e.g. 5.25 for 5.25 kg' : ''}
                              onBlur={async (e)=>{
                                if (tenant && v.variant_sku && e.target.value !== '') {
                                  try { await setInventory(tenant, v.variant_sku, Number(e.target.value)); } catch(err) { console.error('Failed to update variant inventory:', err); }
                                }
                              }}
                            />
                            <TextField select size='small' label="Status" value={(v.active??true)?'active':'inactive'} onChange={e=> setForm(prev=> ({...prev, variants: (prev.variants||[]).map((vx,ix)=> ix===i? {...vx, active: e.target.value==='active' }: vx)}))}>
                              <MenuItem value='active'>Active</MenuItem>
                              <MenuItem value='inactive'>Inactive</MenuItem>
                            </TextField>
                          </Stack>
                        </TableCell>
                        <TableCell align='right' sx={{ verticalAlign: 'top', pt: 2 }}>
                          <Stack>
                            <Tooltip title="Duplicate Variant">
                              <IconButton size='small' onClick={()=> setForm(prev=> {
                                const copy = { ...v, variant_sku: v.variant_sku ? `${v.variant_sku}-copy` : '' }
                                return {...prev, variants: [...(prev.variants||[]), copy]}
                              })}>
                                <ContentCopyIcon fontSize='small' />
                              </IconButton>
                            </Tooltip>
                            <IconButton size='small' color="error" onClick={()=> setForm(prev=> ({...prev, variants: (prev.variants||[]).filter((_,ix)=> ix!==i)}))}>
                              <DeleteIcon fontSize='small' />
                            </IconButton>
                          </Stack>
                        </TableCell>
                      </TableRow>
                    )
                  })}
                  {(!form.variants || form.variants.length===0) && (
                    <TableRow>
                      <TableCell colSpan={4} align="center" sx={{ py: 4 }}>
                        <Typography variant='body2' color='text.secondary'>No variants defined. Products like clothes or shoes usually need variants for Size and Color.</Typography>
                        <Button startIcon={<AddIcon />} variant="outlined" size='small' sx={{ mt: 2 }} onClick={()=> setForm(prev=> ({...prev, variants: [...(prev.variants||[]), { variant_sku:'', color:'', size:'', active: true }]}))}>Add First Variant</Button>
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
              </Box>
            </Box>
          )}

          {activeTab === 3 && (
            <Box sx={{ mt: 1, width: '100%', overflow: 'auto' }}>
              <Grid container spacing={2} alignItems="center" sx={{ mb: 2 }}>
                <Grid item xs={12} sm>
                  <Typography variant="subtitle2" color="primary">Unit Conversions</Typography>
                  <Typography variant="caption" color="text.secondary">Define weight or volume conversions relative to the base unit ({form.unit || 'none'}).</Typography>
                </Grid>
                <Grid item xs={12} sm={6} md={4}>
                  <Button startIcon={<AddIcon />} variant="outlined" size='small' fullWidth sx={{ minWidth: 140 }} onClick={() => setForm(prev => ({ ...prev, unit_conversions: [...(prev.unit_conversions || []), { unit: '', factor: 1 }] }))}>Add Conversion</Button>
                </Grid>
              </Grid>

              <Box sx={{ mb: 2, p: 2, bgcolor: 'rgba(30, 41, 59, 0.8)', borderRadius: 1, border: '1px solid #334155' }}>
                <Typography variant="caption" fontWeight="bold" sx={{ color: '#93c5fd', display: 'block', mb: 1 }}>How to use Units (Quick Presets):</Typography>
                <Grid container spacing={1}>
                  {[
                    { label: 'kg ➔ gram', unit: 'gram', factor: 0.001, reason: '1g = 0.001kg' },
                    { label: 'dozen ➔ pc', unit: 'pc', factor: 0.083333, reason: '1pc = 1/12 dozen' },
                    { label: 'pc ➔ dozen', unit: 'dozen', factor: 12, reason: '1 dozen = 12pcs' },
                    { label: 'box ➔ pc (6)', unit: 'pc', factor: 0.166667, reason: '1pc = 1/6 box' },
                    { label: 'box ➔ pc (10)', unit: 'pc', factor: 0.1, reason: '1pc = 1/10 box' },
                    { label: 'box ➔ pc (12)', unit: 'pc', factor: 0.083333, reason: '1pc = 1/12 box' },
                    { label: 'box ➔ pc (24)', unit: 'pc', factor: 0.041667, reason: '1pc = 1/24 box' },
                    { label: 'piece ➔ dozen', unit: 'dozen', factor: 12, reason: '1 dozen = 12 pieces' },
                    { label: 'dozen ➔ piece', unit: 'piece', factor: 0.083333, reason: '1 piece = 1/12 dozen' },
                  ].map((p, idx) => (
                    <Grid item key={idx}>
                      <Tooltip title={p.reason}>
                        <Chip 
                          label={p.label} 
                          size="small" 
                          onClick={() => {
                            const exists = (form.unit_conversions || []).find(uc => uc.unit === p.unit);
                            if (exists) return;
                            setForm(prev => ({ 
                              ...prev, 
                              unit_conversions: [...(prev.unit_conversions || []), { unit: p.unit, factor: p.factor }] 
                            }));
                          }}
                          sx={{ bgcolor: '#334155', color: '#f1f5f9', border: '1px solid #475569', '&:hover': { bgcolor: '#475569' } }}
                        />
                      </Tooltip>
                    </Grid>
                  ))}
                </Grid>
                
                <Typography variant="caption" fontWeight="bold" sx={{ color: '#93c5fd', display: 'block', mt: 2, mb: 1 }}>Example Reference Table:</Typography>
                <Box sx={{ overflowX: 'auto' }}>
                <Table size="small" sx={{ minWidth: 400 }}>
                  <TableHead>
                    <TableRow>
                      <TableCell sx={{ fontSize: '0.75rem', py: 0.5, color: '#e2e8f0' }}><b>Scenario</b></TableCell>
                      <TableCell sx={{ fontSize: '0.75rem', py: 0.5, color: '#e2e8f0' }}><b>Base Unit</b></TableCell>
                      <TableCell sx={{ fontSize: '0.75rem', py: 0.5, color: '#e2e8f0' }}><b>Target Unit</b></TableCell>
                      <TableCell sx={{ fontSize: '0.75rem', py: 0.5, color: '#e2e8f0' }}><b>Factor (Target ÷ Base)</b></TableCell>
                      <TableCell sx={{ fontSize: '0.75rem', py: 0.5, color: '#e2e8f0' }}><b>Reasoning</b></TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    <TableRow>
                      <TableCell sx={{ fontSize: '0.75rem', py: 0.5, color: '#f1f5f9' }}>Grocery</TableCell>
                      <TableCell sx={{ fontSize: '0.75rem', py: 0.5, color: '#f1f5f9' }}>kg</TableCell>
                      <TableCell sx={{ fontSize: '0.75rem', py: 0.5, color: '#f1f5f9' }}>gram</TableCell>
                      <TableCell sx={{ fontSize: '0.75rem', py: 0.5, color: '#f1f5f9' }}>0.001</TableCell>
                      <TableCell sx={{ fontSize: '0.75rem', py: 0.5, color: '#e2e8f0' }}>1 gram = 0.001 kg</TableCell>
                    </TableRow>
                    <TableRow>
                      <TableCell sx={{ fontSize: '0.75rem', py: 0.5, color: '#f1f5f9' }}>Wholesale</TableCell>
                      <TableCell sx={{ fontSize: '0.75rem', py: 0.5, color: '#f1f5f9' }}>dozen</TableCell>
                      <TableCell sx={{ fontSize: '0.75rem', py: 0.5, color: '#f1f5f9' }}>pc (piece)</TableCell>
                      <TableCell sx={{ fontSize: '0.75rem', py: 0.5, color: '#f1f5f9' }}>0.0833</TableCell>
                      <TableCell sx={{ fontSize: '0.75rem', py: 0.5, color: '#e2e8f0' }}>1 piece = 1/12 dozen</TableCell>
                    </TableRow>
                    <TableRow>
                      <TableCell sx={{ fontSize: '0.75rem', py: 0.5, color: '#f1f5f9' }}>Bakery</TableCell>
                      <TableCell sx={{ fontSize: '0.75rem', py: 0.5, color: '#f1f5f9' }}>pc</TableCell>
                      <TableCell sx={{ fontSize: '0.75rem', py: 0.5, color: '#f1f5f9' }}>pack of 6</TableCell>
                      <TableCell sx={{ fontSize: '0.75rem', py: 0.5, color: '#f1f5f9' }}>6</TableCell>
                      <TableCell sx={{ fontSize: '0.75rem', py: 0.5, color: '#e2e8f0' }}>1 pack = 6 pieces</TableCell>
                    </TableRow>
                  </TableBody>
                </Table>
                </Box>
              </Box>

              <Alert severity="info" sx={{ mb: 2 }}>
                Example: If your base unit is <b>kg</b> and you want to sell in <b>grams</b>, add "gram" with factor <b>0.001</b>. (Because 1 gram = 0.001 kg).
              </Alert>

              <Box sx={{ overflowX: 'auto' }}>
              <Table size='small' sx={{ minWidth: 400 }}>
                <TableHead>
                  <TableRow sx={{ bgcolor: 'rgba(51, 65, 85, 0.5)' }}>
                    <TableCell sx={{ fontWeight: 'bold', color: '#e2e8f0' }}>Target Unit</TableCell>
                    <TableCell sx={{ fontWeight: 'bold', color: '#e2e8f0' }}>Conversion Factor</TableCell>
                    <TableCell align='right'></TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {(form.unit_conversions || []).map((uc, i) => (
                    <TableRow key={i}>
                      <TableCell>
                        <TextField size='small' value={uc.unit} onChange={e => setForm(prev => ({ ...prev, unit_conversions: (prev.unit_conversions || []).map((u, ix) => ix === i ? { ...u, unit: e.target.value } : u) }))} placeholder='e.g., gram, dozen, pack of 6' fullWidth />
                      </TableCell>
                      <TableCell>
                        <TextField size='small' type='number' value={uc.factor} onChange={e => setForm(prev => ({ ...prev, unit_conversions: (prev.unit_conversions || []).map((u, ix) => ix === i ? { ...u, factor: Number(e.target.value) } : u) }))} placeholder='0.001' fullWidth />
                      </TableCell>
                      <TableCell align='right'>
                        <IconButton size='small' color='error' onClick={() => setForm(prev => ({ ...prev, unit_conversions: (prev.unit_conversions || []).filter((_, ix) => ix !== i) }))}><DeleteIcon fontSize='small' /></IconButton>
                      </TableCell>
                    </TableRow>
                  ))}
                  {(form.unit_conversions || []).length === 0 && (
                    <TableRow>
                      <TableCell colSpan={3} align="center" sx={{ py: 4 }}>
                        <Typography variant='body2' color='text.secondary'>No unit conversions defined. Useful for grocery or wholesale items.</Typography>
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
              </Box>
            </Box>
          )}
        </DialogContent>
        <DialogActions sx={{ px: 3, py: 2 }}>
          <Button onClick={()=>setOpen(false)}>Cancel</Button>
          <Button variant='contained' onClick={save} sx={{ px: 4 }}>Save Product</Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}
