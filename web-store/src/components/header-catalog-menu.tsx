"use client";

import { SlidersHorizontal } from "lucide-react";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";

type HeaderCategory = {
  id: string;
  name: string;
  slug: string;
};

export function HeaderCatalogMenu({ categories }: { categories: HeaderCategory[] }) {
  const [open, setOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;

    function onPointerDown(event: PointerEvent) {
      if (!menuRef.current?.contains(event.target as Node)) {
        setOpen(false);
      }
    }

    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setOpen(false);
      }
    }

    document.addEventListener("pointerdown", onPointerDown);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("pointerdown", onPointerDown);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [open]);

  return (
    <div className="relative" ref={menuRef}>
      <button
        type="button"
        aria-expanded={open}
        aria-label="Открыть каталог"
        onClick={() => setOpen((value) => !value)}
        className="inline-flex h-10 items-center gap-2 rounded-lg px-2 text-sm font-medium text-zinc-700 hover:bg-zinc-100 sm:px-3"
      >
        <SlidersHorizontal className="size-4" aria-hidden />
        <span className="hidden sm:inline">Каталог</span>
      </button>
      {open ? (
        <div className="absolute right-0 top-full z-50 mt-2 max-h-[70vh] w-[calc(100vw-2rem)] overflow-auto rounded-lg border border-zinc-200 bg-white p-3 shadow-xl sm:w-[520px] lg:w-[640px]">
          <Link href="/catalog" onClick={() => setOpen(false)} className="block rounded-md px-3 py-2 text-sm font-bold text-zinc-950 hover:bg-stone-100">
            Весь каталог
          </Link>
          <div className="mt-2 grid gap-1 sm:grid-cols-2">
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
        </div>
      ) : null}
    </div>
  );
}
