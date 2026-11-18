import { createClient } from "@/lib/supabase/client";

export class ApiError extends Error {
  readonly status: number;
  readonly code: string | null;
  readonly details: Record<string, unknown> | null;
  readonly body: unknown;

  constructor(
    status: number,
    message: string,
    body?: unknown,
    code?: string | null,
    details?: Record<string, unknown> | null,
  ) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.body = body;
    this.code = code ?? null;
    this.details = details ?? null;
  }

  get isUpgradeRequired(): boolean {
    if (this.code === "entitlement_exceeded") return true;
    if (this.details?.upgrade_required === true) return true;
    if (this.status === 402) return true;
    return /upgrade to pro|requires (the )?pro plan|pro plan required/i.test(
      this.message,
    );
  }
}

function getApiBaseUrl(): string {
  const base = process.env.NEXT_PUBLIC_API_BASE_URL;
  if (!base) {
    throw new Error("Missing NEXT_PUBLIC_API_BASE_URL");
  }
  return base.replace(/\/$/, "");
}

function parseErrorPayload(body: unknown, fallback: string): {
  message: string;
  code: string | null;
  details: Record<string, unknown> | null;
} {
  if (!body || typeof body !== "object") {
    return { message: fallback, code: null, details: null };
  }
  const record = body as Record<string, unknown>;
  const nested =
    record.error && typeof record.error === "object"
      ? (record.error as Record<string, unknown>)
      : null;

  const messageCandidate =
    (nested && typeof nested.message === "string" && nested.message) ||
    (typeof record.detail === "string" && record.detail) ||
    (typeof record.message === "string" && record.message) ||
    fallback;

  const code =
    (nested && typeof nested.code === "string" && nested.code) ||
    (typeof record.code === "string" && record.code) ||
    null;

  const detailsRaw = nested?.details ?? record.details;
  const details =
    detailsRaw && typeof detailsRaw === "object"
      ? (detailsRaw as Record<string, unknown>)
      : null;

  return { message: messageCandidate, code, details };
}

export async function getAccessToken(): Promise<string> {
  const supabase = createClient();
  const { data, error } = await supabase.auth.getSession();
  if (error) {
    throw new ApiError(401, error.message);
  }
  const token = data.session?.access_token;
  if (!token) {
    throw new ApiError(401, "Not authenticated");
  }
  return token;
}

type ApiFetchOptions = Omit<RequestInit, "body"> & {
  body?: unknown;
  token?: string;
};

export async function apiFetch<T>(
  path: string,
  options: ApiFetchOptions = {},
): Promise<T> {
  const { body, token, headers, ...rest } = options;
  const accessToken = token ?? (await getAccessToken());
  const url = `${getApiBaseUrl()}${path.startsWith("/") ? path : `/${path}`}`;

  const response = await fetch(url, {
    ...rest,
    headers: {
      Accept: "application/json",
      Authorization: `Bearer ${accessToken}`,
      ...(body !== undefined ? { "Content-Type": "application/json" } : {}),
      ...headers,
    },
    body: body === undefined ? undefined : JSON.stringify(body),
  });

  if (response.status === 204) {
    return undefined as T;
  }

  const contentType = response.headers.get("content-type") ?? "";
  const payload = contentType.includes("application/json")
    ? await response.json().catch(() => null)
    : await response.text().catch(() => null);

  if (!response.ok) {
    const parsed = parseErrorPayload(
      payload,
      response.statusText || "Request failed",
    );
    throw new ApiError(
      response.status,
      parsed.message,
      payload,
      parsed.code,
      parsed.details,
    );
  }

  return payload as T;
}
