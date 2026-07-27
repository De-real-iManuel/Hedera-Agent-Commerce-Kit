"use client";
import { cn } from "@/lib/utils";
import { ENDPOINT_GROUPS, type EndpointDef } from "./endpoints";

const METHOD_STYLES: Record<string, string> = {
  GET: "text-cyan border-cyan/40 bg-cyan/10",
  POST: "text-purple border-purple/40 bg-purple/10",
};

export function EndpointPanel({
  active,
  onSelect,
}: {
  active: string;
  onSelect: (e: EndpointDef) => void;
}) {
  return (
    <aside className="w-[260px] shrink-0 border-r border-border bg-surface-1 overflow-y-auto">
      <div className="px-4 py-3 border-b border-border">
        <div className="text-[10px] uppercase tracking-widest text-text-muted">Endpoints</div>
      </div>
      <div className="py-2">
        {ENDPOINT_GROUPS.map((g) => (
          <div key={g.category} className="mb-4">
            <div className="px-4 py-1 text-[10px] uppercase tracking-widest text-text-muted">
              {g.category}
            </div>
            <ul>
              {g.endpoints.map((e) => (
                <li key={e.id}>
                  <button
                    onClick={() => onSelect(e)}
                    className={cn(
                      "w-full text-left px-4 py-2 flex items-center gap-2 transition-colors border-l-2",
                      active === e.id
                        ? "border-purple bg-surface-2"
                        : "border-transparent hover:bg-surface-2",
                    )}
                  >
                    <span
                      className={cn(
                        "font-mono text-[9px] px-1.5 py-0.5 rounded border",
                        METHOD_STYLES[e.method],
                      )}
                    >
                      {e.method}
                    </span>
                    <span className="font-mono text-xs text-text-primary truncate flex-1">
                      {e.path.replace(/^\/api\//, "")}
                    </span>
                    {e.x402 && (
                      <span className="text-[9px] font-mono text-amber">402</span>
                    )}
                  </button>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>
    </aside>
  );
}
