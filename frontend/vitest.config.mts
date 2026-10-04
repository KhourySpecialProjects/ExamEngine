import react from "@vitejs/plugin-react";
import tsconfigPaths from "vite-tsconfig-paths";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [tsconfigPaths(), react()],
  test: {
    environment: "jsdom",
    // Table tests driving Radix Select take ~1 s alone but over 5 s (the
    // default) when every worker runs at once on a busy machine.
    testTimeout: 15_000,
    exclude: [
      "**/node_modules/**",
      "**/dist/**",
      "**/e2e/**", // Exclude E2E folder
      "**/.{idea,git,cache,output,temp}/**",
    ],
    setupFiles: "./src/test/setup.ts",
    coverage: {
      provider: "v8",
      reporter: ["text", "json", "html"],
      exclude: ["node_modules/", "src/test/"],
    },
  },
});
