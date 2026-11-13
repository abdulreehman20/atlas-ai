"use client";

import { z } from "zod";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { OwnerGate } from "@/components/shared/owner-gate";
import {
  EmptyState,
  ErrorState,
  LoadingBlock,
} from "@/components/shared/state-panel";

import { ApiError } from "@/lib/client";
import { fetchMembers, inviteMember, removeMember } from "@/lib/endpoints";

const inviteSchema = z.object({
  email: z.email("Enter a valid email"),
});

type InviteValues = z.infer<typeof inviteSchema>;

function MembersContent() {
  const queryClient = useQueryClient();
  const members = useQuery({
    queryKey: ["members"],
    queryFn: async () => {
      const page = await fetchMembers();
      return page.items;
    },
  });

  const form = useForm<InviteValues>({
    resolver: zodResolver(inviteSchema),
    defaultValues: { email: "" },
  });

  const invite = useMutation({
    mutationFn: (values: InviteValues) => inviteMember(values.email),
    onSuccess: async () => {
      form.reset();
      await queryClient.invalidateQueries({ queryKey: ["members"] });
    },
  });

  const remove = useMutation({
    mutationFn: removeMember,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["members"] });
    },
  });

  return (
    <div className="space-y-6">
      <form
        className="flex max-w-xl flex-wrap items-end gap-3"
        onSubmit={form.handleSubmit((values) => invite.mutate(values))}
      >
        <div className="min-w-56 flex-1 space-y-2">
          <Label htmlFor="invite-email">Invite by email</Label>
          <Input
            id="invite-email"
            type="email"
            placeholder="member@company.com"
            {...form.register("email")}
          />
          {form.formState.errors.email ? (
            <p className="text-xs text-destructive">
              {form.formState.errors.email.message}
            </p>
          ) : null}
        </div>
        <Button type="submit" disabled={invite.isPending}>
          {invite.isPending ? "Inviting…" : "Invite member"}
        </Button>
      </form>

      {invite.isError ? (
        <ErrorState
          title="Invite failed"
          message={
            invite.error instanceof Error
              ? invite.error.message
              : "Could not invite"
          }
        />
      ) : null}
      {remove.isError ? (
        <ErrorState
          title="Remove failed"
          message={
            remove.error instanceof Error
              ? remove.error.message
              : "Could not remove"
          }
        />
      ) : null}

      {members.isLoading ? <LoadingBlock rows={4} /> : null}
      {members.isError ? (
        <ErrorState
          title="Could not load members"
          message={
            members.error instanceof ApiError
              ? members.error.message
              : members.error instanceof Error
                ? members.error.message
                : "Request failed"
          }
        />
      ) : null}

      {members.data && members.data.length === 0 ? (
        <EmptyState
          title="No members yet"
          description="Invite teammates by email. Only owners can manage membership."
        />
      ) : null}

      {members.data && members.data.length > 0 ? (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Email</TableHead>
              <TableHead>Role</TableHead>
              <TableHead>Status</TableHead>
              <TableHead className="text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {members.data.map((member) => (
              <TableRow key={member.id}>
                <TableCell>{member.email}</TableCell>
                <TableCell className="capitalize">{member.role}</TableCell>
                <TableCell>
                  <Badge variant="outline" className="capitalize">
                    {member.status}
                  </Badge>
                </TableCell>
                <TableCell className="text-right">
                  {member.role === "owner" ? (
                    <span className="text-xs text-muted-foreground">Owner</span>
                  ) : (
                    <Button
                      variant="ghost"
                      size="sm"
                      disabled={remove.isPending}
                      onClick={() => remove.mutate(member.id)}
                    >
                      Remove
                    </Button>
                  )}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      ) : null}
    </div>
  );
}

export function MembersPage() {
  return (
    <div className="space-y-6">
      <div className="space-y-1">
        <h1 className="text-lg font-semibold tracking-tight">Members</h1>
        <p className="text-sm text-muted-foreground">
          Invite and remove members. Roles cannot be changed after invite in v1.
        </p>
      </div>
      <OwnerGate>
        <MembersContent />
      </OwnerGate>
    </div>
  );
}
