/**
 * Minimal browser stubs for @hashgraph/sdk and @hashgraph/proto.
 *
 * DAppConnector from @hashgraph/hedera-wallet-connect only needs:
 *   - LedgerId.TESTNET / LedgerId.MAINNET  (string enum used as chain ID)
 *   - Transaction (base class — only used for instanceof checks in DAppSigner)
 *
 * Everything else is server-side only (TransferTransaction, Hbar, etc.)
 * which is handled by /api/wallet/build-tx.
 */

// ── @hashgraph/sdk stub ───────────────────────────────────────────────────
export const LedgerId = {
  TESTNET: { toString: () => 'testnet', _value: 'testnet' },
  MAINNET: { toString: () => 'mainnet', _value: 'mainnet' },
  fromString: (s) => ({
    toString: () => s,
    _value: s,
  }),
};

export class Transaction {
  toBytes() { return new Uint8Array(); }
  static fromBytes() { return new Transaction(); }
}

export class AccountId {
  static fromString(s) { return { toString: () => s, accountNum: 0 }; }
  toString() { return ''; }
}

export class Hbar {
  constructor(v) { this._value = v; }
  negated() { return new Hbar(-this._value); }
  toString() { return `${this._value} ℏ`; }
  static fromTinybars(v) { return new Hbar(v / 1e8); }
}

export class TransferTransaction {
  addHbarTransfer() { return this; }
  setTransactionMemo() { return this; }
  setTransactionId() { return this; }
  setMaxTransactionFee() { return this; }
  freezeWith() { return this; }
  toBytes() { return new Uint8Array(); }
}

export class TransactionId {
  static generate(accountId) {
    return { toString: () => `${accountId}@${Date.now()}` };
  }
}

// ── @hashgraph/proto stub ─────────────────────────────────────────────────
export const proto = {
  Transaction: { decode: () => ({}), encode: () => ({ finish: () => new Uint8Array() }) },
  TransactionBody: { decode: () => ({}) },
};
