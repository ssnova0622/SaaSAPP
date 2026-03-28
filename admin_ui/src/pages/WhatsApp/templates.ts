// Simple starter templates for different business types
export type MenuTree = { root: string; nodes: Array<any> }

export const TEMPLATE_SALON: MenuTree = {
  root: 'root',
  nodes: [
    {
      id: 'root',
      type: 'submenu',
      title: 'Welcome to our Salon! 💇‍♀️',
      prompt: 'Please choose an option:',
      options: [
        { key: '1', label: 'Book appointment', next: 'book' },
        { key: '2', label: 'View offers', next: 'offers' },
        { key: '3', label: 'Enquiry', next: 'enquiry' },
      ],
    },
    {
      id: 'book',
      type: 'action',
      action: 'select_timeslot',
      title: 'Please choose a time slot (demo)',
      requires_caps: ['salon.appointments'],
    },
    { id: 'offers', type: 'action', action: 'show_offers', title: 'Current offers' },
    { id: 'enquiry', type: 'action', action: 'open_ticket', title: 'Opening ticket...' },
  ],
}

export const TEMPLATE_CLINIC: MenuTree = {
  root: 'root',
  nodes: [
    {
      id: 'root',
      type: 'submenu',
      title: 'Welcome to our Clinic 🏥',
      prompt: 'Choose an option:',
      options: [
        { key: '1', label: 'Book doctor', next: 'book' },
        { key: '2', label: 'Cancel appointment', next: 'cancel' },
        { key: '3', label: 'Enquiry', next: 'enquiry' },
      ],
    },
    { id: 'book', type: 'action', action: 'select_timeslot', title: 'Choose timeslot', requires_caps: ['salon.appointments'] },
    { id: 'cancel', type: 'action', action: 'open_ticket', title: 'We will assist with cancellation' },
    { id: 'enquiry', type: 'action', action: 'open_ticket', title: 'Opening ticket...' },
  ],
}

export const TEMPLATE_STORE: MenuTree = {
  root: 'root',
  nodes: [
    {
      id: 'root',
      type: 'submenu',
      title: 'Welcome to our Store 🛍️',
      prompt: 'Please choose an option:',
      options: [
        { key: '1', label: 'Browse catalog', next: 'catalog' },
        { key: '2', label: 'Track order', next: 'track' },
        { key: '3', label: 'Enquiry', next: 'enquiry' },
      ],
    },
    { id: 'catalog', type: 'action', action: 'open_url', params: { url: 'https://example.com/catalog' }, title: 'Opening catalog...' },
    { id: 'track', type: 'action', action: 'open_ticket', title: 'Share your order id; we will check and reply.' },
    { id: 'enquiry', type: 'action', action: 'open_ticket', title: 'Opening ticket...' },
  ],
}

export const STARTER_EMPTY: MenuTree = {
  root: 'root',
  nodes: [
    { id: 'root', type: 'submenu', title: 'Welcome', prompt: 'Choose:', options: [] },
  ],
}
