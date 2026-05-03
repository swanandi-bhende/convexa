"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

export function MegaBreadcrumb() {
  const pathname = usePathname();
  const paths = pathname.split("/").filter(Boolean);

  if (paths.length === 0) return null; // Don't show on home page if desired, or maybe show "Home"

  return (
    <nav aria-label="Breadcrumb" className="mb-12">
      <ol className="flex flex-wrap items-center gap-4">
        <li>
          <Link href="/" className="headline-md text-on-surface-variant hover:text-secondary transition-colors">
            Convexa
          </Link>
        </li>
        {paths.map((path, index) => {
          const isLast = index === paths.length - 1;
          const href = `/${paths.slice(0, index + 1).join("/")}`;
          const label = path.charAt(0).toUpperCase() + path.slice(1).replace(/-/g, " ");

          return (
            <li key={path} className="flex items-center gap-4">
              <span className="headline-md text-outline-variant" aria-hidden="true">/</span>
              {isLast ? (
                <span className="headline-md text-on-surface" aria-current="page">
                  {label}
                </span>
              ) : (
                <Link href={href} className="headline-md text-on-surface-variant hover:text-secondary transition-colors">
                  {label}
                </Link>
              )}
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
