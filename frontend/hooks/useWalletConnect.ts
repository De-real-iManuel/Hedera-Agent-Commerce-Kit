'use client';

import { useCallback, useEffect, useRef, useState } from 'react';

export interface UseWalletConnectReturn {
  isConnected: boolean;
  accountId: string | null;
  network: string;
  connect: () => Promise<void>;
  disconnect: () => Promise<void>;
  sendHbar: (params: SendHbarParams) => Promise<string>;
  isPending: boolean;
  error: string | null;
}

export type SendHbarParams = {
  recipientAccountId: string;
  amount: number;
  memo?: string;
};

const PROJECT_ID = process.env.NEXT_PUBLIC_WALLETCONNECT_PROJECT_ID || '';
const NETWORK = process.env.NEXT_PUBLIC_HEDERA_NETWORK ?? 'testnet';

const APP_METADATA = {
  name: 'Hedera Agent Commerce Kit',
  description: 'Pay-per-request infrastructure for AI agents on Hedera',
  url: typeof window !== 'undefined' ? window.location.origin : 'https://hack.hedera.dev',
  icons: [
    typeof window !== 'undefined'
      ? `${window.location.origin}/icon.png`
      : 'https://hack.hedera.dev/icon.png',
  ],
};

// ── Friendly error messages ───────────────────────────────────────────────

function friendlyError(err: unknown): string {
  const msg = err instanceof Error ? err.message : String(err);

  // WalletConnect relay rejects connections from unregistered origins.
  // Fix: add this domain to Allowed Origins in cloud.reown.com → your project.
  if (msg.includes('3000') || msg.includes('Unauthorized: origin not allowed')) {
    return (
      'WalletConnect relay rejected this domain. ' +
      'Go to cloud.reown.com → your project → Allowed Origins and add: ' +
      (typeof window !== 'undefined' ? window.location.origin : 'this domain') +
      '. No redeploy needed after saving.'
    );
  }

  // Session proposal publish fails when the relay WebSocket is not established.
  if (msg.includes('Failed to publish custom payload') || msg.includes('tag:undefined')) {
    return (
      'WalletConnect relay is unreachable. This is usually caused by an ' +
      'unregistered domain — add this origin to cloud.reown.com → your project → Allowed Origins.'
    );
  }

  if (msg.includes('NEXT_PUBLIC_WALLETCONNECT_PROJECT_ID')) {
    return 'WalletConnect Project ID is not set. Add NEXT_PUBLIC_WALLETCONNECT_PROJECT_ID to your environment variables.';
  }

  return msg || 'WalletConnect pairing failed.';
}

// ── Singleton state (survives re-renders, reset on disconnect) ────────────

type WalletSnapshot = {
  isConnected: boolean;
  accountId: string | null;
  isPending: boolean;
  error: string | null;
};

let snapshot: WalletSnapshot = {
  isConnected: false,
  accountId: null,
  isPending: false,
  error: null,
};

const listeners = new Set<(s: WalletSnapshot) => void>();
// eslint-disable-next-line @typescript-eslint/no-explicit-any
let _connector: any = null;
// eslint-disable-next-line @typescript-eslint/no-explicit-any
let _connectorPromise: Promise<any> | null = null;
let _initialized = false;
let _txInFlight = false;

function emit(patch: Partial<WalletSnapshot>) {
  snapshot = { ...snapshot, ...patch };
  listeners.forEach((l) => l(snapshot));
}

