"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

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

export function Header({ connectedWallet = "0x13A2...B94f", network = "Unichain Sepolia" }: HeaderProps) {
  const pathname = usePathname();

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
          <span className="rounded-full bg-slate-100 px-3 py-1 font-semibold text-slate-700">{connectedWallet}</span>
        </div>
      </div>
    </header>
  );
}
