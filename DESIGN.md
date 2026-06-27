---
version: alpha
name: TechShop AI
description: Visual identity for a Vietnamese electronics e-commerce chat assistant — laptop, phone, tablet advisory.

colors:
  primary: "#2563eb"
  primary-dark: "#1d4ed8"
  primary-light: "#eff6ff"
  surface: "#ffffff"
  bg: "#f1f5f9"
  border: "#e2e8f0"
  text: "#1e293b"
  text-muted: "#64748b"
  success: "#16a34a"
  success-light: "#f0fdf4"
  warning-bg: "#fef9c3"
  warning-text: "#854d0e"
  error-bg: "#fee2e2"
  error-text: "#991b1b"
  user-bubble: "#2563eb"
  badge-bg: "#fef9c3"
  badge-text: "#854d0e"

typography:
  bot-name:
    fontFamily: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif
    fontSize: 17px
    fontWeight: 700
    letterSpacing: 0.2px
  bot-tagline:
    fontFamily: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif
    fontSize: 12px
  body:
    fontFamily: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif
    fontSize: 14.5px
    lineHeight: 1.55
  card-name:
    fontFamily: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif
    fontSize: 13px
    fontWeight: 600
    lineHeight: 1.4
  card-price:
    fontFamily: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif
    fontSize: 13px
    fontWeight: 700
  label-small:
    fontFamily: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif
    fontSize: 11px
  label-mono:
    fontFamily: ui-monospace, 'SF Mono', Menlo, monospace
    fontSize: 11px
  quick-btn:
    fontFamily: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif
    fontSize: 12.5px

rounded:
  pill: 9999px
  lg: 20px
  md: 18px
  card: 14px
  sm: 4px

spacing:
  xs: 4px
  sm: 8px
  md: 12px
  lg: 16px
  xl: 20px
  2xl: 24px

components:
  chat-wrapper:
    backgroundColor: "{colors.surface}"
    rounded: "{rounded.lg}"
    width: "100%; max-width: 780px"
    height: "92vh; max-height: 860px"

  chat-header:
    backgroundColor: "linear-gradient(135deg, {colors.primary} 0%, {colors.primary-dark} 100%)"
    textColor: "#ffffff"
    padding: "{spacing.lg} {spacing.xl}"

  bubble-bot:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.text}"
    rounded: "{rounded.md}"
    padding: "11px 15px"
    typography: "{typography.body}"

  bubble-user:
    backgroundColor: "{colors.user-bubble}"
    textColor: "#ffffff"
    rounded: "{rounded.md}"
    padding: "11px 15px"
    typography: "{typography.body}"

  product-card:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.text}"
    rounded: "{rounded.card}"
    padding: "{spacing.md}"

  product-card-hover:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.text}"
    rounded: "{rounded.card}"
    padding: "{spacing.md}"

  quick-btn:
    backgroundColor: "{colors.primary-light}"
    textColor: "{colors.primary}"
    rounded: "{rounded.pill}"
    padding: "6px 12px"
    typography: "{typography.quick-btn}"

  send-btn:
    backgroundColor: "{colors.primary}"
    textColor: "#ffffff"
    rounded: "{rounded.pill}"
    width: "44px"
    height: "44px"

  order-card:
    backgroundColor: "{colors.success-light}"
    textColor: "{colors.text}"
    rounded: "{rounded.card}"
    padding: "{spacing.lg}"

  badge-recommended:
    backgroundColor: "{colors.badge-bg}"
    textColor: "{colors.badge-text}"
    rounded: "{rounded.pill}"
    padding: "2px 7px"

  input-field:
    backgroundColor: "#f8fafc"
    textColor: "{colors.text}"
    rounded: "{rounded.pill}"
    padding: "11px 16px"
    typography: "{typography.body}"

  conn-banner-connecting:
    backgroundColor: "{colors.warning-bg}"
    textColor: "{colors.warning-text}"
    rounded: "{rounded.pill}"

  conn-banner-error:
    backgroundColor: "{colors.error-bg}"
    textColor: "{colors.error-text}"
    rounded: "{rounded.pill}"
---

## Overview

TechShop AI is a Vietnamese electronics retail assistant delivered as a compact chat widget. The visual identity is built around **trusted authority** — the blue gradient header signals reliability, while the clean white chat surface keeps focus on the conversation. Product cards break out of the chat stream as tangible objects the user can inspect and act on.

The design prioritises Vietnamese consumer context: touch-friendly tap targets, quick-reply chips for common requests (laptop, phone, tablet categories), and a streaming cursor that signals real-time AI reasoning rather than a loading spinner.

## Colors

The palette uses a Tailwind Blue spine as the interaction driver — high-contrast, universally read as "digital trust" across Vietnamese e-commerce contexts.

