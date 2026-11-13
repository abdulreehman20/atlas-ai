"use client";

import { useRef, useState, type ChangeEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  EmptyState,
  ErrorState,
  LoadingBlock,
} from "@/components/shared/state-panel";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

import {
  completeDocumentUpload,
  createDocument,
  deleteDocument,
  fetchDocuments,
} from "@/lib/endpoints";
import { useMe } from "@/hooks/use-me";
import { ApiError } from "@/lib/client";
import type { DocumentStatus } from "@/types/types";
import { createClient } from "@/lib/supabase/client";

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

export function DocumentsPage() {
  const queryClient = useQueryClient();
  const me = useMe();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [pendingDeleteId, setPendingDeleteId] = useState<string | null>(null);

  const documents = useQuery({
    queryKey: ["documents"],
    queryFn: async () => {
      const page = await fetchDocuments();
      return page.items;
    },
    refetchInterval: (query) => {
      const rows = query.state.data ?? [];
      return rows.some((doc) =>
        [
          "queued",
          "uploading",
          "upload_pending",
          "uploaded",
          "processing",
          "deleting",
        ].includes(doc.status),
      )
        ? 4000
        : false;
    },
  });

  const uploadMutation = useMutation({
    mutationFn: async (file: File) => {
      const reservation = await createDocument({
        filename: file.name,
        mime_type: file.type || "application/octet-stream",
        size_bytes: file.size,
      });

      const storagePath = reservation.storage_path;
      const bucket = reservation.bucket || "atlas-private-documents";

      const supabase = createClient();
      const { error: uploadErr } = await supabase.storage
        .from(bucket)
        .upload(storagePath, file, {
          contentType: file.type || "application/octet-stream",
          upsert: false,
        });
      if (uploadErr) {
        throw new Error(uploadErr.message);
      }

      return completeDocumentUpload(reservation.id, storagePath);
    },
    onSuccess: async () => {
      setUploadError(null);
      await queryClient.invalidateQueries({ queryKey: ["documents"] });
      if (fileInputRef.current) fileInputRef.current.value = "";
    },
    onError: (error) => {
      setUploadError(error instanceof Error ? error.message : "Upload failed");
    },
  });

  const deleteMutation = useMutation({
    mutationFn: deleteDocument,
    onSuccess: async () => {
      setPendingDeleteId(null);
      await queryClient.invalidateQueries({ queryKey: ["documents"] });
    },
  });

  function onFileChange(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;
    const lower = file.name.toLowerCase();
    if (!ALLOWED_EXTENSIONS.some((ext) => lower.endsWith(ext))) {
      setUploadError("Supported formats: PDF, TXT, MD, DOCX, HTML.");
      return;
    }
    uploadMutation.mutate(file);
  }

  const currentUserId = me.data?.user_id;
  const isOwner = me.data?.role === "owner";

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div className="space-y-1">
          <h1 className="text-lg font-semibold tracking-tight">Documents</h1>
          <p className="text-sm text-muted-foreground">
            Upload workspace knowledge. Members can delete their own uploads;
            owners can delete any document.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Input
            ref={fileInputRef}
            type="file"
            accept=".pdf,.txt,.md,.docx,.html,.htm"
            className="max-w-xs"
            onChange={onFileChange}
            disabled={uploadMutation.isPending}
          />
          <Button
            type="button"
            variant="outline"
            disabled={uploadMutation.isPending}
            onClick={() => fileInputRef.current?.click()}
          >
            {uploadMutation.isPending ? "Uploading…" : "Upload"}
          </Button>
        </div>
      </div>

      {uploadError ? (
        <ErrorState title="Upload failed" message={uploadError} />
      ) : null}
      {deleteMutation.isError ? (
        <ErrorState
          title="Delete failed"
          message={
            deleteMutation.error instanceof Error
              ? deleteMutation.error.message
              : "Could not delete document"
          }
        />
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
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Name</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Size</TableHead>
              <TableHead>Uploaded</TableHead>
              <TableHead className="text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {documents.data.map((doc) => {
              const canDelete =
                isOwner ||
                (currentUserId != null && doc.owner_user_id === currentUserId);
              return (
                <TableRow key={doc.id}>
                  <TableCell>
                    <div className="space-y-1">
                      <p className="font-medium">{doc.title || doc.filename}</p>
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
                  <TableCell>
                    <Badge
                      variant={statusVariant(doc.status)}
                      className="capitalize"
                    >
                      {doc.status}
                    </Badge>
                  </TableCell>
                  <TableCell>{formatBytes(doc.size_bytes)}</TableCell>
                  <TableCell>
                    {new Date(doc.created_at).toLocaleString()}
                  </TableCell>
                  <TableCell className="text-right">
                    {canDelete ? (
                      <AlertDialog
                        open={pendingDeleteId === doc.id}
                        onOpenChange={(open) =>
                          setPendingDeleteId(open ? doc.id : null)
                        }
                      >
                        <AlertDialogTrigger
                          render={<Button variant="ghost" size="sm" />}
                        >
                          Delete
                        </AlertDialogTrigger>
                        <AlertDialogContent>
                          <AlertDialogHeader>
                            <AlertDialogTitle>
                              Delete document?
                            </AlertDialogTitle>
                            <AlertDialogDescription>
                              This removes the file from the workspace library
                              and queues vector cleanup. This cannot be undone
                              from the UI.
                            </AlertDialogDescription>
                          </AlertDialogHeader>
                          <AlertDialogFooter>
                            <AlertDialogCancel>Cancel</AlertDialogCancel>
                            <AlertDialogAction
                              variant="destructive"
                              onClick={() => deleteMutation.mutate(doc.id)}
                            >
                              Delete
                            </AlertDialogAction>
                          </AlertDialogFooter>
                        </AlertDialogContent>
                      </AlertDialog>
                    ) : (
                      <span className="text-xs text-muted-foreground">—</span>
                    )}
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      ) : null}
    </div>
  );
}
