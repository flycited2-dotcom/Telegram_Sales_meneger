import type { Metadata } from "next";
import { ArrowLeft, CheckCircle2, CreditCard, Truck } from "lucide-react";
import Link from "next/link";
import { notFound } from "next/navigation";
import { AddToCartButton } from "@/components/add-to-cart-button";
import { ProductGallery } from "@/components/product-gallery";
import { StockBadge } from "@/components/stock-badge";
import { decimalToNumber, getProductBySlug } from "@/lib/catalog";
import { publicFulfillmentText } from "@/lib/fulfillment";
import { formatRub } from "@/lib/format";
import { buildProductFacts, productDescriptionText } from "@/lib/product-display";
import { productImageSrc } from "@/lib/product-images";
import { storefront } from "@/lib/storefront";

export const revalidate = 300;

type Props = {
  params: Promise<{ slug: string }>;
};

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { slug } = await params;
  const product = await getProductBySlug(slug);

  if (!product) {
    return {
      title: "Товар не найден",
    };
  }

  const name = product.name ?? product.supplierName;
  return {
    title: product.seoTitle ?? name,
    description:
      product.seoDescription ??
      `${name} в интернет-магазине ${storefront.brand}. Доставка по региону: ${storefront.region}. Оплата при получении.`,
  };
}

export default async function ProductPage({ params }: Props) {
  const { slug } = await params;
  const product = await getProductBySlug(slug);

  if (!product) {
    notFound();
  }

  const name = product.name ?? product.supplierName;
  const price = decimalToNumber(product.retailPrice);
  const fulfillment = publicFulfillmentText({ isAvailable: product.isAvailable && Boolean(price) });
  const categoryName = product.category?.name ?? null;
  const galleryImages = product.images.flatMap((image) => {
    const src = productImageSrc(image);
    return src ? [{ id: image.id, src, alt: name }] : [];
  });
  const facts = buildProductFacts({
    sku: product.sku,
    categoryName,
    vendor: product.vendor,
    part: product.part,
    barcodes: product.barcodes,
    warranty: product.warranty,
    weight: product.weight,
    volume: product.volume,
    deliveryDays: product.deliveryDays,
    multiplicity: product.multiplicity,
  });
  const description = productDescriptionText(product.description, {
    supplierName: product.supplierName,
    name: product.name,
    categoryName,
    vendor: product.vendor,
    warranty: product.warranty,
    deliveryDays: product.deliveryDays,
    multiplicity: product.multiplicity,
  });

  return (
    <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
      <Link href="/catalog" className="inline-flex items-center gap-2 text-sm font-semibold text-zinc-600 hover:text-teal-800">
        <ArrowLeft className="size-4" aria-hidden />
        Назад в каталог
      </Link>

      <div className="mt-6 grid gap-6 xl:grid-cols-[minmax(0,0.95fr)_minmax(360px,0.75fr)_360px]">
        <ProductGallery images={galleryImages} name={name} />

        <section className="min-w-0 rounded-lg border border-zinc-200 bg-white p-6">
          <div className="flex flex-wrap gap-2">
            {product.category ? (
              <Link href={`/catalog/${product.category.slug}`} className="rounded-full bg-stone-100 px-3 py-1 text-xs font-semibold text-zinc-600">
                {product.category.name}
              </Link>
            ) : null}
            <span className="rounded-full bg-teal-50 px-3 py-1 text-xs font-semibold text-teal-800">{fulfillment.deliveryShortLabel}</span>
          </div>
          <p className="mt-5 text-sm font-semibold uppercase tracking-wide text-teal-700">{product.vendor ?? "Товар"}</p>
          <h1 className="mt-2 text-2xl font-black tracking-normal text-zinc-950 lg:text-3xl">{name}</h1>
          <p className="mt-3 text-sm leading-6 text-zinc-600">{description}</p>
          <div className="mt-5 text-sm text-zinc-500">SKU {product.sku}</div>
        </section>

        <aside className="h-fit rounded-lg border border-zinc-200 bg-white p-6 shadow-sm">
          <div className="flex flex-wrap gap-2">
            <StockBadge state={product.stockStatus} label={fulfillment.stockLabel} />
          </div>
          <div className="mt-5 text-4xl font-black text-zinc-950">{price ? formatRub(price) : "Цена уточняется"}</div>
          {product.rrp ? <div className="mt-2 text-sm text-zinc-500">РРЦ: {formatRub(decimalToNumber(product.rrp))}</div> : null}
          <div className="mt-5 rounded-md bg-emerald-50 p-3 text-sm text-emerald-900">
            <p className="font-semibold">{fulfillment.deliveryLabel}</p>
            <p className="mt-1 text-emerald-800">{fulfillment.confirmationNote}</p>
          </div>
          <div className="mt-5">
            <AddToCartButton sku={product.sku} multiplicity={product.multiplicity} disabled={!fulfillment.canOrder || !price} />
          </div>
          {product.multiplicity > 1 ? <p className="mt-3 text-sm text-amber-800">Заказ кратно {product.multiplicity} шт.</p> : null}
          <div className="mt-6 grid gap-2 text-sm text-zinc-600">
            <div className="flex gap-2 rounded-md bg-stone-50 p-3">
              <CreditCard className="size-5 shrink-0 text-teal-700" aria-hidden />
              <span>Оплата после подтверждения заказа менеджером.</span>
            </div>
            <div className="flex gap-2 rounded-md bg-stone-50 p-3">
              <Truck className="size-5 shrink-0 text-teal-700" aria-hidden />
              <span>Доставка по региону: {storefront.region}</span>
            </div>
          </div>
        </aside>
      </div>

      <section className="mt-8 grid gap-6 lg:grid-cols-2">
        <div className="rounded-lg border border-zinc-200 bg-white p-6">
          <h2 className="text-xl font-bold text-zinc-950">О товаре</h2>
          <p className="mt-3 leading-7 text-zinc-600">{description}</p>
        </div>
        <div className="rounded-lg border border-zinc-200 bg-white p-6">
          <h2 className="text-xl font-bold text-zinc-950">Характеристики</h2>
          <dl className="mt-4 divide-y divide-zinc-100 overflow-hidden rounded-md border border-zinc-100">
            {facts.map((fact) => (
              <div key={fact.label} className="grid gap-1 px-4 py-3 text-sm sm:grid-cols-[180px_minmax(0,1fr)] sm:gap-4">
                <dt className="text-zinc-500">{fact.label}</dt>
                <dd className="break-words font-semibold text-zinc-950">{fact.value}</dd>
              </div>
            ))}
          </dl>
        </div>
        <div className="rounded-lg border border-zinc-200 bg-white p-6">
          <h2 className="text-xl font-bold text-zinc-950">Как оформляется заказ</h2>
          <div className="mt-4 space-y-3 text-sm text-zinc-600">
            {[
              "Вы добавляете товар в корзину и отправляете заявку.",
              "Менеджер подтверждает наличие у поставщика, цену и доставку под заказ 7 дней.",
              "Вы оплачиваете заказ после подтверждения.",
            ].map((item) => (
              <div key={item} className="flex gap-3">
                <CheckCircle2 className="size-5 shrink-0 text-teal-700" aria-hidden />
                <span>{item}</span>
              </div>
            ))}
          </div>
        </div>
      </section>
    </div>
  );
}
