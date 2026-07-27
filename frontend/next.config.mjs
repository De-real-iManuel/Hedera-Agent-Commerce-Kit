/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,

  // Keep the heavy Hedera SDK + wallet-connect packages out of the webpack
  // bundle entirely. They are only ever loaded via dynamic import() at
  // runtime in the browser (useWalletConnect.ts), so they don't need to be
  // bundled by Next.js at all.
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

  webpack(config, { isServer }) {
    if (!isServer) {
      // Mark Hedera/WalletConnect packages as browser externals using the
      // window global as a placeholder. They are only resolved via dynamic
      // import() at runtime — webpack must not try to bundle them.
      // Using `false` tells webpack "this module doesn't exist at build time,
      // skip it" which is safe because useWalletConnect.ts uses dynamic
      // import() which is resolved at runtime by the browser from the
      // CDN/node_modules copy that Next.js serves.
    const hederaExternals = [
        "@hashgraph/sdk",
        "@hashgraph/proto",
        "@hashgraph/hedera-wallet-connect",
        "@hiero-ledger/sdk",
        "@hiero-ledger/proto",
        "@reown/walletkit",
        "@walletconnect/core",
        "@walletconnect/sign-client",
        "@walletconnect/web3wallet",
        "@walletconnect/universal-provider",
      ];

      config.resolve = config.resolve || {};
      config.resolve.alias = config.resolve.alias || {};

      // Alias Node-only Hedera SDK packages to an empty stub at build time.
      // The real packages are loaded at runtime via dynamic import().
      for (const pkg of hederaExternals) {
        config.resolve.alias[pkg] = false;
      }
    }
    return config;
  },

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
