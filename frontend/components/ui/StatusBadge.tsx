import { cn } from "@/lib/utils";
import type { PaymentState } from "@/lib/types";

const STATUS_STYLES: Record<PaymentState, { bg: string; text: string; label: string }> = {
  quoted:    { bg: "bg-amber/15 border-amber/40",    text: "text-amber",    label: "QUOTED" },
  verified:  { bg: "bg-cyan/15 border-cyan/40",      text: "text-cyan",     label: "VERIFIED" },
  granted:   { bg: "bg-green/15 border-green/40",    text: "text-green",    label: "GRANTED" },
  consumed:  { bg: "bg-green/10 border-green/30",    text: "text-green/80", label: "CONSUMED" },
  expired:   { bg: "bg-red/15 border-red/40",        text: "text-red",      label: "EXPIRED" },
  duplicate: { bg: "bg-red/15 border-red/40",        text: "text-red",      label: "DUPLICATE" },
};

export function StatusBadge({ status, className }: { status: PaymentState; className?: string }) {
  const s = STATUS_STYLES[status];
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-[10px] font-mono font-medium tracking-wider",
        s.bg, s.text, className,
      )}
    >
      <span className={cn("h-1.5 w-1.5 rounded-full", s.text.replace("text-", "bg-"))} />
      {s.label}
    </span>
  );
}
