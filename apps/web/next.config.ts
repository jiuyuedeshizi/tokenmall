import type { NextConfig } from "next";

const internalApiProxyTarget =
  process.env.NODE_ENV === "production"
    ? "http://api:8000"
    : (process.env.INTERNAL_API_PROXY_TARGET ?? "http://127.0.0.1:8000");

const nextConfig: NextConfig = {
  reactCompiler: true,
  allowedDevOrigins: ["127.0.0.1", "localhost", "49.232.143.230"],
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${internalApiProxyTarget}/:path*`,
      },
    ];
  },
};

export default nextConfig;
