"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { LoadingBlock } from "@/components/shared/state-panel";

/** Billing moved under Settings — keep route as a redirect. */
export function BillingPage() {
  const router = useRouter();

  useEffect(() => {
    router.replace("/settings#billing");
  }, [router]);

  return <LoadingBlock rows={3} />;
}
