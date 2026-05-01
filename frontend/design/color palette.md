# Convexa Design System

## Overview

Convexa's design system is built on a foundation of brightness and spaciousness, with clear semantic color roles for the Bull vs Bear debate framework. The palette emphasizes readability, accessibility, and premium visual hierarchy.

## Color Palette

### Primary Backgrounds

| Token | Value | Usage |
|-------|-------|-------|
| `background` | #FFFFFF | Primary background for all views |
| `surface` | #F8FAFC | Default surface for cards and containers |
| `surface-secondary` | #F1F5F9 | Secondary surface for elevated content |
| `surface-tertiary` | #E2E8F0 | Tertiary surface for additional depth |

### Text & Foreground

| Token | Value | Usage |
|-------|-------|-------|
| `text-primary` | #0F172A | Primary text color (darkest) |
| `text-secondary` | #475569 | Secondary text for descriptions |
| `text-tertiary` | #64748B | Tertiary text for metadata |
| `text-inverted` | #FFFFFF | Text on dark/colored backgrounds |

### Bull Side (Bullish - Blue/Purple)

| Token | Value | Usage |
|-------|-------|-------|
| `bull-primary` | #2563EB | Bull primary interactive color |
| `bull-light` | #DBEAFE | Bull light background |
| `bull-lighter` | #EFF6FF | Bull lightest background |
| `bull-dark` | #1E40AF | Bull dark variant |
| `bull-accent` | #60A5FA | Bull accent for secondary actions |

### Bear Side (Bearish - Orange/Red)

| Token | Value | Usage |
|-------|-------|-------|
| `bear-primary` | #EA580C | Bear primary interactive color |
| `bear-light` | #FFEDD5 | Bear light background |
| `bear-lighter` | #FEF3C7 | Bear lightest background |
| `bear-dark` | #B45309 | Bear dark variant |
| `bear-accent` | #FB923C | Bear accent for secondary actions |

### Semantic Colors

| Token | Value | Usage |
|-------|-------|-------|
| `success` | #16A34A | Victory, successful predictions |
| `success-light` | #DCFCE7 | Success background |
| `warning` | #EABB08 | Caution, amber alerts |
| `warning-light` | #FEFCE8 | Warning background |
| `error` | #DC2626 | Error states, invalid input |
| `error-light` | #FEE2E2 | Error background |
| `info` | #0284C7 | Informational messages |
| `info-light` | #E0F2FE | Info background |

### Neutral & Borders

| Token | Value | Usage |
|-------|-------|-------|
| `border-light` | #E2E8F0 | Light border, dividers |
| `border-medium` | #CBD5E1 | Medium border |
| `border-dark` | #94A3B8 | Dark border |
| `overlay` | rgba(15, 23, 42, 0.4) | Modal overlay |
| `overlay-dark` | rgba(15, 23, 42, 0.6) | Darker overlay |

## Typography Scale

### Font Family

- **Primary**: System font stack (-apple-system, BlinkMacSystemFont, "Segoe UI", "Roboto", sans-serif)
- **Mono**: System monospace stack (ui-monospace, "Cascadia Code", "Source Code Pro", monospace)

### Font Sizes & Weights

| Name | Size | Weight | Line Height | Usage |
|------|------|--------|-------------|-------|
| `display-lg` | 36px | 700 | 44px | Page titles, hero content |
| `display-md` | 28px | 700 | 36px | Section titles |
| `heading-lg` | 24px | 600 | 32px | Card titles, subsections |
| `heading-md` | 20px | 600 | 28px | Smaller headings |
| `body-lg` | 16px | 400 | 24px | Body text, arguments |
| `body-md` | 14px | 400 | 20px | Default body text |
| `body-sm` | 12px | 400 | 18px | Secondary text, captions |
| `label-lg` | 14px | 600 | 20px | Labels, badges |
| `label-md` | 12px | 600 | 16px | Small labels |
| `mono-lg` | 14px | 400 | 20px | Code, metrics values |
| `mono-md` | 12px | 400 | 18px | Small code |

