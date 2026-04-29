import { prisma } from "@/lib/db";
import { itpRpc } from "@/lib/itp/client";
import { chunk, sleep } from "@/lib/itp/utils";
import type { ItpProductImage } from "@/lib/itp/types";
import { finishSyncLog, sanitizePayload, startSyncLog } from "@/lib/sync-log";

type ProductImagesResponse = {
  product_images: ItpProductImage[];
  total: number;
};

function supplierImageUrl(path: string): string {
  const baseUrl = process.env.ITP_API_BASE_URL ?? "https://b2b.i-t-p.pro";
  const imageSize = process.env.ITP_IMAGE_SIZE ?? "large";
  return `${baseUrl}/${path.replace(/^\/+/, "")}?size=${imageSize}`;
}

export async function syncItpImages(limit = 1000) {
  const log = await startSyncLog("images");

  try {
    const products = await prisma.product.findMany({
      where: {
        hasImage: true,
        isActive: true,
      },
      select: {
        id: true,
        sku: true,
      },
      take: limit,
      orderBy: {
        updatedAt: "desc",
      },
    });
    const productIdsBySku = new Map(products.map((product) => [product.sku, product.id]));
    let processed = 0;
    let failed = 0;

    for (const skus of chunk(products.map((product) => product.sku), 100)) {
      const response = await itpRpc<ProductImagesResponse>({
        request: {
          method: "read_new",
          model: "products_clients_images",
          module: "platform",
        },
        filter: [
          {
            property: "sku",
            operator: "IN",
            value: skus,
          },
        ],
      });

      if (!response.success || !response.data) {
        failed += skus.length;
        continue;
      }

      for (const image of response.data.product_images) {
        const productId = productIdsBySku.get(image.sku);
        if (!productId) {
          failed += 1;
          continue;
        }

        await prisma.productImage.upsert({
          where: {
            supplierImageId: image.id,
          },
          create: {
            supplierImageId: image.id,
            productId,
            sku: image.sku,
            supplierImageUrl: supplierImageUrl(image.url),
            priority: image.priority,
            deleted: image.deleted,
            isPrimary: image.priority <= 100,
          },
          update: {
            supplierImageUrl: supplierImageUrl(image.url),
            priority: image.priority,
            deleted: image.deleted,
            isPrimary: image.priority <= 100,
          },
        });
        processed += 1;
      }

      await sleep(500);
    }

    await finishSyncLog(log.id, {
      status: failed ? "error" : "success",
      total: products.length,
      processed,
      failed,
      message: "Image metadata synchronized. Local file downloading can be enabled as the next stage.",
    });

    return {
      total: products.length,
      processed,
      failed,
    };
  } catch (error) {
    await finishSyncLog(log.id, {
      status: "error",
      message: error instanceof Error ? error.message : "Unknown images sync error",
      failed: 1,
      payload: sanitizePayload(error),
    });
    throw error;
  }
}
