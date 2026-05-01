import type { Config } from 'tailwindcss';
import { colors, spacing, borderRadius, shadows } from './design/tokens';

const config: Config = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        // Backgrounds
        background: colors.background,
        surface: colors.surface,
        'surface-secondary': colors.surfaceSecondary,
        'surface-tertiary': colors.surfaceTertiary,

        // Text
        text: {
          primary: colors.textPrimary,
          secondary: colors.textSecondary,
          tertiary: colors.textTertiary,
          inverted: colors.textInverted,
        },

        // Bull
        bull: {
          50: colors.bull.lighter,
          100: colors.bull.light,
          500: colors.bull.primary,
          600: colors.bull.accent,
          800: colors.bull.dark,
        },

        // Bear
        bear: {
          50: colors.bear.lighter,
          100: colors.bear.light,
          500: colors.bear.primary,
          600: colors.bear.accent,
          800: colors.bear.dark,
        },

        // Semantic
        success: {
          50: colors.successLight,
          500: colors.success,
        },
        warning: {
          50: colors.warningLight,
          500: colors.warning,
        },
        error: {
          50: colors.errorLight,
          500: colors.error,
        },
        info: {
          50: colors.infoLight,
          500: colors.info,
        },

        // Borders
        border: {
          light: colors.borderLight,
          medium: colors.borderMedium,
          dark: colors.borderDark,
        },
      },

      spacing: {
        xs: spacing.xs,
        sm: spacing.sm,
        md: spacing.md,
        lg: spacing.lg,
        xl: spacing.xl,
        '2xl': spacing['2xl'],
        '3xl': spacing['3xl'],
      },

      borderRadius: {
        sm: borderRadius.sm,
        md: borderRadius.md,
        lg: borderRadius.lg,
        xl: borderRadius.xl,
        full: borderRadius.full,
      },

      boxShadow: {
        sm: shadows.sm,
        md: shadows.md,
        lg: shadows.lg,
        xl: shadows.xl,
        '2xl': shadows['2xl'],
      },

      fontSize: {
        'display-lg': ['36px', { lineHeight: '44px', fontWeight: '700' }],
        'display-md': ['28px', { lineHeight: '36px', fontWeight: '700' }],
        'heading-lg': ['24px', { lineHeight: '32px', fontWeight: '600' }],
        'heading-md': ['20px', { lineHeight: '28px', fontWeight: '600' }],
        'body-lg': ['16px', { lineHeight: '24px', fontWeight: '400' }],
        'body-md': ['14px', { lineHeight: '20px', fontWeight: '400' }],
        'body-sm': ['12px', { lineHeight: '18px', fontWeight: '400' }],
        'label-lg': ['14px', { lineHeight: '20px', fontWeight: '600' }],
        'label-md': ['12px', { lineHeight: '16px', fontWeight: '600' }],
      },

      fontFamily: {
        sans: [
          '-apple-system',
          'BlinkMacSystemFont',
          '"Segoe UI"',
          '"Roboto"',
          'sans-serif',
        ],
        mono: [
          'ui-monospace',
          '"Cascadia Code"',
          '"Source Code Pro"',
          'monospace',
        ],
      },
    },
  },
  plugins: [],
};

export default config;
