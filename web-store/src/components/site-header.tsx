import { Phone, Search, SlidersHorizontal } from "lucide-react";
import Link from "next/link";
import { CartLink } from "@/components/cart-link";
import { phoneHref, storefront } from "@/lib/storefront";

export function SiteHeader() {
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
          <Link
            href="/catalog"
            className="inline-flex h-10 items-center gap-2 rounded-lg px-3 text-sm font-medium text-zinc-700 hover:bg-zinc-100"
          >
            <SlidersHorizontal className="size-4" aria-hidden />
            <span className="hidden sm:inline">Каталог</span>
          </Link>
          <CartLink />
        </nav>
      </div>
    </header>
  );
}
