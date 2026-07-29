/**
 * Browser stubs for @hashgraph/sdk and @hashgraph/proto.
 *
 * DAppConnector + DAppSigner from @hashgraph/hedera-wallet-connect import
 * these at module load time. In the browser we alias the real SDK to this
 * file so webpack can bundle hedera-wallet-connect without Node.js deps.
 *
 * All actual transaction building happens server-side in /api/wallet/build-tx
 * using the real @hashgraph/sdk on Node.js.
 */

// ── Stub base class ───────────────────────────────────────────────────────
class StubQuery {
  setAccountId() { return this; }
  setTransactionId() { return this; }
  execute() { return Promise.resolve({}); }
}

// ── @hashgraph/sdk exports used by DAppConnector / DAppSigner ─────────────

export const LedgerId = {
  TESTNET: { toString: () => 'testnet', _value: 'testnet', isMainnet: () => false },
  MAINNET: { toString: () => 'mainnet', _value: 'mainnet', isMainnet: () => true },
  fromString: (s) => ({
    toString: () => s,
    _value: s,
    isMainnet: () => s === 'mainnet',
  }),
};

export class Transaction {
  toBytes() { return new Uint8Array(); }
  static fromBytes() { return new Transaction(); }
  freezeWith() { return this; }
  sign() { return Promise.resolve(this); }
}

export class AccountId {
  constructor(num) { this.num = num; }
  static fromString(s) { return new AccountId(s); }
  toString() { return String(this.num); }
}

export class PublicKey {
  static fromString(s) { return new PublicKey(s); }
  constructor(val) { this._val = val; }
  toStringRaw() { return String(this._val); }
  toString() { return String(this._val); }
  verify() { return true; }
}

export class Hbar {
  constructor(v) { this._value = v; }
  negated() { return new Hbar(-this._value); }
  toString() { return `${this._value} ℏ`; }
  toTinybars() { return Math.round(this._value * 1e8); }
  static fromTinybars(v) { return new Hbar(v / 1e8); }
  static from(v, unit) { return new Hbar(v); }
}

export class TransferTransaction {
  addHbarTransfer() { return this; }
  setTransactionMemo() { return this; }
  setTransactionId() { return this; }
  setMaxTransactionFee() { return this; }
  freezeWith() { return this; }
  toBytes() { return new Uint8Array(); }
  sign() { return Promise.resolve(this); }
}

export class TransactionId {
  constructor(accountId, validStart) {
    this.accountId = accountId;
    this.validStart = validStart;
  }
  static generate(accountId) {
    return new TransactionId(accountId, { seconds: Math.floor(Date.now() / 1000), nanos: 0 });
  }
  toString() { return `${this.accountId}@${this.validStart?.seconds ?? 0}.000000000`; }
}

// Query stubs — DAppSigner constructs these but never executes them in browser
export class AccountBalanceQuery extends StubQuery {}
export class AccountInfoQuery extends StubQuery {}
export class AccountRecordsQuery extends StubQuery {}
export class TransactionReceiptQuery extends StubQuery {}
export class TransactionRecordQuery extends StubQuery {}

// Client stub — DAppSigner uses Client.forName / Client.forTestnet
export class Client {
  static forTestnet() { return new Client('testnet'); }
  static forMainnet() { return new Client('mainnet'); }
  static forName(name) { return new Client(name); }
  constructor(network) { this.network = network; }
  setOperator() { return this; }
  close() {}
}

// Additional types DAppSigner / wallet provider reference
export class SignerSignature {
  constructor(opts) { Object.assign(this, opts); }
}

export class AccountBalance {
  constructor(opts) { Object.assign(this, opts); }
}

export class AccountInfo {
  constructor(opts) { Object.assign(this, opts); }
}

export class TransactionRecord {
  constructor(opts) { Object.assign(this, opts); }
}

export class TransactionReceipt {
  constructor(opts) { Object.assign(this, opts); }
}

export class TransactionResponse {
  constructor(opts) { Object.assign(this, opts); }
  getReceipt() { return Promise.resolve(new TransactionReceipt({})); }
}

export class Query extends StubQuery {}

// ── @hashgraph/proto stub ─────────────────────────────────────────────────
export const proto = {
  Transaction: {
    decode: () => ({}),
    encode: () => ({ finish: () => new Uint8Array() }),
  },
  TransactionBody: { decode: () => ({}) },
  SignedTransaction: { decode: () => ({}) },
  TransactionList: { decode: () => ({ transactionList: [] }) },
};

// Default export (some imports use `import sdk from '@hashgraph/sdk'`)
export default {
  LedgerId, Transaction, AccountId, PublicKey, Hbar, TransferTransaction,
  TransactionId, AccountBalanceQuery, AccountInfoQuery, AccountRecordsQuery,
  TransactionReceiptQuery, TransactionRecordQuery, Client, SignerSignature,
  AccountBalance, AccountInfo, TransactionRecord, TransactionReceipt,
  TransactionResponse, Query,
};
