"use client";
/**
 * SkillExport
 * -----------
 * Collapsible panel that shows the generated SKILL.md for the certified service.
 *
 * The SKILL.md file lets an AI coding agent ingest the service's payment strategy,
 * retry logic, timeout rules, and supported endpoints without reading documentation.
 *
 * Exports:
 *   - Copy to clipboard
 *   - Download as .SKILL.md
 */

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ChevronDown, Download, FileText } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { CodeBlock } from "@/components/ui/CodeBlock";
import { cn } from "@/lib/utils";

interface Props {
  skillMd: string;
  serviceName: string;
  delay?: number;
}

export function SkillExport({ skillMd, serviceName, delay = 0 }: Props) {
  const [open, setOpen] = useState(false);

  function download() {
    const blob = new Blob([skillMd], { type: "text/markdown" });
    const url  = URL.createObjectURL(blob);
    const a    = document.createElement("a");
    a.href     = url;
    a.download = `${serviceName.replace(/\s+/g, "-")}.SKILL.md`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay }}
      className="mt-10"
    >
      {/* Section header — always visible */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <h2 className="text-xl font-semibold tracking-tight">AI Skill File</h2>
          <p className="text-xs text-text-muted mt-1">
            A machine-readable profile your AI agent can ingest instead of reading docs.
          </p>
        </div>
        <Button size="sm" variant="ghost" onClick={download}>
          <Download className="h-3.5 w-3.5" />
          Download SKILL.md
        </Button>
      </div>

      {/* Collapsible preview */}
      <div className="rounded-lg border border-border bg-surface-1 overflow-hidden">
        <button
          onClick={() => setOpen((o) => !o)}
          className="w-full flex items-center justify-between px-5 py-4 hover:bg-surface-2 transition-colors"
        >
          <div className="flex items-center gap-3">
            <FileText className="h-4 w-4 text-purple" />
            <span className="font-mono text-sm text-text-primary">
              {serviceName.replace(/\s+/g, "-")}.SKILL.md
            </span>
            <span className="text-xs text-text-muted">
              {skillMd.split("\n").length} lines
            </span>
          </div>
          <ChevronDown
            className={cn(
              "h-4 w-4 text-text-muted transition-transform duration-200",
              open && "rotate-180",
            )}
          />
        </button>

        <AnimatePresence>
          {open && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: "auto", opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={{ duration: 0.25 }}
              className="overflow-hidden border-t border-border"
            >
              <CodeBlock
                code={skillMd}
                language="markdown"
                filename={`${serviceName}.SKILL.md`}
                showLineNumbers
              />
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* What this is */}
      <div className="mt-4 rounded-md border border-border-subtle bg-surface-2 px-4 py-3 text-xs text-text-secondary">
        <strong className="text-text-primary">How to use:</strong> Place this file in your AI
        agent&apos;s context or skills directory. The agent will use it to understand payment
        retry logic, supported endpoints, and x402 configuration without additional documentation.
      </div>
    </motion.div>
  );
}
