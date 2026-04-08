/**
 * Navigation config for admin_ui sidebar.
 * Matches routes in App.tsx; visibility is controlled by capabilities in Sidebar.
 */
export interface NavItem {
  label: string
  to: string
  cap: string | null
}

/** Super Admin only (tenants, ops). Shown under “Super Admin” section. */
export const SUPER_ADMIN_NAV: NavItem[] = [
  { label: 'Tenants', to: '/tenants', cap: 'core.tenants' },
  { label: 'Tenant Tracker', to: '/admin/tenant-tracker', cap: 'super_admin_only' },
  { label: 'Cron Jobs', to: '/admin/cron-jobs', cap: 'super_admin_only' },
]

/** Day-to-day tenant app: dashboard, settings, CRM, salon-adjacent core. */
export const TENANT_NAV: NavItem[] = [
  { label: 'Dashboard', to: '/', cap: 'core.dashboard' },
  { label: 'Settings', to: '/settings', cap: 'core.settings' },
  { label: 'Customers', to: '/customers', cap: 'core.customers' },
  { label: 'Staff', to: '/staff', cap: 'core.staff' },
  { label: 'Promotions', to: '/promotions', cap: 'core.promotions' },
  { label: 'Follow-ups', to: '/followups', cap: 'core.followups' },
  { label: 'Reports', to: '/reports', cap: 'core.reports' },
  { label: 'Retention', to: '/retention', cap: 'core.retention' },
]

export const SALON_NAV: NavItem[] = [
  { label: 'Services', to: '/services', cap: 'salon.services' },
  { label: 'Professionals', to: '/professionals', cap: 'salon.professionals' },
  { label: 'Appointments', to: '/appointments', cap: 'salon.appointments' },
  { label: 'No-Show Blocked', to: '/no-show-blocked', cap: 'salon.no_show_blocked' },
]

export const STORE_NAV: NavItem[] = [
  { label: 'Store — Carts', to: '/store/carts', cap: 'store.orders' },
  { label: 'Store — Orders', to: '/store/orders', cap: 'store.orders' },
  { label: 'Store — Products', to: '/store/products', cap: 'store.catalog' },
  { label: 'Store — Categories', to: '/store/categories', cap: 'store.catalog' },
  { label: 'Store — Offers', to: '/store/offers', cap: 'store.catalog' },
  { label: 'Store — Catalog', to: '/store/catalog', cap: 'store.catalog' },
]

export const AI_NAV: NavItem[] = [
  { label: 'AI Appointments', to: '/ai/appointments', cap: 'ai.appointment_recs' },
  { label: 'AI Config', to: '/ai/config', cap: 'core.settings' },
]

export const WHATSAPP_NAV: NavItem[] = [
  { label: 'WhatsApp', to: '/whatsapp', cap: 'core.whatsapp_menu' },
  { label: 'Messages', to: '/whatsapp/messages', cap: 'core.whatsapp_menu' },
  { label: 'Workflow', to: '/whatsapp/workflows', cap: 'core.whatsapp_menu' },
  { label: 'WhatsApp Bot', to: '/whatsapp/bot', cap: 'core.whatsapp_menu' },
]

