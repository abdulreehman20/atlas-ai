"use client";

import { useQuery } from "@tanstack/react-query";

import { ApiError } from "@/lib/client";
import { fetchMe } from "@/lib/endpoints";

export function useMe() {
  return useQuery({
    queryKey: ["me"],
    queryFn: fetchMe,
    retry: (failureCount, error) => {
      if (
        error instanceof ApiError &&
        (error.status === 401 || error.status === 403)
      ) {
        return false;
      }
      return failureCount < 1;
    },
  });
}
