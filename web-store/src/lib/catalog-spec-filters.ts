import type { Prisma } from "@prisma/client";

export const catalogSpecFilterValues = [
  "daily_capacity",
  "tank_volume",
  "tv_4k",
  "tv_full_hd",
  "storage_ssd",
  "computer_ram",
] as const;

export type CatalogSpecFilterValue = (typeof catalogSpecFilterValues)[number];

export type CatalogSpecFilterOption = {
  key: CatalogSpecFilterValue;
  label: string;
};

type CatalogSpecFilterDefinition = CatalogSpecFilterOption & {
  categoryHints: string[];
  searchTerms: string[];
};

const specFilterDefinitions: CatalogSpecFilterDefinition[] = [
  {
    key: "daily_capacity",
    label: "Производительность, л/сутки",
    categoryHints: ["осушител", "климат", "воздух"],
    searchTerms: ["л/сут", "л / сут"],
  },
  {
    key: "tank_volume",
    label: "Объем бака, л",
    categoryHints: ["осушител", "увлажнител", "мойк", "воздух"],
    searchTerms: ["бак", "резервуар"],
  },
  {
    key: "tv_4k",
    label: "4K / UHD",
    categoryHints: ["телевиз", "тв", "видеотехника"],
    searchTerms: ["4k", "4 k", "uhd"],
  },
  {
    key: "tv_full_hd",
    label: "Full HD",
    categoryHints: ["телевиз", "тв", "видеотехника"],
    searchTerms: ["full hd", "fhd"],
  },
  {
    key: "storage_ssd",
    label: "SSD",
    categoryHints: ["ноутбук", "компьют", "моноблок", "пк", "накопител"],
    searchTerms: ["ssd"],
  },
  {
    key: "computer_ram",
    label: "Оперативная память",
    categoryHints: ["ноутбук", "компьют", "моноблок", "пк", "планшет"],
    searchTerms: ["ram", "оператив"],
  },
];

const specFilterByKey = new Map(specFilterDefinitions.map((definition) => [definition.key, definition]));

export function isCatalogSpecFilterValue(value: string): value is CatalogSpecFilterValue {
  return specFilterByKey.has(value as CatalogSpecFilterValue);
}

export function normalizeCatalogSpecFilterValues(values: Array<string | null | undefined>): CatalogSpecFilterValue[] {
  const normalized: CatalogSpecFilterValue[] = [];

  for (const value of values) {
    if (value && isCatalogSpecFilterValue(value) && !normalized.includes(value)) {
      normalized.push(value);
    }
  }

  return normalized;
}

export function getCatalogSpecFilterOptions({
  categoryName,
  activeFilters = [],
}: {
  categoryName?: string | null;
  activeFilters?: CatalogSpecFilterValue[];
}): CatalogSpecFilterOption[] {
  const normalizedCategory = categoryName?.toLocaleLowerCase("ru-RU") ?? "";
  const active = new Set(activeFilters);
  const matchesCategory = (definition: CatalogSpecFilterDefinition) => {
    return normalizedCategory ? definition.categoryHints.some((hint) => normalizedCategory.includes(hint)) : false;
  };

  const options = specFilterDefinitions.filter((definition) => matchesCategory(definition) || active.has(definition.key));
  const visibleOptions = options.length ? options : specFilterDefinitions.slice(0, 4);

  return visibleOptions.map(({ key, label }) => ({ key, label }));
}

export function getCatalogSpecFilterLabel(value: CatalogSpecFilterValue): string {
  return specFilterByKey.get(value)?.label ?? value;
}

export function buildCatalogSpecFilterWhere(values: CatalogSpecFilterValue[]): Prisma.ProductWhereInput {
  const filters = normalizeCatalogSpecFilterValues(values);
  if (!filters.length) {
    return {};
  }

  return {
    AND: filters.flatMap((value) => {
      const definition = specFilterByKey.get(value);
      if (!definition) return [];

      return [
        {
          OR: definition.searchTerms.flatMap((term) => [
            { name: { contains: term, mode: "insensitive" as const } },
            { supplierName: { contains: term, mode: "insensitive" as const } },
          ]),
        },
      ];
    }),
  };
}
