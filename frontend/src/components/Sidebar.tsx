'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { navigationItems } from '@/types/navigation';

/**
 * Icon components for navigation items
 */
const NavIcon: React.FC<{ name: string; className?: string }> = ({
  name,
  className = 'h-5 w-5',
}) => {
  const icons: Record<string, React.ReactNode> = {
    grid: (
      <svg
        className={className}
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M4 5a1 1 0 011-1h4a1 1 0 011 1v4a1 1 0 01-1 1H5a1 1 0 01-1-1V5zM14 5a1 1 0 011-1h4a1 1 0 011 1v4a1 1 0 01-1 1h-4a1 1 0 01-1-1V5zM4 15a1 1 0 011-1h4a1 1 0 011 1v4a1 1 0 01-1 1H5a1 1 0 01-1-1v-4zM14 15a1 1 0 011-1h4a1 1 0 011 1v4a1 1 0 01-1 1h-4a1 1 0 01-1-1v-4z"
        />
      </svg>
    ),
    activity: (
      <svg
        className={className}
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M13 10V3L4 14h7v7l9-11h-7z"
        />
      </svg>
    ),
    history: (
      <svg
        className={className}
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
        />
      </svg>
    ),
    'bar-chart': (
      <svg
        className={className}
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
        />
      </svg>
    ),
    settings: (
      <svg
        className={className}
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"
        />
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
        />
      </svg>
    ),
  };

  return <>{icons[name] || null}</>;
};

/**
 * Sidebar component with main and secondary navigation
 */
export const Sidebar: React.FC = () => {
  const [isOpen, setIsOpen] = useState(true);
  const pathname = usePathname();

  const isActive = (href: string) => {
    if (href === '/' && pathname === '/') return true;
    if (href !== '/' && pathname.startsWith(href)) return true;
    return false;
  };

  const mainItems = navigationItems.filter((item) => item.section === 'main');
  const secondaryItems = navigationItems.filter(
    (item) => item.section === 'secondary'
  );

  return (
    <>
      {/* Sidebar */}
      <aside
        className={`fixed left-0 top-16 bottom-0 border-r border-border-light bg-background transition-all duration-300 ${
          isOpen ? 'w-56' : 'w-20'
        } hidden md:flex flex-col`}
      >
        {/* Main Navigation */}
        <nav className="flex-1 space-y-sm px-sm py-lg">
          <div className="space-y-xs">
            {mainItems.map((item) => (
              <Link
                key={item.id}
                href={item.href}
                className={`group flex items-center gap-md rounded-md px-md py-sm transition-colors ${
                  isActive(item.href)
                    ? 'bg-bull-100 text-bull-primary'
                    : 'text-text-secondary hover:bg-surface hover:text-text-primary'
                }`}
                title={!isOpen ? item.label : undefined}
              >
                <NavIcon name={item.icon} />
                {isOpen && <span className="text-label-md font-medium">{item.label}</span>}
              </Link>
            ))}
          </div>

          {/* Divider */}
          {isOpen && <div className="my-lg h-px bg-border-light" />}

          {/* Secondary Navigation */}
          <div className="space-y-xs">
            {secondaryItems.map((item) => (
              <Link
                key={item.id}
                href={item.href}
                className={`group flex items-center gap-md rounded-md px-md py-sm transition-colors ${
                  isActive(item.href)
                    ? 'bg-bull-100 text-bull-primary'
                    : 'text-text-secondary hover:bg-surface hover:text-text-primary'
                }`}
                title={!isOpen ? item.label : undefined}
              >
                <NavIcon name={item.icon} />
                {isOpen && <span className="text-label-md font-medium">{item.label}</span>}
              </Link>
            ))}
          </div>
        </nav>

        {/* Sidebar Toggle */}
        <div className="border-t border-border-light px-sm py-md">
          <button
            onClick={() => setIsOpen(!isOpen)}
            className="flex w-full items-center justify-center rounded-md border border-border-light bg-surface px-md py-sm text-text-secondary transition-colors hover:bg-surface-secondary hover:text-text-primary"
            aria-label={isOpen ? 'Collapse sidebar' : 'Expand sidebar'}
          >
            {isOpen ? (
              <svg
                className="h-5 w-5"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M15 19l-7-7 7-7"
                />
              </svg>
            ) : (
              <svg
                className="h-5 w-5"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M9 5l7 7-7 7"
                />
              </svg>
            )}
          </button>
        </div>
      </aside>

      {/* Mobile Sidebar Backdrop and Menu - will be implemented with state management */}
      {/* Mobile menu can be triggered from Header mobile button */}
    </>
  );
};
