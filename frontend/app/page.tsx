import Link from "next/link";

import { Button } from "@/components/ui/button";
import { SiteHeader } from "@/components/layout/site-header";

export default function HomePage() {
  return (
    <>
      <SiteHeader />
      <main className="mx-auto flex w-full max-w-5xl flex-1 flex-col justify-center gap-8 px-4 py-16">
        <div className="max-w-2xl space-y-4">
          <h1 className="text-4xl font-semibold tracking-tight text-foreground">
            Atlas Enterprise AI
          </h1>
          <p className="text-lg text-muted-foreground">
            Grounded answers over your private workspace documents — with
            citations, owner-controlled prompts, and plan limits that protect
            your knowledge base.
          </p>
        </div>
        <div className="flex flex-wrap gap-3">
          <Button size="lg" render={<Link href="/signup" />}>
            Create workspace
          </Button>
          <Button size="lg" variant="outline" render={<Link href="/login" />}>
            Sign in
          </Button>
        </div>
      </main>
    </>
  );
}
