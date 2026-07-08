import path from "node:path";
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Pin the workspace root to this app to avoid Next.js picking up an
  // unrelated lockfile higher in the filesystem.
  turbopack: {
    root: path.join(__dirname),
  },
};

export default nextConfig;
