import type { MetadataRoute } from "next";
import { prisma } from "@/lib/db";
import { normalRetailNameWhere } from "@/lib/retail-products";
import { storefront } from "@/lib/storefront";

export const revalidate = 3600;

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const now = new Date();
  const staticRoutes: MetadataRoute.Sitemap = [
    {
      url: storefront.siteUrl,
      lastModified: now,
      changeFrequency: "daily",
      priority: 1,
    },
    {
      url: `${storefront.siteUrl}/catalog`,
      lastModified: now,
      changeFrequency: "daily",
      priority: 0.95,
    },
    {
      url: `${storefront.siteUrl}/cart`,
      lastModified: now,
      changeFrequency: "monthly",
      priority: 0.4,
    },
    {
      url: `${storefront.siteUrl}/privacy`,
      lastModified: now,
      changeFrequency: "yearly",
      priority: 0.3,
    },
  ];

  if (!process.env.DATABASE_URL) {
    return staticRoutes;
  }

  try {
    const [categories, products] = await Promise.all([
      prisma.category.findMany({
        where: {
          isActive: true,
          isVisible: true,
        },
        select: {
          slug: true,
          updatedAt: true,
        },
        orderBy: {
          updatedAt: "desc",
        },
        take: 300,
      }),
      prisma.product.findMany({
        where: {
          isActive: true,
          isVisible: true,
          isAvailable: true,
          retailPrice: {
            not: null,
          },
          ...normalRetailNameWhere(),
        },
        select: {
          slug: true,
          updatedAt: true,
        },
        orderBy: [{ hasImage: "desc" }, { updatedAt: "desc" }],
        take: 700,
      }),
    ]);

    return [
      ...staticRoutes,
      ...categories.map((category) => ({
        url: `${storefront.siteUrl}/catalog/${category.slug}`,
        lastModified: category.updatedAt,
        changeFrequency: "weekly" as const,
        priority: 0.75,
      })),
      ...products.map((product) => ({
        url: `${storefront.siteUrl}/product/${product.slug}`,
        lastModified: product.updatedAt,
        changeFrequency: "weekly" as const,
        priority: 0.65,
      })),
    ];
  } catch {
    return staticRoutes;
  }
}
