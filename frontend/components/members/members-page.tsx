"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { RefreshCw, UserPlus } from "lucide-react";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { OwnerGate } from "@/components/shared/owner-gate";
import {
  EmptyState,
  ErrorState,
  LoadingBlock,
} from "@/components/shared/state-panel";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

import { ApiError } from "@/lib/client";
import { fetchMembers, inviteMember, removeMember } from "@/lib/endpoints";
import { toastApiError, toastSuccess } from "@/lib/toast";

const inviteSchema = z.object({
  first_name: z.string().min(1, "First name is required").max(100),
  last_name: z.string().min(1, "Last name is required").max(100),
  email: z.email("Enter a valid email"),
});

type InviteValues = z.infer<typeof inviteSchema>;

function MembersContent() {
  const queryClient = useQueryClient();
  const [inviteOpen, setInviteOpen] = useState(false);

  const members = useQuery({
    queryKey: ["members"],
    queryFn: async () => {
      const page = await fetchMembers();
      return page.items;
    },
  });

  const form = useForm<InviteValues>({
    resolver: zodResolver(inviteSchema),
    defaultValues: { first_name: "", last_name: "", email: "" },
  });

  const invite = useMutation({
    mutationFn: (values: InviteValues) =>
      inviteMember({
        email: values.email,
        first_name: values.first_name,
        last_name: values.last_name,
      }),
    onSuccess: async () => {
      form.reset();
      setInviteOpen(false);
      toastSuccess("Invite sent.");
      await queryClient.invalidateQueries({ queryKey: ["members"] });
    },
    onError: (error) => {
      toastApiError(error, "Could not invite");
    },
  });

  const remove = useMutation({
    mutationFn: removeMember,
    onSuccess: async () => {
      toastSuccess("Member removed.");
      await queryClient.invalidateQueries({ queryKey: ["members"] });
    },
    onError: (error) => {
      toastApiError(error, "Could not remove");
    },
  });

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-end gap-2">
        <Button
          type="button"
          variant="outline"
          disabled={members.isFetching}
          onClick={() => void members.refetch()}
        >
          <RefreshCw className="size-4" />
          Refresh
        </Button>
        <Button type="button" onClick={() => setInviteOpen(true)}>
          <UserPlus className="size-4" />
          Invite Member
        </Button>
      </div>

      <Dialog
        open={inviteOpen}
        onOpenChange={(open) => {
          setInviteOpen(open);
          if (!open) {
            form.reset();
            invite.reset();
          }
        }}
      >
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Invite Member</DialogTitle>
            <DialogDescription>
              We’ll add them to this workspace and email a Supabase invite so
              they can sign in.
            </DialogDescription>
          </DialogHeader>
          <form
            className="space-y-4"
            onSubmit={form.handleSubmit((values) => invite.mutate(values))}
          >
            <div className="grid gap-3 sm:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="invite-first-name">First name</Label>
                <Input
                  id="invite-first-name"
                  autoComplete="given-name"
                  {...form.register("first_name")}
                />
                {form.formState.errors.first_name ? (
                  <p className="text-xs text-destructive">
                    {form.formState.errors.first_name.message}
                  </p>
                ) : null}
              </div>
              <div className="space-y-2">
                <Label htmlFor="invite-last-name">Last name</Label>
                <Input
                  id="invite-last-name"
                  autoComplete="family-name"
                  {...form.register("last_name")}
                />
                {form.formState.errors.last_name ? (
                  <p className="text-xs text-destructive">
                    {form.formState.errors.last_name.message}
                  </p>
                ) : null}
              </div>
            </div>
            <div className="space-y-2">
              <Label htmlFor="invite-email">Email</Label>
              <Input
                id="invite-email"
                type="email"
                autoComplete="email"
                placeholder="member@company.com"
                {...form.register("email")}
              />
              {form.formState.errors.email ? (
                <p className="text-xs text-destructive">
                  {form.formState.errors.email.message}
                </p>
              ) : null}
            </div>

            <DialogFooter>
              <Button
                type="button"
                variant="outline"
                onClick={() => setInviteOpen(false)}
              >
                Cancel
              </Button>
              <Button type="submit" disabled={invite.isPending}>
                {invite.isPending ? "Sending…" : "Send"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

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
