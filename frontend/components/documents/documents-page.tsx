"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { EllipsisVertical, Eye, RefreshCw, Trash2 } from "lucide-react";
import { type ChangeEvent, useRef, useState } from "react";
import {
  EmptyState,
  ErrorState,
  LoadingBlock,
} from "@/components/shared/state-panel";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Input } from "@/components/ui/input";
import {
  Progress,
  ProgressLabel,
  ProgressValue,
} from "@/components/ui/progress";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useMe } from "@/hooks/use-me";
import { ApiError } from "@/lib/client";
import { toastApiError } from "@/lib/toast";
import {
  completeDocumentUpload,
  createDocument,
  deleteDocument,
  fetchDocuments,
  fetchDocumentViewUrl,
  reprocessDocument,
} from "@/lib/endpoints";
import { createClient } from "@/lib/supabase/client";
import type { DocumentItem, DocumentStatus } from "@/types/types";

const ALLOWED_EXTENSIONS = [".pdf", ".txt", ".md", ".docx", ".html", ".htm"];

function statusVariant(
  status: DocumentStatus,
): "default" | "secondary" | "outline" | "destructive" {
  switch (status) {
    case "ready":
      return "default";
    case "failed":
      return "destructive";
    case "processing":
    case "queued":
    case "uploading":
    case "upload_pending":
    case "uploaded":
      return "secondary";
    case "deleting":
    case "deleted":
      return "outline";
    default: {
      const _exhaustive: never = status;
      return _exhaustive;
    }
  }
}

