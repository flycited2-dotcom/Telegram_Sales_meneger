import type { Prisma } from "@prisma/client";

export const catalogSpecFilterValues = [
  "ac_split_system",
  "ac_inverter",
  "air_purification",
  "daily_capacity",
  "tank_volume",
  "fridge_no_frost",
  "fridge_two_chamber",
  "freezer",
  "tv_4k",
  "tv_full_hd",
  "tv_smart",
  "storage_ssd",
  "computer_ram",
  "laptop",
  "gaming",
  "washer_narrow",
  "washer_inverter",
  "washer_front_load",
] as const;

export type CatalogSpecFilterValue = (typeof catalogSpecFilterValues)[number];

export type CatalogSpecFilterOption = {
  key: CatalogSpecFilterValue;
  label: string;
  groupLabel: string;
  count?: number;
};

type CatalogSpecFilterDefinition = CatalogSpecFilterOption & {
  categoryHints: string[];
  searchTerms: string[];
  attributeFilters?: Prisma.ProductWhereInput[];
};

const specFilterDefinitions: CatalogSpecFilterDefinition[] = [
  {
    key: "ac_split_system",
    label: "Сплит-системы",
    groupLabel: "Климат",
    categoryHints: ["кондиционер", "сплит", "климат"],
    searchTerms: ["сплит", "split"],
  },
  {
    key: "ac_inverter",
    label: "Инверторные",
    groupLabel: "Климат",
    categoryHints: ["кондиционер", "сплит", "климат"],
    searchTerms: ["инвертор", "inverter"],
  },
  {
    key: "air_purification",
    label: "Очистка воздуха",
    groupLabel: "Климат",
    categoryHints: ["климат", "воздух", "очистител", "увлажнител", "осушител"],
    searchTerms: ["очист", "фильтр", "иониз"],
  },
  {
    key: "daily_capacity",
    label: "Производительность, л/сутки",
    groupLabel: "Климат",
    categoryHints: ["осушител", "климат", "воздух"],
    searchTerms: ["л/сут", "л / сут"],
    attributeFilters: [
      {
        attributes: {
          some: {
            key: "daily_capacity",
          },
        },
      },
    ],
  },
  {
    key: "tank_volume",
    label: "Объем бака, л",
    groupLabel: "Климат",
    categoryHints: ["осушител", "увлажнител", "мойк", "воздух"],
    searchTerms: ["бак", "резервуар"],
    attributeFilters: [
      {
        attributes: {
          some: {
            key: "tank_volume",
          },
        },
      },
    ],
  },
  {
    key: "fridge_no_frost",
    label: "No Frost",
    groupLabel: "Холодильники",
    categoryHints: ["холодильник", "морозильник"],
    searchTerms: ["no frost", "nofrost", "ноу фрост"],
  },
  {
    key: "fridge_two_chamber",
    label: "Двухкамерные",
    groupLabel: "Холодильники",
    categoryHints: ["холодильник"],
    searchTerms: ["двухкамер", "2-камер", "2 камер"],
  },
  {
    key: "freezer",
    label: "Морозильники",
    groupLabel: "Холодильники",
    categoryHints: ["холодильник", "морозильник"],
    searchTerms: ["морозиль", "freezer"],
  },
  {
    key: "tv_4k",
    label: "4K / UHD",
    groupLabel: "Телевизоры",
    categoryHints: ["телевиз", "тв", "видеотехника"],
    searchTerms: ["4k", "4 k", "uhd"],
    attributeFilters: [
      {
        attributes: {
          some: {
            key: "resolution",
            normalizedValue: {
              in: ["4k", "4k_uhd"],
            },
          },
        },
      },
    ],
  },
  {
    key: "tv_full_hd",
    label: "Full HD",
    groupLabel: "Телевизоры",
    categoryHints: ["телевиз", "тв", "видеотехника"],
    searchTerms: ["full hd", "fhd"],
    attributeFilters: [
      {
        attributes: {
          some: {
            key: "resolution",
            normalizedValue: "full_hd",
          },
        },
      },
    ],
  },
  {
    key: "tv_smart",
    label: "Smart TV",
    groupLabel: "Телевизоры",
    categoryHints: ["телевиз", "тв", "видеотехника"],
    searchTerms: ["smart", "смарт"],
    attributeFilters: [
      {
        attributes: {
          some: {
            key: "smart_tv",
            normalizedValue: "yes",
          },
        },
      },
    ],
  },
  {
    key: "storage_ssd",
    label: "SSD",
    groupLabel: "Компьютеры",
    categoryHints: ["ноутбук", "компьют", "моноблок", "пк", "накопител"],
    searchTerms: ["ssd"],
    attributeFilters: [
      {
        attributes: {
          some: {
            key: "storage_type",
            normalizedValue: "ssd",
          },
        },
      },
    ],
  },
  {
    key: "computer_ram",
    label: "Оперативная память",
    groupLabel: "Компьютеры",
    categoryHints: ["ноутбук", "компьют", "моноблок", "пк", "планшет"],
    searchTerms: ["ram", "оператив"],
    attributeFilters: [
      {
        attributes: {
          some: {
            key: "ram",
          },
        },
      },
    ],
  },
  {
    key: "laptop",
    label: "Ноутбуки",
    groupLabel: "Компьютеры",
    categoryHints: ["ноутбук", "компьют", "планшет"],
    searchTerms: ["ноутбук", "laptop"],
  },
  {
    key: "gaming",
    label: "Игровые",
    groupLabel: "Компьютеры",
    categoryHints: ["ноутбук", "компьют", "пк", "приставк"],
    searchTerms: ["игров", "gaming", "game"],
  },
  {
    key: "washer_narrow",
    label: "Узкие",
    groupLabel: "Стиральные машины",
    categoryHints: ["стираль", "сушиль"],
    searchTerms: ["узк", "slim"],
  },
  {
    key: "washer_inverter",
    label: "Инверторные",
    groupLabel: "Стиральные машины",
    categoryHints: ["стираль", "сушиль"],
    searchTerms: ["инвертор", "inverter"],
  },
  {
    key: "washer_front_load",
    label: "Фронтальная загрузка",
    groupLabel: "Стиральные машины",
    categoryHints: ["стираль", "сушиль"],
    searchTerms: ["фронтал", "front"],
  },
];

