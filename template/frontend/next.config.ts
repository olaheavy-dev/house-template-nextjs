import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // The container ships the minimal standalone server (`node server.js`).
  output: "standalone",
  // No X-Powered-By: it tells a scanner which framework to try.
  poweredByHeader: false,
  // Next.js 16's caching model: pages are static unless they read request data or opt out.
  cacheComponents: true,
  partialPrefetching: true,
  // Tailwind v4 through Turbopack's loader, as create-next-app 16.4 sets it up.
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
};

export default nextConfig;