- **Primary (#2563eb):** All interactive controls — header gradient base, user bubbles, send button, card price labels, focus rings. One hue, consistently applied.
- **Primary Dark (#1d4ed8):** Header gradient terminus and hover state. Slightly cooler to give the gradient directionality.
- **Primary Light (#eff6ff):** Bot avatar background and quick-reply chip fill. Same hue family, desaturated — creates visual kinship without competing with primary.
- **Surface (#ffffff):** Bot message bubbles and product cards. Absolute white makes streamed text maximally legible.
- **Background (#f1f5f9):** Page canvas. Slate-tinted rather than neutral grey — the slight blue bias coheres with the primary hue family.
- **Border (#e2e8f0):** Hairline separators and card outlines. Cool-grey keeps the interface airy.
- **Text (#1e293b):** Slate-900 equivalent. Deep enough for WCAG AA at all type sizes.
- **Text Muted (#64748b):** Ratings, timestamps, labels — enough contrast against white for secondary information.
- **Success (#16a34a) / Success Light (#f0fdf4):** Reserved exclusively for order confirmation. Semantic green stays isolated from the blue accent so completion reads as a different class of event.

## Typography

Single typeface: the system sans stack (`-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto`). Rationale: Vietnamese users are on diverse devices; the system face is always present, renders Vietnamese diacritics correctly without custom font loading, and matches the native OS context that builds trust in a shopping flow.

Type scale is intentionally narrow — five sizes covering the full hierarchy:

| Role | Size | Weight | Usage |
|---|---|---|---|
| `bot-name` | 17px / 700 | Bold | Header bot identity |
| `body` | 14.5px / 400 | Regular | Chat bubbles, descriptions |
| `card-name` | 13px / 600 | Semibold | Product card titles |
| `card-price` | 13px / 700 | Bold | Price labels (primary color) |
| `label-small` | 11px / 400 | Regular | Ratings, metadata, session ID |

Monospace (`label-mono`) used only for order IDs — signals machine-generated reference codes.

## Layout

The widget is a vertically stacked flex column capped at `780px × 860px`, centred on the viewport. Three zones divide the height: fixed header, scrolling message list, fixed input bar. This prevents the input from scrolling out of reach on mobile — critical for a conversational interface.

Product cards break into a CSS grid (`repeat(auto-fill, minmax(200px, 1fr))`) anchored to the bot message flow, not the full viewport width. Cards align left with the bot avatar so they read as the bot's structured response.

## Shapes

Border radii encode interaction level:

- `pill (9999px)` — interactive controls: send button, quick-reply chips, clear button, status badges. The pill signals "tap me."
- `lg (20px) / md (18px)` — chat container and message bubbles. Soft without being cartoon-like.
- `card (14px)` — product cards and order confirmation. Slightly tighter than bubbles to distinguish information objects from conversation.
- `sm (4px)` — bubble "tail" corner (bottom-left for bot, bottom-right for user). The flattened corner gives directionality to the speech bubble shape.

## Components

### Chat Bubbles

User messages: primary blue fill, white text, right-aligned with flattened bottom-right corner. Bot messages: white fill with a 1px border and shadow, left-aligned with flattened bottom-left corner. The contrast pair makes authorship unambiguous at a glance.

The streaming cursor (`▍`) shares the primary color and blinks at 0.75s — slow enough to read as purposeful, fast enough to signal activity.

### Product Cards

Cards use a 1px border at rest; on hover, the border transitions to primary and a directional box-shadow elevates the card 1px. The `🏆 Đề xuất` badge calls out the top recommendation using the warning-adjacent amber pair — distinct from success green, attention-grabbing without alarm connotation.

Cards are clickable and trigger a follow-up query (`"Cho tôi biết thêm về [name]"`), so they function as both display and navigation. Pointer cursor, hover lift, and border highlight together ensure this affordance is discoverable.

### Quick Reply Chips

Pre-seeded with the five most common Vietnamese shopping intents. Primary-light fill on primary border — legible, clearly tappable, visually subordinate to the send action. Disabled state reduces opacity to 40% during processing.

### Order Confirmation Card

Green gradient background (`#f0fdf4 → #dcfce7`) with a 1.5px green border. Visually distinct from all other surfaces to mark the terminal success state. Order ID rendered in monospace primary blue to look like a reference number.

### Connection Banner

Two semantic states only: `connecting` (amber) and `disconnected` (red). Auto-dismisses on reconnect by hiding the element. Position between header and message list keeps it visible without disrupting the chat flow.

## Do's and Don'ts

**Do**
- Use `{colors.primary}` for all interactive affordances; keep semantic colours (success, warning, error) for their specific states only.
- Apply the `pill` radius to all controls the user taps directly; apply `card` radius to information objects.
- Keep product card grids left-aligned with bot messages — they are part of the bot's reply, not page-level UI.
- Use the monospace stack only for order IDs and session tokens.

**Don't**
- Don't use `{colors.success}` or `{colors.warning-*}` as decorative accents; reserve them for order confirmation and connection status.
- Don't add new typefaces — the diacritic rendering of Vietnamese requires a typeface with full Latin-ext coverage; system fonts guarantee this, webfonts do not unless explicitly checked.
- Don't centre-align product cards or chat messages — left-alignment of bot content is a directional signal, not an aesthetic default.
- Don't increase border radii on cards above `14px` — it begins to conflict with the more rounded bubble and control shapes.
