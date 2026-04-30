import type { Metadata } from "next";
import { CatalogView } from "@/app/catalog/catalog-view";
import { getCatalogPage } from "@/lib/catalog";

export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "Каталог техники и товаров для дома",
  description:
    "Каталог бытовой техники, электроники, климатического оборудования и товаров для дома с доставкой по Крыму, Херсонской и Запорожской областям.",
};

type Props = {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
};

function first(value: string | string[] | undefined): string | undefined {
  return Array.isArray(value) ? value[0] : value;
}

export default async function CatalogPage({ searchParams }: Props) {
  const params = await searchParams;
  const query = first(params.q);
  const brand = first(params.brand);
  const page = Number(first(params.page) ?? 1);
  const onlyAvailable = first(params.available) === "1";

  let data;
  try {
    data = await getCatalogPage({
      query,
      brand,
      available: onlyAvailable,
      page,
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
      currentQuery={query}
      currentBrand={brand}
      onlyAvailable={onlyAvailable}
    />
  );
}
