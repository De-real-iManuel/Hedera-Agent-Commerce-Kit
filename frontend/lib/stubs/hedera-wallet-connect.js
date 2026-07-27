/**
 * Build-time stub for @hashgraph/hedera-wallet-connect
 *
 * webpack alias in next.config.mjs points here at build time so the heavy
 * Node-only dependencies (@walletconnect/web3wallet, @hashgraph/proto, gRPC)
 * never enter the webpack bundle.
 *
 * useWalletConnect.ts loads everything via dynamic import() at runtime, so
 * the real package is resolved from node_modules in the browser — this stub
 * is only used to satisfy the static module graph during the build.
 */

// DAppConnector — mirrors the real constructor / method signatures
export class DAppConnector {
  constructor(_metadata, _network, _projectId, _methods, _events, _chains, _logLevel) {}
  async init()                         { return; }
  async openModal()                    { return { namespaces: {} }; }
  async disconnectAll()                { return; }
  async disconnect(_topic)             { return true; }
  async signAndExecuteTransaction(_p)  { return {}; }
  async executeTransaction(_p)         { return {}; }
  async signTransaction(_p)            { return {}; }
  get signers()                        { return []; }
}

// Enums
export const HederaJsonRpcMethod = {
  GetNodeAddresses:          "hedera_getNodeAddresses",
  ExecuteTransaction:        "hedera_executeTransaction",
  SignMessage:               "hedera_signMessage",
  SignAndExecuteQuery:       "hedera_signAndExecuteQuery",
  SignAndExecuteTransaction: "hedera_signAndExecuteTransaction",
  SignTransaction:           "hedera_signTransaction",
};

export const HederaSessionEvent = {
  ChainChanged:    "chainChanged",
  AccountsChanged: "accountsChanged",
};

export const HederaChainId = {
  Mainnet:    "hedera:mainnet",
  Testnet:    "hedera:testnet",
  Previewnet: "hedera:previewnet",
  Devnet:     "hedera:devnet",
};

// Utility used in sendHbar — returns empty string at build time
export function transactionToBase64String(_tx) {
  return "";
}
