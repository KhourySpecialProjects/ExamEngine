/**
 * Integrity checks for the user docs in `content/docs/` (Fumadocs).
 *
 * Mirrors how fumadocs-core builds the sidebar from `meta.json` files, so a renamed or deleted
 * page, a page missing from the sidebar, or a missing image fails the suite instead of showing
 * up as a broken page.
 */
import { existsSync, readdirSync, readFileSync, statSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const FRONTEND = path.resolve(
  path.dirname(fileURLToPath(import.meta.url)),
  "../../..",
);
const DOCS = path.join(FRONTEND, "content/docs");
const PUBLIC = path.join(FRONTEND, "public");

// The same item syntax fumadocs-core's page-tree builder accepts in `pages`.
const SEPARATOR = /^---(?:\[[^\]]+])?.+---$|^---$/;
const LINK = /^(?:\[[^\]]+])?\[[^\]]+]\([^)]+\)$/;

const rel = (file: string) => path.relative(DOCS, file);

function isDir(p: string) {
  return existsSync(p) && statSync(p).isDirectory();
}

function allMdx(dir: string): string[] {
  return readdirSync(dir, { withFileTypes: true }).flatMap((entry) => {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) return allMdx(full);
    return entry.name.endsWith(".mdx") ? [full] : [];
  });
}

/**
 * Walks the sidebar from the root `meta.json`. Returns the pages it reaches (including pages
 * excluded with `!name`, which are deliberate) and every entry that points at nothing.
 */
function walkSidebar() {
  const reached = new Set<string>();
  const broken: string[] = [];

  function visitFolder(dir: string, isRoot: boolean) {
    const metaFile = path.join(dir, "meta.json");
    const meta: { pages?: string[] } | undefined = existsSync(metaFile)
      ? JSON.parse(readFileSync(metaFile, "utf8"))
      : undefined;
    const index = path.join(dir, "index.mdx");
    // A section folder's index.mdx becomes the folder's own page even when unlisted.
    if (!isRoot && existsSync(index)) reached.add(index);
    if (!meta?.pages) {
      visitRest(dir);
      return;
    }
    let rest = false;
    for (const item of meta.pages) {
      if (SEPARATOR.test(item) || LINK.test(item)) continue;
      if (item === "..." || item === "z...a") {
        rest = true;
        continue;
      }
      const where = `${rel(path.join(dir, "meta.json"))}: "${item}"`;
      const spread = item.startsWith("...");
      const excluded = item.startsWith("!");
      const name = spread ? item.slice(3) : excluded ? item.slice(1) : item;
      const target = path.join(dir, name);
      if (spread) {
        if (!isDir(target)) broken.push(`${where}: no folder ${rel(target)}/`);
        else if (!existsSync(path.join(target, "meta.json")))
          broken.push(`${where}: ${rel(target)}/ has no meta.json`);
        else visitFolder(target, false);
      } else if (existsSync(`${target}.mdx`)) {
        reached.add(`${target}.mdx`);
      } else if (isDir(target) && !excluded) {
        visitFolder(target, false);
      } else if (!isDir(target)) {
        broken.push(`${where}: no page ${rel(target)}.mdx`);
      }
    }
    if (rest) visitRest(dir);
  }

  // `...` (or no `pages`): every page and folder not listed elsewhere.
  function visitRest(dir: string) {
    for (const entry of readdirSync(dir, { withFileTypes: true })) {
      const full = path.join(dir, entry.name);
      if (entry.isDirectory()) visitFolder(full, false);
      else if (entry.name.endsWith(".mdx")) reached.add(full);
    }
  }

  visitFolder(DOCS, true);
  return { reached, broken };
}

/** Image paths referenced by an MDX file, as written (code blocks ignored). */
function imageRefs(source: string): string[] {
  const text = source.replace(/^(```|~~~)[\s\S]*?^\1/gm, "");
  const markdown = [...text.matchAll(/!\[[^\]]*]\(\s*<?([^)\s>]+)>?/g)];
  const html = [...text.matchAll(/<img\b[^>]*\bsrc=["']([^"']+)["']/g)];
  return [...markdown, ...html]
    .map((m) => m[1])
    .filter(
      (src) => !/^(?:[a-z]+:)?\/\//i.test(src) && !src.startsWith("data:"),
    );
}

describe("docs content", () => {
  const pages = allMdx(DOCS);

  it("finds the docs pages", () => {
    expect(pages).toContain(path.join(DOCS, "index.mdx"));
  });

  it("every sidebar entry resolves to a page or folder", () => {
    expect(walkSidebar().broken).toEqual([]);
  });

  it("every page is listed in a sidebar meta.json", () => {
    const { reached } = walkSidebar();
    const orphans = pages.filter((p) => !reached.has(p)).map(rel);
    expect(orphans).toEqual([]);
  });

  it("every image a page references exists", () => {
    const missing = pages.flatMap((page) =>
      imageRefs(readFileSync(page, "utf8"))
        .filter((src) => {
          const file = src.startsWith("/")
            ? path.join(PUBLIC, src)
            : path.resolve(path.dirname(page), src.split(/[?#]/)[0]);
          return !existsSync(file);
        })
        .map((src) => `${rel(page)}: ${src}`),
    );
    expect(missing).toEqual([]);
  });
});
