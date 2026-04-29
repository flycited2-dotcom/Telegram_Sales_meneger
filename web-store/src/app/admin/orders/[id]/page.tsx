import { OrderStatus } from "@prisma/client";
import { notFound } from "next/navigation";
import { updateOrderStatusAction } from "@/app/admin/actions";
import { AdminShell } from "@/components/admin-shell";
import { requireAdmin } from "@/lib/admin-auth";
import { prisma } from "@/lib/db";
import { formatRub } from "@/lib/format";

export const dynamic = "force-dynamic";

type Props = {
  params: Promise<{ id: string }>;
};

export default async function AdminOrderPage({ params }: Props) {
  await requireAdmin();
  const { id } = await params;
  const order = await prisma.order.findUnique({
    where: { id },
    include: { items: true },
  });

  if (!order) notFound();

  return (
    <AdminShell title={order.orderNumber}>
      <div className="grid gap-6 lg:grid-cols-[1fr_320px]">
        <div className="rounded-lg border border-zinc-200 bg-white p-5 shadow-sm">
          <h2 className="text-lg font-bold">Состав заказа</h2>
          <div className="mt-4 divide-y divide-zinc-100">
            {order.items.map((item) => (
              <div key={item.id} className="grid gap-2 py-3 text-sm sm:grid-cols-[1fr_80px_120px]">
                <span>SKU {item.sku} · {item.name}</span>
                <span>{item.quantity} шт.</span>
                <strong>{formatRub(Number(item.total))}</strong>
              </div>
            ))}
          </div>
          <div className="mt-4 rounded-md bg-stone-50 p-4 text-right text-2xl font-black">{formatRub(Number(order.total))}</div>
        </div>
        <aside className="h-fit rounded-lg border border-zinc-200 bg-white p-5 shadow-sm">
          <p className="font-bold">{order.customerName}</p>
          <p className="mt-2 text-sm text-zinc-600">{order.phone}</p>
          {order.email ? <p className="text-sm text-zinc-600">{order.email}</p> : null}
          {order.comment ? <p className="mt-3 rounded-md bg-stone-50 p-3 text-sm text-zinc-600">{order.comment}</p> : null}
          <form action={updateOrderStatusAction} className="mt-5 grid gap-2">
            <input type="hidden" name="id" value={order.id} />
            <select name="status" defaultValue={order.status} className="h-10 rounded-lg border border-zinc-200 px-3 text-sm">
              {Object.values(OrderStatus).map((status) => (
                <option key={status} value={status}>
                  {status}
                </option>
              ))}
            </select>
            <button className="h-10 rounded-lg bg-teal-700 text-sm font-bold text-white hover:bg-teal-800">Обновить статус</button>
          </form>
        </aside>
      </div>
    </AdminShell>
  );
}
