/**
 * Convexa Design Tokens
 * 
 * Centralized design system tokens for colors, typography, spacing, and effects.
 * Import and use these tokens throughout the application for consistency.
 */

export const colors = {
  // Primary Backgrounds
  background: '#FFFFFF',
  surface: '#F8FAFC',
  surfaceSecondary: '#F1F5F9',
  surfaceTertiary: '#E2E8F0',

  // Text Colors
  textPrimary: '#0F172A',
  textSecondary: '#475569',
  textTertiary: '#64748B',
  textInverted: '#FFFFFF',

  // Bull Side (Bullish - Blue/Purple)
  bull: {
    primary: '#2563EB',
    light: '#DBEAFE',
    lighter: '#EFF6FF',
    dark: '#1E40AF',
    accent: '#60A5FA',
  },

  // Bear Side (Bearish - Orange/Red)
  bear: {
    primary: '#EA580C',
    light: '#FFEDD5',
    lighter: '#FEF3C7',
    dark: '#B45309',
    accent: '#FB923C',
  },

  // Semantic Colors
  success: '#16A34A',
  successLight: '#DCFCE7',
  warning: '#EABB08',
  warningLight: '#FEFCE8',
  error: '#DC2626',
  errorLight: '#FEE2E2',
  info: '#0284C7',
  infoLight: '#E0F2FE',

  // Borders & Dividers
  borderLight: '#E2E8F0',
  borderMedium: '#CBD5E1',
  borderDark: '#94A3B8',

  // Overlays
  overlay: 'rgba(15, 23, 42, 0.4)',
  overlayDark: 'rgba(15, 23, 42, 0.6)',
} as const;

export const typography = {
  fontFamily: {
    sans: [
      '-apple-system',
      'BlinkMacSystemFont',
      '"Segoe UI"',
      '"Roboto"',
      'sans-serif',
    ].join(', '),
    mono: [
      'ui-monospace',
      '"Cascadia Code"',
      '"Source Code Pro"',
      'monospace',
    ].join(', '),
  },

  // Font Sizes and Line Heights
  fontSize: {
    displayLg: '36px',
    displayMd: '28px',
    headingLg: '24px',
    headingMd: '20px',
    bodyLg: '16px',
    bodyMd: '14px',
    bodySm: '12px',
    labelLg: '14px',
    labelMd: '12px',
    monoLg: '14px',
    monoMd: '12px',
  },

  fontWeight: {
    light: 300,
    regular: 400,
    medium: 500,
    semibold: 600,
    bold: 700,
  },

  lineHeight: {
    displayLg: '44px',
    displayMd: '36px',
    headingLg: '32px',
    headingMd: '28px',
    bodyLg: '24px',
    bodyMd: '20px',
    bodySm: '18px',
    labelLg: '20px',
    labelMd: '16px',
    monoLg: '20px',
    monoMd: '18px',
  },
} as const;

export const spacing = {
  xs: '4px',
  sm: '8px',
  md: '16px',
  lg: '24px',
  xl: '32px',
  '2xl': '48px',
  '3xl': '64px',
} as const;

export const borderRadius = {
  sm: '4px',
  md: '8px',
  lg: '12px',
  xl: '16px',
  full: '9999px',
} as const;

export const shadows = {
  sm: '0 1px 2px rgba(15, 23, 42, 0.05)',
  md: '0 4px 6px rgba(15, 23, 42, 0.1)',
  lg: '0 10px 15px rgba(15, 23, 42, 0.1)',
  xl: '0 20px 25px rgba(15, 23, 42, 0.1)',
  '2xl': '0 25px 50px rgba(15, 23, 42, 0.15)',
} as const;

export const opacity = {
  disabled: 0.5,
  hover: 0.8,
  focus: 0.95,
} as const;

// Composite Styles
export const styles = {
  // Display Styles
  displayLg: {
    fontSize: typography.fontSize.displayLg,
    fontWeight: typography.fontWeight.bold,
    lineHeight: typography.lineHeight.displayLg,
    fontFamily: typography.fontFamily.sans,
  },
  displayMd: {
    fontSize: typography.fontSize.displayMd,
    fontWeight: typography.fontWeight.bold,
    lineHeight: typography.lineHeight.displayMd,
    fontFamily: typography.fontFamily.sans,
  },

  // Heading Styles
  headingLg: {
    fontSize: typography.fontSize.headingLg,
    fontWeight: typography.fontWeight.semibold,
    lineHeight: typography.lineHeight.headingLg,
    fontFamily: typography.fontFamily.sans,
  },
  headingMd: {
    fontSize: typography.fontSize.headingMd,
    fontWeight: typography.fontWeight.semibold,
    lineHeight: typography.lineHeight.headingMd,
    fontFamily: typography.fontFamily.sans,
  },

  // Body Styles
  bodyLg: {
    fontSize: typography.fontSize.bodyLg,
    fontWeight: typography.fontWeight.regular,
    lineHeight: typography.lineHeight.bodyLg,
    fontFamily: typography.fontFamily.sans,
  },
  bodyMd: {
    fontSize: typography.fontSize.bodyMd,
    fontWeight: typography.fontWeight.regular,
    lineHeight: typography.lineHeight.bodyMd,
    fontFamily: typography.fontFamily.sans,
  },
  bodySm: {
    fontSize: typography.fontSize.bodySm,
    fontWeight: typography.fontWeight.regular,
    lineHeight: typography.lineHeight.bodySm,
    fontFamily: typography.fontFamily.sans,
  },

  // Label Styles
  labelLg: {
    fontSize: typography.fontSize.labelLg,
    fontWeight: typography.fontWeight.semibold,
    lineHeight: typography.lineHeight.labelLg,
    fontFamily: typography.fontFamily.sans,
  },
  labelMd: {
    fontSize: typography.fontSize.labelMd,
    fontWeight: typography.fontWeight.semibold,
    lineHeight: typography.lineHeight.labelMd,
    fontFamily: typography.fontFamily.sans,
  },

  // Monospace Styles
  monoLg: {
    fontSize: typography.fontSize.monoLg,
    fontWeight: typography.fontWeight.regular,
    lineHeight: typography.lineHeight.monoLg,
    fontFamily: typography.fontFamily.mono,
  },
  monoMd: {
    fontSize: typography.fontSize.monoMd,
    fontWeight: typography.fontWeight.regular,
    lineHeight: typography.lineHeight.monoMd,
    fontFamily: typography.fontFamily.mono,
  },
} as const;

/**
 * Utility function to get responsive spacing based on breakpoint
 */
export const getResponsiveSpacing = (
  mobile: keyof typeof spacing,
  tablet: keyof typeof spacing,
  desktop: keyof typeof spacing
) => ({
  mobile: spacing[mobile],
  tablet: spacing[tablet],
  desktop: spacing[desktop],
});

/**
 * Utility function for creating color with opacity
 */
export const withOpacity = (color: string, opacity: number): string => {
  if (color.startsWith('#')) {
    const r = parseInt(color.slice(1, 3), 16);
    const g = parseInt(color.slice(3, 5), 16);
    const b = parseInt(color.slice(5, 7), 16);
    return `rgba(${r}, ${g}, ${b}, ${opacity})`;
  }
  return color;
};
