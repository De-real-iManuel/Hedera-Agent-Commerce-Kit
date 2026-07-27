"use client";
import { useState } from "react";
import { Card } from "@/components/ui/card";

export function SkillMdCard({ output }) {
  const raw = output?.raw;
  if (!raw || raw.status !== "SKILL_MD_READY") return null;
  const content = raw.content || "";
  const [copied, setCopied] = useState(false);

  const onCopy = async () => {
    try {
      await navigator.clipboard.writeText(content);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {}
  };

  const onDownload = () => {
    const blob = new Blob([content], { type: "text/markdown;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = raw.filename || "SKILL.md";
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  };

  return (
    <Card className="border-neutral-800 bg-neutral-950">
      <div className="flex items-center justify-between border-b border-neutral-900 px-4 py-2">
        <div>
          <div className="text-xs uppercase tracking-wide text-neutral-500">Integration guide</div>
          <div className="font-mono text-sm text-neutral-100">{raw.filename || "SKILL.md"}</div>
        </div>
        <div className="flex gap-2">
          <button
            onClick={onCopy}
            className="rounded-md border border-neutral-800 bg-neutral-900 px-2 py-1 text-[11px] text-neutral-200 hover:border-neutral-700"
          >
            {copied ? "Copied" : "Copy"}
          </button>
          <button
            onClick={onDownload}
            className="rounded-md border border-purple-500/40 bg-purple-500/10 px-2 py-1 text-[11px] text-purple-200 hover:bg-purple-500/20"
          >
            Download
          </button>
        </div>
      </div>
      <pre className="max-h-72 overflow-auto p-4 font-mono text-[11px] leading-relaxed text-neutral-300">
        {content}
      </pre>
    </Card>
  );
}

export function SkillMdRow({ output }) {
  return <span className="text-neutral-300">SKILL.md ready · {output?.raw?.report_id}</span>;
}
