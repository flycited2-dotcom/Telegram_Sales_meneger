import type { Product, ProductImage } from "@prisma/client";
import Link from "next/link";
import { AddToCartButton } from "@/components/add-to-cart-button";
import { StockBadge } from "@/components/stock-badge";
import { decimalToNumber } from "@/lib/catalog";
import { formatRub } from "@/lib/format";

type ProductCardProduct = Product & {
  images?: ProductImage[];
};

export function ProductCard({ product }: { product: ProductCardProduct }) {
  const name = product.name ?? product.supplierName;
  const image = product.images?.[0]?.localImageUrl ?? product.images?.[0]?.supplierImageUrl;
  const price = decimalToNumber(product.retailPrice);

  return (
    <article className="group flex min-h-[420px] flex-col rounded-lg border border-zinc-200 bg-white p-3 shadow-sm transition hover:-translate-y-0.5 hover:border-teal-200 hover:shadow-md">
      <Link href={`/product/${product.slug}`} className="block">
        <div className="flex aspect-square items-center justify-center overflow-hidden rounded-md bg-zinc-100">
          {image ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img src={image} alt={name} className="h-full w-full object-contain" />
          ) : (
            <div className="flex h-full w-full flex-col items-center justify-center bg-[linear-gradient(135deg,#f4f4f5,#e7f5f1,#fff7ed)] px-6 text-center">
              <span className="text-4xl font-black text-zinc-300">БТО</span>
              <span className="mt-2 text-xs font-medium text-zinc-500">фото скоро появится</span>
            </div>
          )}
        </div>
      </Link>
      <div className="mt-4 flex flex-1 flex-col">
        <div className="flex items-start justify-between gap-3">
          <p className="text-xs font-semibold uppercase tracking-wide text-teal-700">{product.vendor ?? "Товар"}</p>
          <StockBadge state={product.stockStatus} />
        </div>
        <Link href={`/product/${product.slug}`} className="mt-2 line-clamp-3 text-sm font-semibold leading-5 text-zinc-950 hover:text-teal-800">
          {name}
        </Link>
        <div className="mt-3 text-xs text-zinc-500">SKU {product.sku}</div>
        {product.multiplicity > 1 ? (
          <div className="mt-2 rounded-md bg-amber-50 px-2 py-1 text-xs text-amber-800">Заказ кратно {product.multiplicity} шт.</div>
        ) : null}
        <div className="mt-auto pt-4">
          <div className="mb-3 text-xl font-bold text-zinc-950">{price ? formatRub(price) : "Цена уточняется"}</div>
          <AddToCartButton
            sku={product.sku}
            multiplicity={product.multiplicity}
            disabled={!product.isAvailable || !price}
            compact
          />
        </div>
      </div>
    </article>
  );
}
