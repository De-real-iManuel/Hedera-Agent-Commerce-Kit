'use client';
/**
 * useWalletConnect — Hedera wallet integration using raw WalletConnect v2.
 *
 * Zero Hedera SDK in the browser. Transaction bytes are built server-side
 * via /api/wallet/build-tx (uses @hashgraph/sdk on Node.js) and sent to
 * the wallet for signing via the hedera_signAndExecuteTransaction JSON-RPC
 * method defined in HIP-820 / WalletConnect.
 *
 * Only @walletconnect/sign-client is used here — it is pure browser JS with
 * no Node.js dependencies.
 */

import { useCallback, useEffect, useState } from 'react';

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
const CHAIN_ID = NETWORK === 'mainnet' ? 'hedera:mainnet' : 'hedera:testnet';

// ─── Singleton state (module-level, survives re-renders) ──────────────────

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
let client: any = null;
// eslint-disable-next-line @typescript-eslint/no-explicit-any
let session: any = null;
let clientPromise: Promise<unknown> | null = null;

function emit(patch: Partial<WalletSnapshot>) {
  snapshot = { ...snapshot, ...patch };
  listeners.forEach((l) => l(snapshot));
}

function subscribe(listener: (s: WalletSnapshot) => void) {
  listeners.add(listener);
  listener(snapshot);
  return () => { listeners.delete(listener); };
}

// ─── WalletConnect client (lazy, cached) ─────────────────────────────────

async function getClient() {
  if (client) return client;
  if (clientPromise) return clientPromise;

  if (!PROJECT_ID) {
    throw new Error(
      'NEXT_PUBLIC_WALLETCONNECT_PROJECT_ID is not set. ' +
      'Get a free project ID from Reown Cloud and add it to frontend/.env.local.',
    );
  }

  clientPromise = (async () => {
    // @walletconnect/sign-client is pure browser JS — safe to import statically.
    const { SignClient } = await import('@walletconnect/sign-client');
    client = await SignClient.init({
      projectId: PROJECT_ID,
      metadata: {
        name: 'Hedera Agent Commerce Kit',
        description: 'Pay-per-request infrastructure for AI agents on Hedera',
        url: typeof window !== 'undefined' ? window.location.origin : 'https://hack.hedera.dev',
        icons: [
          typeof window !== 'undefined'
            ? `${window.location.origin}/icon.png`
            : 'https://hack.hedera.dev/icon.png',
        ],
      },
    });

    // Restore existing session if any
    const sessions = client.session.getAll();
    if (sessions.length > 0) {
      session = sessions[sessions.length - 1];
      const accountId = extractAccountId(session);
      if (accountId) emit({ isConnected: true, accountId });
    }

    client.on('session_delete', () => {
      session = null;
      emit({ isConnected: false, accountId: null });
    });

    return client;
  })();

  return clientPromise;
}

// ─── Helpers ─────────────────────────────────────────────────────────────

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function extractAccountId(sess: any): string | null {
  try {
    const accounts: string[] = Object.values(sess?.namespaces ?? {})
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      .flatMap((ns: any) => ns?.accounts ?? [])
      .filter((v): v is string => typeof v === 'string');
    if (accounts.length === 0) return null;
    // Format: "hedera:testnet:0.0.XXXXX"
    const parts = accounts[0].split(':');
    return parts[parts.length - 1] || null;
  } catch {
    return null;
  }
}

// ─── Public hook ─────────────────────────────────────────────────────────

export function useWalletConnect(): UseWalletConnectReturn {
  const [state, setState] = useState<WalletSnapshot>(snapshot);
  useEffect(() => subscribe(setState), []);

  const connect = useCallback(async (): Promise<void> => {
    emit({ isPending: true, error: null });
    try {
      const c = await getClient();

      const { uri, approval } = await c.connect({
        optionalNamespaces: {
          hedera: {
            chains: [CHAIN_ID],
            methods: ['hedera_signAndExecuteTransaction', 'hedera_executeTransaction'],
            events: ['chainChanged', 'accountsChanged'],
          },
        },
      });

      // Open the WalletConnect QR modal
      if (uri) {
        const { WalletConnectModal } = await import('@walletconnect/modal');
        const modal = new WalletConnectModal({ projectId: PROJECT_ID });
        modal.openModal({ uri });

        session = await approval();
        modal.closeModal();
      } else {
        session = await approval();
      }

      const accountId = extractAccountId(session);
      if (!accountId) throw new Error('No Hedera account returned from wallet.');

      emit({ isConnected: true, accountId, error: null });
    } catch (err) {
      const message = err instanceof Error ? err.message : 'WalletConnect pairing failed.';
      emit({ error: message });
      throw err instanceof Error ? err : new Error(message);
    } finally {
      emit({ isPending: false });
    }
  }, []);

  const disconnect = useCallback(async (): Promise<void> => {
    try {
      if (client && session) {
        await client.disconnect({
          topic: session.topic,
          reason: { code: 6000, message: 'User disconnected.' },
        });
      }
    } catch {
      // ignore
    }
    session = null;
    emit({ isConnected: false, accountId: null, error: null });
  }, []);

  const sendHbar = useCallback(
    async ({ recipientAccountId, amount, memo = 'hack-payment' }: SendHbarParams): Promise<string> => {
      const activeAccount = snapshot.accountId;
      if (!snapshot.isConnected || !activeAccount || !session) {
        throw new Error('Wallet is not connected.');
      }

      emit({ isPending: true, error: null });
      try {
        const c = await getClient();

        // Build the transaction server-side (Node.js / @hashgraph/sdk)
        const res = await fetch('/api/wallet/build-tx', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            senderAccountId: activeAccount,
            recipientAccountId,
            amount,
            memo,
          }),
        });

        if (!res.ok) {
          const err = await res.json().catch(() => ({}));
          throw new Error(err.error ?? `build-tx failed (${res.status})`);
        }

        const { transactionBytes } = await res.json() as { transactionBytes: string };

        // Send to wallet for signing via HIP-820 JSON-RPC
        const result = await c.request({
          topic: session.topic,
          chainId: CHAIN_ID,
          request: {
            method: 'hedera_signAndExecuteTransaction',
            params: { transactionList: transactionBytes },
          },
        });

        // Extract transaction ID from wallet response
        const txId: string =
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          (result as any)?.transactionId ??
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          (result as any)?.response?.transactionId ??
          '';

        if (!txId) {
          throw new Error(
            'Wallet submitted the transaction but did not return a transaction ID.',
          );
        }

        return txId;
      } catch (err) {
        const message = err instanceof Error ? err.message : 'HBAR payment failed.';
        emit({ error: message });
        throw err instanceof Error ? err : new Error(message);
      } finally {
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
