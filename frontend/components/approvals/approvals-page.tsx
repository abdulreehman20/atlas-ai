"use client";

import { useQuery } from "@tanstack/react-query";

import {
  EmptyState,
  ErrorState,
  LoadingBlock,
} from "@/components/shared/state-panel";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { OwnerGate } from "@/components/shared/owner-gate";

import { ApiError } from "@/lib/client";
import { fetchApprovals } from "@/lib/endpoints";
import type { ApprovalStatus } from "@/types/types";

function statusVariant(
  status: ApprovalStatus | string,
): "default" | "secondary" | "outline" | "destructive" {
  switch (status) {
    case "pending":
    case "executing":
      return "secondary";
    case "approved":
    case "edited":
    case "executed":
      return "default";
    case "rejected":
      return "destructive";
    case "expired":
      return "outline";
    default:
      return "outline";
  }
}

function approvalType(item: {
  action_type?: string;
  action?: string;
  tool_name?: string;
}): string {
  return item.action_type ?? item.action ?? item.tool_name ?? "—";
}

function ApprovalsContent() {
  const approvals = useQuery({
    queryKey: ["approvals"],
    queryFn: fetchApprovals,
  });

  if (approvals.isLoading) return <LoadingBlock rows={5} />;
  if (approvals.isError) {
    return (
      <ErrorState
        title="Could not load approvals"
        message={
          approvals.error instanceof ApiError
            ? approvals.error.message
            : approvals.error instanceof Error
              ? approvals.error.message
              : "Request failed"
        }
      />
    );
  }

  if (!approvals.data || approvals.data.length === 0) {
    return (
      <EmptyState
        title="No approval requests"
        description="Sensitive agent tool actions that need human review will appear here."
      />
    );
  }

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Summary</TableHead>
          <TableHead>Type</TableHead>
          <TableHead>Status</TableHead>
          <TableHead>Requester</TableHead>
          <TableHead>Created</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {approvals.data.map((item) => (
          <TableRow key={item.id}>
            <TableCell className="max-w-md">{item.summary}</TableCell>
            <TableCell className="font-mono text-xs">
              {approvalType(item)}
            </TableCell>
            <TableCell>
              <Badge
                variant={statusVariant(item.status)}
                className="capitalize"
              >
                {item.status}
              </Badge>
            </TableCell>
            <TableCell>
              {item.requester_email ?? item.requester_user_id ?? "—"}
            </TableCell>
            <TableCell>{new Date(item.created_at).toLocaleString()}</TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}

export function ApprovalsPage() {
  return (
    <div className="space-y-6">
      <div className="space-y-1">
        <h1 className="text-lg font-semibold tracking-tight">Approvals</h1>
        <p className="text-sm text-muted-foreground">
          Owner review queue for future sensitive agent actions.
        </p>
      </div>
      <OwnerGate>
        <ApprovalsContent />
      </OwnerGate>
    </div>
  );
}