function formatBytes(size: number): string {
  if (size < 1024) return `${size} B`;
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`;
  return `${(size / (1024 * 1024)).toFixed(1)} MB`;
}

function canProcess(status: DocumentStatus): boolean {
  return ["upload_pending", "uploaded", "queued", "failed", "ready"].includes(
    status,
  );
}

function statusProgress(status: DocumentStatus): number {
  switch (status) {
    case "upload_pending":
      return 10;
    case "uploading":
      return 30;
    case "uploaded":
      return 45;
    case "queued":
      return 60;
    case "processing":
      return 80;
    case "ready":
      return 100;
    case "failed":
      return 100;
    case "deleting":
      return 90;
    case "deleted":
      return 100;
    default: {
      const _exhaustive: never = status;
      return _exhaustive;
    }
  }
}

function isInFlight(status: DocumentStatus): boolean {
  return [
    "upload_pending",
    "uploading",
    "uploaded",
    "queued",
    "processing",
    "deleting",
  ].includes(status);
}

export function DocumentsPage() {
  const queryClient = useQueryClient();
  const me = useMe();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [pendingDeleteId, setPendingDeleteId] = useState<string | null>(null);
  const [localProgress, setLocalProgress] = useState<number | null>(null);

  const documents = useQuery({
    queryKey: ["documents"],
    queryFn: async () => {
      const page = await fetchDocuments();
      return page.items;
    },
    refetchInterval: (query) => {
      const rows = query.state.data ?? [];
      return rows.some((doc) => isInFlight(doc.status)) ? 2500 : false;
    },
  });

  const uploadMutation = useMutation({
    mutationFn: async (file: File) => {
      setLocalProgress(8);
      const reservation = await createDocument({
        filename: file.name,
        mime_type: file.type || "application/octet-stream",
        size_bytes: file.size,
      });
      setLocalProgress(20);

      const storagePath = reservation.storage_path;
      const bucket = reservation.bucket || "atlas-private-documents";
      const supabase = createClient();

      if (reservation.upload_token) {
        const { error: signedErr } = await supabase.storage
          .from(bucket)
          .uploadToSignedUrl(storagePath, reservation.upload_token, file, {
            contentType: file.type || "application/octet-stream",
            upsert: true,
          });
        if (signedErr) throw new Error(signedErr.message);
      } else {
        const { error: uploadErr } = await supabase.storage
          .from(bucket)
          .upload(storagePath, file, {
            contentType: file.type || "application/octet-stream",
            upsert: true,
          });
        if (uploadErr) throw new Error(uploadErr.message);
      }

      setLocalProgress(50);
      const completed = await completeDocumentUpload(
        reservation.id,
        storagePath,
      );
      setLocalProgress(65);
      return completed;
    },
    onSuccess: async () => {
      setLocalProgress(null);
      await queryClient.invalidateQueries({ queryKey: ["documents"] });
      if (fileInputRef.current) fileInputRef.current.value = "";
    },
    onError: (error) => {
      setLocalProgress(null);
      toastApiError(error, "Upload failed");
    },
  });

  const processMutation = useMutation({
    mutationFn: async (doc: DocumentItem) => {
      if (
        doc.status === "upload_pending" ||
        doc.status === "uploaded" ||
        doc.status === "queued"
      ) {
        if (!doc.storage_path) {
          throw new Error("Document has no storage path to process");
        }
        return completeDocumentUpload(doc.id, doc.storage_path);
      }
      return reprocessDocument(doc.id);
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["documents"] });
    },
    onError: (error) => {
      toastApiError(error, "Could not process document");
    },
  });

  const viewMutation = useMutation({
    mutationFn: fetchDocumentViewUrl,
    onSuccess: (data) => {
      window.open(data.url, "_blank", "noopener,noreferrer");
    },
    onError: (error) => {
      toastApiError(error, "Could not open document");
    },
  });

  const deleteMutation = useMutation({
    mutationFn: deleteDocument,
    onSuccess: async () => {
      setPendingDeleteId(null);
      await queryClient.invalidateQueries({ queryKey: ["documents"] });
    },
    onError: (error) => {
      toastApiError(error, "Could not delete document");
    },
  });

  function onFileChange(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;
    const lower = file.name.toLowerCase();
    if (!ALLOWED_EXTENSIONS.some((ext) => lower.endsWith(ext))) {
      toastApiError(
        new Error("Supported formats: PDF, TXT, MD, DOCX, HTML."),
        "Unsupported file type",
      );
      return;
    }
    uploadMutation.mutate(file);
  }

  const currentUserId = me.data?.user_id;
  const isOwner = me.data?.role === "owner";
  const pendingDelete = documents.data?.find(
    (doc) => doc.id === pendingDeleteId,
  );

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:flex-wrap sm:items-end sm:justify-between">
        <div className="space-y-1">
          <h1 className="text-lg font-semibold tracking-tight">Documents</h1>
          <p className="text-sm text-muted-foreground">
            Upload workspace knowledge. Processing embeds chunks into Pinecone
            and marks documents Ready when finished.
          </p>
        </div>
        <div className="flex w-full flex-col gap-2 sm:w-auto sm:flex-row sm:items-center">
          <Input
            ref={fileInputRef}
            type="file"
            accept=".pdf,.txt,.md,.docx,.html,.htm"
            className="w-full sm:max-w-xs"
            onChange={onFileChange}
            disabled={uploadMutation.isPending}
          />
          <Button
            type="button"
            variant="outline"
            className="w-full sm:w-auto"
            disabled={uploadMutation.isPending}
            onClick={() => fileInputRef.current?.click()}
          >
            {uploadMutation.isPending ? "Uploading…" : "Upload"}
          </Button>
        </div>
      </div>

      {uploadMutation.isPending && localProgress != null ? (
        <Progress value={localProgress} className="max-w-xl">
          <ProgressLabel>Uploading & queuing ingestion</ProgressLabel>
          <ProgressValue />
        </Progress>
      ) : null}

      {documents.isLoading ? <LoadingBlock rows={5} /> : null}
      {documents.isError ? (
        <ErrorState
          title="Could not load documents"
          message={
            documents.error instanceof ApiError
              ? documents.error.message
              : documents.error instanceof Error
                ? documents.error.message
                : "Request failed"
          }
        />
      ) : null}

      {documents.data && documents.data.length === 0 ? (
        <EmptyState
          title="No documents yet"
          description="Upload a PDF, TXT, MD, DOCX, or HTML file to start grounding chat answers."
        />
      ) : null}

      {documents.data && documents.data.length > 0 ? (
        <div className="overflow-x-auto rounded-xl border border-border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>Status</TableHead>
                <TableHead className="hidden md:table-cell">Size</TableHead>
                <TableHead className="hidden lg:table-cell">Uploaded</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {documents.data.map((doc) => {
                const canDelete =
                  isOwner ||
                  (currentUserId != null &&
                    doc.owner_user_id === currentUserId);
                const progress = statusProgress(doc.status);
                return (
                  <TableRow key={doc.id}>
                    <TableCell>
                      <div className="space-y-1">
                        <p className="font-medium">
                          {doc.title || doc.filename}
                        </p>
                        <p className="text-xs text-muted-foreground">
                          {doc.filename}
                        </p>
                        {doc.error_message ? (
                          <p className="text-xs text-destructive">
                            {doc.error_message}
                          </p>
                        ) : null}
                      </div>
                    </TableCell>
                    <TableCell className="min-w-40">
                      <div className="space-y-2">
                        <Badge
                          variant={statusVariant(doc.status)}
                          className="capitalize"
                        >
                          {doc.status}
                        </Badge>
                        {isInFlight(doc.status) || doc.status === "failed" ? (
                          <Progress value={progress}>
                            <ProgressValue />
                          </Progress>
                        ) : doc.status === "ready" ? (
                          <p className="text-xs text-muted-foreground">
                            100% ready
                          </p>
                        ) : null}
                      </div>
                    </TableCell>
                    <TableCell className="hidden md:table-cell">
                      {formatBytes(doc.size_bytes)}
                    </TableCell>
                    <TableCell className="hidden lg:table-cell">
                      {new Date(doc.created_at).toLocaleString()}
                    </TableCell>
                    <TableCell className="text-right">
                      <DropdownMenu>
                        <DropdownMenuTrigger
                          render={<Button variant="ghost" size="icon-sm" />}
                        >
                          <EllipsisVertical className="size-4" />
                          <span className="sr-only">Open document menu</span>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                          <DropdownMenuItem
                            disabled={
                              !canProcess(doc.status) ||
                              processMutation.isPending
                            }
                            onClick={() => processMutation.mutate(doc)}
                          >
                            <RefreshCw className="size-4" />
                            Process Document
                          </DropdownMenuItem>
                          <DropdownMenuItem
                            disabled={
                              !doc.storage_path || viewMutation.isPending
                            }
                            onClick={() => viewMutation.mutate(doc.id)}
                          >
                            <Eye className="size-4" />
                            View Document
                          </DropdownMenuItem>
                          {canDelete ? (
                            <DropdownMenuItem
                              variant="destructive"
                              onClick={() => setPendingDeleteId(doc.id)}
                            >
                              <Trash2 className="size-4" />
                              Delete Document
                            </DropdownMenuItem>
                          ) : null}
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </div>
      ) : null}

      <AlertDialog
        open={pendingDeleteId != null}
        onOpenChange={(open) => {
          if (!open) setPendingDeleteId(null);
        }}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete document?</AlertDialogTitle>
            <AlertDialogDescription>
              {pendingDelete
                ? `Remove “${pendingDelete.title || pendingDelete.filename}” from the workspace library and queue vector cleanup.`
                : "This removes the file from the workspace library and queues vector cleanup."}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              variant="destructive"
              disabled={!pendingDeleteId || deleteMutation.isPending}
              onClick={() => {
                if (pendingDeleteId) deleteMutation.mutate(pendingDeleteId);
              }}
            >
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
