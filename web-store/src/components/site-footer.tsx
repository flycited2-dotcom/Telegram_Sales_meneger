import Link from "next/link";
import { phoneHref, storefront } from "@/lib/storefront";

export function SiteFooter() {
  return (
    <footer className="border-t border-zinc-200 bg-white">
      <div className="mx-auto grid max-w-7xl gap-6 px-4 py-8 text-sm text-zinc-600 sm:px-6 md:grid-cols-[1.5fr_1fr_1fr] lg:px-8">
        <div>
          <p className="font-semibold text-zinc-950">{storefront.brand}</p>
          <p className="mt-2 max-w-xl">
            Интернет-магазин бытовой техники, электроники, климатического оборудования и товаров для дома.
            Помогаем оформить заказ и доставку по региону: {storefront.region}.
          </p>
          <p className="mt-2">Оплата при получении после подтверждения заказа.</p>
        </div>
        <div className="space-y-2">
          <Link href="/catalog" className="block hover:text-zinc-950">
            Каталог
          </Link>
          <Link href="/cart" className="block hover:text-zinc-950">
            Корзина
          </Link>
          <Link href="/checkout" className="block hover:text-zinc-950">
            Оформление
          </Link>
          <Link href="/privacy" className="block hover:text-zinc-950">
            Персональные данные
          </Link>
        </div>
        <div className="space-y-2">
          <p className="font-semibold text-zinc-950">{storefront.city}</p>
          {storefront.phones.map((phone) => (
            <a key={phone} href={phoneHref(phone)} className="block hover:text-zinc-950">
              {phone}
            </a>
          ))}
          <a href={`mailto:${storefront.email}`} className="block hover:text-zinc-950">
            {storefront.email}
          </a>
          <p>{storefront.telegram}</p>
          <p>{storefront.hours}</p>
        </div>
      </div>
    </footer>
  );
}
