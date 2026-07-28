import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,

  // Keep heavy Hedera/Node.js packages out of the SSR server bundle.
  // On the server, @hashgraph/sdk is only used in app/api/wallet/build-tx
  // which Next.js handles as a server route (not SSR rendered).
  serverExternalPackages: [
    "@hashgraph/sdk",
    "@hashgraph/proto",
    "@hiero-ledger/sdk",
    "@hiero-ledger/proto",
  ],

  transpilePackages: [
    "@hashgraph/hedera-wallet-connect",
    "@walletconnect/core",
    "@walletconnect/sign-client",
  ],

  webpack(config, { isServer }) {
    if (!isServer) {
      // In the browser bundle, alias @hashgraph/sdk and @hashgraph/proto to
      // lightweight stubs. DAppConnector only needs LedgerId from the SDK;
      // all actual transaction building happens in /api/wallet/build-tx.
      const stubPath = path.resolve(__dirname, 'lib/hedera-stubs.js');
      config.resolve = config.resolve || {};
      config.resolve.alias = {
        ...(config.resolve.alias || {}),
        '@hashgraph/sdk': stubPath,
        '@hashgraph/proto': stubPath,
        '@hiero-ledger/sdk': stubPath,
        '@hiero-ledger/proto': stubPath,
        // protobufjs is pulled in by @hashgraph/proto — stub it out too
        'protobufjs/minimal': stubPath,
        'protobufjs/minimal.js': stubPath,
        'protobufjs': stubPath,
      };
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
