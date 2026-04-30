import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { CatalogView } from "@/app/catalog/catalog-view";
import { getCatalogPage, getCategoryBySlug } from "@/lib/catalog";
import { parseCatalogSearchParams } from "@/lib/catalog-query";
import { storefront } from "@/lib/storefront";

export const revalidate = 300;

type Props = {
  params: Promise<{ slug: string }>;
  searchParams: Promise<Record<string, string | string[] | undefined>>;
};

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { slug } = await params;
  const category = await getCategoryBySlug(slug);

  if (!category) {
    return {
      title: "Раздел каталога",
    };
  }

  return {
    title: category.name,
    description: `${category.name} в интернет-магазине ${storefront.brand}. Доставка по региону: ${storefront.region}.`,
  };
}

export default async function CategoryPage({ params, searchParams }: Props) {
  const { slug } = await params;
  const filters = parseCatalogSearchParams(await searchParams);
  const data = await getCatalogPage({
    categorySlug: slug,
    query: filters.query,
    brand: filters.brand,
    available: filters.onlyAvailable,
    minPrice: filters.minPrice,
    maxPrice: filters.maxPrice,
    page: filters.page,
  });

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
      currentQuery={filters.query}
      currentBrand={filters.brand}
      onlyAvailable={filters.onlyAvailable}
      minPrice={filters.minPrice}
      maxPrice={filters.maxPrice}
      basePath={`/catalog/${data.category.slug}`}
    />
  );
}
