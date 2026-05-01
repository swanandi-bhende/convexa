# Step 3: Component Architecture & Dependencies

## Component Hierarchy

```
src/app/page.tsx (Dashboard)
├── MetricCard
│   ├── Uses: design tokens (colors, spacing)
│   ├── Props: label, value, trend, trendDirection, icon, highlight
│   └── Features: Hover effects, trend colors, icon support
│
├── MarketSnapshot
│   ├── Uses: design tokens, formatting utilities
│   ├── Props: tokenPair, currentPrice, priceChange24h, volume24h, volatility, timestamp, sparkline
│   └── Features: Directional indicators, sparkline, volatility bars
│
├── DebatePreviewCard
│   ├── Uses: Next.js Link, design tokens
│   ├── Props: id, tokenPair, round, totalRounds, bullScore, bearScore, status, arguments, confidence
│   ├── Features: Score bars, argument preview, status badge, clickable link
│   └── Routes to: /debates/active/{id} or /debates/history/{id}
│
├── ConvictionTracker
│   ├── Uses: React hooks (useState, useEffect), design tokens
│   ├── Props: bullScore, bearScore, winThreshold, animationDuration, showThreshold
│   ├── State: Animated score values
│   └── Features: Animated bars, threshold line, status indicators
│
└── StatsGrid
    ├── Uses: design tokens
    ├── Props: title, subtitle, stats array, columns
    ├── Responsive: 1-4 columns based on screen size
    └── Features: Color-coded stats, change indicators
```

## Data Flow

```
Dashboard Page Component
│
├─ Read Mock Data
│  ├── recentDebates
│  ├── platformStats
│  └── agentStats
│
└─ Render Sections
   ├── Hero Section
   │  └── Inline JSX with buttons
   │
   ├── StatsGrid ("Platform Overview")
   │  ├── Props: title, subtitle, stats={platformStats}
   │  └── Renders: 4 StatItems in 4-column grid
   │
   ├── Featured Debate Section
   │  ├── DebatePreviewCard
   │  │  ├── Props: {...recentDebates[0]}
   │  │  └── Features: Full arguments, confidence scores
   │  │
   │  ├── ConvictionTracker
   │  │  ├── Props: bullScore, bearScore, winThreshold
   │  │  └── Animates when scores change
   │  │
   │  └── MarketSnapshot (x2)
   │     ├── ETH/USDC snapshot
   │     └── BTC/USDC snapshot
   │
   ├── StatsGrid ("Agent Performance")
   │  ├── Props: title, subtitle, stats={agentStats}
   │  └── Renders: 4 StatItems with colors
   │
   ├── Recent Debates Grid
   │  └── DebatePreviewCard (x2)
   │     └── Props: {...recentDebates[1..n]}
   │
   ├── Quick Access Cards
   │  └── Inline cards with counts and colors
   │
   └── About Section
      └── Plain text information
```

## Component Reusability

### MetricCard
```
Used in:
- StatsGrid (as stat display)
- Custom metrics sections
- Any 1-metric layout

Can be extended:
- Add icons
- Add trends
- Add highlights
- Add custom colors
```

### MarketSnapshot
```
Used in:
- Dashboard featured section
- Future: Live debate page
- Future: Debate detail page

Can be extended:
- Add order book data
- Add trading volume details
- Add technical indicators
- Add multiple timeframes
```

### DebatePreviewCard
```
Used in:
- Dashboard featured debate
- Dashboard recent debates grid
- Future: Debate list pages
- Future: Sidebar recent activity

Can be extended:
- Add judge verdict preview
- Add more argument details
- Add staking info
- Add market impact
```

### ConvictionTracker
```
Used in:
- Dashboard featured debate section
- Future: Live debate page
- Future: Debate detail page
- Future: Leaderboard tracking

Can be extended:
- Add historical tracking
- Add round-by-round history
- Add prediction accuracy
- Add settlement info
```

