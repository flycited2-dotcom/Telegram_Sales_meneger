import type { Product, ProductImage } from "@prisma/client";
import { Search } from "lucide-react";
import Link from "next/link";
import { CatalogGrid } from "@/components/catalog-grid";
import type { CategoryTreeItem } from "@/lib/catalog-tree";

function hasActiveCategory(category: CategoryTreeItem, currentCategorySlug?: string): boolean {
  return category.slug === currentCategorySlug || category.children.some((child) => hasActiveCategory(child, currentCategorySlug));
}

function CategoryBranch({
  category,
  currentCategorySlug,
  level = 0,
}: {
  category: CategoryTreeItem;
  currentCategorySlug?: string;
  level?: number;
}) {
  const active = category.slug === currentCategorySlug;
  const expanded = currentCategorySlug ? hasActiveCategory(category, currentCategorySlug) : false;

  return (
    <div>
      <Link
        href={`/catalog/${category.slug}`}
        aria-current={active ? "page" : undefined}
        className={[
          "flex items-center justify-between gap-3 rounded-md py-2 pr-2 text-sm font-medium hover:bg-stone-100",
          active ? "bg-teal-50 text-teal-900" : "text-zinc-700",
        ].join(" ")}
        style={{ paddingLeft: `${8 + level * 14}px` }}
      >
        <span className="min-w-0 truncate">{category.name}</span>
        <span className="shrink-0 rounded-full bg-zinc-100 px-2 py-0.5 text-xs text-zinc-500">
          {category.productCount.toLocaleString("ru-RU")}
        </span>
      </Link>
      {expanded && category.children.length ? (
        <div className="mt-1 space-y-1">
          {category.children.map((child) => (
            <CategoryBranch key={child.id} category={child} currentCategorySlug={currentCategorySlug} level={level + 1} />
          ))}
        </div>
      ) : null}
    </div>
  );
}

export function CatalogView({
  title,
  products,
  total,
  page,
  perPage,
  categories,
  brands,
  currentCategorySlug,
  currentQuery,
  currentBrand,
  onlyAvailable,
  basePath = "/catalog",
  error,
}: {
  title: string;
  products: Array<Product & { images?: ProductImage[] }>;
  total: number;
  page: number;
  perPage: number;
  categories: CategoryTreeItem[];
  brands: string[];
  currentCategorySlug?: string;
  currentQuery?: string;
  currentBrand?: string;
  onlyAvailable?: boolean;
  basePath?: string;
  error?: string;
}) {
  const totalPages = Math.max(Math.ceil(total / perPage), 1);
  const pageHref = (nextPage: number) => {
    const params = new URLSearchParams();
    if (currentQuery) params.set("q", currentQuery);
    if (currentBrand) params.set("brand", currentBrand);
    if (onlyAvailable) params.set("available", "1");
    if (nextPage > 1) params.set("page", String(nextPage));
    const query = params.toString();
    return query ? `${basePath}?${query}` : basePath;
  };

  return (
    <div className="mx-auto grid max-w-7xl gap-8 px-4 py-8 sm:px-6 lg:grid-cols-[280px_1fr] lg:px-8">
      <aside className="space-y-6">
        <div className="rounded-lg border border-zinc-200 bg-white p-4">
          <p className="text-sm font-bold uppercase tracking-wide text-zinc-500">Поиск</p>
          <form action={basePath} className="mt-3 flex items-center rounded-lg border border-zinc-200 bg-zinc-50 px-3 py-2">
            <Search className="mr-2 size-4 text-zinc-400" aria-hidden />
            <input
              name="q"
              defaultValue={currentQuery}
              placeholder="Название, SKU, бренд"
              className="min-w-0 flex-1 bg-transparent text-sm"
            />
          </form>
        </div>

        <div className="rounded-lg border border-zinc-200 bg-white p-4">
          <p className="text-sm font-bold uppercase tracking-wide text-zinc-500">Категории</p>
          <div className="mt-3 max-h-[70vh] space-y-1 overflow-auto pr-1">
            <Link
              href="/catalog"
              aria-current={!currentCategorySlug ? "page" : undefined}
              className={[
                "flex items-center justify-between rounded-md px-2 py-2 text-sm font-medium hover:bg-stone-100",
                !currentCategorySlug ? "bg-teal-50 text-teal-900" : "text-zinc-700",
              ].join(" ")}
            >
              <span>Все товары</span>
              <span className="rounded-full bg-zinc-100 px-2 py-0.5 text-xs text-zinc-500">
                {categories.reduce((sum, category) => sum + category.productCount, 0).toLocaleString("ru-RU")}
              </span>
            </Link>
            {categories.map((category) => (
              <CategoryBranch key={category.id} category={category} currentCategorySlug={currentCategorySlug} />
            ))}
          </div>
        </div>

        <form action={basePath} className="rounded-lg border border-zinc-200 bg-white p-4">
          <p className="text-sm font-bold uppercase tracking-wide text-zinc-500">Фильтры</p>
          {currentQuery ? <input type="hidden" name="q" value={currentQuery} /> : null}
          <label className="mt-4 block text-sm font-medium text-zinc-700">
            Бренд
            <select name="brand" defaultValue={currentBrand ?? ""} className="mt-2 h-10 w-full rounded-lg border border-zinc-200 bg-white px-3 text-sm">
              <option value="">Любой</option>
              {brands.map((brand) => (
                <option key={brand} value={brand}>
                  {brand}
                </option>
              ))}
            </select>
          </label>
          <label className="mt-4 flex items-center gap-2 text-sm text-zinc-700">
            <input name="available" value="1" type="checkbox" defaultChecked={onlyAvailable} className="size-4 accent-teal-700" />
            Только в наличии
          </label>
          <button className="mt-4 h-10 w-full rounded-lg bg-zinc-950 text-sm font-semibold text-white hover:bg-teal-800">
            Применить
          </button>
        </form>
      </aside>

      <section className="min-w-0">
        <div className="mb-6 flex flex-wrap items-end justify-between gap-3">
          <div>
            <p className="text-sm font-semibold uppercase tracking-wide text-teal-700">Каталог</p>
            <h1 className="mt-2 text-3xl font-black tracking-normal text-zinc-950">{title}</h1>
            <p className="mt-2 text-sm text-zinc-500">Найдено товаров: {total}</p>
          </div>
        </div>

        {error ? (
          <div className="mb-6 rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">{error}</div>
        ) : null}

        <CatalogGrid products={products} />

        {totalPages > 1 ? (
          <div className="mt-8 flex items-center justify-center gap-2">
            {page > 1 ? (
              <Link href={pageHref(page - 1)} className="rounded-lg border border-zinc-200 bg-white px-4 py-2 text-sm font-semibold hover:bg-zinc-50">
                Назад
              </Link>
            ) : null}
            <span className="text-sm text-zinc-500">
              {page} / {totalPages}
            </span>
            {page < totalPages ? (
              <Link href={pageHref(page + 1)} className="rounded-lg border border-zinc-200 bg-white px-4 py-2 text-sm font-semibold hover:bg-zinc-50">
                Дальше
              </Link>
            ) : null}
          </div>
        ) : null}
      </section>
    </div>
  );
}
