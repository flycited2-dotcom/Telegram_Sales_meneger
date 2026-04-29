"use client";

import { ShoppingCart } from "lucide-react";
import Link from "next/link";
import { useCart } from "@/lib/use-cart";

export function CartLink() {
  const count = useCart().reduce((sum, item) => sum + item.quantity, 0);

  return (
    <Link
      href="/cart"
      className="relative inline-flex h-10 items-center gap-2 rounded-lg bg-zinc-950 px-3 text-sm font-semibold text-white hover:bg-teal-800"
      aria-label="Корзина"
    >
      <ShoppingCart className="size-4" aria-hidden />
      <span className="hidden sm:inline">Корзина</span>
      {count > 0 ? (
        <span className="absolute -right-2 -top-2 flex min-w-5 items-center justify-center rounded-full bg-amber-400 px-1.5 text-xs font-bold text-zinc-950">
          {count}
        </span>
      ) : null}
    </Link>
  );
}
