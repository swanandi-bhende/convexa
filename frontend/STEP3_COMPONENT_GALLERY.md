# Step 3: Component Gallery & Visual Reference

## Dashboard Layout Structure

```
┌─────────────────────────────────────────────────────────────────┐
│                          Hero Section                           │
│  "Autonomous Market Debate Platform" with CTAs                  │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                   Platform Overview Stats                       │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────┐
│  │Total Debates │ │ Active Now   │ │ Total Stake  │ │Avg Acc.  │
│  │     47       │ │      3       │ │  285.4 ETH   │ │ 69.8%    │
│  └──────────────┘ └──────────────┘ └──────────────┘ └──────────┘
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                    Featured Debate Section                      │
│  ┌──────────────────────────┐  ┌─────────────────────────────┐  │
│  │  DebatePreviewCard       │  │  ConvictionTracker          │  │
│  │  - ETH/USDC              │  │  - Bull: 65%                │  │
│  │  - Round 7 of 10         │  │  - Bear: 35%                │  │
│  │  - Bull vs Bear args     │  │  - Live indicator           │  │
│  │  - Confidence scores     │  │  - Threshold line           │  │
│  └──────────────────────────┘  └─────────────────────────────┘  │
│  ┌──────────────────────┐  ┌──────────────────────────┐         │
│  │ MarketSnapshot ETH   │  │ MarketSnapshot BTC       │         │
│  │ - $3,248.52          │  │ - $63,420.75             │         │
│  │ - +8.5% (24h)        │  │ - +5.2% (24h)            │         │
│  │ - Volume & Volatility│  │ - Volume & Volatility    │         │
│  └──────────────────────┘  └──────────────────────────┘         │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                  Agent Performance Stats                        │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────┐
│  │Bull Win Rate │ │Bear Win Rate │ │Most Accurate │ │ Avg Conf │
│  │     52%      │ │     48%      │ │Bull Agent    │ │  64.2%   │
│  └──────────────┘ └──────────────┘ └──────────────┘ └──────────┘
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                     Recent Debates Grid                         │
│  ┌──────────────────────────┐  ┌──────────────────────────┐     │
│  │  DebatePreviewCard       │  │  DebatePreviewCard       │     │
│  │  - BTC/USDC              │  │  - Other token pair      │     │
│  │  - Round 3 of 8          │  │  - ...                   │     │
│  │  - In Progress           │  │  - ...                   │     │
│  └──────────────────────────┘  └──────────────────────────┘     │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                     Quick Access Cards                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐           │
│  │Active Debates│  │Debate History│  │Agent Leaders │           │
│  │  Count: 3    │  │  Count: 47   │  │  Count: 34   │           │
│  └──────────────┘  └──────────────┘  └──────────────┘           │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                    About Convexa Section                        │
│  Information about the platform and how it works                │
└─────────────────────────────────────────────────────────────────┘
```

## Component Specifications

### MetricCard

**Visual Layout**:
```
┌─────────────────────────────────┐
│ Label                    [Icon] │
│                                 │
│ 47                              │
│ +12 this month (colored)        │
└─────────────────────────────────┘
```

**States**:
- Default: surface background, border-light
- Highlight: bull-50 background, bull-500 border

**Colors**:
- Text: text-tertiary (label), text-primary (value)
- Trend: success-500 (up), error-500 (down), text-secondary (neutral)

### MarketSnapshot

**Visual Layout**:
```
┌──────────────────────────────────────┐
│ ETH/USDC              $3,248.52      │
│ Real-time                            │
│                                      │
│ ┌────────────────┐                   │
│ │ +8.5%          │                   │
│ └────────────────┘                   │
│                                      │
│ 24h Volume        Volatility         │
│ $18.5B            2.4%               │
│ ▆▆▆▆▆ (bars)                       │
└──────────────────────────────────────┘
```

**Responsive**:
- Mobile: Full width
- Desktop: Side-by-side with gap-lg

### DebatePreviewCard

**Visual Layout**:
```
┌──────────────────────────────────────┐
│ ETH/USDC              [Live Badge]   │
│ Round 7 of 10                        │
│                                      │
│ ┌────────────────┐ ┌────────────────┐
│ │Bull Position   │ │Bear Position   │
│ │72% confidence  │ │58% confidence  │
│ │"ETH showing... │ │"Elevated vol...│
│ └────────────────┘ └────────────────┘
│                                      │
│ Bull Conviction          65          │
│ ████████████████░░░░░░░░            │
│ Bear Conviction          58          │
│ ██████████████░░░░░░░░░░░░          │
│                                      │
│ Bull Leading        View Details →  │
└──────────────────────────────────────┘
```

**Click Behavior**: Links to `/debates/active/{id}` or `/debates/history/{id}`

### ConvictionTracker

