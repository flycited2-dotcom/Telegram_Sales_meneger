import { CatalogView } from "@/app/catalog/catalog-view";
import { getCatalogPage } from "@/lib/catalog";

export const dynamic = "force-dynamic";

type Props = {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
};

function first(value: string | string[] | undefined): string | undefined {
  return Array.isArray(value) ? value[0] : value;
}

export default async function SearchPage({ searchParams }: Props) {
  const params = await searchParams;
  const query = first(params.q) ?? "";
  const data = await getCatalogPage({ query });

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
    />
  );
}
