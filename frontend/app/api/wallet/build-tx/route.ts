/**
 * POST /api/wallet/build-tx
 *
 * Server-side only. Builds a Hedera TransferTransaction and returns it as a
 * base64-encoded string. The browser forwards it to the wallet via WalletConnect
 * (hedera_signAndExecuteTransaction / HIP-820) — the wallet handles signing
 * and submission, so we do NOT need a funded operator key here.
 *
 * Body: { senderAccountId, recipientAccountId, amount, memo? }
 * Returns: { transactionBytes: string }  (base64)
 */

import { NextResponse } from "next/server";

export const runtime = "nodejs";

// Testnet node account IDs (Hedera public nodes 0.0.3 – 0.0.9).
// Required when freezing a transaction without a Client instance.
const TESTNET_NODES: Record<string, string> = {
  "0.testnet.hedera.com:50211": "0.0.3",
  "1.testnet.hedera.com:50211": "0.0.4",
  "2.testnet.hedera.com:50211": "0.0.5",
  "3.testnet.hedera.com:50211": "0.0.6",
};

const MAINNET_NODES: Record<string, string> = {
  "35.237.200.180:50211": "0.0.3",
  "35.186.191.247:50211": "0.0.4",
  "35.192.2.25:50211": "0.0.5",
  "35.199.161.108:50211": "0.0.6",
};

export async function POST(req: Request) {
  try {
    const {
      senderAccountId,
      recipientAccountId,
      amount,
      memo = "hack-payment",
    } = await req.json();

    if (!senderAccountId || !recipientAccountId || !amount) {
      return NextResponse.json(
        { error: "Missing required fields: senderAccountId, recipientAccountId, amount" },
        { status: 400 },
      );
    }

    const network = process.env.NEXT_PUBLIC_HEDERA_NETWORK ?? "testnet";

    const {
      AccountId,
      Hbar,
      TransferTransaction,
      TransactionId,
      Client,
    } = await import("@hashgraph/sdk");

    const sender    = AccountId.fromString(senderAccountId);
    const recipient = AccountId.fromString(recipientAccountId);
    const hbar      = new Hbar(Number(amount));

    // Build a minimal client just for freezing — no operator key needed.
    // The wallet signs and submits; we only need the node map.
    const client = network === "mainnet"
      ? Client.forMainnet()
      : Client.forTestnet();

    const tx = new TransferTransaction()
      .addHbarTransfer(sender, hbar.negated())
      .addHbarTransfer(recipient, hbar)
      .setTransactionMemo(memo)
      .setTransactionId(TransactionId.generate(sender))
      .setMaxTransactionFee(new Hbar(2))
      .freezeWith(client);

    client.close(); // release the connection pool immediately

    const bytes  = tx.toBytes();
    const base64 = Buffer.from(bytes).toString("base64");

    return NextResponse.json({ transactionBytes: base64 });
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    console.error("[build-tx]", message);
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
