"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { LoadingBlock } from "@/components/shared/state-panel";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { createClient } from "@/lib/supabase/client";

const schema = z
  .object({
    password: z.string().min(8, "Password must be at least 8 characters"),
    confirm_password: z.string().min(8, "Confirm your password"),
  })
  .refine((values) => values.password === values.confirm_password, {
    message: "Passwords do not match",
    path: ["confirm_password"],
  });

type FormValues = z.infer<typeof schema>;

function parseHashParams(): URLSearchParams {
  if (typeof window === "undefined") return new URLSearchParams();
  const hash = window.location.hash.startsWith("#")
    ? window.location.hash.slice(1)
    : window.location.hash;
  return new URLSearchParams(hash);
}

export function AcceptInviteForm() {
  const router = useRouter();
  const [ready, setReady] = useState(false);
  const [email, setEmail] = useState<string | null>(null);
  const [bootError, setBootError] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { password: "", confirm_password: "" },
  });

  useEffect(() => {
    let cancelled = false;

    async function bootstrap() {
      const supabase = createClient();
      const hash = parseHashParams();
      const errorCode = hash.get("error_code") || hash.get("error");
      const errorDescription = hash.get("error_description");
      if (errorCode) {
        if (!cancelled) {
          setBootError(
            errorDescription?.replace(/\+/g, " ") ||
              "This invitation link is invalid or has expired. Ask the owner to invite you again.",
          );
          setReady(true);
        }
        return;
      }

      // Invite / magic-link tokens may arrive as query params (PKCE) or hash.
      const search = new URLSearchParams(window.location.search);
      const code = search.get("code");
      if (code) {
        const { error } = await supabase.auth.exchangeCodeForSession(code);
        if (error && !cancelled) {
          setBootError(error.message);
          setReady(true);
          return;
        }
      } else {
        const accessToken = hash.get("access_token");
        const refreshToken = hash.get("refresh_token");
        const type = hash.get("type");
        if (accessToken && refreshToken) {
          const { error } = await supabase.auth.setSession({
            access_token: accessToken,
            refresh_token: refreshToken,
          });
          if (error && !cancelled) {
            setBootError(error.message);
            setReady(true);
            return;
          }
        } else if (
          type === "invite" ||
          type === "recovery" ||
          type === "magiclink"
        ) {
          // Token hash style links without access_token — try verifyOtp when present.
          const tokenHash = hash.get("token_hash") || search.get("token_hash");
          if (tokenHash) {
            const { error } = await supabase.auth.verifyOtp({
              type: type === "recovery" ? "recovery" : "invite",
              token_hash: tokenHash,
            });
            if (error && !cancelled) {
              setBootError(error.message);
              setReady(true);
              return;
            }
          }
        }
      }

      const { data, error } = await supabase.auth.getUser();
      if (cancelled) return;
      if (error || !data.user) {
        setBootError(
          "Could not open this invitation. Open the latest invite email link, or ask the owner to resend.",
        );
        setReady(true);
        return;
      }

      setEmail(data.user.email ?? null);
      setReady(true);
      // Clean sensitive tokens from the address bar.
      window.history.replaceState({}, "", "/auth/accept-invite");
    }

    void bootstrap();
    return () => {
      cancelled = true;
    };
  }, []);

  async function onSubmit(values: FormValues) {
    setFormError(null);
    setSaving(true);
    const supabase = createClient();
    const { error } = await supabase.auth.updateUser({
      password: values.password,
    });
    setSaving(false);
    if (error) {
      setFormError(error.message);
      return;
    }
    router.push("/chat");
    router.refresh();
  }

  if (!ready) return <LoadingBlock rows={4} />;

  if (bootError) {
    return (
      <div className="space-y-4">
        <Alert variant="destructive">
          <AlertTitle>Invitation unavailable</AlertTitle>
          <AlertDescription>{bootError}</AlertDescription>
        </Alert>
        <Button
          type="button"
          variant="outline"
          className="w-full"
          onClick={() => router.push("/login")}
        >
          Go to sign in
        </Button>
      </div>
    );
  }

  return (
    <form className="space-y-4" onSubmit={form.handleSubmit(onSubmit)}>
      {email ? (
        <div className="space-y-2">
          <Label htmlFor="invite-email">Email</Label>
          <Input id="invite-email" value={email} disabled />
        </div>
      ) : null}

      <div className="space-y-2">
        <Label htmlFor="invite-password">Create password</Label>
        <Input
          id="invite-password"
          type="password"
          autoComplete="new-password"
          {...form.register("password")}
        />
        {form.formState.errors.password ? (
          <p className="text-xs text-destructive">
            {form.formState.errors.password.message}
          </p>
        ) : null}
      </div>

      <div className="space-y-2">
        <Label htmlFor="invite-confirm">Confirm password</Label>
        <Input
          id="invite-confirm"
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

      {formError ? (
        <Alert variant="destructive">
          <AlertTitle>Could not set password</AlertTitle>
          <AlertDescription>{formError}</AlertDescription>
        </Alert>
      ) : null}

      <Button type="submit" className="w-full" disabled={saving}>
        {saving ? "Saving…" : "Activate account"}
      </Button>
    </form>
  );
}
