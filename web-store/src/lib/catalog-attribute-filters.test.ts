import { describe, expect, it } from "vitest";
import {
  buildCatalogAttributeFilterGroups,
  buildCatalogAttributeFilterWhere,
  normalizeCatalogAttributeFilters,
} from "@/lib/catalog-attribute-filters";

describe("catalog attribute filters", () => {
  it("normalizes URL attribute filters and removes duplicates", () => {
    expect(normalizeCatalogAttributeFilters(["storage_type:ssd", "bad", "ram:16", "storage_type:ssd", " : "])).toEqual([
      { key: "storage_type", normalizedValue: "ssd" },
      { key: "ram", normalizedValue: "16" },
    ]);
  });

  it("builds Prisma AND conditions for selected attributes", () => {
    expect(buildCatalogAttributeFilterWhere([{ key: "storage_type", normalizedValue: "ssd" }, { key: "ram", normalizedValue: "16" }])).toEqual({
      AND: [
        {
          attributes: {
            some: {
              key: "storage_type",
              normalizedValue: "ssd",
            },
          },
        },
        {
          attributes: {
            some: {
              key: "ram",
              normalizedValue: "16",
            },
          },
        },
      ],
    });
  });

  it("builds grouped facet options from ProductAttribute counts", () => {
    expect(
      buildCatalogAttributeFilterGroups(
        [
          { key: "ram", label: "Оперативная память", value: "8 ГБ", normalizedValue: "8", numericValue: 8, unit: "ГБ", count: 4 },
          { key: "ram", label: "Оперативная память", value: "16 ГБ", normalizedValue: "16", numericValue: 16, unit: "ГБ", count: 9 },
          { key: "storage_type", label: "Тип накопителя", value: "SSD", normalizedValue: "ssd", numericValue: null, unit: null, count: 10 },
          { key: "storage_type", label: "Тип накопителя", value: "HDD", normalizedValue: "hdd", numericValue: null, unit: null, count: 2 },
          { key: "unknown", label: "Unknown", value: "x", normalizedValue: "x", numericValue: null, unit: null, count: 10 },
        ],
        [{ key: "ram", normalizedValue: "16" }],
      ),
    ).toEqual([
      {
        key: "storage_type",
        label: "Тип накопителя",
        options: [
          { value: "storage_type:hdd", label: "HDD", count: 2 },
          { value: "storage_type:ssd", label: "SSD", count: 10 },
        ],
      },
      {
        key: "ram",
        label: "Оперативная память",
        options: [
          { value: "ram:8", label: "8 ГБ", count: 4 },
          { value: "ram:16", label: "16 ГБ", count: 9 },
        ],
      },
    ]);
  });
});
