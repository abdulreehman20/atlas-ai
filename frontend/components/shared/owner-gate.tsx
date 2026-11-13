"use client";

import type { ReactNode } from "react";

import { useMe } from "@/hooks/use-me";
import { ErrorState, LoadingBlock } from "@/components/shared/state-panel";

export function OwnerGate({ children }: { children: ReactNode }) {
  const me = useMe();

  if (me.isLoading) {
    return <LoadingBlock rows={4} />;
  }

  if (me.isError) {
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
    return (
      <ErrorState
        title="Owner access required"
        message="Only the workspace owner can open this page."
      />
    );
  }

  return children;
}
