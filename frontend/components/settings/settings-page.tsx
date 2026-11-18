"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { BillingSection } from "@/components/billing/billing-section";
import { ModeToggle } from "@/components/mode-toggle";
import { OwnerGate } from "@/components/shared/owner-gate";
import { ErrorState, LoadingBlock } from "@/components/shared/state-panel";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import { Textarea } from "@/components/ui/textarea";

import { useMe } from "@/hooks/use-me";
import { ApiError } from "@/lib/client";
import {
  deleteWorkspace,
  fetchWorkspaceSettings,
  updateWorkspaceSettings,
} from "@/lib/endpoints";
import { createClient } from "@/lib/supabase/client";
import { toastApiError, toastSuccess } from "@/lib/toast";

const profileSchema = z
  .object({
    first_name: z.string().max(100),
    last_name: z.string().max(100),
    email: z.string(),
    role: z.string(),
    password: z.string().optional(),
    confirm_password: z.string().optional(),
  })
  .superRefine((values, ctx) => {
    const password = values.password?.trim() ?? "";
    const confirm = values.confirm_password?.trim() ?? "";
    if (!password && !confirm) return;
    if (password.length < 8) {
      ctx.addIssue({
        code: "custom",
        path: ["password"],
        message: "Password must be at least 8 characters",
      });
    }
    if (password !== confirm) {
      ctx.addIssue({
        code: "custom",
        path: ["confirm_password"],
        message: "Passwords do not match",
      });
    }
  });

type ProfileValues = z.infer<typeof profileSchema>;

const workspaceSchema = z.object({
  name: z.string().min(1, "Workspace name is required").max(255),
  system_prompt_override: z
    .string()
    .max(8000, "Keep the override under 8,000 characters"),
});

type WorkspaceValues = z.infer<typeof workspaceSchema>;

function splitName(
  meta: Record<string, unknown>,
  email: string | null,
): {
  first_name: string;
  last_name: string;
} {
  const first = String(meta.first_name ?? "").trim();
  const last = String(meta.last_name ?? "").trim();
  if (first || last) return { first_name: first, last_name: last };

  const full = String(meta.full_name ?? meta.name ?? "").trim();
  if (full) {
    const parts = full.split(/\s+/);
    return {
      first_name: parts[0] ?? "",
      last_name: parts.slice(1).join(" "),
    };
  }

  const local = (email ?? "").split("@")[0] ?? "";
  if (!local) return { first_name: "", last_name: "" };
  const pretty = local
    .replace(/[._-]+/g, " ")
    .split(" ")
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1));
  return {
    first_name: pretty[0] ?? local,
    last_name: pretty.slice(1).join(" "),
  };
}

