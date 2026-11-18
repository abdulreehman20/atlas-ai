"use client";

import type { ReactNode } from "react";
import { ErrorState, LoadingBlock } from "@/components/shared/state-panel";
import { useMe } from "@/hooks/use-me";

export function OwnerGate({
  children,
  fallback,
}: {
  children: ReactNode;
  /** When set, non-owners see this instead of the default error panel. */
  fallback?: ReactNode;
}) {
  const me = useMe();

  if (me.isLoading) {
    return <LoadingBlock rows={4} />;
  }

  if (me.isError) {
    if (fallback !== undefined) return fallback;
    return (
      <ErrorState
        title="Unable to load workspace"
        message={
          me.error instanceof Error ? me.error.message : "Request failed"
        }
      />
    );
  }

  if (me.data?.role !== "owner") {
    if (fallback !== undefined) return fallback;
    return (
      <ErrorState
        title="Owner access required"
        message="Only the workspace owner can open this page."
      />
    );
  }

  return children;
}
