import { describe, expect, it } from "vitest";
import { parseCatalogSearchParams, parsePositiveNumberParam } from "@/lib/catalog-query";

describe("parsePositiveNumberParam", () => {
  it("keeps positive numeric values and discards invalid values", () => {
    expect(parsePositiveNumberParam("12990")).toBe(12990);
    expect(parsePositiveNumberParam("12,5")).toBe(12.5);
    expect(parsePositiveNumberParam("0")).toBeUndefined();
    expect(parsePositiveNumberParam("-1")).toBeUndefined();
    expect(parsePositiveNumberParam("text")).toBeUndefined();
  });
});

describe("parseCatalogSearchParams", () => {
  it("normalizes catalog filters from URL search params", () => {
    expect(
      parseCatalogSearchParams({
        q: " холодильник ",
        brand: ["ATLANT", "Indesit", "ATLANT", " "],
        available: "1",
        photo: "1",
        minPrice: "10000",
        maxPrice: "50000",
        page: "3",
        sort: "price_asc",
        spec: ["tv_4k", "unknown", "storage_ssd"],
      }),
    ).toEqual({
      query: "холодильник",
      brand: "ATLANT",
      brands: ["ATLANT", "Indesit"],
      onlyAvailable: true,
      withPhoto: true,
      minPrice: 10000,
      maxPrice: 50000,
      page: 3,
      sort: "price_asc",
      specFilters: ["tv_4k", "storage_ssd"],
    });
  });

  it("uses safe defaults for empty filters and bad page values", () => {
    expect(parseCatalogSearchParams({ q: " ", page: "-4", minPrice: "bad", sort: "unknown" })).toEqual({
      query: undefined,
      brand: undefined,
      brands: [],
      onlyAvailable: false,
      withPhoto: false,
      minPrice: undefined,
      maxPrice: undefined,
      page: 1,
      sort: "popular",
      specFilters: [],
    });
  });
});
