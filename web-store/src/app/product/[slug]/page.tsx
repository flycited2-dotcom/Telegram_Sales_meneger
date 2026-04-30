import type { Metadata } from "next";
import { ArrowLeft, CheckCircle2, CreditCard, Truck } from "lucide-react";
import Link from "next/link";
import { notFound } from "next/navigation";
import { AddToCartButton } from "@/components/add-to-cart-button";
import { ProductImageFallback } from "@/components/product-image-fallback";
import { StockBadge } from "@/components/stock-badge";
import { decimalToNumber, getProductBySlug } from "@/lib/catalog";
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
    title: name,
    description: `${name} в интернет-магазине ${storefront.brand}. Доставка по региону: ${storefront.region}. Оплата при получении.`,
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
  const image = productImageSrc(product.images[0]);
  const facts = buildProductFacts(product);

  return (
    <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
      <Link href="/catalog" className="inline-flex items-center gap-2 text-sm font-semibold text-zinc-600 hover:text-teal-800">
        <ArrowLeft className="size-4" aria-hidden />
        Назад в каталог
      </Link>

      <div className="mt-6 grid gap-8 lg:grid-cols-[minmax(0,1fr)_440px]">
        <div className="rounded-lg border border-zinc-200 bg-white p-4">
          <div className="flex aspect-[4/3] items-center justify-center overflow-hidden rounded-md bg-zinc-100">
            {image ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img src={image} alt={name} className="h-full w-full object-contain" />
            ) : (
              <ProductImageFallback />
            )}
          </div>
        </div>

        <aside className="h-fit rounded-lg border border-zinc-200 bg-white p-6 shadow-sm">
          <div className="flex flex-wrap gap-2">
            <StockBadge state={product.stockStatus} />
            {product.category ? (
              <Link href={`/catalog/${product.category.slug}`} className="rounded-full bg-stone-100 px-3 py-1 text-xs font-semibold text-zinc-600">
                {product.category.name}
              </Link>
            ) : null}
          </div>
          <p className="mt-5 text-sm font-semibold uppercase tracking-wide text-teal-700">{product.vendor ?? "Товар"}</p>
          <h1 className="mt-2 text-3xl font-black tracking-normal text-zinc-950">{name}</h1>
          <div className="mt-4 text-sm text-zinc-500">SKU {product.sku}</div>
          <div className="mt-6 text-4xl font-black text-zinc-950">{price ? formatRub(price) : "Цена уточняется"}</div>
          {product.rrp ? <div className="mt-2 text-sm text-zinc-500">РРЦ: {formatRub(decimalToNumber(product.rrp))}</div> : null}
          <div className="mt-6">
            <AddToCartButton sku={product.sku} multiplicity={product.multiplicity} disabled={!product.isAvailable || !price} />
          </div>
          {product.multiplicity > 1 ? (
            <p className="mt-3 text-sm text-amber-800">Заказ кратно {product.multiplicity} шт.</p>
          ) : null}
          <div className="mt-6 grid gap-2 text-sm text-zinc-600">
            <div className="flex gap-2 rounded-md bg-emerald-50 p-3 text-emerald-800">
              <Truck className="size-5 shrink-0" aria-hidden />
              <span>Доставка по региону: {storefront.region}</span>
            </div>
            <div className="flex gap-2 rounded-md bg-stone-50 p-3">
              <CreditCard className="size-5 shrink-0 text-teal-700" aria-hidden />
              <span>Оплата при получении после подтверждения заказа.</span>
            </div>
          </div>
        </aside>
      </div>

      <section className="mt-8 grid gap-6 lg:grid-cols-2">
        <div className="rounded-lg border border-zinc-200 bg-white p-6">
          <h2 className="text-xl font-bold text-zinc-950">О товаре</h2>
          <p className="mt-3 leading-7 text-zinc-600">{productDescriptionText(product.description)}</p>
        </div>
        <div className="rounded-lg border border-zinc-200 bg-white p-6">
          <h2 className="text-xl font-bold text-zinc-950">Характеристики</h2>
          <dl className="mt-4 grid gap-3 sm:grid-cols-2">
            {facts.map((fact) => (
              <div key={fact.label} className="rounded-md bg-stone-50 p-3 text-sm">
                <dt className="text-zinc-500">{fact.label}</dt>
                <dd className="mt-1 break-words font-semibold text-zinc-950">{fact.value}</dd>
              </div>
            ))}
          </dl>
        </div>
        <div className="rounded-lg border border-zinc-200 bg-white p-6">
          <h2 className="text-xl font-bold text-zinc-950">Как оформляется заказ</h2>
          <div className="mt-4 space-y-3 text-sm text-zinc-600">
            {["Вы добавляете товар в корзину и оставляете контакты.", "Менеджер подтверждает наличие, цену и срок доставки.", "Вы оплачиваете заказ при получении."].map((item) => (
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
