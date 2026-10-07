import type { NextConfig } from "next";
const nextConfig: NextConfig = {
  transpilePackages: ["@careerlens/api-client"],
  poweredByHeader: false,
};
export default nextConfig;