const specFilterByKey = new Map(specFilterDefinitions.map((definition) => [definition.key, definition]));
const defaultSpecFilterValues: CatalogSpecFilterValue[] = [
  "tv_4k",
  "tv_smart",
  "storage_ssd",
  "fridge_no_frost",
  "ac_inverter",
  "washer_narrow",
];

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
  const visibleOptions = options.length
    ? options
    : defaultSpecFilterValues.flatMap((value) => {
        const definition = specFilterByKey.get(value);
        return definition ? [definition] : [];
      });

  return visibleOptions.map(({ key, label, groupLabel }) => ({ key, label, groupLabel }));
}

export function getCatalogSpecFilterLabel(value: CatalogSpecFilterValue): string {
  return specFilterByKey.get(value)?.label ?? value;
}

export function attachCatalogSpecFilterCounts(
  options: CatalogSpecFilterOption[],
  counts: Map<CatalogSpecFilterValue, number>,
): CatalogSpecFilterOption[] {
  return options.map((option) => ({
    ...option,
    count: counts.get(option.key) ?? 0,
  }));
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
          OR: [
            ...(definition.attributeFilters ?? []),
            ...definition.searchTerms.flatMap((term) => [
              { name: { contains: term, mode: "insensitive" as const } },
              { supplierName: { contains: term, mode: "insensitive" as const } },
            ]),
          ],
        },
      ];
    }),
  };
}
