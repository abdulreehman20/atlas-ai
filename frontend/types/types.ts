export type WorkspaceRole = "owner" | "member";

export type PlanLimits = {
  members: number;
  documents: number;
  max_file_mib: number;
  storage_mib: number;
  chats_monthly: number;
  custom_prompt: boolean;
};

export type MeResponse = {
  user_id: string;
  email: string | null;
  role: WorkspaceRole;
  organization: { id: string; name: string } | null;
  workspace: {
    id: string;
    name: string;
    system_prompt_override?: string | null;
  } | null;
  member_count: number;
  plan: string;
  limits: PlanLimits;
};

export type DocumentStatus =
  | "upload_pending"
  | "uploaded"
  | "queued"
  | "uploading"
  | "processing"
  | "ready"
  | "failed"
  | "deleting"
  | "deleted";

export type DocumentItem = {
  id: string;
  title: string;
  filename: string;
  status: DocumentStatus;
  size_bytes: number;
  owner_user_id: string;
  created_at: string;
  error_message?: string | null;
};

export type DocumentCreateResponse = {
  id: string;
  storage_path: string;
  bucket: string;
  status: DocumentStatus | string;
};

export type UploadCompleteResponse = {
  document_id: string;
  job_id: string;
  status: DocumentStatus | string;
};

export type DeleteDocumentResponse = {
  id: string;
  status: string;
};

export type Paginated<T> = {
  items: T[];
};

export type Citation = {
  document_id: string;
  document_title?: string;
  title?: string;
  chunk_id?: string;
  page?: number | null;
  page_number?: number | null;
  section?: string | null;
  excerpt?: string | null;
};

export type ChatMessage = {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  citations?: Citation[];
  created_at: string;
};

export type Conversation = {
  id: string;
  title: string | null;
  created_at: string;
  updated_at: string;
};

export type ConversationDetail = {
  conversation: Conversation;
  messages: ChatMessage[];
};

export type ChatResponse = {
  conversation_id: string;
  message_id: string;
  answer: string;
  citations: Citation[];
  insufficient_evidence: boolean;
  prompt_version: string;
};

export type MemberItem = {
  id: string;
  user_id: string;
  email: string;
  role: WorkspaceRole;
  status: "active" | "invited" | "removed" | string;
  created_at?: string;
};

export type SubscriptionStatus = {
  status: string;
  plan_tier: string;
  stripe_price_id: string | null;
  cancel_at_period_end: boolean;
};

export type WorkspaceSettings = {
  organization_id: string;
  workspace_id: string;
  system_prompt_override: string | null;
};

export type CheckoutResponse = {
  checkout_url: string;
  id: string;
};

export type PortalResponse = {
  portal_url: string;
};

export type ApprovalStatus =
  | "pending"
  | "approved"
  | "edited"
  | "rejected"
  | "expired"
  | "executing"
  | "executed";

export type ApprovalItem = {
  id: string;
  action?: string;
  action_type?: string;
  tool_name?: string;
  summary: string;
  status: ApprovalStatus | string;
  requester_email?: string | null;
  requester_user_id?: string | null;
  created_at: string;
};
