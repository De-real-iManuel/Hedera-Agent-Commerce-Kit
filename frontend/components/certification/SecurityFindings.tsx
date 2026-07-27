"use client";
/**
 * SecurityFindings
 * ----------------
 * Renders the security analysis section of a compliance report.
 *
 * Shows:
 *   - Summary badges: Critical / Medium / Warnings / Suggestions
 *   - Expandable finding rows grouped by severity
 *   - Color-coded severity indicators matching the design system
 */

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { AlertTriangle, Info, ChevronDown, ShieldAlert, ShieldCheck } from "lucide-react";
import { cn } from "@/lib/utils";
import type { SecurityFinding, RuleSeverity } from "@/lib/types";

interface Props {
  findings: SecurityFinding[];
  delay?: number;
}

const SEVERITY_CONFIG: Record<
  RuleSeverity,
  { label: string; badgeClass: string; textClass: string; icon: React.ElementType }
> = {
  critical:   { label: "Critical",    badgeClass: "border-red/40 bg-red/10 text-red",       textClass: "text-red",   icon: ShieldAlert },
  medium:     { label: "Medium",      badgeClass: "border-amber/40 bg-amber/10 text-amber",  textClass: "text-amber", icon: AlertTriangle },
  warning:    { label: "Warnings",    badgeClass: "border-amber/40 bg-amber/10 text-amber",  textClass: "text-amber", icon: AlertTriangle },
  suggestion: { label: "Suggestions", badgeClass: "border-cyan/40 bg-cyan/10 text-cyan",     textClass: "text-cyan",  icon: Info },
};

export function SecurityFindings({ findings, delay = 0 }: Props) {
  const counts = { critical: 0, medium: 0, warning: 0, suggestion: 0 } as Record<RuleSeverity, number>;
  findings.forEach((f) => counts[f.severity]++);

  const allClear = counts.critical === 0 && counts.medium === 0;

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay }}
      className="mt-10"
    >
      <div className="flex items-baseline justify-between mb-4">
        <h2 className="text-xl font-semibold tracking-tight">Security Analysis</h2>
        {allClear && (
          <div className="flex items-center gap-1.5 text-xs text-green">
            <ShieldCheck className="h-4 w-4" />
            No critical issues
          </div>
        )}
      </div>

      {/* Summary badges */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
        {(["critical", "medium", "warning", "suggestion"] as RuleSeverity[]).map((sev) => {
          const cfg = SEVERITY_CONFIG[sev];
          return (
            <div
              key={sev}
              className={cn(
                "rounded-md border px-4 py-3 flex items-center justify-between text-xs font-mono",
                cfg.badgeClass,
              )}
            >
              <span className="uppercase tracking-widest">{cfg.label}</span>
              <span className="font-semibold text-base">{counts[sev]}</span>
            </div>
          );
        })}
      </div>

      {/* Finding rows */}
      {findings.length === 0 ? (
        <div className="rounded-lg border border-green/30 bg-green/5 px-6 py-8 text-center">
          <ShieldCheck className="h-8 w-8 text-green mx-auto mb-2" />
          <div className="text-sm text-green font-medium">No security findings</div>
          <div className="text-xs text-text-muted mt-1">
            This service passed all automated security checks.
          </div>
        </div>
      ) : (
        <div className="rounded-lg border border-border bg-surface-1 divide-y divide-border">
          {findings.map((f, i) => (
            <FindingRow key={f.id} finding={f} index={i} />
          ))}
        </div>
      )}
    </motion.div>
  );
}

function FindingRow({ finding, index }: { finding: SecurityFinding; index: number }) {
  const [expanded, setExpanded] = useState(false);
  const cfg = SEVERITY_CONFIG[finding.severity];
  const Icon = cfg.icon;

  return (
    <motion.div
      initial={{ opacity: 0, x: -8 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.3, delay: index * 0.04 }}
    >
      <button
        onClick={() => setExpanded((e) => !e)}
        className="w-full flex items-start gap-4 px-6 py-4 text-left hover:bg-surface-2 transition-colors"
      >
        {/* Severity icon */}
        <Icon className={cn("h-4 w-4 mt-0.5 shrink-0", cfg.textClass)} />

        {/* Content */}
        <div className="flex-1 min-w-0">
          <div className="flex items-baseline gap-2">
            <span
              className={cn(
                "text-[10px] uppercase tracking-widest font-mono",
                cfg.textClass,
              )}
            >
              {finding.severity}
            </span>
            <span className="text-sm text-text-primary truncate">{finding.title}</span>
          </div>
          <div className="mt-0.5 text-xs text-text-secondary truncate">{finding.detail}</div>
        </div>

        <ChevronDown
          className={cn(
            "h-4 w-4 text-text-muted shrink-0 transition-transform duration-200",
            expanded && "rotate-180",
          )}
        />
      </button>

      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
            <div className="px-6 pb-4 pl-14">
              <div className="rounded-md border border-border-subtle bg-surface-2 px-4 py-3 text-xs text-text-secondary">
                <div className="font-mono text-text-muted mb-1">ID: {finding.id}</div>
                {finding.detail}
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}
