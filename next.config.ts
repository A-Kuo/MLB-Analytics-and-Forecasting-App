import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  /* config options here */
  // Local-dev-only: `vercel.json` handles /api/* -> the Python function in
  // an actual Vercel deploy, but plain `next dev` has no equivalent, so
  // route to a locally-running `uvicorn macroservice.api:app` instead.
  // Skipped in production builds so this never risks shipping.
  async rewrites() {
    if (process.env.NODE_ENV === "production") return [];
    return [{ source: "/api/:path*", destination: "http://127.0.0.1:8000/:path*" }];
  },
};

export default nextConfig;
