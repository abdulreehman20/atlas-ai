"use client";

import type { ReactNode } from "react";

import { UserMenu } from "@/components/layout/user-menu";
import { AppSidebar } from "@/components/layout/app-sidebar";
import { ErrorState, LoadingBlock } from "@/components/shared/state-panel";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";

import { useMe } from "@/hooks/use-me";
import { ApiError } from "@/lib/client";
import type { WorkspaceRole } from "@/types/types";

function resolveRole(role: WorkspaceRole | undefined): WorkspaceRole {
  return role ?? "member";
}

export function AppShell({
  email,
  children,
}: {
  email: string | null;
  children: ReactNode;
}) {
  const me = useMe();

  if (me.isLoading) {
    return (
      <div className="flex min-h-full flex-1">
        <div className="w-56 border-r border-border p-4">
          <LoadingBlock rows={6} />
        </div>
        <div className="flex-1 p-6">
          <LoadingBlock rows={8} />
        </div>
      </div>
    );
  }

  const role = resolveRole(me.data?.role);
  const apiUnavailable =
    me.isError &&
    (!(me.error instanceof ApiError) ||
      me.error.status >= 500 ||
      me.error.status === 0);

  return (
    <div className="flex min-h-full flex-1">
      <AppSidebar role={role} />
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-14 items-center justify-between border-b border-border px-4">
          <div className="text-sm text-muted-foreground">
            {me.data?.workspace?.name
              ? me.data.workspace.name
              : me.data?.workspace?.id
                ? `Workspace ${me.data.workspace.id.slice(0, 8)}…`
                : "Workspace"}
          </div>
          <UserMenu email={me.data?.email ?? email} />
        </header>
        <main className="flex min-h-0 flex-1 flex-col p-4 md:p-6">
          {me.isError ? (
            <div className="mb-4">
              {apiUnavailable ? (
                <Alert>
                  <AlertTitle>API unavailable</AlertTitle>
                  <AlertDescription>
                    {me.error instanceof Error
                      ? me.error.message
                      : "Could not reach FastAPI. Auth still works; workspace data will load when the API is up."}
                  </AlertDescription>
                </Alert>
              ) : (
                <ErrorState
                  title="Workspace access error"
                  message={
                    me.error instanceof Error
                      ? me.error.message
                      : "Request failed"
                  }
                />
              )}
            </div>
          ) : null}
          {children}
        </main>
      </div>
    </div>
  );
}
