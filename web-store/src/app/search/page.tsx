import type { Metadata } from "next";
import { CatalogView } from "@/app/catalog/catalog-view";
import { getCatalogPage } from "@/lib/catalog";
import { parseCatalogSearchParams } from "@/lib/catalog-query";

export const revalidate = 300;

export const metadata: Metadata = {
  title: "Поиск товаров",
  description: "Поиск бытовой техники, электроники, климатического оборудования и товаров для дома в БытТехОпт.",
};

type Props = {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
};

export default async function SearchPage({ searchParams }: Props) {
  const filters = parseCatalogSearchParams(await searchParams);
  const query = filters.query ?? "";
  let data;
  try {
    data = await getCatalogPage({
      query,
      brand: filters.brand,
      available: filters.onlyAvailable,
      minPrice: filters.minPrice,
      maxPrice: filters.maxPrice,
      page: filters.page,
    });
  } catch {
    return (
      <CatalogView
        title={query ? `Поиск: ${query}` : "Поиск товаров"}
        products={[]}
        total={0}
        page={1}
        perPage={24}
        categories={[]}
        brands={[]}
        currentQuery={query}
        currentBrand={filters.brand}
        onlyAvailable={filters.onlyAvailable}
        minPrice={filters.minPrice}
        maxPrice={filters.maxPrice}
        basePath="/search"
        error="Поиск временно недоступен. Позвоните нам, и менеджер поможет подобрать товар вручную."
      />
    );
  }

  return (
    <CatalogView
      title={query ? `Поиск: ${query}` : "Поиск товаров"}
      products={data.products}
      total={data.total}
      page={data.page}
      perPage={data.perPage}
      categories={data.categories}
      brands={data.brands}
      currentQuery={query}
      currentBrand={filters.brand}
      onlyAvailable={filters.onlyAvailable}
      minPrice={filters.minPrice}
      maxPrice={filters.maxPrice}
      basePath="/search"
    />
  );
}
