// Built-in WhatsApp menu templates for the wizard
// These are UI-side presets; backend still validates trees on upsert.

export type MenuTemplate = {
  menu_id: string
  name: string
  tree: any
  locales?: Record<string, any>
}

export const retailTemplate: MenuTemplate = {
  menu_id: 'default',
  name: 'Retail Store Menu',
  tree: {
    id: 'root',
    title: { en: 'Welcome! How can we help?' },
    items: [
      { id: 'browse', label: { en: '🛍️ Browse Catalog' }, action: { kind: 'invoke_action', action_id: 'store.browse_catalog' } },
      { id: 'check', label: { en: '🔎 Check Product' }, action: { kind: 'invoke_action', action_id: 'store.check_product' } },
      { id: 'track', label: { en: '📦 Track Order' }, action: { kind: 'invoke_action', action_id: 'store.track_order' } },
      { id: 'offers', label: { en: '✨ Offers' }, action: { kind: 'invoke_action', action_id: 'core.static_text', params: { title: 'Latest offers coming soon!' } } }
    ]
  },
  locales: { en: {} }
}

export const restaurantTemplate: MenuTemplate = {
  menu_id: 'default',
  name: 'Restaurant Menu',
  tree: {
    id: 'root',
    title: { en: 'Welcome to our restaurant!' },
    items: [
      { id: 'table', label: { en: '🍽️ Book a Table' }, action: { kind: 'invoke_action', action_id: 'core.open_url', params: { url: 'https://example.com/book' } } },
      { id: 'menu', label: { en: '📖 View Menu' }, action: { kind: 'invoke_action', action_id: 'core.open_url', params: { url: 'https://example.com/menu' } } },
      { id: 'offers', label: { en: '✨ Today’s Specials' }, action: { kind: 'invoke_action', action_id: 'core.static_text', params: { title: 'Ask for chef special!' } } }
    ]
  },
  locales: { en: {} }
}

export const salonTemplate: MenuTemplate = {
  menu_id: 'default',
  name: 'Salon Menu',
  tree: {
    id: 'root',
    title: { en: 'Welcome to our salon!' },
    items: [
      { id: 'book', label: { en: '💇 Book a Slot' }, action: { kind: 'invoke_action', action_id: 'salon.select_timeslot' } },
      { id: 'offers', label: { en: '✨ Offers' }, action: { kind: 'invoke_action', action_id: 'core.static_text', params: { title: 'Festive offers available!' } } }
    ]
  },
  locales: { en: {} }
}

export const blankTemplate: MenuTemplate = {
  menu_id: 'default',
  name: 'Blank Menu',
  tree: {
    id: 'root',
    title: { en: 'Welcome!' },
    items: []
  },
  locales: { en: {} }
}

export const defaultTrigger = (menu_id = 'default') => ({
  trigger_id: 'hello_default',
  match: { type: 'contains', value: 'hello' },
  action: { kind: 'render_submenu', menu_id },
  enabled: true,
  priority: 100,
})

export const templatesCatalog: Array<{ key: string; label: string; tpl: MenuTemplate }> = [
  { key: 'retail', label: 'Retail', tpl: retailTemplate },
  { key: 'restaurant', label: 'Restaurant', tpl: restaurantTemplate },
  { key: 'salon', label: 'Salon', tpl: salonTemplate },
  { key: 'blank', label: 'Blank', tpl: blankTemplate },
]
