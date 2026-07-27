"use client";
import { motion } from "framer-motion";
import { cn } from "@/lib/utils";
import { AnimatedNumber } from "./AnimatedNumber";

export function ScoreRing({
  score,
  size = "lg",
  label,
}: {
  score: number;
  size?: "sm" | "lg";
  label?: string;
}) {
  const dim = size === "lg" ? 200 : 96;
  const stroke = size === "lg" ? 12 : 8;
  const r = (dim - stroke) / 2;
  const c = 2 * Math.PI * r;
  const pct = Math.max(0, Math.min(100, score));
  const dash = (pct / 100) * c;

  const color = score >= 80 ? "#10b981" : score >= 60 ? "#f59e0b" : "#ef4444";

  return (
    <div className="flex flex-col items-center" style={{ width: dim }}>
      <div className="relative" style={{ width: dim, height: dim }}>
        <svg width={dim} height={dim} className="-rotate-90">
          <circle
            cx={dim / 2}
            cy={dim / 2}
            r={r}
            stroke="#27272a"
            strokeWidth={stroke}
            fill="none"
          />
          <motion.circle
            cx={dim / 2}
            cy={dim / 2}
            r={r}
            stroke={color}
            strokeWidth={stroke}
            strokeLinecap="round"
            fill="none"
            initial={{ strokeDasharray: `0 ${c}` }}
            animate={{ strokeDasharray: `${dash} ${c}` }}
            transition={{ duration: 1.1, ease: "easeOut" }}
          />
        </svg>
        <div className={cn(
          "absolute inset-0 flex flex-col items-center justify-center",
          size === "lg" ? "text-5xl font-bold" : "text-xl font-semibold",
        )}>
          <span style={{ color }}><AnimatedNumber value={score} /></span>
          {size === "lg" && (
            <span className="mt-1 text-xs font-normal text-text-muted">/ 100</span>
          )}
        </div>
      </div>
      {label && <div className="mt-3 text-sm text-text-secondary">{label}</div>}
    </div>
  );
}