**Visual Layout**:
```
┌──────────────────────────────────────┐
│ Conviction Tracker        [Bull Win] │
│                                      │
│         Bull      Conviction   Bear  │
│          65        Score      58     │
│                                      │
│ ███████████████░░░░░░░░░░░░░░░░    │
│   54% Bull              46% Bear     │
│                                      │
│ Win Threshold (70)                   │
│ ████████████░░░░░░░░░░░░░░░░░░      │
│                                      │
│ Bull Advantage    In Progress        │
│ Difference: 7     Combined: 123      │
└──────────────────────────────────────┘
```

**Animated**: Score bars animate when values change

### StatsGrid

**Grid Layouts**:

#### 4 Columns (default)
```
┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────┐
│   Metric 1   │ │   Metric 2   │ │   Metric 3   │ │Metric 4  │
└──────────────┘ └──────────────┘ └──────────────┘ └──────────┘
```

#### 2 Columns
```
┌──────────────────────┐ ┌──────────────────────┐
│     Metric 1         │ │     Metric 2         │
└──────────────────────┘ └──────────────────────┘

┌──────────────────────┐ ┌──────────────────────┐
│     Metric 3         │ │     Metric 4         │
└──────────────────────┘ └──────────────────────┘
```

#### 3 Columns
```
┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐
│    Metric 1      │ │    Metric 2      │ │    Metric 3      │
└──────────────────┘ └──────────────────┘ └──────────────────┘
```

**Responsive Behavior**:
- Mobile: Always 1 column
- Tablet (sm): 2 columns for 4-col layout, 2 columns for 3-col layout
- Desktop (lg): Full specified columns

## Color System

### Hero Section
- Background: Gradient from bull-50 to background
- Border: bull-500 with 20% opacity
- Text: text-primary and text-secondary

### Status Badges
- Live: success-50 background, success-500 text
- Pending: warning-50 background, warning-500 text
- Completed: surface-tertiary background, text-secondary text

### Quick Access Cards
- Bull-themed: bull-50 hover:bull-100, bull-primary text
- Bear-themed: bear-50 hover:bear-100, bear-primary text

### Arguments
- Bull: bull-50 background, bull-500 border (20% opacity), bull-primary text
- Bear: bear-50 background, bear-500 border (20% opacity), bear-primary text

## Typography Hierarchy

```
Hero Title (display-lg, 36px, bold)
    ↓
Section Titles (heading-lg, 24px, semibold)
    ↓
Card Titles (heading-md, 20px, semibold)
    ↓
Body Text (body-md, 14px, regular)
    ↓
Secondary Text (body-sm, 12px, regular)
    ↓
Captions (text-tertiary, text-secondary)
```

## Spacing System

### Vertical Sections
- Between major sections: `space-y-3xl` (64px)
- Between subsections: `space-y-lg` or `space-y-xl`
- Within cards: `space-y-md` to `space-y-lg`

### Horizontal
- Page padding: `p-lg md:p-xl`
- Card padding: `p-lg` standard, `p-xl` spacious
- Gap between cards: `gap-md` to `gap-lg`

### Grid Gaps
- Metric grids: `gap-md` (16px)
- Debate cards: `gap-md` (16px)
- Quick access: `gap-md` (16px)

## Responsive Breakpoints

### Layout Changes

| Feature | Mobile | Tablet | Desktop |
|---------|--------|--------|---------|
| Hero CTA | Stack | Side-by-side | Side-by-side |
| Stats Grid 4-col | 1 col | 2 col | 4 col |
| Featured Debate | Stack | Stack | 3 col (debate, tracker, market) |
| Market Snapshots | Stack | Stack | 2 col |
| Recent Debates | Stack | 2 col | 2 col |
| Quick Access | Stack | 1 col | 3 col |

### Padding Adjustments
- Mobile: `px-lg py-lg`
- Tablet: `px-lg py-xl`
- Desktop: `px-xl py-3xl`

## Animation Details

### Hover States
- Cards: `hover:shadow-lg transition-all duration-200`
- Buttons: `hover:bg-bull-600 transition-colors`
- Score bars: `transition-all duration-500`

### Score Updates
- Conviction tracker animates over 500ms when scores change
- Score bars use smooth width transitions

## Accessibility

### Semantic HTML
- `<section>` for major sections
- `<h1>`, `<h2>` for heading hierarchy
- `<div>` for card containers
- Proper link semantics with `<Link>`

### Focus States
- Keyboard navigation fully supported
- Focus rings visible on interactive elements
- Link underlines for navigation clarity

### Color Contrast
- All text meets 4.5:1 WCAG AA standard
- Status badges use high-contrast colors
- Score indicators clearly differentiated

## Performance

### CSS
- All styles use Tailwind classes
- No inline styles (except for dynamic widths)
- CSS custom properties for theme consistency

### JavaScript
- No external API calls (mock data)
- Minimal re-renders
- Stateless functional components
- No heavy calculations

### Load Time
- Estimated first paint: <1s
- Estimated interactive: <2s
- All images optimized (none in Step 3)

## Browser Support

- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+
- Mobile browsers (iOS Safari, Chrome Mobile)

## Future Enhancements

- Add real data from Step 5 API integration
- Implement live updates via WebSocket
- Add animations for debate reveals
- Create debate detail views (Step 4)
- Add leaderboard page (Step 7)
