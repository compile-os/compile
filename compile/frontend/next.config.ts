import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone", // Required for Docker deployment
  experimental: {
    // Enable server actions
  },
};

export default nextConfig;
