"use client";
import { useEffect, useState } from "react";
import { cn } from "@/lib/utils";

interface TerminalProps {
  lines: string[];
  typingSpeed?: number;
  loop?: boolean;
  title?: string;
  className?: string;
}

export function Terminal({
  lines,
  typingSpeed = 12,
  loop = true,
  title = "hack-demo — zsh",
  className,
}: TerminalProps) {
  const [rendered, setRendered] = useState<string[]>([]);
  const [currentLine, setCurrentLine] = useState("");
  const [lineIdx, setLineIdx] = useState(0);
  const [charIdx, setCharIdx] = useState(0);
  const [done, setDone] = useState(false);

  useEffect(() => {
    if (done) {
      if (!loop) return;
      const t = setTimeout(() => {
        setRendered([]);
        setCurrentLine("");
        setLineIdx(0);
        setCharIdx(0);
        setDone(false);
      }, 3000);
      return () => clearTimeout(t);
    }
    if (lineIdx >= lines.length) {
      setDone(true);
      return;
    }
    const currentTarget = lines[lineIdx];
    if (charIdx < currentTarget.length) {
      const t = setTimeout(() => {
        setCurrentLine(currentTarget.slice(0, charIdx + 1));
        setCharIdx(charIdx + 1);
      }, typingSpeed);
      return () => clearTimeout(t);
    } else {
      const t = setTimeout(() => {
        setRendered((prev) => [...prev, currentTarget]);
        setCurrentLine("");
        setCharIdx(0);
        setLineIdx((i) => i + 1);
      }, 120);
      return () => clearTimeout(t);
    }
  }, [charIdx, lineIdx, lines, typingSpeed, done, loop]);

  return (
    <div
      className={cn(
        "rounded-lg border border-border bg-surface-1 shadow-2xl overflow-hidden",
        "font-mono text-sm",
        className,
      )}
    >
      <div className="flex items-center gap-2 border-b border-border bg-surface-2 px-4 py-2.5">
        <span className="h-3 w-3 rounded-full bg-red" />
        <span className="h-3 w-3 rounded-full bg-amber" />
        <span className="h-3 w-3 rounded-full bg-green" />
        <span className="ml-2 text-xs text-text-muted">{title}</span>
      </div>
      <div className="p-4 min-h-[340px] leading-relaxed">
        {rendered.map((l, i) => (
          <div key={i} className={colorize(l)}>
            {l || "\u00A0"}
          </div>
        ))}
        {!done && (
          <div className={cn(colorize(currentLine), "terminal-cursor inline")}>{currentLine}</div>
        )}
      </div>
    </div>
  );
}

function colorize(line: string): string {
  if (line.startsWith("$")) return "text-purple";
  if (line.includes("402")) return "text-amber";
  if (line.includes("200 OK") || line.includes("✓")) return "text-green";
  if (line.startsWith(">")) return "text-cyan";
  if (line.startsWith("#")) return "text-text-muted";
  return "text-text-primary";
}
