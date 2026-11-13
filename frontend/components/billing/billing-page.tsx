"use client";

import { useMutation, useQuery } from "@tanstack/react-query";

import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { OwnerGate } from "@/components/shared/owner-gate";
import { ErrorState, LoadingBlock } from "@/components/shared/state-panel";

import { ApiError } from "@/lib/client";
import {
  createBillingPortalSession,
  createCheckoutSession,
  fetchSubscription,
} from "@/lib/endpoints";

function BillingContent() {
  const subscription = useQuery({
    queryKey: ["subscription"],
    queryFn: fetchSubscription,
  });

  const checkout = useMutation({
    mutationFn: createCheckoutSession,
    onSuccess: (data) => {
      window.location.assign(data.checkout_url);
    },
  });

  const portal = useMutation({
    mutationFn: createBillingPortalSession,
    onSuccess: (data) => {
      window.location.assign(data.portal_url);
    },
  });

  if (subscription.isLoading) return <LoadingBlock rows={4} />;
  if (subscription.isError) {
    return (
      <ErrorState
        title="Could not load billing"
        message={
          subscription.error instanceof ApiError
            ? subscription.error.message
            : subscription.error instanceof Error
              ? subscription.error.message
              : "Request failed"
        }
      />
    );
  }

  const plan = subscription.data?.plan_tier ?? "free";
  const status = subscription.data?.status ?? "none";

  return (
    <div className="grid max-w-4xl gap-4 md:grid-cols-2">
      <Card>
        <CardHeader>
          <CardTitle>Current plan</CardTitle>
          <CardDescription>
            Entitlements come from verified Stripe webhooks, not this page
            alone.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex items-center gap-2">
            <span className="text-2xl font-semibold capitalize">{plan}</span>
            <Badge variant="outline" className="capitalize">
              {status}
            </Badge>
          </div>
          {subscription.data?.cancel_at_period_end ? (
            <p className="text-sm text-muted-foreground">
              Cancels at the end of the current billing period.
            </p>
          ) : null}
          <ul className="space-y-1 text-sm text-muted-foreground">
            <li>Free: 3 members, 20 docs, 100 chats/month</li>
            <li>Pro: 25 members, 500 docs, 5,000 chats/month, custom prompt</li>
          </ul>
        </CardContent>
        <CardFooter className="gap-2">
          {plan === "pro" ? (
            <Button
              variant="outline"
              disabled={portal.isPending}
              onClick={() => portal.mutate()}
            >
              {portal.isPending ? "Opening…" : "Manage billing"}
            </Button>
          ) : (
            <Button
              disabled={checkout.isPending}
              onClick={() => checkout.mutate()}
            >
              {checkout.isPending ? "Redirecting…" : "Upgrade to Pro"}
            </Button>
          )}
        </CardFooter>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Over-limit behavior</CardTitle>
          <CardDescription>Option A billing policy</CardDescription>
        </CardHeader>
        <CardContent className="space-y-2 text-sm text-muted-foreground">
          <p>When a workspace is over plan limits:</p>
          <ul className="list-disc space-y-1 pl-5">
            <li>New uploads are blocked</li>
            <li>New chat is blocked</li>
            <li>Existing documents and history stay visible</li>
          </ul>
        </CardContent>
      </Card>

      {checkout.isError || portal.isError ? (
        <div className="md:col-span-2">
          <ErrorState
            title="Billing action failed"
            message={
              (checkout.error ?? portal.error) instanceof Error
                ? ((checkout.error ?? portal.error) as Error).message
                : "Request failed"
            }
          />
        </div>
      ) : null}
    </div>
  );
}

export function BillingPage() {
  return (
    <div className="space-y-6">
      <div className="space-y-1">
        <h1 className="text-lg font-semibold tracking-tight">Billing</h1>
        <p className="text-sm text-muted-foreground">
          Owner-only plan status and Stripe Checkout.
        </p>
      </div>
      <OwnerGate>
        <BillingContent />
      </OwnerGate>
    </div>
  );
}
