/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,

  // Keep the heavy Hedera SDK + wallet-connect packages out of the SSR
  // server bundle. They are Node.js-only packages that cannot run in the
  // server renderer.
  serverExternalPackages: [
    "@hashgraph/sdk",
    "@hashgraph/proto",
    "@hashgraph/hedera-wallet-connect",
    "@hiero-ledger/sdk",
    "@hiero-ledger/proto",
    "@reown/walletkit",
    "@walletconnect/core",
    "@walletconnect/modal",
    "@walletconnect/sign-client",
    "@walletconnect/web3wallet",
    "@walletconnect/types",
    "@walletconnect/utils",
    "@walletconnect/universal-provider",
  ],

  transpilePackages: [],

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

