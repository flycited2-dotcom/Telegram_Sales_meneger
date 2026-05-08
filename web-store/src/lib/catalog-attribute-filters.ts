import type { Prisma } from "@prisma/client";

export type CatalogAttributeFilter = {
  key: string;
  normalizedValue: string;
};

export type CatalogAttributeFilterGroup = {
  key: string;
  label: string;
  options: Array<{
    value: string;
    label: string;
    count: number;
  }>;
};

export type CatalogAttributeFacetRow = {
  key: string;
  label: string;
  value: string;
  normalizedValue: string;
  numericValue: number | null;
  unit: string | null;
  count: number;
};

const attributeKeyOrder = [
  "storage_type",
  "storage_capacity",
  "ram",
  "screen_diagonal",
  "resolution",
  "smart_tv",
  "daily_capacity",
  "tank_volume",
  "power_source",
  "power_hp",
  "battery_voltage",
  "battery_capacity",
];

export const catalogAttributeFacetKeys = attributeKeyOrder;

const keyRank = new Map(attributeKeyOrder.map((key, index) => [key, index]));

export function catalogAttributeFilterParam(filter: CatalogAttributeFilter): string {
  return `${filter.key}:${filter.normalizedValue}`;
}

export function normalizeCatalogAttributeFilters(values: Array<string | null | undefined>): CatalogAttributeFilter[] {
  const filters: CatalogAttributeFilter[] = [];
  const seen = new Set<string>();

  for (const value of values) {
    const raw = value?.trim();
    if (!raw || !raw.includes(":")) continue;

    const [key, ...rest] = raw.split(":");
    const normalizedValue = rest.join(":").trim();
    const normalizedKey = key.trim();
    if (!normalizedKey || !normalizedValue || !keyRank.has(normalizedKey)) continue;

    const id = `${normalizedKey}:${normalizedValue}`;
    if (seen.has(id)) continue;
    filters.push({ key: normalizedKey, normalizedValue });
    seen.add(id);
  }

  return filters.slice(0, 24);
}

export function buildCatalogAttributeFilterWhere(filters: CatalogAttributeFilter[]): Prisma.ProductWhereInput {
  if (!filters.length) return {};

  return {
    AND: filters.map((filter) => ({
      attributes: {
        some: {
          key: filter.key,
          normalizedValue: filter.normalizedValue,
        },
      },
    })),
  };
}

function toProductWhereArray(value: Prisma.ProductWhereInput["AND"]): Prisma.ProductWhereInput[] {
  if (!value) return [];

  return Array.isArray(value) ? value : [value];
}

export function buildCatalogAttributeFacetProductWhere(
  baseWhere: Prisma.ProductWhereInput,
  activeFilters: CatalogAttributeFilter[],
  facetKey: string,
): Prisma.ProductWhereInput {
  const otherAttributeWhere = buildCatalogAttributeFilterWhere(activeFilters.filter((filter) => filter.key !== facetKey));
  const otherAttributeAnd = toProductWhereArray(otherAttributeWhere.AND);
  if (!otherAttributeAnd.length) return { ...baseWhere };

  return {
    ...baseWhere,
    AND: [...toProductWhereArray(baseWhere.AND), ...otherAttributeAnd],
  };
}

export function buildCatalogAttributeFilterGroups(
  rows: CatalogAttributeFacetRow[],
  activeFilters: CatalogAttributeFilter[] = [],
): CatalogAttributeFilterGroup[] {
  const active = new Set(activeFilters.map(catalogAttributeFilterParam));
  const groups = new Map<string, CatalogAttributeFilterGroup>();

  for (const row of rows) {
    if (!keyRank.has(row.key)) continue;
    const optionValue = catalogAttributeFilterParam({ key: row.key, normalizedValue: row.normalizedValue });
    if (row.count <= 0 && !active.has(optionValue)) continue;

    const group = groups.get(row.key) ?? { key: row.key, label: row.label, options: [] };
    if (!group.options.some((option) => option.value === optionValue)) {
      group.options.push({
        value: optionValue,
        label: row.value,
        count: row.count,
      });
    }
    groups.set(row.key, group);
  }

  return Array.from(groups.values())
    .sort((left, right) => (keyRank.get(left.key) ?? 999) - (keyRank.get(right.key) ?? 999))
    .map((group) => ({
      ...group,
      options: group.options
        .sort((left, right) => {
          const leftRow = rows.find((row) => catalogAttributeFilterParam(row) === left.value);
          const rightRow = rows.find((row) => catalogAttributeFilterParam(row) === right.value);
          if (leftRow?.numericValue !== null && leftRow?.numericValue !== undefined && rightRow?.numericValue !== null && rightRow?.numericValue !== undefined) {
            return leftRow.numericValue - rightRow.numericValue;
          }
          return left.label.localeCompare(right.label, "ru-RU");
        })
        .slice(0, 16),
    }))
    .filter((group) => group.options.length > 1 || activeFilters.some((filter) => filter.key === group.key));
}
