import { describe, expect, it } from "vitest";
import { buildProductAttributeRows } from "@/lib/product-attribute-backfill";

describe("buildProductAttributeRows", () => {
  it("uses public product name before supplier name and keeps product ownership fields", () => {
    expect(
      buildProductAttributeRows({
        productId: "product-1",
        name: 'Телевизор Samsung UE55CU7100U 55" 4K UHD Smart TV',
        supplierName: "Поставщик: другое название",
      }),
    ).toEqual([
      {
        productId: "product-1",
        key: "screen_diagonal",
        label: "Диагональ",
        value: '55"',
        normalizedValue: "55",
        numericValue: 55,
        unit: "дюйм",
        source: "name",
      },
      {
        productId: "product-1",
        key: "resolution",
        label: "Разрешение",
        value: "4K UHD",
        normalizedValue: "4k_uhd",
        numericValue: null,
        unit: null,
        source: "name",
      },
      {
        productId: "product-1",
        key: "smart_tv",
        label: "Smart TV",
        value: "Да",
        normalizedValue: "yes",
        numericValue: null,
        unit: null,
        source: "name",
      },
    ]);
  });

  it("falls back to supplier name when public name is empty", () => {
    expect(
      buildProductAttributeRows({
        productId: "product-2",
        name: null,
        supplierName: "Ноутбук Lenovo IdeaPad 15, 16 ГБ RAM, SSD 512 ГБ",
      }).map((row) => row.key),
    ).toEqual(["ram", "storage_type", "storage_capacity"]);
  });
});
