"use client";

import { SlidersHorizontal } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

type HeaderCategory = {
  id: string;
  name: string;
  slug: string;
};

export function HeaderCatalogMenu({ categories }: { categories: HeaderCategory[] }) {
  const [open, setOpen] = useState(false);

  return (
    <div className="relative">
      <button
        type="button"
        aria-expanded={open}
        aria-label="Открыть каталог"
        onClick={() => setOpen((value) => !value)}
        className="inline-flex h-10 items-center gap-2 rounded-lg px-3 text-sm font-medium text-zinc-700 hover:bg-zinc-100"
      >
        <SlidersHorizontal className="size-4" aria-hidden />
        <span className="hidden sm:inline">Каталог</span>
      </button>
      {open ? (
        <div className="absolute right-0 top-full z-50 mt-2 w-[calc(100vw-2rem)] rounded-lg border border-zinc-200 bg-white p-3 shadow-xl sm:w-96">
          <Link href="/catalog" onClick={() => setOpen(false)} className="block rounded-md px-3 py-2 text-sm font-bold text-zinc-950 hover:bg-stone-100">
            Весь каталог
          </Link>
          {categories.map((category) => (
            <Link
              key={category.id}
              href={`/catalog/${category.slug}`}
              onClick={() => setOpen(false)}
              className="block rounded-md px-3 py-2 text-sm font-medium leading-5 text-zinc-700 hover:bg-stone-100"
            >
              {category.name}
            </Link>
          ))}
        </div>
      ) : null}
    </div>
  );
}
