"use client";

import { useQuery } from "@tanstack/react-query";
import {
  FileText,
  Menu,
  MessageSquare,
  MessageSquareText,
  Settings,
  ShieldCheck,
  Users,
  X,
} from "lucide-react";
import Link from "next/link";
import { usePathname, useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import { fetchConversations } from "@/lib/endpoints";
import { cn } from "@/lib/utils";
import type { WorkspaceRole } from "@/types/types";

type NavItem = {
  href: string;
  label: string;
  icon: typeof MessageSquare;
  ownerOnly?: boolean;
};

const NAV_ITEMS: NavItem[] = [
  { href: "/chat", label: "Chat", icon: MessageSquare },
  { href: "/documents", label: "Documents", icon: FileText },
  { href: "/members", label: "Members", icon: Users, ownerOnly: true },
  // {
  //   href: "/approvals",
  //   label: "Approvals",
  //   icon: ShieldCheck,
  //   ownerOnly: true,
  // },
  { href: "/settings", label: "Settings", icon: Settings },
];

function conversationTitle(title: string | null, id: string): string {
  if (title?.trim()) return title.trim();
  return `Chat ${id.slice(0, 8)}`;
}

function SidebarBody({
  role,
  workspaceName,
  onNavigate,
}: {
  role: WorkspaceRole;
  workspaceName: string | null;
  onNavigate?: () => void;
}) {
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const activeConversationId = searchParams.get("conversation");
  const items = NAV_ITEMS.filter((item) => !item.ownerOnly || role === "owner");

  const conversations = useQuery({
    queryKey: ["conversations"],
    queryFn: async () => {
      const page = await fetchConversations();
      return page.items;
    },
  });

  return (
    <>
      <div className="border-b border-border px-4 py-4">
        <Link
          href="/chat"
          onClick={onNavigate}
          className="text-lg font-semibold tracking-tight"
        >
          Atlas Enterprise AI
        </Link>
        <p className="mt-2 truncate text-sm text-foreground">
          {workspaceName ?? "Workspace"}
        </p>
        <p className="mt-0.5 text-xs text-muted-foreground capitalize">
          {role}
        </p>
      </div>
      <nav className="flex flex-col gap-1 p-2">
        {items.map((item) => {
          const Icon = item.icon;
          const active =
            pathname === item.href || pathname.startsWith(`${item.href}/`);
          return (
            <Link
              key={item.href}
              href={item.href}
              onClick={onNavigate}
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

      <div className="px-2">
        <Separator className="my-2" />
      </div>

      <div className="flex min-h-0 flex-1 flex-col px-2 pb-2">
        <p className="px-3 py-1 text-xs font-medium text-muted-foreground">
          Conversations
        </p>
        <ScrollArea className="min-h-0 flex-1">
          <div className="flex flex-col gap-0.5 pr-1">
            {conversations.isLoading ? (
              <p className="px-3 py-2 text-xs text-muted-foreground">
                Loading…
              </p>
            ) : null}
            {conversations.isError ? (
              <p className="px-3 py-2 text-xs text-destructive">
                Could not load chats
              </p>
            ) : null}
            {conversations.data && conversations.data.length === 0 ? (
              <p className="px-3 py-2 text-xs text-muted-foreground">
                No conversations yet
              </p>
            ) : null}
            {conversations.data?.map((conversation) => {
              const active =
                pathname.startsWith("/chat") &&
                activeConversationId === conversation.id;
              return (
                <Link
                  key={conversation.id}
                  href={`/chat?conversation=${conversation.id}`}
                  onClick={onNavigate}
                  className={cn(
                    "flex items-center gap-2 rounded-lg px-3 py-2 text-sm transition-colors",
                    active
                      ? "bg-muted text-foreground"
                      : "text-muted-foreground hover:bg-muted/60 hover:text-foreground",
                  )}
                  title={conversationTitle(conversation.title, conversation.id)}
                >
                  <MessageSquareText className="size-4 shrink-0" />
                  <span className="truncate">
                    {conversationTitle(conversation.title, conversation.id)}
                  </span>
                </Link>
              );
            })}
          </div>
        </ScrollArea>
      </div>
    </>
  );
}

export function AppSidebar({
  role,
  workspaceName,
}: {
  role: WorkspaceRole;
  workspaceName: string | null;
}) {
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const [mobileOpen, setMobileOpen] = useState(false);

  // biome-ignore lint/correctness/useExhaustiveDependencies: close drawer on route changes
  useEffect(() => {
    setMobileOpen(false);
  }, [pathname, searchParams]);

  return (
    <>
      <div className="flex h-14 items-center gap-2 border-b border-border px-3 md:hidden">
        <Button
          type="button"
          variant="ghost"
          size="icon-sm"
          aria-label="Open menu"
          onClick={() => setMobileOpen(true)}
        >
          <Menu className="size-4" />
        </Button>
        <div className="min-w-0">
          <p className="truncate text-sm font-semibold">Atlas Enterprise AI</p>
          <p className="truncate text-xs text-muted-foreground">
            {workspaceName ?? "Workspace"}
          </p>
        </div>
      </div>

      <aside className="hidden w-56 shrink-0 flex-col border-r border-border bg-background md:flex">
        <SidebarBody role={role} workspaceName={workspaceName} />
      </aside>

      {mobileOpen ? (
        <div className="fixed inset-0 z-50 md:hidden">
          <button
            type="button"
            className="absolute inset-0 bg-black/40"
            aria-label="Close menu overlay"
            onClick={() => setMobileOpen(false)}
          />
          <aside className="relative flex h-full w-[min(20rem,85vw)] flex-col bg-background shadow-xl">
            <div className="flex items-center justify-end border-b border-border px-2 py-2">
              <Button
                type="button"
                variant="ghost"
                size="icon-sm"
                aria-label="Close menu"
                onClick={() => setMobileOpen(false)}
              >
                <X className="size-4" />
              </Button>
            </div>
            <SidebarBody
              role={role}
              workspaceName={workspaceName}
              onNavigate={() => setMobileOpen(false)}
            />
          </aside>
        </div>
      ) : null}
    </>
  );
}
