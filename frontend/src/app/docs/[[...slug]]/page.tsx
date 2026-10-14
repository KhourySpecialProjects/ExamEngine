import defaultMdxComponents from "fumadocs-ui/mdx";
import {
  DocsBody,
  DocsDescription,
  DocsPage,
  DocsTitle,
} from "fumadocs-ui/page";
import type { Metadata } from "next";
import { notFound } from "next/navigation";
import type { ComponentProps } from "react";
import { source } from "@/lib/docs/source";

const DefaultImage = defaultMdxComponents.img;

/**
 * Docs images are screenshots taken at twice the screen's pixel density
 * (npm run docs:screenshots), so show them at half their pixel size: the size
 * they had on screen, sharp on high-density displays.
 */
function Screenshot(props: ComponentProps<typeof DefaultImage>) {
  // A local image arrives as a static import: { src, width, height }.
  const src = props.src as unknown as { width?: number; height?: number };
  if (typeof src !== "object" || !src.width || !src.height) {
    return <DefaultImage {...props} />;
  }
  return (
    <DefaultImage {...props} width={src.width / 2} height={src.height / 2} />
  );
}

type Props = { params: Promise<{ slug?: string[] }> };

export default async function Page({ params }: Props) {
  const page = source.getPage((await params).slug);
  if (!page) notFound();

  const MDX = page.data.body;
  return (
    <DocsPage toc={page.data.toc} full={page.data.full}>
      <DocsTitle>{page.data.title}</DocsTitle>
      <DocsDescription>{page.data.description}</DocsDescription>
      <DocsBody>
        <MDX components={{ ...defaultMdxComponents, img: Screenshot }} />
      </DocsBody>
    </DocsPage>
  );
}

export function generateStaticParams() {
  return source.generateParams();
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const page = source.getPage((await params).slug);
  if (!page) notFound();
  return { title: page.data.title, description: page.data.description };
}
