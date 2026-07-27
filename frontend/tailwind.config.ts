import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx,mdx}",
    "./components/**/*.{ts,tsx}",
    "./content/**/*.{md,mdx}",
  ],
  theme: {
    container: {
      center: true,
      padding: "1.5rem",
      screens: { "2xl": "1200px" },
    },
    extend: {
      colors: {
        background: "#09090b",
        "surface-1": "#111113",
        "surface-2": "#18181b",
        "surface-3": "#1c1c21",
        border: "#27272a",
        "border-subtle": "#1f1f23",
        purple: {
          DEFAULT: "#7c3aed",
          dim: "#4c1d95",
        },
        cyan: { DEFAULT: "#06b6d4" },
        green: { DEFAULT: "#10b981" },
        amber: { DEFAULT: "#f59e0b" },
        red: { DEFAULT: "#ef4444" },
        "text-primary": "#fafafa",
        "text-secondary": "#a1a1aa",
        "text-muted": "#52525b",
      },
      fontFamily: {
        sans: ["var(--font-inter)", "system-ui", "sans-serif"],
        mono: ["var(--font-jetbrains)", "ui-monospace", "monospace"],
      },
      borderRadius: {
        md: "6px",
        lg: "8px",
      },
      keyframes: {
        "fade-up": {
          "0%": { opacity: "0", transform: "translateY(24px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        blink: {
          "0%, 50%": { opacity: "1" },
          "51%, 100%": { opacity: "0" },
        },
      },
      animation: {
        "fade-up": "fade-up 0.4s ease-out both",
        blink: "blink 1s steps(1) infinite",
      },
    },
  },
  plugins: [],
};
export default config;
