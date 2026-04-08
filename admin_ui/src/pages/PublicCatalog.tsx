import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useParams } from 'react-router-dom'
import {
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  Dialog,
  DialogContent,
  Divider,
  FormControl,
  Grid,
  IconButton,
  InputAdornment,
  InputLabel,
  MenuItem,
  Select,
  Stack,
  TextField,
  Typography,
} from '@mui/material'
import AddIcon from '@mui/icons-material/Add'
import RemoveIcon from '@mui/icons-material/Remove'
import SearchIcon from '@mui/icons-material/Search'
import ShoppingCartIcon from '@mui/icons-material/ShoppingCart'
import DeleteOutlineIcon from '@mui/icons-material/DeleteOutline'
import WhatsAppIcon from '@mui/icons-material/WhatsApp'
import ChevronLeftIcon from '@mui/icons-material/ChevronLeft'
import ChevronRightIcon from '@mui/icons-material/ChevronRight'
import CloseIcon from '@mui/icons-material/Close'
import {
  listProductsPublic,
  listPopularProductsPublic,
  listCategoriesPublic,
  getTenantPublicInfo,
  createOrderFromCatalog,
  type Product,
} from '@api/catalog'
import { listActiveOffersPublic, type Offer } from '@api/offers'
import { fullUrlForMedia } from '@api/upload'
import { getCurrencySymbol } from '../hooks/useTenantDateFormat'

const PRODUCTS_PER_CATEGORY = 20

