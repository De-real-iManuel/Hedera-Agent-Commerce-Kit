import { notFound } from "next/navigation";
import { DOC_PAGES } from "@/content/docs";
import { MarkdownRenderer, ComingSoonBlock } from "@/components/ui/MarkdownRenderer";

export default async function DocsPage({
  params,
}: {
  params: Promise<{ slug?: string[] }>;
}) {
  const { slug } = await params;
  const key = slug?.[0] ?? "installation";
  const page = DOC_PAGES[key];
  if (!page) notFound();

  if (page.status === "coming-soon") {
    return (
      <div>
        <div className="text-xs uppercase tracking-widest text-purple">{page.section}</div>
        <h1 className="text-3xl font-bold tracking-tight mt-1 mb-6">{page.title}</h1>
        <ComingSoonBlock />
      </div>
    );
  }

  return (
    <div>
      <div className="text-xs uppercase tracking-widest text-purple">{page.section}</div>
      <MarkdownRenderer content={page.content} />
    </div>
  );
}
