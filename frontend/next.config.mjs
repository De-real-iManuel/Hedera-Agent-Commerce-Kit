/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,

  // Keep the heavy Hedera SDK out of the SSR/webpack server bundle entirely.
  // It's only used client-side via dynamic import() in useWalletConnect.ts.
  serverExternalPackages: [
    "@hashgraph/sdk",
    "@hashgraph/proto",
    "@hiero-ledger/sdk",
  ],

  // WalletConnect packages ship ESM that must be transpiled by Next for the browser.
  transpilePackages: [
    "@hashgraph/hedera-wallet-connect",
    "@reown/walletkit",
    "@walletconnect/core",
    "@walletconnect/modal",
    "@walletconnect/sign-client",
    "@walletconnect/web3wallet",
    "@walletconnect/types",
    "@walletconnect/utils",
  ],

  env: {
    NEXT_PUBLIC_API_BASE_URL:
      process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000",
  },

  async redirects() {
    return [
      { source: "/playground",        destination: "/api-explorer",        permanent: true },
      { source: "/playground/:path*", destination: "/api-explorer/:path*", permanent: true },
    ];
  },
};
export default nextConfig;
