import type { Prisma } from "@prisma/client";
import { prisma } from "@/lib/db";

const PRODUCTS_PER_PAGE = 24;

export type CatalogQuery = {
  categorySlug?: string;
  query?: string;
  brand?: string;
  available?: boolean;
  minPrice?: number;
  maxPrice?: number;
  page?: number;
};

export function decimalToNumber(value: unknown): number {
  if (value === null || value === undefined) {
    return 0;
  }

  return Number(value);
}

export async function getHomeSnapshot() {
  const [categories, products] = await Promise.all([
    prisma.category.findMany({
      where: {
        isActive: true,
        isVisible: true,
        parentId: null,
      },
      orderBy: {
        name: "asc",
      },
      take: 8,
    }),
    prisma.product.findMany({
      where: {
        isActive: true,
        isVisible: true,
        isAvailable: true,
        retailPrice: {
          not: null,
        },
      },
      include: {
        images: {
          where: {
            deleted: false,
          },
          orderBy: {
            priority: "asc",
          },
          take: 1,
        },
      },
      orderBy: [{ images: { _count: "desc" } }, { updatedAt: "desc" }],
      take: 8,
    }),
  ]);

  return { categories, products };
}

export async function getCatalogPage(query: CatalogQuery) {
  const page = Math.max(query.page ?? 1, 1);
  const where: Prisma.ProductWhereInput = {
    isActive: true,
    isVisible: true,
  };

  let category = null;
  if (query.categorySlug) {
    category = await prisma.category.findFirst({
      where: {
        slug: query.categorySlug,
        isActive: true,
        isVisible: true,
      },
    });

    if (category) {
      where.categoryId = category.id;
    }
  }

  if (query.query) {
    const numericSku = Number(query.query);
    where.OR = [
      { supplierName: { contains: query.query, mode: "insensitive" } },
      { name: { contains: query.query, mode: "insensitive" } },
      { vendor: { contains: query.query, mode: "insensitive" } },
      { part: { contains: query.query, mode: "insensitive" } },
      { barcodes: { contains: query.query, mode: "insensitive" } },
      ...(Number.isFinite(numericSku) ? [{ sku: numericSku }] : []),
    ];
  }

  if (query.brand) {
    where.vendor = query.brand;
  }

  if (query.available) {
    where.isAvailable = true;
  }

  if (query.minPrice || query.maxPrice) {
    where.retailPrice = {
      gte: query.minPrice,
      lte: query.maxPrice,
    };
  }

  const [products, total, categories, brands] = await Promise.all([
    prisma.product.findMany({
      where,
      include: {
        category: true,
        images: {
          where: {
            deleted: false,
          },
          orderBy: {
            priority: "asc",
          },
          take: 1,
        },
      },
      orderBy: [{ images: { _count: "desc" } }, { isAvailable: "desc" }, { updatedAt: "desc" }],
      skip: (page - 1) * PRODUCTS_PER_PAGE,
      take: PRODUCTS_PER_PAGE,
    }),
    prisma.product.count({ where }),
    prisma.category.findMany({
      where: {
        isActive: true,
        isVisible: true,
        parentId: null,
      },
      orderBy: {
        name: "asc",
      },
      take: 40,
    }),
    prisma.product.findMany({
      where: {
        isActive: true,
        isVisible: true,
        vendor: {
          not: null,
        },
      },
      distinct: ["vendor"],
      select: {
        vendor: true,
      },
      orderBy: {
        vendor: "asc",
      },
      take: 80,
    }),
  ]);

  return {
    category,
    products,
    total,
    page,
    perPage: PRODUCTS_PER_PAGE,
    categories,
    brands: brands.map((row) => row.vendor).filter(Boolean) as string[],
  };
}

export async function getProductBySlug(slug: string) {
  return prisma.product.findFirst({
    where: {
      slug,
      isActive: true,
      isVisible: true,
    },
    include: {
      category: true,
      images: {
        where: {
          deleted: false,
        },
        orderBy: {
          priority: "asc",
        },
      },
    },
  });
}

export async function getProductsForQuote(skus: number[]) {
  const products = await prisma.product.findMany({
    where: {
      sku: {
        in: skus,
      },
      isActive: true,
      isVisible: true,
    },
    select: {
      id: true,
      sku: true,
      supplierName: true,
      name: true,
      retailPrice: true,
      supplierPrice: true,
      multiplicity: true,
      isAvailable: true,
    },
  });

  return products.map((product) => ({
    productId: product.id,
    sku: product.sku,
    name: product.name ?? product.supplierName,
    price: decimalToNumber(product.retailPrice),
    supplierPrice: product.supplierPrice ? decimalToNumber(product.supplierPrice) : null,
    multiplicity: product.multiplicity,
    isAvailable: product.isAvailable && Boolean(product.retailPrice),
  }));
}
