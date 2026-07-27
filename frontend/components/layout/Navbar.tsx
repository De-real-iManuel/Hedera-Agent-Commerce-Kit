"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { Github, Menu, X } from "lucide-react";
import { LinkButton } from "@/components/ui/Button";
import { cn } from "@/lib/utils";

const NAV = [
  { href: "/api-explorer", label: "API Explorer" },
  { href: "/docs", label: "Docs" },
  { href: "/certification", label: "Get Certified" },
  { href: "/certificates", label: "Certificates" },
];

export function Navbar() {
  const [scrolled, setScrolled] = useState(false);
  const [open, setOpen] = useState(false);
  const [stars, setStars] = useState<number | null>(null);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 8);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  useEffect(() => {
    fetch("https://api.github.com/repos/De-real-iManuel/Hedera-Agent-Commerce-Kit", {
      headers: { Accept: "application/vnd.github+json" },
    })
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => d && setStars(d.stargazers_count))
      .catch(() => {});
  }, []);

  return (
    <header
      className={cn(
        "sticky top-0 z-40 w-full transition-all duration-200",
        scrolled
          ? "bg-background/80 backdrop-blur-md border-b border-border"
          : "bg-transparent border-b border-transparent",
      )}
    >
      <div className="container mx-auto flex h-14 items-center justify-between px-6">
        <Link href="/" className="flex items-center gap-2">
          <span className="font-semibold tracking-tight text-purple">HACK</span>
          <span className="rounded-full border border-border bg-surface-2 px-2 py-0.5 font-mono text-[10px] text-text-muted">
            v0.1.0
          </span>
        </Link>

        <nav className="hidden md:flex items-center gap-8">
          {NAV.map((n) => (
            <Link
              key={n.href}
              href={n.href}
              className="text-sm text-text-secondary hover:text-text-primary transition-colors"
            >
              {n.label}
            </Link>
          ))}
        </nav>

        <div className="hidden md:flex items-center gap-3">
          <a
            href="https://github.com/De-real-iManuel/Hedera-Agent-Commerce-Kit"
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center gap-1.5 rounded-md border border-border bg-surface-1 px-2.5 py-1.5 text-xs text-text-secondary hover:border-purple/60 hover:text-text-primary transition-colors"
          >
            <Github className="h-3.5 w-3.5" />
            <span>Star</span>
            {stars !== null && (
              <span className="font-mono text-text-muted">{stars.toLocaleString()}</span>
            )}
          </a>
          <LinkButton href="/docs" size="sm">
            Get Started →
          </LinkButton>
        </div>

        <button
          className="md:hidden text-text-secondary"
          onClick={() => setOpen(!open)}
          aria-label="Menu"
        >
          {open ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
        </button>
      </div>

      {open && (
        <div className="md:hidden border-t border-border bg-background/95 backdrop-blur-md">
          <div className="container mx-auto px-6 py-4 flex flex-col gap-3">
            {NAV.map((n) => (
              <Link
                key={n.href}
                href={n.href}
                onClick={() => setOpen(false)}
                className="text-sm text-text-secondary hover:text-text-primary"
              >
                {n.label}
              </Link>
            ))}
            <LinkButton href="/docs" size="sm">Get Started →</LinkButton>
          </div>
        </div>
      )}
    </header>
  );
}
