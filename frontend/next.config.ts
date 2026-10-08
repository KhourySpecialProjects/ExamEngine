import { createMDX } from "fumadocs-mdx/next";
import type { NextConfig } from "next";

const nextConfig: NextConfig = {};

// Compiles the docs content (content/docs) into .source/ for /docs.
const withMDX = createMDX();

export default withMDX(nextConfig);
