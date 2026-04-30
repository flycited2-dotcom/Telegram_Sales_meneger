import type { Metadata } from "next";
import { CatalogView } from "@/app/catalog/catalog-view";
import { getCatalogPage } from "@/lib/catalog";

export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "Поиск товаров",
  description: "Поиск бытовой техники, электроники, климатического оборудования и товаров для дома в БытТехОпт.",
};

type Props = {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
};

function first(value: string | string[] | undefined): string | undefined {
  return Array.isArray(value) ? value[0] : value;
}

export default async function SearchPage({ searchParams }: Props) {
  const params = await searchParams;
  const query = first(params.q) ?? "";
  const brand = first(params.brand);
  const page = Number(first(params.page) ?? 1);
  const onlyAvailable = first(params.available) === "1";
  const data = await getCatalogPage({ query, brand, available: onlyAvailable, page });

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
      currentBrand={brand}
      onlyAvailable={onlyAvailable}
      basePath="/search"
    />
  );
}
