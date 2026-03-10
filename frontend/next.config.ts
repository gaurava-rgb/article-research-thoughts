import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async rewrites() {
    // In development: proxy /api/* to FastAPI (localhost:8000).
    // In production on Vercel: vercel.json handles this routing instead.
    // This file is only active during `next dev`.
    return process.env.NODE_ENV === "development"
      ? [
          {
            source: "/api/:path*",
            destination: "http://localhost:8000/api/:path*",
          },
        ]
      : [];
  },
};

export default nextConfig;
