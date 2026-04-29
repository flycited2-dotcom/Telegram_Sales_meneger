import Link from "next/link";

export function SiteFooter() {
  return (
    <footer className="border-t border-zinc-200 bg-white">
      <div className="mx-auto grid max-w-7xl gap-6 px-4 py-8 text-sm text-zinc-600 sm:px-6 md:grid-cols-[1.5fr_1fr_1fr] lg:px-8">
        <div>
          <p className="font-semibold text-zinc-950">БытТехОпт</p>
          <p className="mt-2 max-w-xl">
            Витрина бытовой техники, электроники и товаров для дома с локальным каталогом,
            контролем остатков и заказами для менеджера.
          </p>
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
        </div>
        <div className="space-y-2">
          <p>Синхронизация с I-T-P B2B выполняется сервером по расписанию.</p>
          <p>Автоотправка заказов поставщику выключена на первом этапе.</p>
        </div>
      </div>
    </footer>
  );
}
