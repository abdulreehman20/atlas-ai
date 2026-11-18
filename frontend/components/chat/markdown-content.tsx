"use client";

import type { Components } from "react-markdown";
import ReactMarkdown from "react-markdown";
import remarkBreaks from "remark-breaks";
import remarkGfm from "remark-gfm";

import { cn } from "@/lib/utils";

const components: Components = {
  h1: ({ children }) => (
    <h1 className="mt-3 mb-2 text-base font-semibold tracking-tight first:mt-0">
      {children}
    </h1>
  ),
  h2: ({ children }) => (
    <h2 className="mt-3 mb-1.5 text-sm font-semibold tracking-tight first:mt-0">
      {children}
    </h2>
  ),
  h3: ({ children }) => (
    <h3 className="mt-2.5 mb-1 text-sm font-semibold first:mt-0">{children}</h3>
  ),
  p: ({ children }) => (
    <p className="my-2 leading-relaxed text-pretty first:mt-0 last:mb-0">
      {children}
    </p>
  ),
  ul: ({ children }) => (
    <ul className="my-2 list-disc space-y-1.5 ps-5 first:mt-0 last:mb-0">
      {children}
    </ul>
  ),
  ol: ({ children }) => (
    <ol className="my-2 list-decimal space-y-1.5 ps-5 first:mt-0 last:mb-0">
      {children}
    </ol>
  ),
  li: ({ children }) => <li className="leading-relaxed">{children}</li>,
  strong: ({ children }) => (
    <strong className="font-semibold text-foreground">{children}</strong>
  ),
  em: ({ children }) => <em className="italic">{children}</em>,
  a: ({ href, children }) => (
    <a
      href={href}
      target="_blank"
      rel="noreferrer noopener"
      className="font-medium text-primary underline underline-offset-2"
    >
      {children}
    </a>
  ),
  blockquote: ({ children }) => (
    <blockquote className="my-2 border-l-2 border-border ps-3 text-muted-foreground italic">
      {children}
    </blockquote>
  ),
  hr: () => <hr className="my-3 border-border" />,
  code: ({ className, children, ...props }) => {
    const isBlock = Boolean(className?.includes("language-"));
    if (isBlock) {
      return (
        <code className={cn("font-mono text-[0.8rem]", className)} {...props}>
          {children}
        </code>
      );
    }
    return (
      <code
        className="rounded-md bg-background/70 px-1 py-0.5 font-mono text-[0.8rem]"
        {...props}
      >
        {children}
      </code>
    );
  },
  pre: ({ children }) => (
    <pre className="my-2 overflow-x-auto rounded-lg border border-border bg-background/70 p-3 font-mono text-[0.8rem] leading-relaxed">
      {children}
    </pre>
  ),
  table: ({ children }) => (
    <div className="my-2 overflow-x-auto">
      <table className="w-full border-collapse text-left text-xs">
        {children}
      </table>
    </div>
  ),
  th: ({ children }) => (
    <th className="border-b border-border px-2 py-1.5 font-semibold">
      {children}
    </th>
  ),
  td: ({ children }) => (
    <td className="border-b border-border/70 px-2 py-1.5 align-top">
      {children}
    </td>
  ),
};

/** Normalize model output so Markdown parsers get real structure. */
export function prepareMarkdown(raw: string): string {
  let text = raw.replace(/\r\n/g, "\n").replace(/\r/g, "\n");
  // Models sometimes emit literal \n sequences.
  text = text.replace(/\\n/g, "\n");
  // Unescape over-escaped emphasis markers.
  text = text.replace(/\\\*/g, "*").replace(/\\_/g, "_");
  // Normalize fancy asterisks to ASCII.
  text = text.replace(/[＊⁎✱✲]/g, "*");
  // Drop inline chunk_id / Sources lines (citations panel shows sources).
  text = text.replace(/\s*\(\s*chunk_id\s*=\s*[^)]+\)/gi, "");
  text = text.replace(/\s*\[\s*chunk_id\s*=\s*[^\]]+\]/gi, "");
  text = text.replace(/^[ \t]*(?:sources?|citations?)\s*:\s*.+$/gim, "");
  text = text.replace(/chunk_id\s*=\s*[0-9a-fA-F-]{8,}(?::\d+)?/gi, "");
  // Promote lone bold lines into headings for clearer hierarchy.
  text = text.replace(/^(?:\s*)\*\*(.+?)\*\*\s*$/gm, "## $1");
  // Ensure list markers start on their own line.
  text = text.replace(/([^\n])\n([-*]\s+)/g, "$1\n\n$2");
  // Collapse 3+ blank lines.
  text = text.replace(/\n{3,}/g, "\n\n");
  return text.trim();
}

export function MarkdownContent({
  content,
  className,
}: {
  content: string;
  className?: string;
}) {
  const markdown = prepareMarkdown(content);

  return (
    <div
      className={cn(
        "markdown-body min-w-0 text-sm leading-relaxed **:first:mt-0 **:last:mb-0",
        className,
      )}
    >
      <ReactMarkdown
        remarkPlugins={[remarkGfm, remarkBreaks]}
        components={components}
      >
        {markdown}
      </ReactMarkdown>
    </div>
  );
}
