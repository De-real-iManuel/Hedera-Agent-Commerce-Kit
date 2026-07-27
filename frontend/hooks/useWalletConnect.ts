'use client';

import { useCallback, useEffect, useState } from 'react';

export interface UseWalletConnectReturn {
  isConnected: boolean;
  accountId: string | null;
  network: string;
  connect: () => Promise<void>;
  disconnect: () => Promise<void>;
  sendHbar: (params: { recipientAccountId: string; amount: number; memo?: string }) => Promise<string>;
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

// Cache heavy SDK imports — resolved once on first use, never re-imported.
// Re-importing @hashgraph/sdk on every sendHbar call was the source of the
// ERR_MEMORY_ALLOCATION_FAILED crash in the Next.js dev server.
// eslint-disable-next-line @typescript-eslint/no-explicit-any
let _sdkCache: any = null;
// eslint-disable-next-line @typescript-eslint/no-explicit-any
let _wcCache: any = null;
// eslint-disable-next-line @typescript-eslint/no-explicit-any
let _importPromise: Promise<[any, any]> | null = null;

async function loadImports() {
  if (_sdkCache && _wcCache) return [_sdkCache, _wcCache] as const;
  if (_importPromise) return _importPromise;
  _importPromise = Promise.all([
    import('@hashgraph/sdk'),
    import('@hashgraph/hedera-wallet-connect'),
  ]).then(([sdk, wc]) => {
    _sdkCache = sdk;
    _wcCache = wc;
    return [sdk, wc] as [typeof sdk, typeof wc];
  });
  return _importPromise;
}

const APP_METADATA = {
  name: 'Hedera Agent Commerce Kit',
  description: 'Pay-per-request infrastructure for AI agents on Hedera',
  url: typeof window !== 'undefined' ? window.location.origin : 'https://hack.hedera.dev',
  icons: [typeof window !== 'undefined' ? `${window.location.origin}/icon.png` : 'https://hack.hedera.dev/icon.png'],
};

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
let connector: any = null;
// eslint-disable-next-line @typescript-eslint/no-explicit-any
let connectorPromise: Promise<any> | null = null;
let initialized = false;
let txInFlight = false;

function emit(patch: Partial<WalletSnapshot>) {
  snapshot = { ...snapshot, ...patch };
  listeners.forEach((listener) => listener(snapshot));
}

function subscribe(listener: (s: WalletSnapshot) => void): () => void {
  listeners.add(listener);
  listener(snapshot);
  return () => {
    listeners.delete(listener);
  };
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function accountFromSigner(signer: any): string | null {
  try {
    return signer?.getAccountId?.()?.toString?.() ?? null;
  } catch {
    return null;
  }
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function accountFromSession(session: any): string | null {
  const accounts = Object.values(session?.namespaces ?? {})
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    .flatMap((ns: any) => ns?.accounts ?? [])
    .filter((v): v is string => typeof v === 'string');
  if (accounts.length === 0) return null;
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
    result?.result?.transactionId,
    result?.result?.transaction_id,
    result?.transaction_id,
  ];
  return candidates.find((v) => typeof v === 'string' && v.length > 0) ?? '';
}

async function getConnector() {
  if (connector) return connector;
  if (connectorPromise) return connectorPromise;

  connectorPromise = (async () => {
    if (!PROJECT_ID) {
      throw new Error(
        'NEXT_PUBLIC_WALLETCONNECT_PROJECT_ID is not set. Get a free project ID from Reown Cloud and add it to frontend/.env.local.',
      );
    }

    const [sdk, walletConnect] = await loadImports();

    const {
      DAppConnector,
      HederaJsonRpcMethod,
      HederaSessionEvent,
      HederaChainId,
    } = walletConnect;
    const { LedgerId } = sdk;

    const ledgerId = NETWORK === 'mainnet' ? LedgerId.MAINNET : LedgerId.TESTNET;

    const c = new DAppConnector(
      APP_METADATA,
      ledgerId,
      PROJECT_ID,
      Object.values(HederaJsonRpcMethod),
      [HederaSessionEvent.ChainChanged, HederaSessionEvent.AccountsChanged],
      [NETWORK === 'mainnet' ? HederaChainId.Mainnet : HederaChainId.Testnet],
    );

    connector = c;
    return c;
  })();

  return connectorPromise;
}

async function ensureInitialized() {
  const c = await getConnector();
  if (!initialized) {
    await c.init({ logger: 'error' });
    initialized = true;

    const signers = c.signers ?? [];
    const restored = signers.length > 0 ? accountFromSigner(signers[signers.length - 1]) : null;
    if (restored) emit({ isConnected: true, accountId: restored });

    const anyConnector = c as any;
    if (typeof anyConnector.onSessionDisconnect === 'function') {
      anyConnector.onSessionDisconnect(() => emit({ isConnected: false, accountId: null }));
    }
  }
  return c;
}

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
        id = signers.length > 0 ? accountFromSigner(signers[signers.length - 1]) : null;
      }
      if (!id) throw new Error('WalletConnect paired, but no Hedera account was returned.');

      emit({ isConnected: true, accountId: id, error: null });
    } catch (err) {
      const message = err instanceof Error ? err.message : 'WalletConnect pairing failed.';
      emit({ error: message });
      throw err instanceof Error ? err : new Error(message);
    } finally {
      emit({ isPending: false });
    }
  }, []);

  const disconnect = useCallback(async (): Promise<void> => {
    if (txInFlight) {
      const deadline = Date.now() + 60_000;
      await new Promise<void>((resolve) => {
        const poll = setInterval(() => {
          if (!txInFlight || Date.now() >= deadline) {
            clearInterval(poll);
            resolve();
          }
        }, 200);
      });
    }

    try {
      await connector?.disconnectAll?.();
    } catch {
      // WalletConnect sometimes logs `{}` on disconnect. Safe to ignore.
    }
    connector = null;
    connectorPromise = null;
    initialized = false;
    emit({ isConnected: false, accountId: null, error: null });
  }, []);

  const sendHbar = useCallback(async ({ recipientAccountId, amount, memo = 'hack-payment' }: SendHbarParams): Promise<string> => {
    const activeAccount = snapshot.accountId;
    if (!snapshot.isConnected || !activeAccount) throw new Error('Wallet is not connected.');

    emit({ isPending: true, error: null });
    txInFlight = true;
    try {
      const c = await ensureInitialized();
      const [{ AccountId, Hbar, TransferTransaction, TransactionId }, { transactionToBase64String }] = await loadImports();

      const tx = new TransferTransaction()
        .addHbarTransfer(AccountId.fromString(activeAccount), new Hbar(amount).negated())
        .addHbarTransfer(AccountId.fromString(recipientAccountId), new Hbar(amount))
        .setTransactionMemo(memo)
        .setTransactionId(TransactionId.generate(AccountId.fromString(activeAccount)));

      const result = await c.signAndExecuteTransaction({
        signerAccountId: `hedera:${NETWORK}:${activeAccount}`,
        transactionList: transactionToBase64String(tx),
      });

      const txId = extractTxId(result);
      if (!txId) {
        throw new Error('Wallet submitted the transaction but did not return a transaction ID. Check the wallet transaction history.');
      }
      return txId;
    } catch (err) {
      const message = err instanceof Error ? err.message : 'HBAR payment failed.';
      emit({ error: message });
      throw err instanceof Error ? err : new Error(message);
    } finally {
      txInFlight = false;
      emit({ isPending: false });
    }
  }, []);

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
