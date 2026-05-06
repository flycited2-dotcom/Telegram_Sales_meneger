import type { Metadata } from "next";
import type { CatalogSort } from "@/lib/catalog-query";
import type { CatalogSpecFilterValue } from "@/lib/catalog-spec-filters";

export type CatalogRobotsFilters = {
  query?: string;
  brand?: string;
  onlyAvailable?: boolean;
  withPhoto?: boolean;
  minPrice?: number;
  maxPrice?: number;
  page: number;
  sort: CatalogSort;
  specFilters: CatalogSpecFilterValue[];
};

export function isIndexableCatalogFilters(filters: CatalogRobotsFilters): boolean {
  return !(
    filters.query ||
    filters.brand ||
    filters.onlyAvailable ||
    filters.withPhoto ||
    filters.minPrice ||
    filters.maxPrice ||
    filters.page > 1 ||
    filters.sort !== "popular" ||
    filters.specFilters.length
  );
}

export function catalogRobotsForFilters(filters: CatalogRobotsFilters): Metadata["robots"] {
  return isIndexableCatalogFilters(filters) ? { index: true, follow: true } : { index: false, follow: true };
}
