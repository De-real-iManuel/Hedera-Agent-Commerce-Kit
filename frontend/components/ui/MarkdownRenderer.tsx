"use client";
import { CodeBlock } from "@/components/ui/CodeBlock";
import { Wrench } from "lucide-react";
import { Fragment } from "react";

/**
 * Minimal markdown renderer — supports:
 * - # / ## / ### headings
 * - fenced code blocks with language
 * - bullet lists (- ...)
 * - inline code and bold via basic replace
 * - tables (pipe rows)
 * - paragraphs
 */
export function MarkdownRenderer({ content }: { content: string }) {
  const blocks = parse(content);
  return (
    <div className="prose-hack max-w-none">
      {blocks.map((b, i) => renderBlock(b, i))}
    </div>
  );
}

type Block =
  | { kind: "heading"; level: 1 | 2 | 3; text: string }
  | { kind: "code"; language: string; code: string }
  | { kind: "list"; items: string[] }
  | { kind: "table"; header: string[]; rows: string[][] }
  | { kind: "p"; text: string };

function parse(md: string): Block[] {
  const lines = md.replace(/\r\n/g, "\n").split("\n");
  const blocks: Block[] = [];
  let i = 0;
  while (i < lines.length) {
    const line = lines[i];
    if (!line.trim()) { i++; continue; }

    if (line.startsWith("```")) {
      const lang = line.slice(3).trim();
      const buf: string[] = [];
      i++;
      while (i < lines.length && !lines[i].startsWith("```")) {
        buf.push(lines[i]); i++;
      }
      i++;
      blocks.push({ kind: "code", language: lang || "text", code: buf.join("\n") });
      continue;
    }

    if (line.startsWith("### ")) { blocks.push({ kind: "heading", level: 3, text: line.slice(4) }); i++; continue; }
    if (line.startsWith("## "))  { blocks.push({ kind: "heading", level: 2, text: line.slice(3) }); i++; continue; }
    if (line.startsWith("# "))   { blocks.push({ kind: "heading", level: 1, text: line.slice(2) }); i++; continue; }

    if (line.startsWith("- ")) {
      const items: string[] = [];
      while (i < lines.length && lines[i].startsWith("- ")) {
        items.push(lines[i].slice(2)); i++;
      }
      blocks.push({ kind: "list", items });
      continue;
    }

    if (line.startsWith("|") && lines[i + 1]?.match(/^\|[\s\-|]+\|$/)) {
      const header = splitRow(line);
      i += 2;
      const rows: string[][] = [];
      while (i < lines.length && lines[i].startsWith("|")) {
        rows.push(splitRow(lines[i])); i++;
      }
      blocks.push({ kind: "table", header, rows });
      continue;
    }

    const buf: string[] = [line];
    i++;
    while (i < lines.length && lines[i].trim() && !isBlockStart(lines[i])) {
      buf.push(lines[i]); i++;
    }
    blocks.push({ kind: "p", text: buf.join(" ") });
  }
  return blocks;
}

function splitRow(l: string): string[] {
  return l.slice(1, -1).split("|").map((c) => c.trim());
}
function isBlockStart(l: string): boolean {
  return /^(#|- |\|| {0,3}```)/.test(l);
}

function renderInline(text: string): React.ReactNode {
  const parts = text.split(/(`[^`]+`|\*\*[^*]+\*\*|\[[^\]]+\]\([^)]+\))/g);
  return parts.map((p, i) => {
    if (!p) return null;
    if (p.startsWith("`") && p.endsWith("`")) return <code key={i}>{p.slice(1, -1)}</code>;
    if (p.startsWith("**") && p.endsWith("**")) return <strong key={i} className="text-text-primary">{p.slice(2, -2)}</strong>;
    const m = p.match(/^\[([^\]]+)\]\(([^)]+)\)$/);
    if (m) return <a key={i} href={m[2]} target={m[2].startsWith("http") ? "_blank" : undefined} rel="noreferrer">{m[1]}</a>;
    return <Fragment key={i}>{p}</Fragment>;
  });
}

function renderBlock(b: Block, i: number) {
  if (b.kind === "heading") {
    const Tag = (`h${b.level}` as keyof React.JSX.IntrinsicElements);
    return <Tag key={i}>{renderInline(b.text)}</Tag>;
  }
  if (b.kind === "code") {
    return <div key={i} className="my-4"><CodeBlock code={b.code} language={b.language} /></div>;
  }
  if (b.kind === "list") {
    return <ul key={i}>{b.items.map((it, j) => <li key={j}>{renderInline(it)}</li>)}</ul>;
  }
  if (b.kind === "table") {
    return (
      <div key={i} className="my-4 rounded-lg border border-border overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-surface-2 text-text-muted text-xs uppercase tracking-wider">
            <tr>{b.header.map((h, j) => <th key={j} className="text-left px-3 py-2">{h}</th>)}</tr>
          </thead>
          <tbody>
            {b.rows.map((r, ri) => (
              <tr key={ri} className="border-t border-border-subtle">
                {r.map((c, ci) => <td key={ci} className="px-3 py-2 text-text-secondary">{renderInline(c)}</td>)}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  }
  return <p key={i}>{renderInline(b.text)}</p>;
}

export function ComingSoonBlock() {
  return (
    <div className="rounded-lg border border-border bg-surface-1 p-6 flex items-center gap-3">
      <Wrench className="h-5 w-5 text-amber" />
      <div>
        <div className="text-sm font-medium text-text-primary">This section is in progress.</div>
        <div className="text-xs text-text-secondary">
          Check back soon or{" "}
          <a
            href="https://github.com/De-real-iManuel/Hedera-Agent-Commerce-Kit/issues"
            target="_blank" rel="noreferrer"
            className="text-purple hover:text-purple/80"
          >
            open a GitHub issue
          </a>.
        </div>
      </div>
    </div>
  );
}
