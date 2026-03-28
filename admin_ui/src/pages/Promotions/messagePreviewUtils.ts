/**
 * Match backend promotion body assembly for WhatsApp preview (see ``promotions.send_promotion_now`` /
 * ``append_cta_urls_to_message_text``).
 */
import type { Promotion, CtaEntry } from '@api/promotions'

export type PromotionPreviewFields = Pick<
  Promotion,
  | 'message'
  | 'interactive_type'
  | 'buttons'
  | 'list_sections'
  | 'cta_url'
  | 'cta_display_text'
  | 'cta_entries'
  | 'cta_append_urls_to_body'
  | 'offer_code'
>

export function promotionCtaEntriesForPreview(doc: PromotionPreviewFields): CtaEntry[] {
  if (doc.interactive_type !== 'cta_url') return []
  const fromEntries = (doc.cta_entries || []).filter(e => (e.url || '').trim())
  if (fromEntries.length) return fromEntries
  if (doc.cta_url?.trim()) {
    return [{ display_text: doc.cta_display_text || 'Shop Now', url: doc.cta_url.trim() }]
  }
  return []
}

export function promotionMessageWithLinks(doc: PromotionPreviewFields): string {
  let msg = doc.message || ''
  if (doc.interactive_type === 'button' && doc.buttons) {
    const links = doc.buttons.filter(b => b.url).map(b => `${b.title}: ${b.url}`)
    if (links.length) msg += '\n\n' + links.join('\n')
  } else if (doc.interactive_type === 'list' && doc.list_sections) {
    const links = doc.list_sections.flatMap(s => s.rows).filter(r => r.url).map(r => `${r.title}: ${r.url}`)
    if (links.length) msg += '\n\n' + links.join('\n')
  } else if (doc.interactive_type === 'cta_url' && doc.cta_append_urls_to_body !== false) {
    const entries = promotionCtaEntriesForPreview(doc)
    const missing = entries.filter(e => !msg.includes((e.url || '').trim()))
    if (missing.length) {
      msg += '\n\n' + missing.map(e => `${(e.display_text || 'Link').trim()}: ${(e.url || '').trim()}`).join('\n')
    }
  }
  const code = doc.offer_code?.trim()
  if (code && !msg.toLowerCase().includes(code.toLowerCase())) {
    msg += `\n\nUse code: ${code}`
  }
  return msg
}
