import { PlaygroundShell } from "@/components/playground/PlaygroundShell";

export const metadata = {
  title: "API Explorer — HACK",
  description:
    "Interactive explorer for the Hedera Agent Commerce Kit REST API. Try every endpoint, walk through the x402 payment flow, and watch HCS receipts stream in.",
};

export default function ApiExplorerPage() {
  return <PlaygroundShell />;
}
