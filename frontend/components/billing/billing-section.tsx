"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useEffect, useRef } from "react";
import { ErrorState, LoadingBlock } from "@/components/shared/state-panel";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

import { ApiError } from "@/lib/client";
import {
  createBillingPortalSession,
  createCheckoutSession,
  fetchSubscription,
} from "@/lib/endpoints";
import { toastApiError, toastSuccess } from "@/lib/toast";

export function BillingSection() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const handledCheckout = useRef(false);

  const subscription = useQuery({
    queryKey: ["subscription"],
    queryFn: fetchSubscription,
  });

  useEffect(() => {
    if (handledCheckout.current || typeof window === "undefined") return;
    const checkout = new URLSearchParams(window.location.search).get(
      "checkout",
    );
    if (!checkout) return;
    handledCheckout.current = true;

    if (checkout === "success") {
      toastSuccess("Payment received. Refreshing your plan…");
      void queryClient.invalidateQueries({ queryKey: ["subscription"] });
      void queryClient.invalidateQueries({ queryKey: ["me"] });
    }

    router.replace("/settings#billing");
  }, [queryClient, router]);

  const checkout = useMutation({
    mutationFn: createCheckoutSession,
    onSuccess: (data) => {
      window.location.assign(data.checkout_url);
    },
    onError: (error) => {
      toastApiError(error, "Could not start checkout");
    },
  });

  const portal = useMutation({
    mutationFn: createBillingPortalSession,
    onSuccess: (data) => {
      window.location.assign(data.portal_url);
    },
    onError: (error) => {
      toastApiError(error, "Could not open billing portal");
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

  const plan = (subscription.data?.plan_tier ?? "free").toLowerCase();
  const status = subscription.data?.status ?? "none";
  const isPro = plan === "pro";

  return (
    <div className="grid max-w-4xl gap-4 md:grid-cols-2">
      {!isPro ? (
        <Card>
          <CardHeader>
            <CardTitle>Free Plan</CardTitle>
            <CardDescription>Your current plan</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex items-center gap-2">
              <span className="text-2xl font-semibold">Free</span>
              <Badge variant="outline" className="capitalize">
                {status}
              </Badge>
            </div>
            <ul className="space-y-1 text-sm text-muted-foreground">
              <li>3 members</li>
              <li>10 documents</li>
              <li>100 chats / month</li>
            </ul>
          </CardContent>
        </Card>
      ) : null}

      <Card className={isPro ? "md:col-span-2 max-w-xl" : undefined}>
        <CardHeader>
          <CardTitle>Pro Plan</CardTitle>
          <CardDescription>
            {isPro
              ? "Your current plan"
              : "Upgrade for higher limits and custom prompts"}
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex items-center gap-2">
            <span className="text-2xl font-semibold">Pro</span>
            {isPro ? (
              <Badge variant="outline" className="capitalize">
                {status}
              </Badge>
            ) : null}
          </div>
          {subscription.data?.cancel_at_period_end ? (
            <p className="text-sm text-muted-foreground">
              Cancels at the end of the current billing period.
            </p>
          ) : null}
          <ul className="space-y-1 text-sm text-muted-foreground">
            <li>25 members</li>
            <li>200 documents</li>
            <li>5,000 chats / month</li>
            <li>Custom system prompt</li>
          </ul>
        </CardContent>
        <CardFooter>
          {isPro ? (
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

    </div>
  );
}
