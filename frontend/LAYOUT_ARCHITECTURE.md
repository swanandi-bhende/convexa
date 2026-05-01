# Frontend Layout Architecture

This document describes the structure and organization of the Convexa frontend layout system.

## Directory Structure

```
src/
├── app/
│   ├── layout.tsx              # Root layout with MainLayout wrapper
│   ├── page.tsx                # Dashboard home page
│   ├── globals.css             # Global styles and design tokens
│   ├── debates/
│   │   ├── active/page.tsx     # Active debates viewer (Step 4)
│   │   └── history/page.tsx    # Debate history archive (Step 8)
│   ├── agents/
│   │   └── page.tsx            # Agent stats dashboard (Step 7)
│   └── settings/
│       └── page.tsx            # User settings (Phase 2)
│
├── components/
│   ├── index.ts                # Component exports
│   ├── Header.tsx              # Header with branding and wallet
│   ├── Sidebar.tsx             # Navigation sidebar (collapsible)
│   └── MainLayout.tsx          # Combined layout wrapper
│
├── types/
│   └── navigation.ts           # Navigation types and constants
│
└── design/
    ├── tokens.ts               # Design system tokens (colors, spacing, etc)
    └── color palette.md        # Design documentation
```

## Component Architecture

### MainLayout
Top-level layout component that combines Header, Sidebar, and content area. All pages are wrapped in this layout via `root layout.tsx`.

**Features:**
- Responsive grid layout (Header → Sidebar + Content)
- Max-width container for content (max-w-7xl)
- Spacious padding (p-lg to p-xl)
- Scrollable content area with fixed header

### Header
Sticky header at the top of the page.

**Elements:**
- **Logo/Branding**: "C" badge with "Convexa" text
- **Network Status**: Shows current network (Unichain Sepolia)
- **Wallet Connection**: Displays connected wallet address or "Connect Wallet" button
- **Mobile Menu Trigger**: Menu icon for mobile navigation (collapse behavior in Sidebar)

**Props:**
- `walletAddress?: string` - Connected wallet address
- `networkName?: string` - Network name (default: "Unichain Sepolia")
- `isConnected?: boolean` - Connection status

### Sidebar
Collapsible navigation sidebar (hidden on mobile, visible on desktop with md breakpoint).

**Features:**
- **Expandable/Collapsible**: Toggle button at bottom expands/collapses
- **Active State**: Current page highlighted with bull-100 background and bull-primary text
- **Navigation Sections**: Main section (Dashboard, Active Debates, History) and secondary section (Agent Stats, Settings)
- **Icons**: Each nav item has an icon
- **Responsive**: Hidden on mobile (<md), visible on desktop
- **Hover States**: Smooth transitions on hover

**Props:**
- None (uses `usePathname()` for active detection)

### Dashboard (Home Page)
Landing page with several sections designed with spaciousness in mind.

**Sections:**
1. **Hero Section** - Title, description, call-to-action buttons
2. **Metrics Cards** - 4 key performance indicators in responsive grid
3. **Current Debate** - Latest debate summary with score bars and CTA buttons
4. **Quick Links** - 3 main actions (Watch Debates, View History, Agent Stats)

**Design Highlights:**
- Large whitespace and breathing room
- Spacious padding (p-xl, p-2xl, p-3xl)
- Bright colors (bull-50, bear-50 backgrounds)
- Card-based layout with subtle shadows

## Design Token Integration

All components use design tokens from `src/design/tokens.ts`:

### Color Usage
- **Bull**: Blue (#2563EB) - Bullish positions, primary actions
- **Bear**: Orange (#EA580C) - Bearish positions, secondary actions
- **Success**: Green (#16A34A) - Victories, positive states
- **Text**: Primary (#0F172A), Secondary (#475569), Tertiary (#64748B)
- **Surfaces**: White backgrounds, light gray surfaces

### Spacing
- Base unit: 8px
- Uses Tailwind spacing tokens (xs, sm, md, lg, xl, 2xl, 3xl)
- Classes: p-sm, p-md, p-lg, gap-md, etc.

### Typography
- **Display**: display-lg, display-md for titles
- **Headings**: heading-lg, heading-md for section titles
- **Body**: body-lg, body-md, body-sm for content
- **Labels**: label-lg, label-md for controls

## Tailwind Configuration

The `tailwind.config.ts` extends the default Tailwind theme with:

- **Custom Colors**: All design token colors mapped
- **Custom Spacing**: 8px base unit spacing scale
- **Custom Font Sizes**: Typography scale with line heights
- **Custom Shadows**: Elevation system

## Responsive Design

### Breakpoints (Tailwind defaults)
- **Mobile**: < 640px (default)
- **Tablet**: sm (640px), md (768px)
- **Desktop**: lg (1024px), xl (1280px)

### Layout Adjustments
- **Mobile**: Single column, no sidebar, hamburger menu in header
- **Tablet/Desktop**: Sidebar visible, content has max-width

### Component Behavior
- **Sidebar**: Hidden mobile, visible md+
- **Header**: Always visible, mobile menu icon appears
- **Metrics Grid**: 1 column mobile → 2 columns tablet → 4 columns desktop
- **Content Padding**: p-lg mobile → p-xl desktop

## Color Theme

The design uses a bright, spacious theme:

- **70% white/light backgrounds** for brightness
- **Large padding and margins** for spaciousness
- **Semantic colors** for user guidance
- **High contrast text** for readability
- **Subtle shadows** for depth without heaviness

## Navigation Flow

1. **Dashboard** (`/`) - Home with metrics and quick links
2. **Active Debates** (`/debates/active`) - Live debate viewer (Step 4)
3. **Debate History** (`/debates/history`) - Archive (Step 8)
4. **Agent Stats** (`/agents`) - Performance leaderboard (Step 7)
5. **Settings** (`/settings`) - User preferences (Phase 2)

## Next Steps

- **Step 3**: Dashboard landing page refinements
- **Step 4**: Live Debate Viewer with split-screen Bull vs Bear
- **Step 5**: Real-time data integration and WebSocket
- **Step 7**: Agent Performance Dashboard
- **Step 8**: Debate History with search/filter

## Notes

- All components use React Client Components (`'use client'`)
- Navigation uses Next.js `usePathname()` for active states
- Images and assets should be placed in `public/` directory
- Component composition follows React best practices
- Accessibility (WCAG AA) standards are implemented
