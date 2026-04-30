import { Phone, Search, SlidersHorizontal } from "lucide-react";
import Link from "next/link";
import { CartLink } from "@/components/cart-link";
import { getHeaderCategories } from "@/lib/catalog";
import { phoneHref, storefront } from "@/lib/storefront";

async function loadHeaderCategories() {
  try {
    return await getHeaderCategories();
  } catch {
    return [];
  }
}

export async function SiteHeader() {
  const categories = await loadHeaderCategories();

  return (
    <header className="sticky top-0 z-40 border-b border-zinc-200/80 bg-white/90 backdrop-blur">
      <div className="mx-auto flex max-w-7xl items-center gap-4 px-4 py-3 sm:px-6 lg:px-8">
        <Link href="/" className="flex min-w-fit items-center gap-3">
          <span className="flex size-10 items-center justify-center rounded-lg bg-zinc-950 text-sm font-bold text-white">
            БТО
          </span>
          <span className="leading-tight">
            <span className="block text-base font-bold tracking-tight">{storefront.brand}</span>
            <span className="block text-xs text-zinc-500">техника и товары под заказ</span>
          </span>
        </Link>

        <form action="/search" className="hidden min-w-0 flex-1 items-center rounded-lg border border-zinc-200 bg-zinc-50 px-3 py-2 md:flex">
          <Search className="mr-2 size-4 text-zinc-400" aria-hidden />
          <input
            name="q"
            type="search"
            placeholder="Поиск по названию, SKU или бренду"
            className="min-w-0 flex-1 bg-transparent text-sm text-zinc-900 placeholder:text-zinc-400"
          />
        </form>

        <nav className="ml-auto flex items-center gap-1 sm:gap-2">
          <a
            href={phoneHref(storefront.phones[0])}
            className="hidden h-10 items-center gap-2 rounded-lg px-3 text-sm font-semibold text-zinc-700 hover:bg-zinc-100 lg:inline-flex"
          >
            <Phone className="size-4" aria-hidden />
            {storefront.phones[0]}
          </a>
          <details className="group relative">
            <summary
              aria-label="Открыть каталог"
              className="inline-flex h-10 cursor-pointer list-none items-center gap-2 rounded-lg px-3 text-sm font-medium text-zinc-700 hover:bg-zinc-100 [&::-webkit-details-marker]:hidden"
            >
              <SlidersHorizontal className="size-4" aria-hidden />
              <span className="hidden sm:inline">Каталог</span>
            </summary>
            <div className="absolute right-0 top-full z-50 mt-2 hidden w-80 rounded-lg border border-zinc-200 bg-white p-3 shadow-xl group-open:block">
              <Link href="/catalog" className="block rounded-md px-3 py-2 text-sm font-bold text-zinc-950 hover:bg-stone-100">
                Весь каталог
              </Link>
              {categories.map((category) => (
                <Link key={category.id} href={`/catalog/${category.slug}`} className="block rounded-md px-3 py-2 text-sm font-medium text-zinc-700 hover:bg-stone-100">
                  {category.name}
                </Link>
              ))}
            </div>
          </details>
          <CartLink />
        </nav>
      </div>
    </header>
  );
}
