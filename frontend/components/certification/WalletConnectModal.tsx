"use client";
/**
 * WalletConnectModal
 * ------------------
 * Thin status shell around the official WalletConnect/Reown modal.
 *
 * When opened it immediately fires connect(), which calls
 * DAppConnector.openModal() — the real Reown QR + wallet-picker modal.
 * This component only renders:
 *   • a spinner while pairing is in progress
 *   • an error state with retry
 *   • a confirmation card once connected (account ID, network, disconnect)
 *
 * No custom wallet list, no fake UI — the actual wallet selection and QR
 * code are handled entirely by the official Reown/WalletConnect SDK.
 */

import { useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X, Loader2, AlertTriangle, Wallet, Unplug } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { useWalletConnect } from "@/hooks/useWalletConnect";

const NETWORK = process.env.NEXT_PUBLIC_HEDERA_NETWORK ?? "testnet";

interface Props {
  open: boolean;
  onClose: () => void;
  onConnected: (accountId: string) => void;
}

export function WalletConnectModal({ open, onClose, onConnected }: Props) {
  const { accountId, isConnected, isPending, error, connect, disconnect } =
    useWalletConnect();
  const network = NETWORK;

  // When the parent opens this modal, immediately trigger the official
  // Reown/WalletConnect pop-up. The user sees the real QR / wallet list there.
  useEffect(() => {
    if (open && !isConnected && !isPending) {
      void connect();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  if (!open) return null;

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4"
        onClick={onClose}
      >
        <motion.div
          initial={{ opacity: 0, scale: 0.98, y: 8 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.98, y: 8 }}
          transition={{ duration: 0.18 }}
          onClick={(e) => e.stopPropagation()}
          className="w-full max-w-sm rounded-xl border border-border bg-surface-1 shadow-2xl overflow-hidden"
        >
          {/* Header */}
          <div className="flex items-center justify-between border-b border-border px-5 py-3">
            <div className="flex items-center gap-2 text-sm font-semibold">
              <Wallet className="h-4 w-4 text-purple" />
              Connect Wallet
            </div>
            <button
              onClick={onClose}
              className="text-text-muted hover:text-text-primary transition-colors"
              aria-label="Close"
            >
              <X className="h-4 w-4" />
            </button>
          </div>

          {/* Body */}
          <div className="px-5 py-6 space-y-4">

            {/* Pairing in progress */}
            {!isConnected && !error && (
              <div className="flex items-start gap-3 text-sm text-text-secondary">
                <Loader2 className="h-4 w-4 animate-spin text-purple shrink-0 mt-0.5" />
                <span>
                  The WalletConnect modal is open — scan the QR code or select
                  your wallet (HashPack, Kabila, …) to pair.
                </span>
              </div>
            )}

            {/* Error + retry */}
            {!isConnected && error && (
              <div className="space-y-3">
                <div className="rounded-md border border-red/40 bg-red/5 px-3 py-2 flex gap-2 text-xs text-red">
                  <AlertTriangle className="h-4 w-4 mt-0.5 shrink-0" />
                  <span>{error}</span>
                </div>
                <Button className="w-full" onClick={() => void connect()} disabled={isPending}>
                  {isPending && <Loader2 className="h-4 w-4 animate-spin" />}
                  Retry
                </Button>
              </div>
            )}

            {/* Connected */}
            {isConnected && accountId && (
              <div className="space-y-4">
                <div className="rounded-lg border border-green/30 bg-green/5 p-4 space-y-3">
                  <div className="flex items-center gap-2">
                    <span className="h-2 w-2 rounded-full bg-green animate-pulse" />
                    <span className="text-xs uppercase tracking-widest text-green font-medium">
                      Connected
                    </span>
                  </div>

                  <div>
                    <div className="text-[10px] uppercase tracking-widest text-text-muted">
                      Hedera Account
                    </div>
                    <div className="mt-0.5 font-mono text-sm text-text-primary break-all">
                      {accountId}
                    </div>
                  </div>

                  <div>
                    <div className="text-[10px] uppercase tracking-widest text-text-muted">
                      Network
                    </div>
                    <div className="mt-0.5 font-mono text-xs text-text-secondary capitalize">
                      {network}
                    </div>
                  </div>
                </div>

                <div className="flex gap-2">
                  <Button
                    variant="ghost"
                    className="flex-1 gap-1.5"
                    onClick={() => void disconnect()}
                  >
                    <Unplug className="h-3.5 w-3.5" />
                    Disconnect
                  </Button>
                  <Button
                    className="flex-1"
                    onClick={() => onConnected(accountId)}
                  >
                    Continue →
                  </Button>
                </div>
              </div>
            )}
          </div>

          {/* Footer */}
          <div className="border-t border-border bg-surface-2 px-5 py-2 flex items-center justify-between">
            <span className="text-[10px] text-text-muted font-mono">
              WalletConnect v2 · HIP-820
            </span>
            <span className="text-[10px] text-text-muted font-mono capitalize">
              {network}
            </span>
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}
