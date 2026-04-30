import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { CatalogView } from "@/app/catalog/catalog-view";
import { getCatalogPage } from "@/lib/catalog";
import { storefront } from "@/lib/storefront";

export const dynamic = "force-dynamic";

type Props = {
  params: Promise<{ slug: string }>;
  searchParams: Promise<Record<string, string | string[] | undefined>>;
};

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { slug } = await params;
  const data = await getCatalogPage({ categorySlug: slug, page: 1 });

  if (!data.category) {
    return {
      title: "Раздел каталога",
    };
  }

  return {
    title: data.category.name,
    description: `${data.category.name} в интернет-магазине ${storefront.brand}. Доставка по региону: ${storefront.region}.`,
  };
}

function first(value: string | string[] | undefined): string | undefined {
  return Array.isArray(value) ? value[0] : value;
}

export default async function CategoryPage({ params, searchParams }: Props) {
  const { slug } = await params;
  const queryParams = await searchParams;
  const query = first(queryParams.q);
  const brand = first(queryParams.brand);
  const page = Number(first(queryParams.page) ?? 1);
  const onlyAvailable = first(queryParams.available) === "1";
  const data = await getCatalogPage({ categorySlug: slug, query, brand, available: onlyAvailable, page });

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
      currentCategorySlug={data.category.slug}
      currentQuery={query}
      currentBrand={brand}
      onlyAvailable={onlyAvailable}
      basePath={`/catalog/${data.category.slug}`}
    />
  );
}