## Spacing Scale

8px base unit (8, 16, 24, 32, 40, 48, 56, 64, 72, 80, 88, 96)

| Token | Value | Usage |
|-------|-------|-------|
| `spacing-xs` | 4px | Minimal spacing |
| `spacing-sm` | 8px | Small gaps, icon spacing |
| `spacing-md` | 16px | Default padding, gaps |
| `spacing-lg` | 24px | Section padding |
| `spacing-xl` | 32px | Large section spacing |
| `spacing-2xl` | 48px | Extra large spacing |
| `spacing-3xl` | 64px | Hero spacing |

## Border Radius

| Token | Value | Usage |
|-------|-------|-------|
| `radius-sm` | 4px | Small buttons, badges |
| `radius-md` | 8px | Default cards, inputs |
| `radius-lg` | 12px | Large containers |
| `radius-xl` | 16px | Extra large components |
| `radius-full` | 9999px | Pills, full roundness |

## Shadows

| Token | Definition | Usage |
|-------|-----------|-------|
| `shadow-sm` | 0 1px 2px rgba(15, 23, 42, 0.05) | Subtle elevation |
| `shadow-md` | 0 4px 6px rgba(15, 23, 42, 0.1) | Default elevation |
| `shadow-lg` | 0 10px 15px rgba(15, 23, 42, 0.1) | Card hover, modals |
| `shadow-xl` | 0 20px 25px rgba(15, 23, 42, 0.1) | Dropdowns, tooltips |
| `shadow-2xl` | 0 25px 50px rgba(15, 23, 42, 0.15) | Maximum elevation |

## Opacity Scale

| Token | Value | Usage |
|-------|-------|-------|
| `opacity-disabled` | 0.5 | Disabled state |
| `opacity-hover` | 0.8 | Hover state |
| `opacity-focus` | 0.95 | Focus state |

## Design Principles

1. **Brightness**: Predominant use of white and very light backgrounds (>70% of visual space)
2. **Spaciousness**: Generous padding and margins create breathing room
3. **Hierarchy**: Clear visual distinction between primary, secondary, and tertiary content
4. **Contrast**: WCAG AA minimum contrast ratio (4.5:1) for all text
5. **Consistency**: All components follow defined token values
6. **Semantic Color**: Colors convey meaning (Bull=Blue, Bear=Orange, Success=Green)
typography:
  h1:
    fontFamily: Inter
    fontSize: 48px
    fontWeight: '700'
    lineHeight: '1.1'
    letterSpacing: -0.02em
  h2:
    fontFamily: Inter
    fontSize: 30px
    fontWeight: '600'
    lineHeight: '1.2'
    letterSpacing: -0.01em
  h3:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '600'
    lineHeight: '1.3'
  body-lg:
    fontFamily: Inter
    fontSize: 18px
    fontWeight: '400'
    lineHeight: '1.6'
  body-md:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: '1.5'
  body-sm:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: '1.5'
  label-caps:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '600'
    lineHeight: '1'
    letterSpacing: 0.05em
  data-mono:
    fontFamily: JetBrains Mono
    fontSize: 14px
    fontWeight: '450'
    lineHeight: '1.4'
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  unit: 4px
  xs: 4px
  sm: 8px
  md: 16px
  lg: 24px
  xl: 40px
  xxl: 64px
  gutter: 24px
  margin-page: 48px
---

## Brand & Style

This design system targets an institutional audience, bridging the gap between traditional high-finance reliability and the innovation of blockchain technology. The personality is defined by **Professionalism, Transparency, and Precision**. It intentionally avoids the high-energy "neon-on-black" tropes of retail crypto in favor of an airy, high-end SaaS aesthetic.

The visual style is **Modern Corporate Minimalism**. It prioritizes clarity through generous negative space and a rigorous information hierarchy. Trust is established not through decorative elements, but through functional excellence, high-legibility typography, and a restrained UI that feels both "light" and stable.

## Colors

