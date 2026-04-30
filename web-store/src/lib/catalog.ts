import type { Prisma } from "@prisma/client";
import { unstable_cache } from "next/cache";
import { buildCategoryTree, collectDescendantCategoryIds, type CategoryTreeItem, type FlatCategory } from "@/lib/catalog-tree";
import { prisma } from "@/lib/db";
import { isDegradedRetailName, normalRetailNameWhere } from "@/lib/retail-products";

const PRODUCTS_PER_PAGE = 24;
const STOREFRONT_CACHE_SECONDS = 300;

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

const getActiveCategories = unstable_cache(async (): Promise<FlatCategory[]> => {
  return prisma.category.findMany({
    where: {
      isActive: true,
      isVisible: true,
    },
    select: {
      id: true,
      parentId: true,
      name: true,
      slug: true,
    },
    orderBy: {
      name: "asc",
    },
  });
}, ["active-catalog-categories"], { revalidate: STOREFRONT_CACHE_SECONDS, tags: ["catalog"] });

export const getHeaderCategories = unstable_cache(async () => {
  if (!process.env.DATABASE_URL) {
    return [];
  }

  const categories = await prisma.category.findMany({
    where: {
      isActive: true,
      isVisible: true,
      parentId: null,
    },
    select: {
      id: true,
      name: true,
      slug: true,
    },
    orderBy: {
      name: "asc",
    },
    take: 12,
  });

  return categories.filter((category) => !isDegradedRetailName(category.name));
}, ["header-categories"], { revalidate: STOREFRONT_CACHE_SECONDS, tags: ["catalog"] });

const getCategoryProductCounts = unstable_cache(async () => {
  return prisma.product.groupBy({
    by: ["categoryId"],
    where: {
      categoryId: {
        not: null,
      },
      isActive: true,
      isVisible: true,
    },
    _count: {
      _all: true,
    },
  });
}, ["catalog-category-product-counts"], { revalidate: STOREFRONT_CACHE_SECONDS, tags: ["catalog"] });

async function getCatalogCategoryTree(categories: FlatCategory[]): Promise<CategoryTreeItem[]> {
  const counts = await getCategoryProductCounts();

  return buildCategoryTree(
    categories,
    new Map(counts.flatMap((row) => (row.categoryId ? [[row.categoryId, row._count._all]] : []))),
  );
}

export const getCategoryBySlug = unstable_cache(async (slug: string): Promise<FlatCategory | null> => {
  return prisma.category.findFirst({
    where: {
      slug,
      isActive: true,
      isVisible: true,
    },
    select: {
      id: true,
      parentId: true,
      name: true,
      slug: true,
    },
  });
}, ["category-by-slug"], { revalidate: STOREFRONT_CACHE_SECONDS, tags: ["catalog"] });

function getExcludedCategoryIds(categories: FlatCategory[]): string[] {
  return Array.from(
    new Set(
      categories
        .filter((category) => isDegradedRetailName(category.name))
        .flatMap((category) => collectDescendantCategoryIds(categories, category.id)),
    ),
  );
}

export const getHomeSnapshot = unstable_cache(async () => {
  if (!process.env.DATABASE_URL) {
    return { categories: [], products: [] };
  }

  const allCategories = await getActiveCategories();
  const excludedCategoryIds = getExcludedCategoryIds(allCategories);
  const [categories, products] = await Promise.all([
    getCatalogCategoryTree(allCategories),
    prisma.product.findMany({
      where: {
        isActive: true,
        isVisible: true,
        isAvailable: true,
        ...(excludedCategoryIds.length
          ? {
              categoryId: {
                notIn: excludedCategoryIds,
              },
            }
          : {}),
        retailPrice: {
          not: null,
        },
        ...normalRetailNameWhere(),
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
}, ["home-snapshot"], { revalidate: STOREFRONT_CACHE_SECONDS, tags: ["catalog", "products"] });

const getCatalogBrands = unstable_cache(async (where: Prisma.ProductWhereInput) => {
  return prisma.product.findMany({
    where,
    distinct: ["vendor"],
    select: {
      vendor: true,
    },
    orderBy: {
      vendor: "asc",
    },
    take: 80,
  });
}, ["catalog-brands"], { revalidate: STOREFRONT_CACHE_SECONDS, tags: ["catalog", "products"] });

export async function getCatalogPage(query: CatalogQuery) {
  const page = Math.max(query.page ?? 1, 1);
  const allCategories = await getActiveCategories();
  const excludedCategoryIds = getExcludedCategoryIds(allCategories);
  const excludedCategoryIdSet = new Set(excludedCategoryIds);
  const baseWhere: Prisma.ProductWhereInput = {
    isActive: true,
    isVisible: true,
  };

  let category: FlatCategory | null = null;
  if (query.categorySlug) {
    category = allCategories.find((item) => item.slug === query.categorySlug) ?? null;

    if (category) {
      const categoryIds = collectDescendantCategoryIds(allCategories, category.id).filter((id) => !excludedCategoryIdSet.has(id));
      baseWhere.categoryId = {
        in: categoryIds.length ? categoryIds : ["__empty_category__"],
      };
    }
  } else if (excludedCategoryIds.length) {
    baseWhere.categoryId = {
      notIn: excludedCategoryIds,
    };
  }

  const filteredWhere: Prisma.ProductWhereInput = { ...baseWhere };
  if (query.query) {
    const numericSku = Number(query.query);
    filteredWhere.OR = [
      { supplierName: { contains: query.query, mode: "insensitive" } },
      { name: { contains: query.query, mode: "insensitive" } },
      { vendor: { contains: query.query, mode: "insensitive" } },
      { part: { contains: query.query, mode: "insensitive" } },
      { barcodes: { contains: query.query, mode: "insensitive" } },
      ...(Number.isFinite(numericSku) ? [{ sku: numericSku }] : []),
    ];
  }

  if (query.available) {
    filteredWhere.isAvailable = true;
  }

  if (query.minPrice || query.maxPrice) {
    const priceFilter: Prisma.DecimalFilter = {};
    if (query.minPrice) priceFilter.gte = query.minPrice;
    if (query.maxPrice) priceFilter.lte = query.maxPrice;
    filteredWhere.retailPrice = priceFilter;
  }

  const brandWhere: Prisma.ProductWhereInput = {
    ...filteredWhere,
    vendor: {
      not: null,
    },
  };

  if (query.brand) {
    filteredWhere.vendor = query.brand;
  }

  const [products, total, categories, brands] = await Promise.all([
    prisma.product.findMany({
      where: filteredWhere,
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
      orderBy: [{ images: { _count: "desc" } }, { isAvailable: "desc" }, { retailPrice: "desc" }, { updatedAt: "desc" }],
      skip: (page - 1) * PRODUCTS_PER_PAGE,
      take: PRODUCTS_PER_PAGE,
    }),
    prisma.product.count({ where: filteredWhere }),
    getCatalogCategoryTree(allCategories),
    getCatalogBrands(brandWhere),
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

export const getProductBySlug = unstable_cache(async (slug: string) => {
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
}, ["product-by-slug"], { revalidate: STOREFRONT_CACHE_SECONDS, tags: ["products"] });

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
