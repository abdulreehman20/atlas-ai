"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  CreditCard,
  FileText,
  MessageSquare,
  Settings,
  ShieldCheck,
  Users,
} from "lucide-react";

import { cn } from "@/lib/utils";
import type { WorkspaceRole } from "@/lib/api/types";

type NavItem = {
  href: string;
  label: string;
  icon: typeof MessageSquare;
  ownerOnly?: boolean;
};

const NAV_ITEMS: NavItem[] = [
  { href: "/chat", label: "Chat", icon: MessageSquare },
  { href: "/documents", label: "Documents", icon: FileText },
  { href: "/settings", label: "Settings", icon: Settings, ownerOnly: true },
  { href: "/members", label: "Members", icon: Users, ownerOnly: true },
  { href: "/billing", label: "Billing", icon: CreditCard, ownerOnly: true },
  { href: "/approvals", label: "Approvals", icon: ShieldCheck, ownerOnly: true },
];

export function AppSidebar({ role }: { role: WorkspaceRole }) {
  const pathname = usePathname();
  const items = NAV_ITEMS.filter((item) => !item.ownerOnly || role === "owner");

  return (
    <aside className="flex w-56 shrink-0 flex-col border-r border-border bg-background">
      <div className="border-b border-border px-4 py-4">
        <Link href="/chat" className="text-sm font-semibold tracking-tight">
          Atlas Enterprise AI
        </Link>
        <p className="mt-1 text-xs text-muted-foreground capitalize">{role}</p>
      </div>
      <nav className="flex flex-1 flex-col gap-1 p-2">
        {items.map((item) => {
          const Icon = item.icon;
          const active =
            pathname === item.href || pathname.startsWith(`${item.href}/`);
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-2 rounded-lg px-3 py-2 text-sm transition-colors",
                active
                  ? "bg-muted text-foreground"
                  : "text-muted-foreground hover:bg-muted/60 hover:text-foreground",
              )}
            >
              <Icon className="size-4" />
              {item.label}
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}
