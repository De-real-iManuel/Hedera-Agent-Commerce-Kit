import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) { return twMerge(clsx(inputs)); }

export function formatHBAR(amount: number, digits = 4): string {
  return `${amount.toFixed(digits).replace(/0+$/, "").replace(/\.$/, "")} HBAR`;
}

export function formatTxId(id: string, head = 8, tail = 6): string {
  if (!id) return "";
  if (id.length <= head + tail + 3) return id;
  return `${id.slice(0, head)}…${id.slice(-tail)}`;
}

export function hashScanTxUrl(txId: string): string {
  const base = process.env.NEXT_PUBLIC_HASHSCAN_BASE || "https://hashscan.io/testnet";
  return `${base}/transaction/${encodeURIComponent(txId)}`;
}

export function hashScanTopicUrl(topicId: string): string {
  const base = process.env.NEXT_PUBLIC_HASHSCAN_BASE || "https://hashscan.io/testnet";
  return `${base}/topic/${encodeURIComponent(topicId)}`;
}

export function formatDuration(seconds: number): string {
  if (seconds <= 0) return "expired";
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}m ${s.toString().padStart(2, "0")}s`;
}

export function shortHash(hash: string, len = 12): string {
  if (!hash) return "";
  return hash.length > len ? `${hash.slice(0, len)}…` : hash;
}
