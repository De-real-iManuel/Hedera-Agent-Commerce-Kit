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
      // These packages are loaded via dynamic import() in the browser and
      // must NOT be bundled by webpack — they contain native/Node.js deps
      // (protobufjs, grpc, etc.) that don't work in the browser bundle.
      // Using a function-based external to remain compatible with Next 15.x
      config.externals = [
        ...(Array.isArray(config.externals) ? config.externals : [config.externals].filter(Boolean)),
        function ({ request }, callback) {
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
          if (hederaExternals.some((pkg) => request === pkg || request?.startsWith(pkg + "/"))) {
            return callback(null, "commonjs " + request);
          }
          callback();
        },
      ];
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
