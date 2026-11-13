import type {
  ApprovalItem,
  ChatResponse,
  CheckoutResponse,
  Conversation,
  ConversationDetail,
  DeleteDocumentResponse,
  DocumentCreateResponse,
  DocumentItem,
  MeResponse,
  MemberItem,
  Paginated,
  PortalResponse,
  SubscriptionStatus,
  UploadCompleteResponse,
  WorkspaceSettings,
} from "@/types/types";
import { apiFetch } from "@/lib/client";

export function fetchMe() {
  return apiFetch<MeResponse>("/me");
}

export function fetchDocuments() {
  return apiFetch<Paginated<DocumentItem>>("/documents");
}

export function createDocument(input: {
  filename: string;
  size_bytes: number;
  mime_type?: string;
  title?: string;
}) {
  return apiFetch<DocumentCreateResponse>("/documents", {
    method: "POST",
    body: input,
  });
}

/** @deprecated Prefer createDocument */
export function createDocumentReservation(input: {
  filename: string;
  content_type?: string;
  mime_type?: string;
  size_bytes: number;
  title?: string;
}) {
  return createDocument({
    filename: input.filename,
    size_bytes: input.size_bytes,
    mime_type: input.mime_type ?? input.content_type,
    title: input.title,
  });
}

export function completeDocumentUpload(
  documentId: string,
  storagePath: string,
) {
  return apiFetch<UploadCompleteResponse>(
    `/documents/${documentId}/upload-complete`,
    {
      method: "POST",
      body: { storage_path: storagePath },
    },
  );
}

export function deleteDocument(documentId: string) {
  return apiFetch<DeleteDocumentResponse>(`/documents/${documentId}`, {
    method: "DELETE",
  });
}

export function fetchConversations() {
  return apiFetch<Paginated<Conversation>>("/conversations");
}

export function fetchConversation(conversationId: string) {
  return apiFetch<ConversationDetail>(`/conversations/${conversationId}`);
}

export function sendChatMessage(input: {
  conversation_id?: string | null;
  message: string;
}) {
  return apiFetch<ChatResponse>("/chat", {
    method: "POST",
    body: {
      message: input.message,
      conversation_id: input.conversation_id ?? undefined,
    },
  });
}

export function fetchWorkspaceSettings() {
  return apiFetch<WorkspaceSettings>("/workspaces/current");
}

export function updateWorkspaceSettings(input: {
  system_prompt_override: string | null;
}) {
  return apiFetch<WorkspaceSettings>("/workspaces/current/system-prompt", {
    method: "PUT",
    body: input,
  });
}

export function fetchMembers() {
  return apiFetch<Paginated<MemberItem>>("/workspaces/current/members");
}

export function inviteMember(email: string) {
  return apiFetch<MemberItem>("/workspaces/current/members", {
    method: "POST",
    body: { email },
  });
}

export function removeMember(membershipId: string) {
  return apiFetch<{ id: string; status: string }>(
    `/workspaces/current/members/${membershipId}`,
    { method: "DELETE" },
  );
}

export function fetchSubscription() {
  return apiFetch<SubscriptionStatus>("/billing/subscription");
}

export function createCheckoutSession() {
  return apiFetch<CheckoutResponse>("/billing/checkout", { method: "POST" });
}

export function createBillingPortalSession() {
  return apiFetch<PortalResponse>("/billing/portal", { method: "POST" });
}

export async function fetchApprovals() {
  const payload = await apiFetch<ApprovalItem[] | Paginated<ApprovalItem>>(
    "/approvals",
  );
  if (Array.isArray(payload)) return payload;
  return payload.items ?? [];
}
