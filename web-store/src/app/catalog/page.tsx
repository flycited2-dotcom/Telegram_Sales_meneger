import type { Metadata } from "next";
import { CatalogView } from "@/app/catalog/catalog-view";
import { getCatalogPage } from "@/lib/catalog";
import { parseCatalogSearchParams } from "@/lib/catalog-query";

export const revalidate = 300;

export const metadata: Metadata = {
  title: "Каталог техники и товаров для дома",
  description:
    "Каталог бытовой техники, электроники, климатического оборудования и товаров для дома с доставкой по Крыму, Херсонской и Запорожской областям.",
};

type Props = {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
};

export default async function CatalogPage({ searchParams }: Props) {
  const filters = parseCatalogSearchParams(await searchParams);

  let data;
  try {
    data = await getCatalogPage({
      query: filters.query,
      brand: filters.brand,
      available: filters.onlyAvailable,
      withPhoto: filters.withPhoto,
      minPrice: filters.minPrice,
      maxPrice: filters.maxPrice,
      page: filters.page,
      sort: filters.sort,
    });
  } catch {
    return (
      <CatalogView
        title="Каталог товаров"
        products={[]}
        total={0}
        page={1}
        perPage={24}
        categories={[]}
        brands={[]}
        error="Каталог временно недоступен. Позвоните нам, и менеджер поможет подобрать товар вручную."
      />
    );
  }

  return (
    <CatalogView
      title="Каталог товаров"
      products={data.products}
      total={data.total}
      page={data.page}
      perPage={data.perPage}
      categories={data.categories}
      brands={data.brands}
      currentQuery={filters.query}
      currentBrand={filters.brand}
      onlyAvailable={filters.onlyAvailable}
      withPhoto={filters.withPhoto}
      minPrice={filters.minPrice}
      maxPrice={filters.maxPrice}
      sort={filters.sort}
    />
  );
}
