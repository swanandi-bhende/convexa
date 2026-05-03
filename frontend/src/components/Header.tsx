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
    <header className="sticky top-0 z-30 border-b border-slate-200/80 bg-white/90 backdrop-blur">
      <div className="mx-auto flex w-full items-center justify-between px-6 py-4 lg:px-10" style={{ maxWidth: 1400 }}>
        <div className="flex items-center gap-3">
          <div
            className="h-10 w-10 rounded-xl"
            style={{ background: "linear-gradient(135deg, #3b82f6 0%, #6366f1 52%, #8b5cf6 100%)" }}
            aria-hidden
          />
          <div>
            <p className="text-lg font-semibold tracking-tight text-slate-900">Convexa</p>
            <p className="text-xs font-medium uppercase tracking-[0.2em] text-slate-500">Autonomous Debate Engine</p>
          </div>
        </div>

        <nav className="hidden items-center gap-6 md:flex">
          {navLinks.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className={`rounded-full px-3 py-1.5 text-sm font-medium transition ${pathname === item.href ? "bg-slate-900 text-white" : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"}`}
            >
              {item.label}
            </Link>
          ))}
        </nav>

        <div className="flex items-center gap-3 text-xs">
          <span className="rounded-full bg-emerald-100 px-3 py-1 font-semibold text-emerald-700">{network}</span>
          <button
            type="button"
            onClick={connectWallet}
            disabled={connecting}
            className="rounded-full bg-slate-100 px-3 py-1 font-semibold text-slate-700 transition hover:bg-slate-200 disabled:cursor-not-allowed disabled:opacity-70"
            title={walletAddress ?? connectedWallet}
          >
            {connecting ? "Connecting..." : walletAddress ? walletLabel : "Connect Wallet"}
          </button>
        </div>
      </div>
      {walletError ? <p className="px-6 pb-2 text-xs text-rose-600 lg:px-10">{walletError}</p> : null}
    </header>
  );
}
