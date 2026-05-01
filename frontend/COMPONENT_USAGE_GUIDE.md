# Component Usage Guide

Quick reference for using the layout components and design tokens.

## Importing Components

```typescript
import { Header, Sidebar, MainLayout } from '@/components';
import { colors, spacing, typography } from '@/design/tokens';
```

## Using the MainLayout (Default in Root)

The MainLayout is already integrated into the root layout, so all pages automatically have Header + Sidebar + Content area.

```typescript
// src/app/some-page/page.tsx
export default function SomePage() {
  return (
    <div className="space-y-lg">
      <h1 className="text-display-md font-bold">Page Title</h1>
      {/* Page content */}
    </div>
  );
}
```

## Design Tokens in Components

### Colors
```typescript
// Using Tailwind class names
<div className="bg-bull-500 text-text-inverted p-lg">
  Bull position content
</div>

// Using CSS custom properties
<div style={{
  backgroundColor: colors.bull.primary,
  color: colors.textInverted,
}}>
  Bull content
</div>
```

### Spacing
```typescript
// Tailwind classes (recommended)
<div className="px-lg py-md gap-xl">
  Spacious content
</div>

// Spacing scale
const SPACING = {
  xs: spacing.xs,     // 4px
  sm: spacing.sm,     // 8px
  md: spacing.md,     // 16px
  lg: spacing.lg,     // 24px
  xl: spacing.xl,     // 32px
};
```

### Typography
```typescript
// Using Tailwind size classes
<h1 className="text-display-lg font-bold">Page Title</h1>
<p className="text-body-lg text-text-secondary">Description</p>

// Custom styles
<div style={typography.styles.headingLg}>
  Styled heading
</div>
```

## Common Component Patterns

### Card Component
```typescript
<div className="surface-default rounded-lg border border-border-light bg-surface p-lg hover:shadow-md transition-shadow">
  <p className="text-label-lg font-semibold text-text-primary">Card Title</p>
  <p className="text-body-md text-text-secondary mt-sm">Card content</p>
</div>
```

### Metric Card
```typescript
<div className="rounded-lg bg-surface border border-border-light p-lg">
  <p className="text-body-sm text-text-tertiary">Label</p>
  <p className="text-heading-md font-semibold text-text-primary mt-sm">Value</p>
  <p className="text-body-sm text-text-secondary mt-sm">Trend info</p>
</div>
```

### Section with Title
```typescript
<section className="space-y-lg">
  <h2 className="text-heading-lg font-semibold text-text-primary">
    Section Title
  </h2>
  {/* Section content */}
</section>
```

### Bull vs Bear Split
```typescript
<div className="grid grid-cols-1 md:grid-cols-2 gap-lg">
  {/* Bull Side */}
  <div className="bg-bull-50 border-l-4 border-bull-500 p-lg rounded-lg">
    <p className="text-label-lg font-semibold text-bull-primary">Bull Position</p>
  </div>
  
  {/* Bear Side */}
  <div className="bg-bear-50 border-l-4 border-bear-500 p-lg rounded-lg">
    <p className="text-label-lg font-semibold text-bear-primary">Bear Position</p>
  </div>
</div>
```

### Progress/Score Bar
```typescript
<div className="space-y-sm">
  <div className="flex justify-between">
    <p className="text-label-md font-semibold">Score</p>
    <p className="text-label-md font-semibold">75/100</p>
  </div>
  <div className="h-3 w-full bg-border-light rounded-full overflow-hidden">
    <div 
      className="h-full bg-bull-500 transition-all"
      style={{ width: '75%' }}
    />
  </div>
</div>
```

### Button Variants

#### Primary (Bull)
```typescript
<button className="bg-bull-500 text-text-inverted px-lg py-md rounded-md font-semibold hover:bg-bull-600 transition-colors">
  Action
</button>
```

#### Secondary (Outlined)
```typescript
<button className="border border-border-light bg-background text-text-primary px-lg py-md rounded-md font-semibold hover:bg-surface transition-colors">
  Secondary Action
</button>
```

