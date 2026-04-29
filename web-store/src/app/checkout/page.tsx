import { CheckoutClient } from "@/app/checkout/checkout-client";

export default function CheckoutPage() {
  return (
    <div className="mx-auto max-w-3xl px-4 py-8 sm:px-6 lg:px-8">
      <p className="text-sm font-semibold uppercase tracking-wide text-teal-700">Оформление</p>
      <h1 className="mt-2 text-3xl font-black tracking-normal text-zinc-950">Контактные данные</h1>
      <p className="mb-6 mt-3 text-zinc-600">
        Перед созданием заказа сервер заново проверит товары, цены, наличие и кратность.
      </p>
      <CheckoutClient />
    </div>
  );
}
