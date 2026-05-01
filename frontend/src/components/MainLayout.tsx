'use client';

import React, { ReactNode } from 'react';
import { Header } from './Header';
import { Sidebar } from './Sidebar';

interface MainLayoutProps {
  children: ReactNode;
}

/**
 * Main application layout combining Header, Sidebar, and content area
 * Provides consistent layout structure with spacious content area
 */
export const MainLayout: React.FC<MainLayoutProps> = ({ children }) => {
  return (
    <div className="flex h-full flex-col">
      {/* Header */}
      <Header isConnected={false} />

      <div className="flex flex-1 overflow-hidden">
        {/* Sidebar */}
        <Sidebar />

        {/* Main Content Area */}
        <main className="flex-1 overflow-auto bg-background">
          {/* Content Container with spacious padding */}
          <div className="mx-auto max-w-7xl p-lg md:p-xl">
            {children}
          </div>
        </main>
      </div>
    </div>
  );
};
