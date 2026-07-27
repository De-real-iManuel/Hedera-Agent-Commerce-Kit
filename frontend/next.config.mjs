/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,

  // @hashgraph/sdk is used exclusively in the Node.js API route
  // (app/api/wallet/build-tx/route.ts). Keeping it out of the client bundle
  // prevents webpack from trying to process its Node.js-only deps.
  serverExternalPackages: [
    "@hashgraph/sdk",
    "@hashgraph/proto",
    "@hiero-ledger/sdk",
    "@hiero-ledger/proto",
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
