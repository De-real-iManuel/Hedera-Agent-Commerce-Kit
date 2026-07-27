import { cn } from "@/lib/utils";
import type { ButtonHTMLAttributes, AnchorHTMLAttributes } from "react";

type Variant = "primary" | "ghost" | "link";
type Size = "sm" | "md" | "lg";

const base = "inline-flex items-center justify-center gap-2 font-medium rounded-md transition-all duration-150 focus:outline-none focus:ring-2 focus:ring-purple/40 disabled:opacity-50 disabled:pointer-events-none";

const variants: Record<Variant, string> = {
  primary: "bg-purple text-white hover:bg-purple/90 shadow-[0_0_0_1px_rgba(124,58,237,0.5),0_8px_24px_-8px_rgba(124,58,237,0.6)]",
  ghost:   "border border-border bg-transparent text-text-primary hover:border-purple/60 hover:bg-surface-2",
  link:    "text-text-secondary hover:text-text-primary underline underline-offset-4 decoration-border hover:decoration-purple",
};

const sizes: Record<Size, string> = {
  sm: "h-8 px-3 text-xs",
  md: "h-10 px-4 text-sm",
  lg: "h-11 px-6 text-sm",
};

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
}

export function Button({ variant = "primary", size = "md", className, ...props }: ButtonProps) {
  return <button className={cn(base, variants[variant], sizes[size], className)} {...props} />;
}

export interface LinkButtonProps extends AnchorHTMLAttributes<HTMLAnchorElement> {
  variant?: Variant;
  size?: Size;
}

export function LinkButton({ variant = "primary", size = "md", className, ...props }: LinkButtonProps) {
  return <a className={cn(base, variants[variant], sizes[size], className)} {...props} />;
}