### StatsGrid
```
Used in:
- Dashboard platform stats
- Dashboard agent stats
- Future: Leaderboard page
- Future: Agent detail pages

Can be extended:
- Add sorting
- Add filtering
- Add comparisons
- Add custom stat types
```

## File Organization

```
frontend/src/
├── app/
│   ├── page.tsx                    ← Main dashboard
│   ├── layout.tsx                  ← Root layout with MainLayout
│   ├── globals.css                 ← Design tokens CSS
│   ├── debates/
│   │   ├── active/
│   │   │   └── page.tsx            ← Placeholder for Step 4
│   │   └── history/
│   │       └── page.tsx            ← Placeholder for Step 8
│   ├── agents/
│   │   └── page.tsx                ← Placeholder for Step 7
│   └── settings/
│       └── page.tsx                ← Placeholder for Phase 2
│
├── components/
│   ├── index.ts                    ← Exports all components
│   ├── Header.tsx                  ← Navigation header
│   ├── Sidebar.tsx                 ← Navigation sidebar
│   ├── MainLayout.tsx              ← Master layout
│   ├── MetricCard.tsx              ← Step 3 new
│   ├── MarketSnapshot.tsx          ← Step 3 new
│   ├── DebatePreviewCard.tsx       ← Step 3 new
│   ├── ConvictionTracker.tsx       ← Step 3 new
│   └── StatsGrid.tsx               ← Step 3 new
│
├── types/
│   └── navigation.ts               ← Navigation types
│
└── design/
    ├── tokens.ts                   ← Design system tokens
    └── color palette.md            ← Color documentation
```

## Import Statements

```typescript
// In src/app/page.tsx
import React from 'react';
import Link from 'next/link';
import {
  MetricCard,
  MarketSnapshot,
  DebatePreviewCard,
  ConvictionTracker,
  StatsGrid,
} from '@/components';
```

## Design Token Usage

### Colors
```typescript
// Used throughout components:
- bg-background (white)
- bg-surface (light gray)
- bg-bull-50 (bull backgrounds)
- bg-bear-50 (bear backgrounds)
- text-text-primary (dark text)
- text-bull-500 (bull accent)
- text-bear-500 (bear accent)
- border-border-light (subtle borders)
```

### Spacing
```typescript
// Consistent spacing scale:
- gap-md (16px) - default gap between cards
- gap-lg (24px) - larger gaps
- gap-xl (32px) - hero spacing
- p-lg (24px) - card padding
- p-xl (32px) - spacious sections
- p-2xl, p-3xl - hero section
```

### Typography
```typescript
// Font sizes:
- text-display-lg - hero title
- text-heading-lg - section titles
- text-heading-md - card titles
- text-body-md - body text
- text-body-sm - secondary text
- text-label-md - labels
```

## State Management

```typescript
// Dashboard Page Component
- No hooks needed for Step 3 (all mock data)
- All components are stateless

// ConvictionTracker Component (has internal state)
export const ConvictionTracker: React.FC<Props> = ({...}) => {
  const [bullScore, setBullScore] = useState(initialBullScore);
  const [bearScore, setBearScore] = useState(initialBearScore);
  
  useEffect(() => {
    // Updates when props change
    setBullScore(initialBullScore);
    setBearScore(initialBearScore);
  }, [initialBullScore, initialBearScore]);
  
  return (...)
}
```

## Props Flow

```
Dashboard (page.tsx)
│
├─→ MetricCard
│   ✓ Receives: label, value, trend, trendDirection, icon, highlight
│   ✓ Controlled (props only)
│
├─→ MarketSnapshot
│   ✓ Receives: tokenPair, currentPrice, priceChange24h, volume24h, volatility, sparkline
│   ✓ Controlled (props only)
│
├─→ DebatePreviewCard
│   ✓ Receives: id, tokenPair, round, totalRounds, bullScore, bearScore, status, arguments, confidence
│   ✓ Controlled (props only)
│   ✓ Renders Link with href
│
├─→ ConvictionTracker
│   ✓ Receives: bullScore, bearScore, winThreshold, animationDuration, showThreshold
│   ✓ Has internal useState for animations
│   ✓ Responds to prop changes via useEffect
│
└─→ StatsGrid
    ✓ Receives: title, subtitle, stats array, columns
    ✓ Controlled (props only)
    ✓ Maps over stats to render MetricCard components
```

