import { ArrowRight, Clock, Database, PackageCheck, Truck } from "lucide-react";
import Image from "next/image";
import Link from "next/link";
import { CatalogGrid } from "@/components/catalog-grid";
import { getHomeSnapshot } from "@/lib/catalog";

export const dynamic = "force-dynamic";

async function loadHome() {
  try {
    return await getHomeSnapshot();
  } catch {
    return { categories: [], products: [] };
  }
}

export default async function Home() {
  const { categories, products } = await loadHome();

  return (
    <>
      <section className="relative min-h-[620px] overflow-hidden bg-zinc-950 text-white">
        <Image
          src="/assets/hero-showroom.png"
          alt="Современная витрина бытовой техники и электроники"
          fill
          priority
          sizes="100vw"
          className="object-cover"
        />
        <div className="absolute inset-0 bg-[linear-gradient(90deg,rgba(9,9,11,0.88),rgba(9,9,11,0.58)_42%,rgba(9,9,11,0.1))]" />
        <div className="relative mx-auto flex min-h-[620px] max-w-7xl items-center px-4 pb-20 pt-16 sm:px-6 lg:px-8">
          <div className="max-w-2xl">
            <p className="text-sm font-semibold uppercase tracking-[0.18em] text-amber-300">Техника, электроника, товары для дома</p>
            <h1 className="mt-5 text-4xl font-black leading-tight tracking-normal sm:text-6xl">
              Интернет-магазин, который продает из локального B2B-каталога
            </h1>
            <p className="mt-6 max-w-xl text-lg leading-8 text-zinc-100">
              Каталог синхронизируется с I-T-P B2B, цены и остатки хранятся в PostgreSQL,
              а менеджер получает новый заказ сразу в Telegram.
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <Link href="/catalog" className="inline-flex h-12 items-center gap-2 rounded-lg bg-amber-400 px-5 text-sm font-bold text-zinc-950 hover:bg-amber-300">
                Открыть каталог
                <ArrowRight className="size-4" aria-hidden />
              </Link>
              <Link href="/admin/sync" className="inline-flex h-12 items-center rounded-lg border border-white/30 px-5 text-sm font-bold text-white hover:bg-white/10">
                Управление синхронизацией
              </Link>
            </div>
          </div>
        </div>
      </section>

      <section className="-mt-12 relative z-10 mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="grid gap-3 rounded-lg border border-zinc-200 bg-white p-3 shadow-lg md:grid-cols-4">
          {[
            ["Локальная база", "Страницы читают PostgreSQL, не API поставщика", Database],
            ["Актуальные остатки", "Символы I-T-P превращаются в понятные статусы", PackageCheck],
            ["Заказы под контроль", "Корзина пересчитывается на сервере", Clock],
            ["Готово к VPS", "Next.js, Prisma, cron/PM2 и Nginx", Truck],
          ].map(([title, text, Icon]) => (
            <div key={title as string} className="flex gap-3 rounded-md bg-stone-50 p-4">
              <Icon className="mt-1 size-5 shrink-0 text-teal-700" aria-hidden />
              <div>
                <p className="font-semibold text-zinc-950">{title as string}</p>
                <p className="mt-1 text-sm text-zinc-600">{text as string}</p>
              </div>
            </div>
          ))}
        </div>
      </section>

      <section className="mx-auto max-w-7xl px-4 py-16 sm:px-6 lg:px-8">
        <div className="mb-6 flex items-end justify-between gap-4">
          <div>
            <p className="text-sm font-semibold uppercase tracking-wide text-teal-700">Категории</p>
            <h2 className="mt-2 text-3xl font-black tracking-normal text-zinc-950">Быстрый вход в ассортимент</h2>
          </div>
          <Link href="/catalog" className="hidden text-sm font-semibold text-teal-800 hover:text-teal-950 sm:inline">
            Все товары
          </Link>
        </div>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {categories.length ? (
            categories.map((category) => (
              <Link key={category.id} href={`/catalog/${category.slug}`} className="rounded-lg border border-zinc-200 bg-white p-5 shadow-sm hover:border-teal-200 hover:shadow-md">
                <p className="text-lg font-bold text-zinc-950">{category.name}</p>
                <p className="mt-2 text-sm text-zinc-500">Открыть подборку</p>
              </Link>
            ))
          ) : (
            <div className="col-span-full rounded-lg border border-dashed border-zinc-300 bg-white p-8 text-zinc-600">
              Категории появятся после первой синхронизации с I-T-P.
            </div>
          )}
        </div>
      </section>

      <section className="mx-auto max-w-7xl px-4 pb-20 sm:px-6 lg:px-8">
        <div className="mb-6">
          <p className="text-sm font-semibold uppercase tracking-wide text-teal-700">В наличии</p>
          <h2 className="mt-2 text-3xl font-black tracking-normal text-zinc-950">Товары, готовые к заказу</h2>
        </div>
        <CatalogGrid products={products} />
      </section>
    </>
  );
}
