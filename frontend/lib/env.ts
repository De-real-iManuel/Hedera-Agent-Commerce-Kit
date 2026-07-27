/**
 * lib/env.ts
 * ----------
 * Single source of truth for all NEXT_PUBLIC_ environment variables.
 *
 * Every component that needs a Hedera account ID, HCS topic, or network
 * value imports from here — no hardcoded strings anywhere in the codebase.
 *
 * Fill in NEXT_PUBLIC_PAYMENT_RECEIVER and NEXT_PUBLIC_HCS_TOPIC_ID in
 * .env.local to match the values in the backend .env file.
 */

export const ENV = {
  /** Backend base URL — e.g. http://localhost:8000 */
  apiBase: process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000",

  /** Hedera network: "testnet" | "mainnet" */
  network: process.env.NEXT_PUBLIC_HEDERA_NETWORK ?? "testnet",

  /** HashScan explorer base — used for all on-chain links */
  hashscanBase:
    process.env.NEXT_PUBLIC_HASHSCAN_BASE ??
    `https://hashscan.io/${process.env.NEXT_PUBLIC_HEDERA_NETWORK ?? "testnet"}`,

  /** The Hedera account that receives x402 HBAR payments.
   *  Must match X402_PAYMENT_RECEIVER_ACCOUNT_ID in the backend .env. */
  paymentReceiver: process.env.NEXT_PUBLIC_PAYMENT_RECEIVER ?? "",

  /** The HCS topic ID where payment receipts are logged.
   *  Must match HCS_RECEIPT_TOPIC_ID in the backend .env. */
  hcsTopicId: process.env.NEXT_PUBLIC_HCS_TOPIC_ID ?? "",

  /** WalletConnect project ID from https://cloud.reown.com */
  walletConnectProjectId: process.env.NEXT_PUBLIC_WALLETCONNECT_PROJECT_ID ?? "",

  /** Mirror Node REST API host */
  mirrorNodeHost:
    process.env.NEXT_PUBLIC_HEDERA_NETWORK === "mainnet"
      ? "mainnet-public.mirrornode.hedera.com"
      : "testnet.mirrornode.hedera.com",
} as const;

/** True once the operator values have been filled in. */
export function isEnvConfigured(): boolean {
  return (
    ENV.paymentReceiver.length > 0 &&
    !ENV.paymentReceiver.includes("XXXX") &&
    ENV.hcsTopicId.length > 0 &&
    !ENV.hcsTopicId.includes("YYYY")
  );
}