## Event Handlers

### DebatePreviewCard
```typescript
// Wrapped in Link component
// Click → Navigate to /debates/active/{id} or /debates/history/{id}
```

### ConvictionTracker
```typescript
// No event handlers
// Animation triggered by prop changes via useEffect
```

### All Other Components
```typescript
// No event handlers
// Display-only (data visualization)
```

## CSS Class Patterns

### Card Styling
```typescript
// Standard card:
className="rounded-lg border border-border-light bg-surface p-lg transition-all hover:shadow-lg"

// Highlighted card:
className="rounded-lg border border-bull-500 bg-bull-50 p-lg transition-all hover:shadow-lg"

// Quick access card:
className="rounded-lg border border-bull-500 border-opacity-20 bg-bull-50 p-lg hover:bg-bull-100"
```

### Grid Patterns
```typescript
// 4-column responsive:
className="grid grid-cols-1 gap-md md:grid-cols-2 lg:grid-cols-4"

// 2-column responsive:
className="grid grid-cols-1 gap-md md:grid-cols-2"

// Flex stack:
className="flex flex-col sm:flex-row gap-lg"
```

### Text Patterns
```typescript
// Heading:
className="text-heading-lg font-semibold text-text-primary"

// Description:
className="text-body-md text-text-secondary"

// Value:
className="text-heading-md font-semibold text-text-primary"
```

## Testing Checklist

- [ ] All 5 new components render without errors
- [ ] MetricCard displays with and without trends
- [ ] MarketSnapshot shows price/volume/volatility correctly
- [ ] DebatePreviewCard displays both arguments
- [ ] ConvictionTracker animates on score changes
- [ ] StatsGrid responsive layout works (1/2/3/4 columns)
- [ ] Links navigate correctly
- [ ] Hover states work on cards
- [ ] Colors match design system
- [ ] Typography hierarchy is readable
- [ ] Mobile responsive (1 column)
- [ ] Tablet responsive (2 columns)
- [ ] Desktop responsive (full layout)
- [ ] No console errors
- [ ] No TypeScript errors
- [ ] Page loads in <2s

## Performance Metrics

### Build Size
- New CSS: Tailwind classes only (~20KB gzipped)
- New JS: Component code (~15KB gzipped)
- Total increase: ~35KB

### Runtime Performance
- No API calls (mock data only)
- No image optimization needed
- No external libraries needed
- Smooth animations (GPU accelerated)
- Fast first paint (<1s)

## Accessibility Checklist

- [ ] Semantic HTML elements used
- [ ] Heading hierarchy proper (h1 > h2)
- [ ] High contrast text (4.5:1 WCAG AA)
- [ ] Color not only differentiator
- [ ] Keyboard navigation works
- [ ] Focus states visible
- [ ] ARIA labels present where needed
- [ ] No flash content
- [ ] Page structure logical

## Future Extensibility

### For Step 4 (Live Debate Viewer)
- Reuse DebatePreviewCard
- Reuse ConvictionTracker
- Reuse MarketSnapshot
- Create new: ArgumentDetail, JudgeVerdict components

### For Step 5 (Real-time Data)
- Replace mock data with API calls
- Add WebSocket for live updates
- Use React hooks: useEffect, useState, useCallback
- Add error boundaries
- Add loading states

### For Step 7 (Agent Dashboard)
- Reuse StatsGrid for leaderboards
- Reuse MetricCard for agent metrics
- Create new: AgentChart, PerformanceHistory components

### For Step 8 (History)
- Reuse DebatePreviewCard
- Reuse StatsGrid
- Add search/filter functionality
- Add date range picker
