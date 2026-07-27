"use client";

import * as React from "react";

import { cn } from "@/lib/utils";
import {
  useChatExtension,
} from "@/features/chat/extension";

export function ChatEmptyState({ onSelect }) {
  const { suggestions } = useChatExtension();
  return (
    <div
      data-slot="empty-state"
      className="mx-auto flex w-full max-w-2xl flex-col items-center gap-6 py-16 text-center"
    >
      <div className="flex flex-col items-center gap-3">
        <span className="rounded-full border border-purple-500/40 bg-purple-500/10 px-3 py-0.5 text-[10px] font-medium uppercase tracking-wider text-purple-300">
          HACK · Compliance Review Agent
        </span>
        <div className="text-xl font-semibold">
          Audit and certify your AI service
        </div>
        <div className="text-muted-foreground max-w-md text-sm leading-relaxed">
          Submit an MCP server, agent, or API endpoint. I&apos;ll run the Hedera
          Agent Commerce Kit compliance pipeline against it, handle the x402
          payment inline, and return a signed report — with optional PDF,
          SKILL.md, and soulbound NFT certificate.
        </div>
      </div>
      <div className="grid w-full grid-cols-1 gap-2 sm:grid-cols-2">
        {suggestions.map((chip) => (
          <SuggestionButton key={chip.id} chip={chip} onSelect={onSelect} />
        ))}
      </div>
    </div>
  );
}

function SuggestionButton({
  chip,
  onSelect,
}) {
  return (
    <button
      type="button"
      onClick={() => onSelect(chip.prompt)}
      className={cn(
        "border-input bg-background hover:bg-accent hover:text-accent-foreground focus-visible:ring-ring/50",
        "flex flex-col items-start gap-1 rounded-lg border px-3 py-2 text-left text-sm transition-colors",
        "outline-none focus-visible:ring-[3px]",
      )}
    >
      <div className="flex w-full items-center justify-between gap-2">
        <span className="font-medium">{chip.label}</span>
        {chip.mutating ? (
          <span className="bg-muted text-muted-foreground rounded-full px-2 py-0.5 text-[10px] font-medium uppercase tracking-wide">
            Paid
          </span>
        ) : null}
      </div>
      <span className="text-muted-foreground line-clamp-2 text-xs">
        {chip.prompt}
      </span>
    </button>
  );
}