#### Ghost (Bear)
```typescript
<button className="text-bear-primary hover:bg-bear-50 px-lg py-md rounded-md font-semibold transition-colors">
  Ghost Action
</button>
```

### Status Badge
```typescript
{/* Success */}
<span className="inline-flex bg-success-50 text-success-500 px-md py-sm rounded-full text-label-md font-semibold">
  Live
</span>

{/* Warning */}
<span className="inline-flex bg-warning-50 text-warning-500 px-md py-sm rounded-full text-label-md font-semibold">
  Pending
</span>

{/* Error */}
<span className="inline-flex bg-error-50 text-error-500 px-md py-sm rounded-full text-label-md font-semibold">
  Error
</span>
```

## Layout Patterns

### Spacious Two-Column
```typescript
<div className="grid grid-cols-1 md:grid-cols-2 gap-xl p-xl">
  <div className="bg-surface rounded-lg p-lg">Left content</div>
  <div className="bg-surface rounded-lg p-lg">Right content</div>
</div>
```

### Centered Container
```typescript
<div className="mx-auto max-w-2xl px-lg py-xl">
  <h1 className="text-display-lg">Centered content</h1>
</div>
```

### Full-Width with Padding
```typescript
<section className="w-full px-lg py-xl md:px-xl">
  <div className="mx-auto max-w-7xl">
    Content
  </div>
</section>
```

## Responsive Patterns

### Hide on Mobile
```typescript
<div className="hidden md:block">
  {/* Visible on tablet and up */}
</div>
```

### Responsive Grid
```typescript
<div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-md">
  {items.map(item => <Card key={item.id} {...item} />)}
</div>
```

### Stack on Mobile
```typescript
<div className="flex flex-col sm:flex-row gap-lg">
  <div className="flex-1">Left</div>
  <div className="flex-1">Right</div>
</div>
```

## Accessibility Tips

### Always provide alt text for images
```typescript
<img src="..." alt="Description of image" />
```

### Use semantic HTML
```typescript
// Good
<header>...</header>
<nav>...</nav>
<main>...</main>
<footer>...</footer>

// Avoid
<div role="header">...</div>
```

### Add aria labels to icon buttons
```typescript
<button aria-label="Toggle sidebar" onClick={() => {}}>
  {/* Icon */}
</button>
```

### Proper heading hierarchy
```typescript
<h1>Main title</h1>           {/* Page title */}
<h2>Section title</h2>         {/* Major section */}
<h3>Subsection title</h3>      {/* Subsection */}

// Don't skip levels
// ❌ Bad: h1 → h3 (skips h2)
// ✅ Good: h1 → h2 → h3 (sequential)
```

## Color Contrast Verification

Minimum contrast ratios (WCAG AA):
- Normal text: 4.5:1
- Large text (18px+ or 14px+ bold): 3:1

Recommended text color combinations:
- `text-text-primary` on light backgrounds
- `text-text-secondary` for secondary information
- `text-text-inverted` on bull-500, bear-500, etc.

## Responsive Breakpoints

```
Mobile:  < 640px   (default)
Tablet:  640px - 1024px   (sm, md)
Desktop: 1024px+   (lg, xl, 2xl)
```

Classes:
```
sm:  min-width 640px
md:  min-width 768px
lg:  min-width 1024px
xl:  min-width 1280px
2xl: min-width 1536px
```

## Performance Tips

1. Use `className` (Tailwind) instead of inline styles when possible
2. Extract repeated patterns into reusable components
3. Lazy load non-critical sections
4. Use `next/image` for images with optimization
5. Minimize CSS custom property usage in hot paths

## Common Mistakes to Avoid

1. **Wrong spacing scale**: Use predefined spacing tokens, not arbitrary values
2. **Inconsistent colors**: Always use the color tokens, not hex codes directly
3. **Missing responsive classes**: Always consider mobile-first design
4. **Inaccessible interactions**: Always include `aria-label`, `title`, or visible text
5. **Poor contrast**: Use only recommended text color combinations
