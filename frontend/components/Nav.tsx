"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Hexagon, LayoutDashboard, MessageSquare } from "lucide-react";

const links = [
  { href: "/dashboard", label: "Scrapers", icon: LayoutDashboard },
  { href: "/chat", label: "Chat", icon: MessageSquare },
];

export function Nav() {
  const path = usePathname();
  return (
    <header className="border-b border-stone-200 bg-white">
      <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-3">
        <Link href="/dashboard" className="flex items-center gap-2 font-semibold">
          <Hexagon className="h-6 w-6 text-honey-600" />
          Waggle
        </Link>
        <nav className="flex gap-1">
          {links.map((link) => {
            const active = path === link.href;
            const Icon = link.icon;
            return (
              <Link
                key={link.href}
                href={link.href}
                className={`flex items-center gap-2 rounded-lg px-3 py-2 text-sm ${
                  active
                    ? "bg-honey-100 text-honey-800"
                    : "text-stone-600 hover:bg-stone-100"
                }`}
              >
                <Icon className="h-4 w-4" />
                {link.label}
              </Link>
            );
          })}
        </nav>
      </div>
    </header>
  );
}
