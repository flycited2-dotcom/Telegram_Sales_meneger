import { AdminShell } from "@/components/admin-shell";
import { requireAdmin } from "@/lib/admin-auth";
import { prisma } from "@/lib/db";
import { formatDateTime, formatRub } from "@/lib/format";

export const dynamic = "force-dynamic";

export default async function AdminPage() {
  await requireAdmin();

  const [products, availableProducts, orders, revenue, logs] = await Promise.all([
    prisma.product.count(),
    prisma.product.count({ where: { isAvailable: true } }),
    prisma.order.count(),
    prisma.order.aggregate({ _sum: { total: true } }),
    prisma.syncLog.findMany({ orderBy: { startedAt: "desc" }, take: 5 }),
  ]);

  return (
    <AdminShell title="Обзор">
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {[
          ["Товаров", products],
          ["В наличии", availableProducts],
          ["Заказов", orders],
          ["Оборот", formatRub(Number(revenue._sum.total ?? 0))],
        ].map(([label, value]) => (
          <div key={label as string} className="rounded-lg border border-zinc-200 bg-white p-5 shadow-sm">
            <p className="text-sm font-semibold text-zinc-500">{label as string}</p>
            <p className="mt-3 text-3xl font-black text-zinc-950">{value as string}</p>
          </div>
        ))}
      </div>

      <div className="mt-6 rounded-lg border border-zinc-200 bg-white p-5 shadow-sm">
        <h2 className="text-lg font-bold text-zinc-950">Последние синхронизации</h2>
        <div className="mt-4 divide-y divide-zinc-100">
          {logs.map((log) => (
            <div key={log.id} className="flex flex-wrap items-center justify-between gap-3 py-3 text-sm">
              <span className="font-semibold">{log.type}</span>
              <span className="text-zinc-500">{formatDateTime(log.startedAt)}</span>
              <span className={log.status === "success" ? "text-emerald-700" : log.status === "running" ? "text-amber-700" : "text-red-700"}>
                {log.status}
              </span>
            </div>
          ))}
          {!logs.length ? <p className="py-4 text-sm text-zinc-500">Логов пока нет.</p> : null}
        </div>
      </div>
    </AdminShell>
  );
}
