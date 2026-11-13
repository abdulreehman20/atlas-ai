"use client";

import { z } from "zod";
import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { OwnerGate } from "@/components/shared/owner-gate";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { ErrorState, LoadingBlock } from "@/components/shared/state-panel";

import { ApiError } from "@/lib/client";
import {
  fetchWorkspaceSettings,
  updateWorkspaceSettings,
} from "@/lib/endpoints";

const schema = z.object({
  system_prompt_override: z
    .string()
    .max(8000, "Keep the override under 8,000 characters"),
});

type FormValues = z.infer<typeof schema>;

function SettingsForm() {
  const queryClient = useQueryClient();
  const settings = useQuery({
    queryKey: ["workspace-settings"],
    queryFn: fetchWorkspaceSettings,
  });

  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { system_prompt_override: "" },
  });

  useEffect(() => {
    if (settings.data) {
      form.reset({
        system_prompt_override: settings.data.system_prompt_override ?? "",
      });
    }
  }, [settings.data, form]);

  const save = useMutation({
    mutationFn: updateWorkspaceSettings,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["workspace-settings"] });
    },
  });

  if (settings.isLoading) return <LoadingBlock rows={4} />;
  if (settings.isError) {
    return (
      <ErrorState
        title="Could not load settings"
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
    <form
      className="max-w-2xl space-y-4"
      onSubmit={form.handleSubmit((values) => save.mutate(values))}
    >
      <Alert>
        <AlertTitle>Prompt layers</AlertTitle>
        <AlertDescription>
          Platform safety/guardrails stay locked. This field is the
          owner-editable workspace instruction override (Pro entitlement
          enforced by FastAPI).
        </AlertDescription>
      </Alert>

      <div className="space-y-2">
        <Label htmlFor="system_prompt_override">
          Workspace system prompt override
        </Label>
        <Textarea
          id="system_prompt_override"
          rows={10}
          placeholder="Optional instructions for how Atlas should answer in this workspace…"
          {...form.register("system_prompt_override")}
        />
        {form.formState.errors.system_prompt_override ? (
          <p className="text-xs text-destructive">
            {form.formState.errors.system_prompt_override.message}
          </p>
        ) : null}
      </div>

      {save.isError ? (
        <ErrorState
          title="Save failed"
          message={
            save.error instanceof Error
              ? save.error.message
              : "Could not save settings"
          }
        />
      ) : null}
      {save.isSuccess ? (
        <Alert>
          <AlertTitle>Saved</AlertTitle>
          <AlertDescription>
            Workspace prompt override updated.
          </AlertDescription>
        </Alert>
      ) : null}

      <Button type="submit" disabled={save.isPending}>
        {save.isPending ? "Saving…" : "Save override"}
      </Button>
    </form>
  );
}

export function SettingsPage() {
  return (
    <div className="space-y-6">
      <div className="space-y-1">
        <h1 className="text-lg font-semibold tracking-tight">Settings</h1>
        <p className="text-sm text-muted-foreground">
          Owner-only workspace configuration.
        </p>
      </div>
      <OwnerGate>
        <SettingsForm />
      </OwnerGate>
    </div>
  );
}
