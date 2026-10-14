import { defineConfig, defineDocs } from "fumadocs-mdx/config";

// User documentation served at /docs. Pages are MDX files in content/docs;
// each folder's meta.json sets its sidebar title and page order.
export const docs = defineDocs({ dir: "content/docs" });

export default defineConfig();
