import { notFound } from "next/navigation";
import { CatalogView } from "@/app/catalog/catalog-view";
import { getCatalogPage } from "@/lib/catalog";

export const dynamic = "force-dynamic";

type Props = {
  params: Promise<{ slug: string }>;
  searchParams: Promise<Record<string, string | string[] | undefined>>;
};

function first(value: string | string[] | undefined): string | undefined {
  return Array.isArray(value) ? value[0] : value;
}

export default async function CategoryPage({ params, searchParams }: Props) {
  const { slug } = await params;
  const queryParams = await searchParams;
  const page = Number(first(queryParams.page) ?? 1);
  const data = await getCatalogPage({ categorySlug: slug, page });

  if (!data.category) {
    notFound();
  }

  return (
    <CatalogView
      title={data.category.name}
      products={data.products}
      total={data.total}
      page={data.page}
      perPage={data.perPage}
      categories={data.categories}
      brands={data.brands}
    />
  );
}
