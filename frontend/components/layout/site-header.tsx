import Link from "next/link";

import { Button } from "@/components/ui/button";

export const SiteHeader = () => {
  return (
    <header className="border-b border-border bg-background">
      <div className="mx-auto flex h-14 w-full max-w-5xl items-center justify-between px-4">
        <Link
          href="/"
          className="text-sm font-semibold tracking-tight text-foreground"
        >
          Atlas Enterprise AI
        </Link>
        <nav className="flex items-center gap-2 text-sm">
          <Button variant="ghost" size="sm" render={<Link href="/login" />}>
            Sign in
          </Button>
          <Button size="sm" render={<Link href="/signup" />}>
            Start free
          </Button>
        </nav>
      </div>
    </header>
  );
};
