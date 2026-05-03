"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { CHAIN_ID, RPC_URLS } from "@/lib/contracts";

const navLinks = [
  { href: "/", label: "Dashboard" },
  { href: "/debate/demo-session", label: "Active Debates" },
  { href: "/history", label: "History" },
  { href: "/agents", label: "Agent Stats" },
  { href: "/settings", label: "Settings" },
];

interface HeaderProps {
  connectedWallet?: string;
  network?: string;
}

interface EthereumProvider {
  request: (args: { method: string; params?: unknown[] | Record<string, unknown> }) => Promise<unknown>;
}

declare global {
  interface Window {
    ethereum?: EthereumProvider;
  }
}

function shortenAddress(address: string): string {
  return `${address.slice(0, 6)}...${address.slice(-4)}`;
}

function toHexChainId(chainId: number): string {
  return `0x${chainId.toString(16)}`;
}

export function Header({ connectedWallet = "0x13A2...B94f", network = "Unichain Sepolia" }: HeaderProps) {
  const pathname = usePathname();
  const [walletAddress, setWalletAddress] = useState<string | null>(null);
  const [walletError, setWalletError] = useState<string | null>(null);
  const [connecting, setConnecting] = useState(false);

  useEffect(() => {
    const provider = window.ethereum;
    if (!provider) {
      return;
    }

    let active = true;

    void provider
      .request({ method: "eth_accounts" })
      .then((accounts) => {
        if (!active) {
          return;
        }

        const first = Array.isArray(accounts) ? (accounts[0] as string | undefined) : undefined;
        if (first) {
          setWalletAddress(first);
        }
      })
      .catch(() => {
        if (active) {
          setWalletError("Unable to read wallet accounts.");
        }
      });

    return () => {
      active = false;
    };
  }, []);

  const walletLabel = useMemo(() => {
    if (walletAddress) {
      return shortenAddress(walletAddress);
    }

    return connectedWallet;
  }, [connectedWallet, walletAddress]);

  const connectWallet = async () => {
    const provider = window.ethereum;
    if (!provider) {
      setWalletError("No injected wallet found. Install MetaMask or Rabby.");
      return;
    }

    setWalletError(null);
    setConnecting(true);

    try {
      await provider.request({
        method: "wallet_switchEthereumChain",
        params: [{ chainId: toHexChainId(CHAIN_ID) }],
      });
    } catch (switchError) {
      const error = switchError as { code?: number };
      if (error.code === 4902) {
        try {
          await provider.request({
            method: "wallet_addEthereumChain",
            params: [
              {
                chainId: toHexChainId(CHAIN_ID),
                chainName: "Unichain Sepolia",
                nativeCurrency: { name: "Ether", symbol: "ETH", decimals: 18 },
                rpcUrls: [RPC_URLS.http],
                blockExplorerUrls: ["https://unichain-sepolia.blockscout.com"],
              },
            ],
          });
        } catch {
          setWalletError("Failed to add Unichain Sepolia to wallet.");
          setConnecting(false);
          return;
        }
      }
    }

    try {
      const accounts = await provider.request({ method: "eth_requestAccounts" });
      const first = Array.isArray(accounts) ? (accounts[0] as string | undefined) : undefined;
      if (!first) {
        setWalletError("Wallet returned no accounts.");
      } else {
        setWalletAddress(first);
      }
    } catch {
      setWalletError("Wallet connection request was rejected.");
    } finally {
      setConnecting(false);
    }
  };

  return (
    <header className="sticky top-0 z-30 backdrop-blur-[24px]" style={{ backgroundColor: "rgba(255, 248, 247, 0.7)" }}>
      {/* Subtle tonal divider instead of border */}
      <div className="h-px" style={{ background: "linear-gradient(to right, transparent, var(--surface-container-low), transparent)" }} />
      
      <div className="mx-auto flex w-full items-center justify-between" style={{ maxWidth: 1400, padding: "1rem 1.5rem 1rem 1.5rem", gap: "1rem" }}>
        <div className="flex items-center gap-4">
          <div
            className="h-10 w-10 rounded"
            style={{ background: "linear-gradient(135deg, #864f51 0%, #a26769 100%)" }}
            aria-hidden
          />
          <div>
            <p className="text-lg font-semibold tracking-tight" style={{ color: "var(--on-surface)" }}>Convexa</p>
            <p className="text-xs font-medium uppercase tracking-[0.05em]" style={{ color: "var(--on-surface-variant)" }}>Autonomous Debate Engine</p>
          </div>
        </div>

        <nav className="hidden items-center gap-2 md:flex">
          {navLinks.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className="px-4 py-2 text-sm font-medium transition rounded"
              style={{
                backgroundColor: pathname === item.href ? "var(--primary)" : "transparent",
                color: pathname === item.href ? "var(--on-primary)" : "var(--on-surface)"
              }}
              onMouseEnter={(e) => {
                if (pathname !== item.href) {
                  e.currentTarget.style.backgroundColor = "var(--surface-container-low)";
                }
              }}
              onMouseLeave={(e) => {
                if (pathname !== item.href) {
                  e.currentTarget.style.backgroundColor = "transparent";
                }
              }}
            >
              {item.label}
            </Link>
          ))}
        </nav>

        <div className="flex items-center gap-3">
          {/* Network Badge - Secondary Color Anchor */}
          <span 
            className="px-4 py-2 text-xs font-semibold uppercase tracking-[0.05em] rounded"
            style={{ backgroundColor: "var(--secondary)", color: "var(--on-primary)" }}
          >
            {network}
          </span>
          
          {/* Wallet Button - Primary Gradient */}
          <button
            type="button"
            onClick={connectWallet}
            disabled={connecting}
            className="px-4 py-2 text-xs font-semibold uppercase tracking-[0.05em] rounded transition disabled:cursor-not-allowed disabled:opacity-70"
            style={{
              background: !connecting && !walletAddress ? "linear-gradient(135deg, var(--primary) 0%, var(--primary-container) 100%)" : "var(--surface-container-high)",
              color: !connecting && !walletAddress ? "var(--on-primary)" : "var(--on-surface)"
            }}
            title={walletAddress ?? connectedWallet}
          >
            {connecting ? "Connecting..." : walletAddress ? walletLabel : "Connect Wallet"}
          </button>
        </div>
      </div>
      
      {/* Error message with warning color */}
      {walletError ? (
        <div className="px-6 pb-3 lg:px-10">
          <p className="text-xs" style={{ color: "var(--bear-500)" }}>
            {walletError}
          </p>
        </div>
      ) : null}
    </header>
  );
}
