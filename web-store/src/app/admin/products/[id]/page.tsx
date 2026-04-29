import { notFound } from "next/navigation";
import { updateProductAction } from "@/app/admin/actions";
import { AdminShell } from "@/components/admin-shell";
import { requireAdmin } from "@/lib/admin-auth";
import { prisma } from "@/lib/db";

export const dynamic = "force-dynamic";

type Props = {
  params: Promise<{ id: string }>;
};

export default async function AdminProductEditPage({ params }: Props) {
  await requireAdmin();
  const { id } = await params;
  const product = await prisma.product.findUnique({ where: { id } });

  if (!product) notFound();

  return (
    <AdminShell title={`Товар SKU ${product.sku}`}>
      <form action={updateProductAction} className="grid max-w-3xl gap-4 rounded-lg border border-zinc-200 bg-white p-6 shadow-sm">
        <input type="hidden" name="id" value={product.id} />
        <label className="flex items-center gap-2 text-sm font-medium text-zinc-700">
          <input type="checkbox" name="isVisible" defaultChecked={product.isVisible} className="size-4 accent-teal-700" />
          Показывать на витрине
        </label>
        <label className="grid gap-2 text-sm font-medium text-zinc-700">
          SEO/витринное название
          <input name="name" defaultValue={product.name ?? ""} className="h-10 rounded-lg border border-zinc-200 px-3" />
        </label>
        <label className="grid gap-2 text-sm font-medium text-zinc-700">
          Ручная цена
          <input name="manualPrice" defaultValue={product.manualPrice?.toString() ?? ""} className="h-10 rounded-lg border border-zinc-200 px-3" />
        </label>
        <label className="grid gap-2 text-sm font-medium text-zinc-700">
          SEO title
          <input name="seoTitle" defaultValue={product.seoTitle ?? ""} className="h-10 rounded-lg border border-zinc-200 px-3" />
        </label>
        <label className="grid gap-2 text-sm font-medium text-zinc-700">
          SEO description
          <input name="seoDescription" defaultValue={product.seoDescription ?? ""} className="h-10 rounded-lg border border-zinc-200 px-3" />
        </label>
        <label className="grid gap-2 text-sm font-medium text-zinc-700">
          Описание
          <textarea name="description" defaultValue={product.description ?? ""} rows={7} className="rounded-lg border border-zinc-200 px-3 py-2" />
        </label>
        <button className="h-11 rounded-lg bg-teal-700 text-sm font-bold text-white hover:bg-teal-800">Сохранить</button>
      </form>
    </AdminShell>
  );
}
