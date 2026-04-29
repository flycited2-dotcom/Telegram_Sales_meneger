import { CartClient } from "@/app/cart/cart-client";

export default function CartPage() {
  return (
    <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
      <h1 className="mb-6 text-3xl font-black tracking-normal text-zinc-950">Корзина</h1>
      <CartClient />
    </div>
  );
}