function PersonalDetailsSection() {
  const me = useMe();
  const router = useRouter();
  const [loaded, setLoaded] = useState(false);
  const [saveMessage, setSaveMessage] = useState<string | null>(null);

  const form = useForm<ProfileValues>({
    resolver: zodResolver(profileSchema),
    defaultValues: {
      first_name: "",
      last_name: "",
      email: "",
      role: "",
      password: "",
      confirm_password: "",
    },
  });

  useEffect(() => {
    let cancelled = false;
    async function loadProfile() {
      if (me.isLoading) return;
      const supabase = createClient();
      const { data } = await supabase.auth.getUser();
      if (cancelled) return;
      const meta = (data.user?.user_metadata ?? {}) as Record<string, unknown>;
      const email = me.data?.email ?? data.user?.email ?? "";
      const names = splitName(meta, email);
      form.reset({
        first_name: names.first_name,
        last_name: names.last_name,
        email,
        role: me.data?.role ?? "",
        password: "",
        confirm_password: "",
      });
      setLoaded(true);
    }
    void loadProfile();
    return () => {
      cancelled = true;
    };
  }, [form, me.data?.email, me.data?.role, me.isLoading]);

  const save = useMutation({
    mutationFn: async (values: ProfileValues) => {
      const supabase = createClient();
      const password = values.password?.trim() ?? "";
      const { error } = await supabase.auth.updateUser({
        data: {
          first_name: values.first_name.trim(),
          last_name: values.last_name.trim(),
          full_name: `${values.first_name} ${values.last_name}`.trim(),
          name: `${values.first_name} ${values.last_name}`.trim(),
        },
        ...(password ? { password } : {}),
      });
      if (error) throw new Error(error.message);
    },
    onSuccess: () => {
      setSaveMessage("Profile updated in Supabase Auth.");
      form.setValue("password", "");
      form.setValue("confirm_password", "");
    },
  });

  async function signOut() {
    const supabase = createClient();
    await supabase.auth.signOut();
    router.push("/login");
    router.refresh();
  }

  if (me.isLoading || !loaded) {
    return (
      <section className="max-w-2xl space-y-4">
        <div className="space-y-1">
          <h2 className="text-sm font-medium">Personal details</h2>
          <p className="text-sm text-muted-foreground">
            Loading your authentication profile…
          </p>
        </div>
        <LoadingBlock rows={5} />
      </section>
    );
  }

  return (
    <section className="max-w-2xl space-y-4">
      <div className="space-y-1">
        <h2 className="text-sm font-medium">Personal details</h2>
        <p className="text-sm text-muted-foreground">
          Your account name, email, password, and workspace role.
        </p>
      </div>

      <form
        className="space-y-4"
        onSubmit={form.handleSubmit((values) => save.mutate(values))}
      >
        <div className="grid gap-3 sm:grid-cols-2">
          <div className="space-y-2">
            <Label htmlFor="first_name">First name</Label>
            <Input id="first_name" {...form.register("first_name")} />
          </div>
          <div className="space-y-2">
            <Label htmlFor="last_name">Last name</Label>
            <Input id="last_name" {...form.register("last_name")} />
          </div>
        </div>

        <div className="space-y-2">
          <Label htmlFor="email">Email</Label>
          <Input id="email" type="email" disabled {...form.register("email")} />
        </div>

        <div className="space-y-2">
          <Label htmlFor="role">Role</Label>
          <Input
            id="role"
            disabled
            className="capitalize"
            {...form.register("role")}
          />
        </div>

        <div className="grid gap-3 sm:grid-cols-2">
          <div className="space-y-2">
            <Label htmlFor="password">New password</Label>
            <Input
              id="password"
              type="password"
              autoComplete="new-password"
              placeholder="Leave blank to keep current"
              {...form.register("password")}
            />
            {form.formState.errors.password ? (
              <p className="text-xs text-destructive">
                {form.formState.errors.password.message}
              </p>
            ) : null}
          </div>
          <div className="space-y-2">
            <Label htmlFor="confirm_password">Confirm password</Label>
            <Input
              id="confirm_password"
              type="password"
              autoComplete="new-password"
              {...form.register("confirm_password")}
            />
            {form.formState.errors.confirm_password ? (
              <p className="text-xs text-destructive">
                {form.formState.errors.confirm_password.message}
              </p>
            ) : null}
          </div>
        </div>

        {save.isError ? (
          <ErrorState
            title="Could not update profile"
            message={
              save.error instanceof Error ? save.error.message : "Update failed"
            }
          />
        ) : null}
        {saveMessage ? (
          <Alert>
            <AlertTitle>Saved</AlertTitle>
            <AlertDescription>{saveMessage}</AlertDescription>
          </Alert>
        ) : null}

        <div className="flex flex-wrap gap-2">
          <Button type="submit" disabled={save.isPending}>
            {save.isPending ? "Saving…" : "Save profile"}
          </Button>
          <Button
            type="button"
            variant="outline"
            onClick={() => void signOut()}
          >
            Sign out
          </Button>
        </div>
      </form>
    </section>
  );
}

