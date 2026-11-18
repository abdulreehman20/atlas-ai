import { toast } from "sonner";

import { ApiError } from "@/lib/client";

export function toastApiError(
  error: unknown,
  fallback = "Something went wrong",
): void {
  if (error instanceof ApiError) {
    if (error.isUpgradeRequired) {
      toast.warning(error.message, {
        description: "Open Settings → Billing to upgrade.",
        duration: 8000,
      });
      return;
    }
    toast.error(error.message);
    return;
  }

  if (error instanceof Error && error.message) {
    toast.error(error.message);
    return;
  }

  toast.error(fallback);
}

export function toastSuccess(message: string): void {
  toast.success(message);
}
