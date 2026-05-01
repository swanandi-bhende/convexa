/**
 * Navigation types and constants for the application
 */

export interface NavItem {
  id: string;
  label: string;
  href: string;
  icon: string;
  section: 'main' | 'secondary';
}

export const navigationItems: NavItem[] = [
  {
    id: 'dashboard',
    label: 'Dashboard',
    href: '/',
    icon: 'grid',
    section: 'main',
  },
  {
    id: 'active-debates',
    label: 'Active Debates',
    href: '/debates/active',
    icon: 'activity',
    section: 'main',
  },
  {
    id: 'history',
    label: 'Debate History',
    href: '/debates/history',
    icon: 'history',
    section: 'main',
  },
  {
    id: 'agents',
    label: 'Agent Stats',
    href: '/agents',
    icon: 'bar-chart',
    section: 'secondary',
  },
  {
    id: 'settings',
    label: 'Settings',
    href: '/settings',
    icon: 'settings',
    section: 'secondary',
  },
];
