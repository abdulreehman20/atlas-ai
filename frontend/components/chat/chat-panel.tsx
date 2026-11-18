"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { SendHorizonal } from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";
import {
  type FormEvent,
  type KeyboardEvent,
  useEffect,
  useRef,
  useState,
} from "react";
import { MarkdownContent } from "@/components/chat/markdown-content";
import {
  EmptyState,
  ErrorState,
  LoadingBlock,
} from "@/components/shared/state-panel";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Textarea } from "@/components/ui/textarea";

import { ApiError } from "@/lib/client";
import { fetchConversation, sendChatMessage } from "@/lib/endpoints";
import { toastApiError } from "@/lib/toast";

import { cn } from "@/lib/utils";
import type { ChatMessage, Citation } from "@/types/types";

function citationTitle(citation: Citation): string {
  return citation.document_title ?? citation.title ?? "Source";
}

function citationPage(citation: Citation): number | null | undefined {
  return citation.page ?? citation.page_number;
}

function CitationsList({ citations }: { citations: Citation[] }) {
  if (citations.length === 0) return null;
  return (
    <div className="mt-3 space-y-2 border-t border-border pt-3">
      <p className="text-xs font-medium text-muted-foreground">Citations</p>
      <ul className="space-y-2">
        {citations.map((citation, index) => {
          const page = citationPage(citation);
          return (
            <li
              key={`${citation.document_id}-${citation.chunk_id ?? index}`}
              className="rounded-lg bg-muted/50 p-2 text-xs"
            >
              <div className="flex flex-wrap items-center gap-2">
                <span className="font-medium text-foreground">
                  {citationTitle(citation)}
                </span>
                {page != null ? (
                  <Badge variant="outline">p. {page}</Badge>
                ) : null}
              </div>
              {citation.excerpt ? (
                <p className="mt-1 text-muted-foreground">{citation.excerpt}</p>
              ) : null}
            </li>
          );
        })}
      </ul>
    </div>
  );
}

export function ChatPanel() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const queryClient = useQueryClient();
  const selectedId = searchParams.get("conversation");

  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [conversationId, setConversationId] = useState<string | null>(
    selectedId,
  );
  const [draft, setDraft] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);

  const conversation = useQuery({
    queryKey: ["conversation", selectedId],
    queryFn: () => fetchConversation(selectedId as string),
    enabled: Boolean(selectedId),
  });

  useEffect(() => {
    setConversationId(selectedId);
    if (!selectedId) {
      setMessages([]);
    }
  }, [selectedId]);

  useEffect(() => {
    if (conversation.data) {
      setMessages(conversation.data.messages);
      setConversationId(conversation.data.conversation.id);
    }
  }, [conversation.data]);

  // biome-ignore lint/correctness/useExhaustiveDependencies: scroll on transcript changes
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const mutation = useMutation({
    mutationFn: sendChatMessage,
    onSuccess: async (data) => {
      setConversationId(data.conversation_id);
      const answer =
        data.insufficient_evidence && !data.answer
          ? "I could not find enough evidence in your workspace documents to answer that."
          : data.answer;
      const assistant: ChatMessage = {
        id: data.message_id,
        role: "assistant",
        content: answer,
        citations: data.citations ?? [],
        created_at: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, assistant]);
      await queryClient.invalidateQueries({ queryKey: ["conversations"] });
      if (selectedId !== data.conversation_id) {
        router.replace(`/chat?conversation=${data.conversation_id}`);
      }
    },
    onError: (error) => {
      toastApiError(error, "Chat request failed");
    },
  });

  async function sendDraft() {
    const content = draft.trim();
    if (!content || mutation.isPending) return;

    const optimistic: ChatMessage = {
      id: `local-${Date.now()}`,
      role: "user",
      content,
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, optimistic]);
    setDraft("");

    try {
      await mutation.mutateAsync({
        conversation_id: conversationId,
        message: content,
      });
    } catch {
      // Error surface handled via mutation.error below.
    }
  }

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    void sendDraft();
  }

  function onComposerKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      void sendDraft();
    }
  }

  return (
    <div className="flex h-[calc(100dvh-5.5rem)] min-h-112 flex-col gap-4 md:h-[calc(100vh-4rem)]">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="space-y-1">
          <h1 className="text-lg font-semibold tracking-tight">Chat</h1>
          <p className="text-sm text-muted-foreground">
            Ask questions grounded in your workspace documents.
          </p>
        </div>
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={() => {
            setMessages([]);
            setConversationId(null);
            router.push("/chat");
          }}
        >
          New chat
        </Button>
      </div>

      <div className="flex min-h-0 flex-1 flex-col overflow-hidden rounded-xl border border-border">
        <ScrollArea className="min-h-0 flex-1">
          <div className="space-y-4 p-4">
            {selectedId && conversation.isLoading ? (
              <LoadingBlock rows={5} />
            ) : null}
            {selectedId && conversation.isError ? (
              <ErrorState
                title="Could not load conversation"
                message={
                  conversation.error instanceof ApiError
                    ? conversation.error.message
                    : conversation.error instanceof Error
                      ? conversation.error.message
                      : "Request failed"
                }
              />
            ) : null}
            {!conversation.isLoading && messages.length === 0 ? (
              <EmptyState
                title="No messages yet"
                description="Upload documents, then ask a question. Answers include citations when evidence is found."
              />
            ) : null}
            {messages.map((message) => (
              <div
                key={message.id}
                className={cn(
                  "max-w-3xl rounded-xl px-3 py-2 text-sm",
                  message.role === "user"
                    ? "ml-auto bg-primary text-primary-foreground"
                    : "bg-muted text-foreground",
                )}
              >
                {message.role === "assistant" ? (
                  <MarkdownContent content={message.content} />
                ) : (
                  <p className="whitespace-pre-wrap">{message.content}</p>
                )}
                {message.role === "assistant" && message.citations ? (
                  <CitationsList citations={message.citations} />
                ) : null}
              </div>
            ))}
            {mutation.isPending ? (
              <p className="text-sm text-muted-foreground">Thinking…</p>
            ) : null}
            <div ref={bottomRef} />
          </div>
        </ScrollArea>

        <div className="border-t border-border p-3">
          <form className="flex items-end gap-2" onSubmit={onSubmit}>
            <Textarea
              value={draft}
              onChange={(event) => setDraft(event.target.value)}
              placeholder="Ask about your documents…"
              className="min-h-12 flex-1 resize-none"
              rows={2}
              onKeyDown={onComposerKeyDown}
            />
            <Button
              type="submit"
              disabled={mutation.isPending || !draft.trim()}
            >
              <SendHorizonal className="size-4" />
              Send
            </Button>
          </form>
        </div>
      </div>
    </div>
  );
}
