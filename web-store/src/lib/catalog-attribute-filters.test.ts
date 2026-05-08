import { describe, expect, it } from "vitest";
import {
  buildCatalogAttributeFilterGroups,
  buildCatalogAttributeFacetProductWhere,
  buildCatalogAttributeFilterWhere,
  buildCatalogAttributeRangeFilterWhere,
  normalizeCatalogAttributeFilters,
  normalizeCatalogAttributeRangeFilters,
} from "@/lib/catalog-attribute-filters";

describe("catalog attribute filters", () => {
  it("normalizes URL attribute filters and removes duplicates", () => {
    expect(normalizeCatalogAttributeFilters(["storage_type:ssd", "bad", "ram:16", "power_source:petrol", "storage_type:ssd", " : "])).toEqual([
      { key: "storage_type", normalizedValue: "ssd" },
      { key: "ram", normalizedValue: "16" },
      { key: "power_source", normalizedValue: "petrol" },
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

  it("normalizes numeric min/max URL filters", () => {
    expect(
      normalizeCatalogAttributeRangeFilters({
        minValues: ["ram:16", "bad", "storage_capacity:512"],
        maxValues: ["ram:64", "screen_diagonal:65", "unknown:1"],
      }),
    ).toEqual([
      { key: "ram", min: 16, max: 64 },
      { key: "storage_capacity", min: 512 },
      { key: "screen_diagonal", max: 65 },
    ]);
  });

  it("builds Prisma numeric attribute range filters", () => {
    expect(buildCatalogAttributeRangeFilterWhere([{ key: "ram", min: 16, max: 64 }])).toEqual({
      AND: [
        {
          attributes: {
            some: {
              key: "ram",
              numericValue: {
                gte: 16,
                lte: 64,
              },
            },
          },
        },
      ],
    });
  });

  it("builds facet count where using other selected attributes but not the current group", () => {
    expect(
      buildCatalogAttributeFacetProductWhere(
        {
          isActive: true,
          AND: [{ isVisible: true }],
        },
        [
          { key: "storage_type", normalizedValue: "ssd" },
          { key: "ram", normalizedValue: "16" },
        ],
        "ram",
      ),
    ).toEqual({
      isActive: true,
      AND: [
        { isVisible: true },
        {
          attributes: {
            some: {
              key: "storage_type",
              normalizedValue: "ssd",
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
