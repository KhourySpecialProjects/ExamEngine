import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  /* config options here */
  output: "standalone",
  allowedDevOrigins: [
   'http://3.16.218.153/',
   'https://3.16.218.153/'
 ]
};

export default nextConfig;
