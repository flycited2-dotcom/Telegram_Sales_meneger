import { describe, expect, it } from "vitest";
import {
  buildCatalogSpecFilterWhere,
  getCatalogSpecFilterOptions,
  normalizeCatalogSpecFilterValues,
} from "@/lib/catalog-spec-filters";

describe("catalog spec filters", () => {
  it("keeps only known spec filters in stable order", () => {
    expect(normalizeCatalogSpecFilterValues(["tv_4k", "unknown", "storage_ssd", "tv_4k", "fridge_no_frost"])).toEqual([
      "tv_4k",
      "storage_ssd",
      "fridge_no_frost",
    ]);
  });

  it("returns category-relevant filters and keeps active filters visible", () => {
    expect(getCatalogSpecFilterOptions({ categoryName: "Телевизоры", activeFilters: ["storage_ssd"] })).toEqual([
      { key: "tv_4k", label: "4K / UHD", groupLabel: "Телевизоры" },
      { key: "tv_full_hd", label: "Full HD", groupLabel: "Телевизоры" },
      { key: "tv_smart", label: "Smart TV", groupLabel: "Телевизоры" },
      { key: "storage_ssd", label: "SSD", groupLabel: "Компьютеры" },
    ]);
  });

  it("returns a balanced starter set when no category is selected", () => {
    expect(getCatalogSpecFilterOptions({})).toEqual([
      { key: "tv_4k", label: "4K / UHD", groupLabel: "Телевизоры" },
      { key: "tv_smart", label: "Smart TV", groupLabel: "Телевизоры" },
      { key: "storage_ssd", label: "SSD", groupLabel: "Компьютеры" },
      { key: "fridge_no_frost", label: "No Frost", groupLabel: "Холодильники" },
      { key: "ac_inverter", label: "Инверторные", groupLabel: "Климат" },
      { key: "washer_narrow", label: "Узкие", groupLabel: "Стиральные машины" },
    ]);
  });

  it("returns richer appliance filters for refrigerator categories", () => {
    expect(getCatalogSpecFilterOptions({ categoryName: "Холодильники и морозильники" })).toEqual([
      { key: "fridge_no_frost", label: "No Frost", groupLabel: "Холодильники" },
      { key: "fridge_two_chamber", label: "Двухкамерные", groupLabel: "Холодильники" },
      { key: "freezer", label: "Морозильники", groupLabel: "Холодильники" },
    ]);
  });

  it("returns climate filters for air conditioner categories", () => {
    expect(getCatalogSpecFilterOptions({ categoryName: "Кондиционеры сплит-системы" })).toEqual([
      { key: "ac_split_system", label: "Сплит-системы", groupLabel: "Климат" },
      { key: "ac_inverter", label: "Инверторные", groupLabel: "Климат" },
    ]);
  });

  it("returns air treatment filters for humidifier and dehumidifier categories", () => {
    expect(getCatalogSpecFilterOptions({ categoryName: "Осушители и увлажнители воздуха" })).toEqual([
      { key: "air_purification", label: "Очистка воздуха", groupLabel: "Климат" },
      { key: "daily_capacity", label: "Производительность, л/сутки", groupLabel: "Климат" },
      { key: "tank_volume", label: "Объем бака, л", groupLabel: "Климат" },
    ]);
  });

  it("builds AND search conditions for selected spec filters", () => {
    const where = buildCatalogSpecFilterWhere(["tv_4k", "storage_ssd", "fridge_no_frost"]);

    expect(where.AND).toHaveLength(3);
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
        expect.objectContaining({
          OR: expect.arrayContaining([
            { name: { contains: "no frost", mode: "insensitive" } },
            { supplierName: { contains: "no frost", mode: "insensitive" } },
          ]),
        }),
      ]),
    );
  });
});
