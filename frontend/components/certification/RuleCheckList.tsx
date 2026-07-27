"use client";
/**
 * RuleCheckList
 * -------------
 * Renders a titled section of compliance rule results.
 * Used for both "x402 Compliance" and "Hedera Integration" sections.
 *
 * Each rule row shows:
 *   - pass/fail icon
 *   - rule name
 *   - detail string
 *   - optional expandable evidence panel
 */

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Check, X, ChevronDown } from "lucide-react";
import { cn } from "@/lib/utils";
import type { RuleResult } from "@/lib/types";

interface Props {
  title: string;
  rules: RuleResult[];
  /** Delay for entrance animation stagger */
  delay?: number;
}

export function RuleCheckList({ title, rules, delay = 0 }: Props) {
  const passed = rules.filter((r) => r.passed).length;

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay }}
      className="mt-10"
    >
      {/* Section header */}
      <div className="flex items-baseline justify-between mb-4">
        <h2 className="text-xl font-semibold tracking-tight">{title}</h2>
        <span
          className={cn(
            "text-sm font-mono",
            passed === rules.length ? "text-green" : "text-amber",
          )}
        >
          {passed}/{rules.length} ✓
        </span>
      </div>

      {/* Rule rows */}
      <div className="rounded-lg border border-border bg-surface-1 divide-y divide-border">
        {rules.map((rule, i) => (
          <RuleRow key={rule.id} rule={rule} index={i} />
        ))}
      </div>
    </motion.div>
  );
}

function RuleRow({ rule, index }: { rule: RuleResult; index: number }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <motion.div
      initial={{ opacity: 0, x: -8 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.3, delay: index * 0.05 }}
    >
      <button
        onClick={() => setExpanded((e) => !e)}
        className="w-full flex items-start gap-4 px-6 py-4 text-left hover:bg-surface-2 transition-colors group"
      >
        {/* Status icon */}
        <div
          className={cn(
            "mt-0.5 h-5 w-5 rounded-full flex items-center justify-center shrink-0",
            rule.passed
              ? "bg-green/10 border border-green/30"
              : "bg-red/10 border border-red/30",
          )}
        >
          {rule.passed ? (
            <Check className="h-3 w-3 text-green" />
          ) : (
            <X className="h-3 w-3 text-red" />
          )}
        </div>

        {/* Text */}
        <div className="flex-1 min-w-0">
          <div className="text-sm font-medium text-text-primary">{rule.name}</div>
          <div className="mt-0.5 text-xs text-text-secondary truncate">{rule.detail}</div>
        </div>

        {/* Expand chevron */}
        <ChevronDown
          className={cn(
            "h-4 w-4 text-text-muted shrink-0 transition-transform duration-200",
            expanded && "rotate-180",
          )}
        />
      </button>

      {/* Expanded detail */}
      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
            <div className="px-6 pb-4 pl-[3.75rem]">
              <div
                className={cn(
                  "rounded-md border px-4 py-3 text-xs",
                  rule.passed
                    ? "border-green/20 bg-green/5 text-green/90"
                    : "border-red/20 bg-red/5 text-red/90",
                )}
              >
                <div className="font-semibold mb-1">
                  {rule.passed ? "Passed" : "Failed"} — {rule.id}
                </div>
                <div className="text-text-secondary">{rule.detail}</div>
                {rule.severity && !rule.passed && (
                  <div className="mt-2 text-amber text-[10px] uppercase tracking-widest">
                    Severity: {rule.severity}
                  </div>
                )}
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}
