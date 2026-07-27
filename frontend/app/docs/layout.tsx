"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { DOCS_NAV } from "@/content/docs";
import { cn } from "@/lib/utils";

export default function DocsLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  return (
    <div className="container mx-auto px-6 py-10 grid grid-cols-1 md:grid-cols-[240px_1fr] gap-10">
      <aside className="md:sticky md:top-20 self-start">
        <nav className="space-y-6">
          {DOCS_NAV.map((s) => (
            <div key={s.section}>
              <div className="text-xs font-semibold uppercase tracking-widest text-text-muted mb-2">
                {s.section}
              </div>
              <ul className="space-y-1">
                {s.pages.map((p) => {
                  const href = `/docs/${p.slug}`;
                  const active = pathname === href;
                  return (
                    <li key={p.slug}>
                      <Link
                        href={href}
                        className={cn(
                          "block text-sm py-1 border-l-2 pl-3 -ml-px transition-colors",
                          active
                            ? "border-purple text-text-primary"
                            : "border-transparent text-text-secondary hover:text-text-primary hover:border-border",
                        )}
                      >
                        {p.title}
                        {p.status === "coming-soon" && (
                          <span className="ml-2 text-[9px] uppercase tracking-widest text-amber">soon</span>
                        )}
                      </Link>
                    </li>
                  );
                })}
              </ul>
            </div>
          ))}
        </nav>
      </aside>

      <div className="min-w-0">{children}</div>
    </div>
  );
}