The palette is anchored in a crisp, light-mode foundation. **Soft Gray (#F8FAFC)** serves as the primary surface color to reduce eye strain and provide a sophisticated backdrop for content containers. 

- **Primary Indigo (#4F46E5)**: Used for primary actions and brand presence. It conveys intelligence and stability.
- **Bullish Emerald (#10B981)**: Applied to positive market movements, buy actions, and successful statuses.
- **Bearish Rose (#F43F5E)**: A muted, professional red used for negative movements and sell actions, avoiding aggressive "danger" tones.
- **Neutrals**: Utilize a range of cool-toned slates for text and borders to maintain a cohesive, high-tech atmosphere.

## Typography

The typography system relies on **Inter** for all interface elements to ensure maximum legibility across dense data sets. Weights are used strategically to create hierarchy without relying on color shifts.

**JetBrains Mono** is introduced specifically for technical data strings, such as wallet addresses, transaction hashes, and smart contract code. This "technical edge" reminds the user of the underlying technology while maintaining the sophisticated shell. 

- Use **h1-h3** for major section headers.
- Use **label-caps** for table headers and small category descriptors.
- Ensure **data-mono** is always rendered with slightly more tracking than sans-serif text to aid character distinction in hashes.

## Layout & Spacing

The layout philosophy follows a **Fixed-Fluid Hybrid Grid**. Content is housed in a centered container (max-width 1440px) to maintain readability on ultra-wide monitors common in trading environments.

- **Generous Whitespace**: High-end appeal is achieved through "luxury of space." Do not crowd elements; use `xl` and `xxl` spacing for section vertical separation.
- **Rhythm**: All spacing is based on a 4px baseline, but defaults should lean toward larger increments (`md` and `lg`) to prevent a cluttered "spreadsheet" feel.
- **Gutters**: A standard 24px gutter ensures clear separation between functional modules or cards.

## Elevation & Depth

This design system uses **Tonal Layering and Soft Shadows** to establish depth. It avoids heavy, dark shadows in favor of ambient light-source simulations.

- **Base Layer**: Pure White (#FFFFFF) or the primary Soft Gray (#F8FAFC).
- **Surface Layer**: Cards and containers use a White background with a subtle `1px` border in `#E2E8F0`. 
- **Shadows**: Use extremely soft, low-opacity shadows (e.g., `y: 4, blur: 20, color: rgba(15, 23, 42, 0.05)`) to lift active components like hover-state cards or dropdown menus.
- **Interactive Depth**: Buttons should feel "tappable" through subtle transitions rather than heavy gradients. On hover, increase shadow spread rather than darkening the color significantly.

## Shapes

The shape language is **Subtle and Intentional**. By using the "Soft" (0.25rem) setting, the UI feels modern and approachable without losing its serious, institutional edge.

- **Standard Radius**: 4px for buttons, inputs, and small widgets.
- **Large Radius**: 8px (rounded-lg) for main content cards and modals.
- **Full Radius**: Reserved exclusively for status indicators (chips) and toggle switches to differentiate them from actionable buttons.

## Components

- **Buttons**: Primary buttons use the Brand Indigo with white text. Secondary buttons use a white background with an Indigo border. Soften the appearance with a slight `4px` corner radius.
- **Inputs**: Clean, outlined fields using `#E2E8F0`. On focus, the border transitions to Brand Indigo with a soft `2px` outer glow. Labels always sit above the input in `label-caps` style.
- **Data Tables**: Remove vertical lines. Use horizontal rules in `#F1F5F9`. The header row should be slightly darker (#F8FAFC) to anchor the data. Use `data-mono` for all numerical values and hashes.
- **Status Chips**: Use "Soft" fills (10% opacity of the status color) with high-contrast text. For example, a "Success" chip uses 10% Emerald background and 100% Emerald text.
- **Cards**: Use a white background, a 1px border (#E2E8F0), and an 8px corner radius. Intersperse with large amounts of whitespace between card headers and content.
- **Navigation**: A clean sidebar or top-nav with active states indicated by a 2px Indigo line and a subtle weight shift in the text. Icons should be "Light" weight (2px stroke) to match the airy aesthetic.