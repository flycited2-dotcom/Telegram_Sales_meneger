import type { Metadata } from "next";
import { ArrowRight, CheckCircle2, Clock, CreditCard, MapPin, PackageCheck, Phone, Search, Truck } from "lucide-react";
import Image from "next/image";
import Link from "next/link";
import { CatalogGrid } from "@/components/catalog-grid";
import { getHomeSnapshot } from "@/lib/catalog";
import { phoneHref, storefront } from "@/lib/storefront";

export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "БытТехОпт - бытовая техника, электроника и товары для дома",
  description:
    "Закажите бытовую технику, электронику, климатическое оборудование и товары для дома с доставкой по Крыму, Херсонской и Запорожской областям. Оплата при получении.",
};

async function loadHome() {
  try {
    return await getHomeSnapshot();
  } catch {
    return { categories: [], products: [] };
  }
}

export default async function Home() {
  const { categories, products } = await loadHome();
  const featuredCategories = categories.slice(0, 10);

  return (
    <>
      <section className="relative overflow-hidden bg-zinc-950 text-white">
        <Image
          src="/assets/hero-showroom.png"
          alt="Витрина бытовой техники и электроники"
          fill
          priority
          sizes="100vw"
          className="pointer-events-none object-cover"
        />
        <div className="pointer-events-none absolute inset-0 bg-[linear-gradient(90deg,rgba(9,9,11,0.9),rgba(9,9,11,0.68)_48%,rgba(9,9,11,0.22))]" />
        <div className="relative mx-auto grid min-h-[620px] max-w-7xl items-center gap-8 px-4 pb-24 pt-16 sm:px-6 lg:grid-cols-[minmax(0,1fr)_420px] lg:px-8">
          <div className="max-w-3xl">
            <p className="text-sm font-semibold uppercase tracking-[0.18em] text-amber-300">Симферополь, Крым, Херсонская и Запорожская области</p>
            <h1 className="mt-5 max-w-3xl text-4xl font-black leading-tight tracking-normal sm:text-6xl">
              Техника, электроника и товары для дома под заказ
            </h1>
            <p className="mt-6 max-w-2xl text-lg leading-8 text-zinc-100">
              {storefront.brand} помогает подобрать и заказать товары из большого каталога: бытовую технику,
              климатическое оборудование, электронику, компьютерные комплектующие и полезные товары для дома.
            </p>
            <form action="/search" className="mt-8 flex max-w-2xl flex-col gap-3 rounded-lg bg-white p-2 shadow-xl sm:flex-row">
              <label className="flex min-w-0 flex-1 items-center gap-2 rounded-md bg-zinc-50 px-3 py-3 text-zinc-900">
                <Search className="size-5 shrink-0 text-zinc-400" aria-hidden />
                <input
                  name="q"
                  type="search"
                  placeholder="Введите товар, бренд или SKU"
                  className="min-w-0 flex-1 bg-transparent text-sm placeholder:text-zinc-400"
                />
              </label>
              <button className="inline-flex h-12 items-center justify-center gap-2 rounded-lg bg-amber-400 px-5 text-sm font-bold text-zinc-950 hover:bg-amber-300">
                Найти товар
                <ArrowRight className="size-4" aria-hidden />
              </button>
            </form>
            <div className="mt-6 flex flex-wrap gap-3">
              <Link href="/catalog" className="inline-flex h-12 items-center gap-2 rounded-lg bg-teal-600 px-5 text-sm font-bold text-white hover:bg-teal-500">
                Перейти в каталог
                <ArrowRight className="size-4" aria-hidden />
              </Link>
              <Link href="#how-order" className="inline-flex h-12 items-center rounded-lg border border-white/30 px-5 text-sm font-bold text-white hover:bg-white/10">
                Как оформить заказ
              </Link>
            </div>
          </div>

          <div className="rounded-lg border border-white/15 bg-white/10 p-5 backdrop-blur">
            <p className="text-sm font-semibold uppercase tracking-wide text-amber-200">Связь с магазином</p>
            <div className="mt-4 space-y-3 text-sm text-zinc-100">
              {storefront.phones.map((phone) => (
                <a key={phone} href={phoneHref(phone)} className="flex items-center gap-3 hover:text-amber-200">
                  <Phone className="size-5 text-amber-300" aria-hidden />
                  <span className="font-semibold">{phone}</span>
                </a>
              ))}
              <div className="flex items-start gap-3">
                <MapPin className="mt-0.5 size-5 text-amber-300" aria-hidden />
                <span>{storefront.region}</span>
              </div>
              <div className="flex items-start gap-3">
                <Clock className="mt-0.5 size-5 text-amber-300" aria-hidden />
                <span>
                  {storefront.hours}. {storefront.telegram}.
                </span>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="-mt-12 relative z-10 mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="grid gap-3 rounded-lg border border-zinc-200 bg-white p-3 shadow-lg md:grid-cols-4">
          {[
            ["Большой выбор", "Техника, электроника, климат и товары для дома в одном каталоге", PackageCheck],
            ["Подтверждение заказа", "Менеджер проверит наличие, срок и детали доставки", CheckCircle2],
            ["Доставка по региону", `Работаем: ${storefront.region}`, Truck],
            ["Оплата при получении", "Платите после подтверждения и получения заказа", CreditCard],
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
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
          {featuredCategories.map((category) => (
            <Link key={category.id} href={`/catalog/${category.slug}`} className="rounded-lg border border-zinc-200 bg-white p-5 shadow-sm hover:border-teal-200 hover:shadow-md">
              <p className="text-lg font-bold text-zinc-950">{category.name}</p>
              <p className="mt-2 text-sm text-zinc-500">
                {category.productCount.toLocaleString("ru-RU")} товаров
              </p>
            </Link>
          ))}
        </div>

        {featuredCategories.length ? (
          <div className="mt-8 flex flex-wrap gap-2">
            {featuredCategories.map((category) => (
              <Link key={category.id} href={`/catalog/${category.slug}`} className="rounded-full border border-zinc-200 bg-white px-4 py-2 text-sm font-semibold text-zinc-700 hover:border-teal-300 hover:text-teal-800">
                {category.name}
              </Link>
            ))}
          </div>
        ) : null}
      </section>

      <section id="how-order" className="bg-white py-16">
        <div className="mx-auto grid max-w-7xl gap-8 px-4 sm:px-6 lg:grid-cols-[0.9fr_1.1fr] lg:px-8">
          <div>
            <p className="text-sm font-semibold uppercase tracking-wide text-teal-700">Как заказать</p>
            <h2 className="mt-2 text-3xl font-black tracking-normal text-zinc-950">Оформление без лишней сложности</h2>
            <p className="mt-4 leading-7 text-zinc-600">
              Добавьте товары в корзину и оставьте контакты. Менеджер свяжется с вами, подтвердит наличие,
              срок доставки и итоговые детали заказа.
            </p>
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            {[
              ["1", "Выберите товары", "Используйте поиск, категории и фильтры каталога."],
              ["2", "Добавьте в корзину", "Сайт пересчитает позиции перед оформлением."],
              ["3", "Оставьте контакты", "Нужны имя и телефон, email можно указать по желанию."],
              ["4", "Получите заказ", "Доставка согласуется менеджером, оплата при получении."],
            ].map(([step, title, text]) => (
              <div key={step} className="rounded-lg border border-zinc-200 bg-stone-50 p-5">
                <span className="inline-flex size-9 items-center justify-center rounded-full bg-teal-700 text-sm font-black text-white">{step}</span>
                <h3 className="mt-4 text-lg font-bold text-zinc-950">{title}</h3>
                <p className="mt-2 text-sm leading-6 text-zinc-600">{text}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-7xl px-4 py-16 sm:px-6 lg:px-8">
        <div className="mb-6 flex items-end justify-between gap-4">
          <div>
            <p className="text-sm font-semibold uppercase tracking-wide text-teal-700">Популярное</p>
            <h2 className="mt-2 text-3xl font-black tracking-normal text-zinc-950">Товары, готовые к заказу</h2>
          </div>
          <Link href="/catalog?available=1" className="hidden text-sm font-semibold text-teal-800 hover:text-teal-950 sm:inline">
            Смотреть наличие
          </Link>
        </div>
        <CatalogGrid products={products} />
      </section>

      <section className="bg-zinc-950 py-14 text-white">
        <div className="mx-auto grid max-w-7xl gap-6 px-4 sm:px-6 md:grid-cols-3 lg:px-8">
          <div>
            <p className="text-sm font-semibold uppercase tracking-wide text-amber-300">Доставка и контакты</p>
            <h2 className="mt-2 text-3xl font-black tracking-normal">Работаем по региону</h2>
          </div>
          <div className="space-y-2 text-zinc-200">
            <p className="font-semibold text-white">{storefront.region}</p>
            <p>{storefront.city}</p>
            <p>{storefront.hours}</p>
            <p>{storefront.telegram}</p>
          </div>
          <div className="space-y-2">
            {storefront.phones.map((phone) => (
              <a key={phone} href={phoneHref(phone)} className="block font-semibold text-white hover:text-amber-200">
                {phone}
              </a>
            ))}
            <a href={`mailto:${storefront.email}`} className="block text-zinc-200 hover:text-amber-200">
              {storefront.email}
            </a>
          </div>
        </div>
      </section>
    </>
  );
}
