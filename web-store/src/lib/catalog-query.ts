export type CatalogSearchParams = Record<string, string | string[] | undefined>;

export type ParsedCatalogSearchParams = {
  query?: string;
  brand?: string;
  onlyAvailable: boolean;
  minPrice?: number;
  maxPrice?: number;
  page: number;
};

export function firstParam(value: string | string[] | undefined): string | undefined {
  return Array.isArray(value) ? value[0] : value;
}

export function parsePositiveNumberParam(value: string | string[] | undefined): number | undefined {
  const raw = firstParam(value)?.trim().replace(",", ".");
  if (!raw) return undefined;

  const parsed = Number(raw);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : undefined;
}

function trimmedParam(value: string | string[] | undefined): string | undefined {
  const trimmed = firstParam(value)?.trim();
  return trimmed || undefined;
}

export function parseCatalogSearchParams(params: CatalogSearchParams): ParsedCatalogSearchParams {
  const page = Math.max(Math.floor(parsePositiveNumberParam(params.page) ?? 1), 1);

  return {
    query: trimmedParam(params.q),
    brand: trimmedParam(params.brand),
    onlyAvailable: firstParam(params.available) === "1",
    minPrice: parsePositiveNumberParam(params.minPrice),
    maxPrice: parsePositiveNumberParam(params.maxPrice),
    page,
  };
}
