import { createFromSource } from "fumadocs-core/search/server";
import { source } from "@/lib/docs/source";

// The docs search index, built once at build time and searched in the
// browser. It lives under /docs because the proxy sends /api/ to the backend.
export const revalidate = false;

export const { staticGET: GET } = createFromSource(source);
