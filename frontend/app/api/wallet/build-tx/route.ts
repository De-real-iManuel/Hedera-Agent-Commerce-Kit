/**
 * POST /api/wallet/build-tx
 *
 * Server-side only. Uses @hashgraph/sdk (Node.js) to build a
 * TransferTransaction and return it as a base64-encoded string that the
 * browser can forward to a Hedera wallet via WalletConnect.
 *
 * Body: { senderAccountId, recipientAccountId, amount, memo }
 * Returns: { transactionBytes: string }  (base64)
 */

import { NextResponse } from "next/server";

export const runtime = "nodejs";

export async function POST(req: Request) {
  try {
    const { senderAccountId, recipientAccountId, amount, memo = "hack-payment" } =
      await req.json();

    if (!senderAccountId || !recipientAccountId || !amount) {
      return NextResponse.json(
        { error: "Missing required fields: senderAccountId, recipientAccountId, amount" },
        { status: 400 },
      );
    }

    // Dynamic import keeps this server-only — never bundled into client JS.
    const {
      AccountId,
      Hbar,
      TransferTransaction,
      TransactionId,
    } = await import("@hashgraph/sdk");

    const sender = AccountId.fromString(senderAccountId);
    const recipient = AccountId.fromString(recipientAccountId);
    const hbar = new Hbar(Number(amount));

    const tx = new TransferTransaction()
      .addHbarTransfer(sender, hbar.negated())
      .addHbarTransfer(recipient, hbar)
      .setTransactionMemo(memo)
      .setTransactionId(TransactionId.generate(sender))
      .setMaxTransactionFee(new Hbar(2));

    // Freeze without a client — the wallet will handle network submission.
    const frozen = tx.freezeWith(null as any); // eslint-disable-line @typescript-eslint/no-explicit-any

    const bytes = frozen.toBytes();
    const base64 = Buffer.from(bytes).toString("base64");

    return NextResponse.json({ transactionBytes: base64 });
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