function subscribe(listener: (s: WalletSnapshot) => void) {
  listeners.add(listener);
  listener(snapshot);
  return () => { listeners.delete(listener); };
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function accountFromSigner(signer: any): string | null {
  try { return signer?.getAccountId?.()?.toString?.() ?? null; } catch { return null; }
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function accountFromSession(session: any): string | null {
  const accounts = Object.values(session?.namespaces ?? {})
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    .flatMap((ns: any) => ns?.accounts ?? [])
    .filter((v): v is string => typeof v === 'string');
  if (!accounts.length) return null;
  const parts = accounts[0].split(':');
  return parts[parts.length - 1] || null;
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function extractTxId(result: any): string {
  const candidates = [
    result?.transactionId?.toString?.(),
    result?.transactionId,
    result?.response?.transactionId?.toString?.(),
    result?.response?.transactionId,
    result?.result?.transactionId?.toString?.(),
    result?.result?.transaction_id,
    result?.transaction_id,
  ];
  return candidates.find((v) => typeof v === 'string' && v.length > 0) ?? '';
}

// ── DAppConnector factory ─────────────────────────────────────────────────

async function getConnector() {
  if (_connector) return _connector;
  if (_connectorPromise) return _connectorPromise;

  if (!PROJECT_ID) throw new Error('NEXT_PUBLIC_WALLETCONNECT_PROJECT_ID');

  _connectorPromise = (async () => {
    // @hashgraph/hedera-wallet-connect is bundled via webpack alias stubs.
    // @hiero-ledger/sdk is the Hedera SDK — also aliased to stubs in browser.
    const [walletConnect, { LedgerId }] = await Promise.all([
      import('@hashgraph/hedera-wallet-connect'),
      import('@hiero-ledger/sdk'),
    ]);

    const {
      DAppConnector,
      HederaJsonRpcMethod,
      HederaSessionEvent,
      HederaChainId,
    } = walletConnect;

    const ledgerId = NETWORK === 'mainnet' ? LedgerId.MAINNET : LedgerId.TESTNET;

    const c = new DAppConnector(
      APP_METADATA,
      ledgerId,
      PROJECT_ID,
      Object.values(HederaJsonRpcMethod),
      [HederaSessionEvent.ChainChanged, HederaSessionEvent.AccountsChanged],
      [NETWORK === 'mainnet' ? HederaChainId.Mainnet : HederaChainId.Testnet],
    );

    _connector = c;
    return c;
  })();

  return _connectorPromise;
}

async function ensureInitialized() {
  const c = await getConnector();
  if (!_initialized) {
    await c.init({ logger: 'error' });
    _initialized = true;

    const signers = c.signers ?? [];
    const restored = signers.length > 0
      ? accountFromSigner(signers[signers.length - 1])
      : null;
    if (restored) emit({ isConnected: true, accountId: restored });

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    if (typeof (c as any).onSessionDisconnect === 'function') {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      (c as any).onSessionDisconnect(() =>
        emit({ isConnected: false, accountId: null }),
      );
    }
  }
  return c;
}

// ── Hook ─────────────────────────────────────────────────────────────────

export function useWalletConnect(): UseWalletConnectReturn {
  const [state, setState] = useState<WalletSnapshot>(snapshot);
  useEffect(() => subscribe(setState), []);

  const connect = useCallback(async (): Promise<void> => {
    emit({ isPending: true, error: null });
    try {
      const c = await ensureInitialized();
      const session = await c.openModal();

      let id = accountFromSession(session);
      if (!id) {
        const signers = c.signers ?? [];
        id = signers.length > 0
          ? accountFromSigner(signers[signers.length - 1])
          : null;
      }
      if (!id) throw new Error('WalletConnect paired but no Hedera account returned.');

      emit({ isConnected: true, accountId: id, error: null });
    } catch (err) {
      const message = friendlyError(err);
      emit({ error: message });
      throw new Error(message);
    } finally {
      emit({ isPending: false });
    }
  }, []);

  const disconnect = useCallback(async (): Promise<void> => {
    if (_txInFlight) {
      const deadline = Date.now() + 60_000;
      await new Promise<void>((resolve) => {
        const poll = setInterval(() => {
          if (!_txInFlight || Date.now() >= deadline) {
            clearInterval(poll);
            resolve();
          }
        }, 200);
      });
    }
    try { await _connector?.disconnectAll?.(); } catch { /* ignore */ }
    _connector = null;
    _connectorPromise = null;
    _initialized = false;
    emit({ isConnected: false, accountId: null, error: null });
  }, []);

  const sendHbar = useCallback(
    async ({ recipientAccountId, amount, memo = 'hack-payment' }: SendHbarParams): Promise<string> => {
      const activeAccount = snapshot.accountId;
      if (!snapshot.isConnected || !activeAccount) throw new Error('Wallet is not connected.');

      emit({ isPending: true, error: null });
      _txInFlight = true;
      try {
        const c = await ensureInitialized();

        // Transaction built server-side; only sign here via the wallet.
        // Falls back to client-side build using @hiero-ledger/sdk stubs if
        // the API route is unavailable.
        let transactionList: string;
        try {
          const res = await fetch('/api/wallet/build-tx', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ senderAccountId: activeAccount, recipientAccountId, amount, memo }),
          });
          if (!res.ok) throw new Error(`build-tx ${res.status}`);
          ({ transactionBytes: transactionList } = await res.json());
        } catch {
          // Fallback: build client-side (works locally where @hiero-ledger/sdk is real)
          const [
            { AccountId, Hbar, TransferTransaction, TransactionId },
            { transactionToBase64String },
          ] = await Promise.all([
            import('@hiero-ledger/sdk'),
            import('@hashgraph/hedera-wallet-connect'),
          ]);
          const tx = new TransferTransaction()
            .addHbarTransfer(AccountId.fromString(activeAccount), new Hbar(amount).negated())
            .addHbarTransfer(AccountId.fromString(recipientAccountId), new Hbar(amount))
            .setTransactionMemo(memo)
            .setTransactionId(TransactionId.generate(AccountId.fromString(activeAccount)));
          transactionList = transactionToBase64String(tx);
        }

        const result = await c.signAndExecuteTransaction({
          signerAccountId: `hedera:${NETWORK}:${activeAccount}`,
          transactionList,
        });

        const txId = extractTxId(result);
        if (!txId) {
          throw new Error(
            'Wallet submitted the transaction but did not return a transaction ID. ' +
            'Check your wallet transaction history.',
          );
        }
        return txId;
      } catch (err) {
        const message = friendlyError(err);
        emit({ error: message });
        throw new Error(message);
      } finally {
        _txInFlight = false;
        emit({ isPending: false });
      }
    },
    [],
  );

  return {
    isConnected: state.isConnected,
    accountId: state.accountId,
    network: NETWORK,
    connect,
    disconnect,
    sendHbar,
    isPending: state.isPending,
    error: state.error,
  };
}

export default useWalletConnect;
