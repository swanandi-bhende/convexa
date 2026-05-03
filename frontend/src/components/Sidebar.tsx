import Link from "next/link";

const links = [
  { href: "/", label: "Dashboard" },
  { href: "/debate/demo-session", label: "Active Debates" },
  { href: "/history", label: "History" },
  { href: "/agents", label: "Agent Stats" },
  { href: "/settings", label: "Settings" },
  { href: "/stake", label: "Stake" },
  { href: "/about", label: "About" },
];

export function Sidebar() {
  return (
    <aside className="hidden min-h-[calc(100vh-73px)] w-72 shrink-0 border-r border-slate-200/70 bg-slate-50/70 px-4 py-8 lg:block">
      <p className="px-3 pb-4 text-xs font-semibold uppercase tracking-[0.28em] text-slate-500">Navigation</p>
      <nav aria-label="Primary" className="space-y-2">
        {links.map((link) => (
          <Link
            key={link.href}
            href={link.href}
            className="block rounded-xl px-3 py-2.5 text-sm font-medium text-slate-700 transition hover:bg-white hover:text-slate-950"
          >
            {link.label}
          </Link>
        ))}
      </nav>
    </aside>
  );
}