/** True when the app is served from localhost (for enabling WhatsApp button with test number). */
const isLocalhost =
  typeof window !== 'undefined' &&
  (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1')

/** Default WhatsApp number for localhost testing (no env required). Override with VITE_CATALOG_WHATSAPP_NUMBER in .env.local if needed. */
const LOCALHOST_DUMMY_WHATSAPP_NUMBER = '919999999999'

/** Fallback WhatsApp number for localhost: env var or dummy number so the button works without config. */
const localhostWhatsAppNumber =
  (typeof import.meta !== 'undefined' && (import.meta as any).env?.VITE_CATALOG_WHATSAPP_NUMBER) ||
  (isLocalhost ? LOCALHOST_DUMMY_WHATSAPP_NUMBER : '')

const DEFAULT_PRODUCT_IMAGE =
  'data:image/svg+xml,' +
  encodeURIComponent(
    '<svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 48 48"><rect fill="#334155" width="48" height="48"/><text x="50%" y="50%" dominant-baseline="middle" text-anchor="middle" fill="#64748b" font-size="10" font-family="sans-serif">No image</text></svg>'
  )

type CartItem = {
  sku: string
  name?: string
  qty: number
  price_snapshot: number
  unit?: string
}

/** Shuffle array (Fisher–Yates). */
function shuffle<T>(arr: T[]): T[] {
  const out = [...arr]
  for (let i = out.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [out[i], out[j]] = [out[j], out[i]]
  }
  return out
}

/** Resolve effective price and "was" price for a product given active offers. */
function getProductPricing(
  p: Product,
  offers: Offer[]
): { priceNow: number; priceWas: number | null; offerLabel?: string } {
  const basePrice = Number(p.price) || 0
  const mrp = p.mrp != null ? Number(p.mrp) : null
  let priceNow = basePrice
  let priceWas: number | null = mrp != null ? mrp : null
  let offerLabel: string | undefined

  for (const offer of offers) {
    const skus = offer.product_skus ?? []
    if (!skus.includes(p.sku)) continue

    // Product is in this offer — always show the label (at minimum).
    if (!offerLabel) offerLabel = offer.title

    const info = (offer.discount_info ?? {}) as { type?: string; value?: number }
    const type = (info.type || 'percent') as 'percent' | 'amount'
    // Use || 0 so undefined/null/NaN all become 0 (avoid NaN propagation).
    const value = Number(info.value || 0)
    if (value <= 0) continue   // no discount saved — label still shown above

    const discount = type === 'amount' ? value : (basePrice * value) / 100
    const discounted = Math.max(0, basePrice - discount)
    if (discounted < priceNow) {
      priceNow = discounted
      priceWas = basePrice
      offerLabel = offer.title  // update to the offer that gives the best price
    }
  }

  if (priceWas != null && priceNow >= priceWas) priceWas = null
  return { priceNow, priceWas, offerLabel }
}

export default function PublicCatalog() {
  const { tenant } = useParams<{ tenant: string }>()
  const [popular, setPopular] = useState<Product[]>([])
  const [allProducts, setAllProducts] = useState<Product[]>([])
  const [categories, setCategories] = useState<{ name: string }[]>([])
  const [offers, setOffers] = useState<Offer[]>([])
  const [tenantInfo, setTenantInfo] = useState<{ name: string; whatsapp_number: string | null; currency?: string } | null>(null)
  const [cart, setCart] = useState<CartItem[]>([])
  const [search, setSearch] = useState('')
  const [categoryFilter, setCategoryFilter] = useState<string>('')
  const [loadingPopular, setLoadingPopular] = useState(true)
  const [loadingProducts, setLoadingProducts] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [sendingToWhatsApp, setSendingToWhatsApp] = useState(false)
  const [sendError, setSendError] = useState<string | null>(null)
  const [detailProduct, setDetailProduct] = useState<Product | null>(null)

  const c = useMemo(() => getCurrencySymbol(tenantInfo?.currency || 'INR'), [tenantInfo])

  const loadMeta = useCallback(async () => {
    if (!tenant) return
    try {
      const [catRes, offerRes, infoRes] = await Promise.all([
        listCategoriesPublic(tenant),
        listActiveOffersPublic(tenant),
        getTenantPublicInfo(tenant).catch(() => ({ name: tenant, whatsapp_number: null })),
      ])
      setCategories(catRes.items ?? [])
      setOffers(offerRes.items ?? [])
      setTenantInfo(infoRes)
    } catch {
      setCategories([])
      setOffers([])
      setTenantInfo({ name: tenant, whatsapp_number: null })
    }
  }, [tenant])

  const loadPopular = useCallback(async () => {
    if (!tenant) return
    setLoadingPopular(true)
    setError(null)
    try {
      const res = await listPopularProductsPublic(tenant, { top: 12, days: 30 })
      setPopular(res.items ?? [])
    } catch {
      setPopular([])
      setError('Could not load popular products')
    } finally {
      setLoadingPopular(false)
    }
  }, [tenant])

  const loadProducts = useCallback(async () => {
    if (!tenant) return
    setLoadingProducts(true)
    setError(null)
    try {
      const res = await listProductsPublic(tenant, {
        page: 1,
        size: 200,
        search: search.trim() || undefined,
        category: categoryFilter || undefined,
      })
      setAllProducts(res.items ?? [])
    } catch {
      setAllProducts([])
      setError('Could not load products')
    } finally {
      setLoadingProducts(false)
    }
  }, [tenant, search, categoryFilter])

  useEffect(() => {
    loadMeta()
  }, [loadMeta])

  useEffect(() => {
    loadPopular()
  }, [loadPopular])

  useEffect(() => {
    loadProducts()
  }, [loadProducts])

  const addToCart = (p: Product) => {
    const { priceNow } = getProductPricing(p, offers)
    setCart((prev) => {
      const i = prev.find((x) => x.sku === p.sku)
      if (i) return prev.map((x) => (x.sku === p.sku ? { ...x, qty: x.qty + 1 } : x))
      return [...prev, { sku: p.sku, name: p.name, qty: 1, price_snapshot: priceNow, unit: p.unit ?? undefined }]
    })
  }

  const removeFromCart = (sku: string) => {
    setCart((prev) => {
      const i = prev.find((x) => x.sku === sku)
      if (!i) return prev
      if (i.qty <= 1) return prev.filter((x) => x.sku !== sku)
      return prev.map((x) => (x.sku === sku ? { ...x, qty: x.qty - 1 } : x))
    })
  }

  const removeItemFromCart = (sku: string) => {
    setCart((prev) => prev.filter((x) => x.sku !== sku))
  }

  const addOneToCart = (sku: string) => {
    setCart((prev) => prev.map((x) => (x.sku === sku ? { ...x, qty: x.qty + 1 } : x)))
  }

  const total = useMemo(() => cart.reduce((s, i) => s + i.qty * i.price_snapshot, 0), [cart])
  const totalItems = useMemo(() => cart.reduce((s, i) => s + i.qty, 0), [cart])

  /** Build WhatsApp message with optional order_id at top (for bot to recognize). */
  const buildWhatsAppMessage = useCallback(
    (orderId: string | null) => {
      const lines: string[] = []
      if (orderId) {
        lines.push(`*Order #${orderId}*`, '')
      }
      lines.push('*My order:*', '')
      for (const i of cart) {
        lines.push(`• ${i.name || i.sku} × ${i.qty} — ${c}${(i.qty * i.price_snapshot).toFixed(2)}`)
      }
      lines.push('')
      lines.push(`*Total: ${c}${total.toFixed(2)}*`)
      return lines.join('\n')
    },
    [cart, total]
  )

  /** WhatsApp number: from tenant config, or on localhost from VITE_CATALOG_WHATSAPP_NUMBER. */
  const effectiveWhatsAppNumber = useMemo(() => {
    const fromTenant = tenantInfo?.whatsapp_number
    if (fromTenant && String(fromTenant).trim()) return String(fromTenant).replace(/^whatsapp:/i, '').trim()
    if (isLocalhost && localhostWhatsAppNumber) return String(localhostWhatsAppNumber).replace(/^whatsapp:/i, '').trim()
    return null
  }, [tenantInfo?.whatsapp_number])

  const canSendToWhatsApp = Boolean(tenant && effectiveWhatsAppNumber && cart.length > 0)

  const handleSendToWhatsApp = useCallback(async () => {
    if (!tenant || !effectiveWhatsAppNumber || cart.length === 0) return
    setSendError(null)
    setSendingToWhatsApp(true)
    try {
      const payload = cart.map((i) => ({
        sku: i.sku,
        name: i.name,
        qty: i.qty,
        price_snapshot: i.price_snapshot,
        unit: i.unit,
      }))
      const options =
        isLocalhost && effectiveWhatsAppNumber
          ? { customer_phone: effectiveWhatsAppNumber.startsWith('+') ? effectiveWhatsAppNumber : `+${effectiveWhatsAppNumber.replace(/\D/g, '')}` }
          : undefined
      const res = await createOrderFromCatalog(tenant, payload, options)
      const orderId = res?.order_id ?? null
      const message = buildWhatsAppMessage(orderId)
      const num = effectiveWhatsAppNumber.replace(/\D/g, '')
      const url = `https://wa.me/${num}?text=${encodeURIComponent(message)}`
      window.open(url, '_blank', 'noopener,noreferrer')
    } catch (e: unknown) {
      const msg = e && typeof e === 'object' && 'response' in e && (e as any).response?.data?.detail
      setSendError(msg || 'Failed to create order. Try again.')
    } finally {
      setSendingToWhatsApp(false)
    }
  }, [tenant, effectiveWhatsAppNumber, cart, buildWhatsAppMessage, isLocalhost])

  const popularSkus = useMemo(() => new Set(popular.map((p) => p.sku)), [popular])

  /** When not searching: products not in popular, grouped by category; each category shows up to PRODUCTS_PER_CATEGORY, order randomized. */
  const productsByCategory = useMemo(() => {
    if (search.trim() || categoryFilter) return null
    const rest = allProducts.filter((p) => !popularSkus.has(p.sku))
    const byCat = new Map<string, Product[]>()
    for (const p of rest) {
      const cat = p.category?.trim() || 'Uncategorized'
      if (!byCat.has(cat)) byCat.set(cat, [])
      byCat.get(cat)!.push(p)
    }
    const result: { category: string; products: Product[] }[] = []
    byCat.forEach((products, category) => {
      result.push({ category, products: shuffle(products).slice(0, PRODUCTS_PER_CATEGORY) })
    })
    result.sort((a, b) => a.category.localeCompare(b.category))
    return result
  }, [allProducts, popularSkus, search, categoryFilter])

  const showPopular = popular.length > 0 && !search.trim() && !categoryFilter
  const isFiltered = Boolean(search.trim() || categoryFilter)

  if (!tenant) {
    return (
      <Box sx={{ p: 3, textAlign: 'center', bgcolor: 'background.default', minHeight: '100vh' }}>
        <Typography color="text.secondary">Invalid catalog link.</Typography>
      </Box>
    )
  }

  return (
    <Box sx={{ minHeight: '100vh', bgcolor: 'background.default', color: 'text.primary', display: 'flex', flexDirection: 'column' }}>
      <Box sx={{ display: 'flex', flex: 1, minHeight: 0, flexDirection: { xs: 'column', md: 'row' } }}>
        {/* Left: products */}
        <Box sx={{ flex: 1, overflow: 'auto', py: 2, px: { xs: 1.5, sm: 2 }, minWidth: 0 }}>
          <Typography variant="h5" fontWeight="700" color="primary" sx={{ mb: 1 }}>
            {tenantInfo?.name ?? 'Store'} — Catalog
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Browse products, add to cart, and send your order via WhatsApp.
          </Typography>

          <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2} sx={{ mb: 2 }} alignItems={{ sm: 'center' }}>
            <TextField
              size="small"
              placeholder="Search by product name (e.g. milk)..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              InputProps={{
                startAdornment: (
                  <InputAdornment position="start">
                    <SearchIcon color="action" />
                  </InputAdornment>
                ),
              }}
              sx={{ flex: 1, maxWidth: 360 }}
            />
            <FormControl size="small" sx={{ minWidth: 180 }}>
              <InputLabel>Category</InputLabel>
              <Select
                value={categoryFilter}
                label="Category"
                onChange={(e) => setCategoryFilter(e.target.value)}
              >
                <MenuItem value="">All categories</MenuItem>
                {categories.map((c) => (
                  <MenuItem key={c.name} value={c.name}>
                    {c.name}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          </Stack>

          {error && (
            <Typography color="error" sx={{ mb: 2 }}>
              {error}
            </Typography>
          )}

          {showPopular && (
            <Box sx={{ mb: 3 }}>
              <Typography variant="subtitle1" fontWeight="600" color="text.secondary" sx={{ mb: 1.5 }}>
                Most selling
              </Typography>
              <Grid container spacing={2}>
                {loadingPopular ? (
                  <Grid item xs={12}>
                    <Typography color="text.secondary">Loading...</Typography>
                  </Grid>
                ) : (
                  popular.map((p) => (
                    <ProductCard
                      key={p.sku}
                      product={p}
                      offers={offers}
                      cartQty={cart.find((i) => i.sku === p.sku)?.qty ?? 0}
                      defaultImage={DEFAULT_PRODUCT_IMAGE}
                      currencySymbol={c}
                      onAdd={() => addToCart(p)}
                      onRemove={() => removeFromCart(p.sku)}
                      onProductClick={() => setDetailProduct(p)}
                    />
                  ))
                )}
              </Grid>
            </Box>
          )}

          {isFiltered && (
            <Grid container spacing={2}>
              {loadingProducts ? (
                <Grid item xs={12}>
                  <Typography color="text.secondary">Loading products...</Typography>
                </Grid>
              ) : allProducts.length === 0 ? (
                <Grid item xs={12}>
                  <Typography color="text.secondary">No products match your search or category.</Typography>
                </Grid>
              ) : (
                allProducts.map((p) => (
                  <ProductCard
                    key={p.sku}
                    product={p}
                    offers={offers}
                    cartQty={cart.find((i) => i.sku === p.sku)?.qty ?? 0}
                    defaultImage={DEFAULT_PRODUCT_IMAGE}
                    currencySymbol={c}
                    onAdd={() => addToCart(p)}
                    onRemove={() => removeFromCart(p.sku)}
                    onProductClick={() => setDetailProduct(p)}
                  />
                ))
              )}
            </Grid>
          )}

          {!isFiltered && loadingProducts && allProducts.length === 0 && popular.length === 0 && (
            <Typography color="text.secondary">Loading products...</Typography>
          )}

          {!isFiltered && productsByCategory && productsByCategory.length > 0 && (
            <>
              {showPopular && <Divider sx={{ my: 2, borderColor: 'divider' }} />}
              {productsByCategory.map(({ category, products }) => (
                <Box key={category} sx={{ mb: 3 }}>
                  <Typography variant="subtitle1" fontWeight="600" color="text.secondary" sx={{ mb: 1.5 }}>
                    {category}
                  </Typography>
                  <Grid container spacing={2}>
                    {products.map((p) => (
                        <ProductCard
                          key={p.sku}
                          product={p}
                          offers={offers}
                          cartQty={cart.find((i) => i.sku === p.sku)?.qty ?? 0}
                          defaultImage={DEFAULT_PRODUCT_IMAGE}
                          currencySymbol={c}
                          onAdd={() => addToCart(p)}
                          onRemove={() => removeFromCart(p.sku)}
                          onProductClick={() => setDetailProduct(p)}
                        />
                      ))}
                  </Grid>
                </Box>
              ))}
            </>
          )}

          {!isFiltered && !loadingProducts && (!productsByCategory || productsByCategory.length === 0) && popular.length === 0 && allProducts.length === 0 && (
            <Typography color="text.secondary">No products yet.</Typography>
          )}
        </Box>

        {/* Product detail modal */}
        {detailProduct && (
          <ProductDetailModal
            product={detailProduct}
            offers={offers}
            cartQty={cart.find((i) => i.sku === detailProduct.sku)?.qty ?? 0}
            defaultImage={DEFAULT_PRODUCT_IMAGE}
            currencySymbol={c}
            onClose={() => setDetailProduct(null)}
            onAdd={() => addToCart(detailProduct)}
            onRemove={() => removeFromCart(detailProduct.sku)}
          />
        )}

        {/* Right: cart panel */}
        <Box
          sx={{
            width: { xs: '100%', md: 340 },
            flexShrink: 0,
            borderLeft: { md: '1px solid' },
            borderTop: { xs: '1px solid', md: 'none' },
            borderColor: 'divider',
            bgcolor: 'background.paper',
            display: 'flex',
            flexDirection: 'column',
            minHeight: { xs: 'auto', md: '100vh' },
            overflow: 'hidden',
          }}
        >
          <Box sx={{ p: 2, borderBottom: '1px solid', borderColor: 'divider', display: 'flex', alignItems: 'center', gap: 1 }}>
            <ShoppingCartIcon color="primary" />
            <Typography variant="subtitle1" fontWeight="600">
              Cart {totalItems > 0 && `(${totalItems})`}
            </Typography>
          </Box>
          <Box sx={{ flex: 1, overflow: 'auto', p: 2 }}>
            {cart.length === 0 ? (
              <Typography variant="body2" color="text.secondary">
                Your cart is empty. Add products from the catalog.
              </Typography>
            ) : (
              <Stack spacing={1}>
                {cart.map((i) => (
                  <Stack
                    key={i.sku}
                    direction="row"
                    justifyContent="space-between"
                    alignItems="center"
                    sx={{ py: 0.75, px: 1.5, bgcolor: 'action.hover', borderRadius: 1, border: '1px solid', borderColor: 'divider' }}
                  >
                    <Typography variant="body2" noWrap sx={{ flex: 1, minWidth: 0 }}>
                      {i.name || i.sku} × {i.qty} — {c}{(i.qty * i.price_snapshot).toFixed(2)}
                    </Typography>
                    <Stack direction="row" alignItems="center" spacing={0}>
                      <IconButton size="small" onClick={() => removeFromCart(i.sku)} aria-label="Decrease">
                        <RemoveIcon fontSize="small" />
                      </IconButton>
                      <Typography variant="body2" sx={{ minWidth: 24, textAlign: 'center' }}>
                        {i.qty}
                      </Typography>
                      <IconButton size="small" onClick={() => addOneToCart(i.sku)} aria-label="Increase">
                        <AddIcon fontSize="small" />
                      </IconButton>
                      <IconButton size="small" onClick={() => removeItemFromCart(i.sku)} color="error" aria-label="Remove">
                        <DeleteOutlineIcon fontSize="small" />
                      </IconButton>
                    </Stack>
                  </Stack>
                ))}
              </Stack>
            )}
          </Box>
          {cart.length > 0 && (
            <Box sx={{ p: 2, borderTop: '1px solid', borderColor: 'divider' }}>
              <Typography variant="subtitle2" fontWeight="600" sx={{ mb: 1.5 }}>
                Total: {c}{total.toFixed(2)}
              </Typography>
              <Typography variant="caption" display="block" color="text.secondary" sx={{ mb: 1.5 }}>
                Creates an order and opens WhatsApp with your cart and order number for the bot.
              </Typography>
              {sendError && (
                <Typography variant="caption" color="error.main" sx={{ mb: 1, display: 'block' }}>
                  {sendError}
                </Typography>
              )}
              <Button
                variant="contained"
                color="success"
                startIcon={<WhatsAppIcon />}
                onClick={handleSendToWhatsApp}
                disabled={!canSendToWhatsApp || sendingToWhatsApp}
                fullWidth
              >
                {sendingToWhatsApp ? 'Creating order…' : 'Send to WhatsApp'}
              </Button>
              {!effectiveWhatsAppNumber && (
                <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
                  {isLocalhost
                    ? 'On localhost: add VITE_CATALOG_WHATSAPP_NUMBER=91XXXXXXXXXX in admin_ui/.env.local (your WhatsApp bot number) and restart the dev server.'
                    : 'Configure WhatsApp in tenant Settings, or set CATALOG_WHATSAPP_NUMBER / TWILIO_WHATSAPP_FROM on the server.'}
                </Typography>
              )}
            </Box>
          )}
        </Box>
      </Box>
    </Box>
  )
}

/** Extracts the ordered image list from a product, falling back to image_url. */
function getProductImages(product: Product, defaultImage: string): string[] {
  const urls: string[] = (product as any).image_urls?.length
    ? (product as any).image_urls
    : product.image_url
    ? [product.image_url]
    : []
  return urls.length ? urls.map((u) => fullUrlForMedia(u)) : [defaultImage]
}

/** Minimal touch-swipe image carousel (no external deps). */
function ImageCarousel({
  images,
  alt,
  aspectRatio = '1',
  large = false,
}: {
  images: string[]
  alt: string
  aspectRatio?: string
  large?: boolean
}) {
  const [idx, setIdx] = useState(0)
  const touchStartX = useRef<number | null>(null)
  const count = images.length

  const prev = (e: React.MouseEvent) => { e.stopPropagation(); setIdx((i) => (i - 1 + count) % count) }
  const next = (e: React.MouseEvent) => { e.stopPropagation(); setIdx((i) => (i + 1) % count) }

  const onTouchStart = (e: React.TouchEvent) => { touchStartX.current = e.touches[0].clientX }
  const onTouchEnd = (e: React.TouchEvent) => {
    if (touchStartX.current === null || count <= 1) return
    const dx = e.changedTouches[0].clientX - touchStartX.current
    if (dx < -40) setIdx((i) => (i + 1) % count)
    else if (dx > 40) setIdx((i) => (i - 1 + count) % count)
    touchStartX.current = null
  }

  return (
    <Box
      sx={{ position: 'relative', width: '100%', aspectRatio, overflow: 'hidden', bgcolor: 'background.default', userSelect: 'none' }}
      onTouchStart={onTouchStart}
      onTouchEnd={onTouchEnd}
    >
      {/* Sliding strip */}
      <Box
        sx={{
          display: 'flex',
          width: `${count * 100}%`,
          height: '100%',
          transform: `translateX(-${(idx / count) * 100}%)`,
          transition: 'transform 0.28s ease',
        }}
      >
        {images.map((src, i) => (
          <Box
            key={i}
            component="img"
            src={src}
            alt={`${alt} ${i + 1}`}
            onError={(e) => { (e.target as HTMLImageElement).src = images[0] }}
            sx={{ width: `${100 / count}%`, height: '100%', objectFit: large ? 'contain' : 'contain', flexShrink: 0, display: 'block' }}
          />
        ))}
      </Box>

      {/* Prev / Next arrows (only when > 1 image) */}
      {count > 1 && (
        <>
          <IconButton
            size="small"
            onClick={prev}
            sx={{ position: 'absolute', left: 2, top: '50%', transform: 'translateY(-50%)', bgcolor: 'rgba(0,0,0,0.4)', color: 'white', p: 0.25, '&:hover': { bgcolor: 'rgba(0,0,0,0.65)' } }}
          >
            <ChevronLeftIcon sx={{ fontSize: large ? 22 : 16 }} />
          </IconButton>
          <IconButton
            size="small"
            onClick={next}
            sx={{ position: 'absolute', right: 2, top: '50%', transform: 'translateY(-50%)', bgcolor: 'rgba(0,0,0,0.4)', color: 'white', p: 0.25, '&:hover': { bgcolor: 'rgba(0,0,0,0.65)' } }}
          >
            <ChevronRightIcon sx={{ fontSize: large ? 22 : 16 }} />
          </IconButton>
        </>
      )}

      {/* Dot indicators */}
      {count > 1 && (
        <Box sx={{ position: 'absolute', bottom: 4, left: 0, right: 0, display: 'flex', justifyContent: 'center', gap: 0.5, pointerEvents: 'none' }}>
          {images.map((_, i) => (
            <Box
              key={i}
              sx={{ width: large ? 8 : 5, height: large ? 8 : 5, borderRadius: '50%', bgcolor: i === idx ? 'primary.main' : 'rgba(255,255,255,0.6)', transition: 'background-color 0.2s' }}
            />
          ))}
        </Box>
      )}
    </Box>
  )
}

function ProductCard({
  product,
  offers,
  cartQty,
  defaultImage,
  currencySymbol,
  onAdd,
  onRemove,
  onProductClick,
}: {
  product: Product
  offers: Offer[]
  cartQty: number
  defaultImage: string
  currencySymbol: string
  onAdd: () => void
  onRemove: () => void
  onProductClick: () => void
}) {
  const { priceNow, priceWas, offerLabel } = getProductPricing(product, offers)
  const unit = product.unit ? ` / ${product.unit}` : ''
  const hasOffer = priceWas != null
  const images = getProductImages(product, defaultImage)

  return (
    <Grid item xs={6} sm={4} md={3} lg={2}>
      <Card
        variant="outlined"
        sx={{ height: '100%', display: 'flex', flexDirection: 'column', minWidth: 0, maxWidth: 200, mx: 'auto', cursor: 'pointer' }}
      >
        {/* Clickable image area → opens detail */}
        <Box onClick={onProductClick} sx={{ position: 'relative' }}>
          <ImageCarousel images={images} alt={product.name || product.sku} />
          {(product as any).image_urls?.length > 1 && (
            <Box sx={{ position: 'absolute', top: 4, right: 4, bgcolor: 'rgba(0,0,0,0.5)', borderRadius: 1, px: 0.5 }}>
              <Typography sx={{ fontSize: 9, color: 'white', lineHeight: 1.6 }}>{(product as any).image_urls.length} photos</Typography>
            </Box>
          )}
        </Box>

        <CardContent sx={{ flex: 1, display: 'flex', flexDirection: 'column', py: 1, px: 1.25, '&:last-child': { pb: 1 } }}>
          {offerLabel && (
            <Chip label={offerLabel} size="small" color="secondary" sx={{ alignSelf: 'flex-start', mb: 0.5, fontSize: '0.7rem' }} />
          )}
          {/* Clickable name → opens detail */}
          <Typography
            variant="body2"
            fontWeight="600"
            onClick={onProductClick}
            sx={{ mb: 0.25, minWidth: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', fontSize: '0.8125rem', '&:hover': { color: 'primary.main' } }}
            title={product.name || product.sku}
          >
            {product.name || product.sku}
          </Typography>
          <Stack direction="row" alignItems="baseline" spacing={0.5} flexWrap="wrap">
            {hasOffer && (
              <Typography variant="caption" color="error.main" sx={{ textDecoration: 'line-through', fontSize: '0.7rem' }}>
                {currencySymbol}{priceWas!.toFixed(2)}{unit}
              </Typography>
            )}
            <Typography variant="body2" fontWeight="600" color="primary.main" sx={{ fontSize: '0.8125rem' }}>
              {currencySymbol}{priceNow.toFixed(2)}{unit}
            </Typography>
          </Stack>
          <Box sx={{ mt: 'auto', pt: 1 }}>
            {cartQty === 0 ? (
              <Button size="small" variant="contained" startIcon={<AddIcon />} onClick={(e) => { e.stopPropagation(); onAdd() }} fullWidth sx={{ minHeight: 32 }}>
                Add
              </Button>
            ) : (
              <Stack direction="row" alignItems="center" spacing={0.5} justifyContent="center">
                <IconButton size="small" onClick={(e) => { e.stopPropagation(); onRemove() }} aria-label="Decrease" sx={{ padding: 0.25 }}>
                  <RemoveIcon sx={{ fontSize: 18 }} />
                </IconButton>
                <Typography variant="body2" fontWeight="600" sx={{ minWidth: 20, textAlign: 'center', fontSize: '0.8125rem' }}>
                  {cartQty}
                </Typography>
                <IconButton size="small" onClick={(e) => { e.stopPropagation(); onAdd() }} aria-label="Increase" sx={{ padding: 0.25 }}>
                  <AddIcon sx={{ fontSize: 18 }} />
                </IconButton>
              </Stack>
            )}
          </Box>
        </CardContent>
      </Card>
    </Grid>
  )
}

function ProductDetailModal({
  product,
  offers,
  cartQty,
  defaultImage,
  currencySymbol,
  onClose,
  onAdd,
  onRemove,
}: {
  product: Product
  offers: Offer[]
  cartQty: number
  defaultImage: string
  currencySymbol: string
  onClose: () => void
  onAdd: () => void
  onRemove: () => void
}) {
  const { priceNow, priceWas, offerLabel } = getProductPricing(product, offers)
  const unit = product.unit ? ` / ${product.unit}` : ''
  const hasOffer = priceWas != null
  const images = getProductImages(product, defaultImage)
  const description: string = (product as any).description || ''

  return (
    <Dialog open onClose={onClose} maxWidth="xs" fullWidth PaperProps={{ sx: { borderRadius: 2, m: 1 } }}>
      <Box sx={{ position: 'relative' }}>
        <IconButton
          onClick={onClose}
          size="small"
          sx={{ position: 'absolute', top: 8, right: 8, zIndex: 10, bgcolor: 'rgba(0,0,0,0.45)', color: 'white', '&:hover': { bgcolor: 'rgba(0,0,0,0.7)' } }}
        >
          <CloseIcon fontSize="small" />
        </IconButton>
        <ImageCarousel images={images} alt={product.name || product.sku} aspectRatio="4/3" large />
      </Box>

      <DialogContent sx={{ pt: 1.5, pb: 2, px: 2 }}>
        {offerLabel && (
          <Chip label={offerLabel} size="small" color="secondary" sx={{ mb: 1, fontSize: '0.75rem' }} />
        )}
        <Typography variant="h6" fontWeight="700" sx={{ mb: 0.5, lineHeight: 1.3 }}>
          {product.name || product.sku}
        </Typography>

        <Stack direction="row" alignItems="baseline" spacing={1} sx={{ mb: 1.5 }}>
          {hasOffer && (
            <Typography variant="body2" color="error.main" sx={{ textDecoration: 'line-through' }}>
              {currencySymbol}{priceWas!.toFixed(2)}{unit}
            </Typography>
          )}
          <Typography variant="h6" fontWeight="700" color="primary.main">
            {currencySymbol}{priceNow.toFixed(2)}{unit}
          </Typography>
        </Stack>

        {description ? (
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2, whiteSpace: 'pre-line', lineHeight: 1.6 }}>
            {description}
          </Typography>
        ) : null}

        <Divider sx={{ mb: 2 }} />

        {cartQty === 0 ? (
          <Button variant="contained" startIcon={<AddIcon />} onClick={onAdd} fullWidth size="large">
            Add to Cart
          </Button>
        ) : (
          <Stack direction="row" alignItems="center" spacing={1} justifyContent="center">
            <IconButton onClick={onRemove} aria-label="Decrease" sx={{ border: '1px solid', borderColor: 'divider' }}>
              <RemoveIcon />
            </IconButton>
            <Typography variant="h6" fontWeight="700" sx={{ minWidth: 32, textAlign: 'center' }}>
              {cartQty}
            </Typography>
            <IconButton onClick={onAdd} aria-label="Increase" sx={{ border: '1px solid', borderColor: 'divider' }}>
              <AddIcon />
            </IconButton>
            <Typography variant="body2" color="text.secondary" sx={{ ml: 1 }}>
              in cart
            </Typography>
          </Stack>
        )}
      </DialogContent>
    </Dialog>
  )
}
