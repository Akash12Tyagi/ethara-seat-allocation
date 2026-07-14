"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Users,
  FolderKanban,
  Armchair,
  Bot,
  Building2,
} from "lucide-react";
import { clsx } from "clsx";

const NAV = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/employees", label: "Employees", icon: Users },
  { href: "/projects", label: "Projects", icon: FolderKanban },
  { href: "/seats", label: "Seats", icon: Armchair },
  { href: "/assistant", label: "AI Assistant", icon: Bot },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="hidden md:flex md:w-60 md:flex-col md:shrink-0 border-r border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-950">
      <div className="flex items-center gap-2 px-5 h-16 border-b border-zinc-200 dark:border-zinc-800">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-zinc-900 dark:bg-zinc-100">
          <Building2 className="h-4.5 w-4.5 text-white dark:text-zinc-900" size={18} />
        </div>
        <div className="leading-tight">
          <p className="text-sm font-semibold text-zinc-900 dark:text-zinc-50">Ethara</p>
          <p className="text-[11px] text-zinc-500 dark:text-zinc-400">Seat Allocation</p>
        </div>
      </div>

      <nav className="flex-1 px-3 py-4 space-y-1">
        {NAV.map(({ href, label, icon: Icon }) => {
          const active = pathname === href || pathname.startsWith(href + "/");
          return (
            <Link
              key={href}
              href={href}
              className={clsx(
                "flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                active
                  ? "bg-zinc-900 text-white dark:bg-zinc-100 dark:text-zinc-900"
                  : "text-zinc-600 hover:bg-zinc-100 hover:text-zinc-900 dark:text-zinc-400 dark:hover:bg-zinc-900 dark:hover:text-zinc-50"
              )}
            >
              <Icon size={17} strokeWidth={2} />
              {label}
            </Link>
          );
        })}
      </nav>

      <div className="px-5 py-4 border-t border-zinc-200 dark:border-zinc-800 text-[11px] text-zinc-400">
        ~5,000 employees · 5 floors
      </div>
    </aside>
  );
}
