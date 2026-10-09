import { createMDX } from "fumadocs-mdx/next";
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // The FAQ moved into the docs.
  async redirects() {
    return [{ source: "/faq", destination: "/docs/faq", permanent: true }];
  },
};

// Compiles the docs content (content/docs) into .source/ for /docs.
const withMDX = createMDX();

export default withMDX(nextConfig);
