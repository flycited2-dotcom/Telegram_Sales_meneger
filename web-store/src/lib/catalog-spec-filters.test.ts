import { describe, expect, it } from "vitest";
import {
  buildCatalogSpecFilterWhere,
  getCatalogSpecFilterOptions,
  normalizeCatalogSpecFilterValues,
} from "@/lib/catalog-spec-filters";

describe("catalog spec filters", () => {
  it("keeps only known spec filters in stable order", () => {
    expect(normalizeCatalogSpecFilterValues(["tv_4k", "unknown", "storage_ssd", "tv_4k"])).toEqual(["tv_4k", "storage_ssd"]);
  });

  it("returns category-relevant filters and keeps active filters visible", () => {
    expect(getCatalogSpecFilterOptions({ categoryName: "Телевизоры", activeFilters: ["storage_ssd"] })).toEqual([
      { key: "tv_4k", label: "4K / UHD" },
      { key: "tv_full_hd", label: "Full HD" },
      { key: "storage_ssd", label: "SSD" },
    ]);
  });

  it("builds AND search conditions for selected spec filters", () => {
    const where = buildCatalogSpecFilterWhere(["tv_4k", "storage_ssd"]);

    expect(where.AND).toHaveLength(2);
    expect(where.AND).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          OR: expect.arrayContaining([
            { name: { contains: "4k", mode: "insensitive" } },
            { supplierName: { contains: "4k", mode: "insensitive" } },
          ]),
        }),
        expect.objectContaining({
          OR: expect.arrayContaining([
            { name: { contains: "ssd", mode: "insensitive" } },
            { supplierName: { contains: "ssd", mode: "insensitive" } },
          ]),
        }),
      ]),
    );
  });
});