function WorkspaceDetailsSection() {
  const queryClient = useQueryClient();
  const me = useMe();
  const settings = useQuery({
    queryKey: ["workspace-settings"],
    queryFn: fetchWorkspaceSettings,
  });

  const form = useForm<WorkspaceValues>({
    resolver: zodResolver(workspaceSchema),
    defaultValues: { name: "", system_prompt_override: "" },
  });

  useEffect(() => {
    if (settings.data || me.data?.workspace?.name) {
      form.reset({
        name: settings.data?.name ?? me.data?.workspace?.name ?? "",
        system_prompt_override:
          settings.data?.system_prompt_override ||
          settings.data?.effective_system_prompt ||
          settings.data?.default_system_prompt ||
          "",
      });
    }
  }, [settings.data, me.data?.workspace?.name, form]);

  const save = useMutation({
    mutationFn: updateWorkspaceSettings,
    onSuccess: async () => {
      toastSuccess("Workspace details updated.");
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["workspace-settings"] }),
        queryClient.invalidateQueries({ queryKey: ["me"] }),
      ]);
    },
    onError: (error) => {
      toastApiError(error, "Could not save workspace");
    },
  });

  if (settings.isLoading) return <LoadingBlock rows={4} />;
  if (settings.isError) {
    return (
      <ErrorState
        title="Could not load workspace"
        message={
          settings.error instanceof ApiError
            ? settings.error.message
            : settings.error instanceof Error
              ? settings.error.message
              : "Request failed"
        }
      />
    );
  }

  return (
    <section className="max-w-2xl space-y-4">
      <div className="space-y-1">
        <h2 className="text-sm font-medium">Workspace details</h2>
        <p className="text-sm text-muted-foreground">
          Update the workspace name and optional system prompt override.
        </p>
      </div>

      <form
        className="space-y-4"
        onSubmit={form.handleSubmit((values) => {
          const defaultPrompt = (
            settings.data?.default_system_prompt ?? ""
          ).trim();
          const nextPrompt = values.system_prompt_override.trim();
          save.mutate({
            name: values.name,
            system_prompt_override:
              !nextPrompt || nextPrompt === defaultPrompt ? null : nextPrompt,
          });
        })}
      >
        <div className="space-y-2">
          <Label htmlFor="workspace_name">Workspace name</Label>
          <Input id="workspace_name" {...form.register("name")} />
          {form.formState.errors.name ? (
            <p className="text-xs text-destructive">
              {form.formState.errors.name.message}
            </p>
          ) : null}
        </div>

        <div className="space-y-2">
          <Label htmlFor="system_prompt_override">System prompt</Label>
          <Textarea
            id="system_prompt_override"
            rows={10}
            {...form.register("system_prompt_override")}
          />
          <p className="text-xs text-muted-foreground">
            Shows the current workspace prompt (defaults to the platform
            prompt). Saving stores it as a workspace override (Pro plan
            required).
          </p>
          {form.formState.errors.system_prompt_override ? (
            <p className="text-xs text-destructive">
              {form.formState.errors.system_prompt_override.message}
            </p>
          ) : null}
        </div>

        <Button type="submit" disabled={save.isPending}>
          {save.isPending ? "Saving…" : "Save workspace"}
        </Button>
      </form>
    </section>
  );
}

function DeleteWorkspaceSection() {
  const router = useRouter();
  const deleteMutation = useMutation({
    mutationFn: deleteWorkspace,
    onSuccess: async () => {
      const supabase = createClient();
      await supabase.auth.signOut();
      router.push("/login");
      router.refresh();
    },
    onError: (error) => {
      toastApiError(error, "Could not delete workspace");
    },
  });

  return (
    <section className="max-w-2xl space-y-4">
      <div className="space-y-1">
        <h2 className="text-sm font-medium text-destructive">
          Delete workspace
        </h2>
        <p className="text-sm text-muted-foreground">
          Permanently archives this workspace and related memberships,
          documents, and organization access. This cannot be undone from the UI.
        </p>
      </div>

      <AlertDialog>
        <AlertDialogTrigger render={<Button variant="destructive" />}>
          Delete workspace
        </AlertDialogTrigger>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete this workspace?</AlertDialogTitle>
            <AlertDialogDescription>
              All members lose access. Documents are marked deleted and the
              organization is suspended. You will be signed out afterward.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              variant="destructive"
              disabled={deleteMutation.isPending}
              onClick={() => deleteMutation.mutate()}
            >
              {deleteMutation.isPending ? "Deleting…" : "Delete"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </section>
  );
}

export function SettingsPage() {
  return (
    <div className="space-y-8">
      <div className="space-y-1">
        <h1 className="text-lg font-semibold tracking-tight">Settings</h1>
        <p className="text-sm text-muted-foreground">
          Manage your account, workspace, appearance, and billing.
        </p>
      </div>

      <PersonalDetailsSection />
      <Separator />

      <OwnerGate fallback={null}>
        <WorkspaceDetailsSection />
        <Separator className="my-8" />
      </OwnerGate>

      <section className="max-w-2xl space-y-3">
        <div className="space-y-1">
          <h2 className="text-sm font-medium">Mode Toggle</h2>
          <p className="text-sm text-muted-foreground">
            Switch between light, dark, or system theme.
          </p>
        </div>
        <ModeToggle />
      </section>
      <Separator />

      <OwnerGate fallback={null}>
        <section id="billing" className="space-y-4 scroll-mt-6">
          <div className="space-y-1">
            <h2 className="text-sm font-medium">Billing</h2>
            <p className="text-sm text-muted-foreground">
              View your plan and upgrade when you need higher limits.
            </p>
          </div>
          <BillingSection />
        </section>
        <Separator className="my-8" />
        <DeleteWorkspaceSection />
      </OwnerGate>
    </div>
  );
}
