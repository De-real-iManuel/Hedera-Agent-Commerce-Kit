"use client";
import { motion } from "framer-motion";
import { Check, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

export interface Step {
  id: string;
  title: string;
  description?: string;
}

export function StepIndicator({
  steps,
  currentStep,
  className,
}: {
  steps: Step[];
  currentStep: number;
  className?: string;
}) {
  return (
    <ol className={cn("space-y-4", className)}>
      {steps.map((step, i) => {
        const state = i < currentStep ? "done" : i === currentStep ? "active" : "future";
        return (
          <li key={step.id} className="flex gap-3">
            <div className="flex flex-col items-center">
              <div
                className={cn(
                  "flex h-8 w-8 items-center justify-center rounded-full border transition-colors",
                  state === "done" && "border-green bg-green/10 text-green",
                  state === "active" && "border-purple bg-purple/10 text-purple",
                  state === "future" && "border-border text-text-muted",
                )}
              >
                {state === "done" && <Check className="h-4 w-4" />}
                {state === "active" && <Loader2 className="h-4 w-4 animate-spin" />}
                {state === "future" && <span className="text-xs font-mono">{i + 1}</span>}
              </div>
              {i < steps.length - 1 && (
                <div className={cn("w-px flex-1 my-1", state === "done" ? "bg-green/40" : "bg-border")} />
              )}
            </div>
            <div className="pb-6">
              <motion.div
                initial={{ opacity: 0, x: -4 }}
                animate={{ opacity: 1, x: 0 }}
                className={cn(
                  "text-sm font-medium",
                  state === "future" ? "text-text-muted" : "text-text-primary",
                )}
              >
                {step.title}
              </motion.div>
              {step.description && (
                <p className="mt-0.5 text-xs text-text-secondary">{step.description}</p>
              )}
            </div>
          </li>
        );
      })}
    </ol>
  );
}
