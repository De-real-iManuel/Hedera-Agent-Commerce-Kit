"use client";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { vscDarkPlus } from "react-syntax-highlighter/dist/esm/styles/prism";
import { CopyButton } from "./CopyButton";
import { cn } from "@/lib/utils";

interface CodeBlockProps {
  code: string;
  language: string;
  filename?: string;
  showLineNumbers?: boolean;
  className?: string;
}

export function CodeBlock({ code, language, filename, showLineNumbers, className }: CodeBlockProps) {
  return (
    <div className={cn("rounded-lg border border-border bg-surface-1 overflow-hidden", className)}>
      <div className="flex items-center justify-between border-b border-border bg-surface-2 px-3 py-2">
        <div className="flex items-center gap-2 text-xs">
          {filename ? (
            <span className="font-mono text-text-secondary">{filename}</span>
          ) : (
            <span className="rounded-full border border-border px-2 py-0.5 font-mono text-[10px] uppercase tracking-wider text-text-muted">
              {language}
            </span>
          )}
        </div>
        <CopyButton value={code} />
      </div>
      <SyntaxHighlighter
        language={language}
        style={vscDarkPlus}
        showLineNumbers={showLineNumbers}
        customStyle={{
          margin: 0,
          padding: "16px",
          background: "transparent",
          fontSize: "13px",
          lineHeight: "1.65",
        }}
        codeTagProps={{ style: { fontFamily: "var(--font-jetbrains), ui-monospace, monospace" } }}
      >
        {code}
      </SyntaxHighlighter>
    </div>
  );
}
