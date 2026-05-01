'use client';

import React from 'react';
import Link from 'next/link';

interface HeaderProps {
  walletAddress?: string;
  networkName?: string;
  isConnected?: boolean;
}

/**
 * Header component with branding, wallet connection, and network indicator
 */
export const Header: React.FC<HeaderProps> = ({
  walletAddress,
  networkName = 'Unichain Sepolia',
  isConnected = false,
}) => {
  const truncateAddress = (address: string) => {
    if (address.length <= 10) return address;
    return `${address.slice(0, 6)}...${address.slice(-4)}`;
  };

  return (
    <header className="sticky top-0 z-40 border-b border-border-light bg-background">
      <div className="flex h-16 items-center justify-between px-lg md:px-xl">
        {/* Logo / Branding */}
        <Link href="/" className="flex items-center gap-md">
          <div className="flex h-10 w-10 items-center justify-center rounded-md bg-bull-500">
            <span className="text-body-md font-semibold text-text-inverted">C</span>
          </div>
          <div className="hidden flex-col gap-xs sm:flex">
            <h1 className="text-label-lg font-semibold text-text-primary">Convexa</h1>
            <p className="text-xs text-text-tertiary">Market Debate Platform</p>
          </div>
        </Link>

        {/* Right Side: Network + Wallet */}
        <div className="flex items-center gap-md md:gap-lg">
          {/* Network Status */}
          <div className="hidden flex-col items-end gap-xs rounded-md bg-surface px-md py-sm md:flex">
            <p className="text-xs text-text-tertiary">Network</p>
            <p className="text-label-md font-semibold text-text-primary">
              {networkName.split(' ')[0]}
            </p>
          </div>

          {/* Wallet Connection */}
          {isConnected && walletAddress ? (
            <div className="flex flex-col items-end gap-xs rounded-md bg-success-50 px-md py-sm">
              <p className="text-xs text-text-tertiary">Connected</p>
              <p className="text-label-md font-semibold font-mono text-text-primary">
                {truncateAddress(walletAddress)}
              </p>
            </div>
          ) : (
            <button
              className="rounded-md bg-bull-500 px-lg py-sm text-label-md font-semibold text-text-inverted transition-colors hover:bg-bull-600"
              aria-label="Connect Wallet"
            >
              Connect Wallet
            </button>
          )}

          {/* Mobile Menu Placeholder */}
          <button
            className="flex h-10 w-10 items-center justify-center rounded-md border border-border-light text-text-primary hover:bg-surface md:hidden"
            aria-label="Toggle menu"
          >
            <svg
              className="h-6 w-6"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M4 6h16M4 12h16M4 18h16"
              />
            </svg>
          </button>
        </div>
      </div>
    </header>
  );
};
