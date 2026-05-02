import { describe, expect, it } from "vitest";
import { buildProductFacts, productDescriptionText, warrantyLabel } from "@/lib/product-display";

describe("warrantyLabel", () => {
  it("hides zero warranties and formats real warranty values", () => {
    expect(warrantyLabel("0")).toBeNull();
    expect(warrantyLabel("")).toBeNull();
    expect(warrantyLabel("12")).toBe("12 мес.");
    expect(warrantyLabel("официальная гарантия")).toBe("официальная гарантия");
  });
});

describe("buildProductFacts", () => {
  it("returns all useful customer-facing facts from supplier data", () => {
    expect(
      buildProductFacts({
        sku: 123,
        categoryName: "Холодильники",
        vendor: "Samsung",
        part: "ABC-1",
        barcodes: "4601234567890, 4601234567891",
        warranty: "0",
        weight: 2.5,
        volume: 0.009044,
        multiplicity: 2,
        deliveryDays: 3,
      }),
    ).toEqual([
      { label: "SKU", value: "123" },
      { label: "Категория", value: "Холодильники" },
      { label: "Бренд", value: "Samsung" },
      { label: "Партномер", value: "ABC-1" },
      { label: "Штрихкоды", value: "4601234567890, 4601234567891" },
      { label: "Вес", value: "2.5 кг" },
      { label: "Объем упаковки", value: "0.009 м³" },
      { label: "Кратность заказа", value: "2 шт." },
      { label: "Срок поставки", value: "3 дня" },
    ]);
  });
});

describe("productDescriptionText", () => {
  it("uses the real description when it exists and a retail fallback otherwise", () => {
    expect(productDescriptionText("  Подробное описание товара. ")).toBe("Подробное описание товара.");
    expect(productDescriptionText(null)).toContain("Подробное описание пока не заполнено");
  });

  it("builds a customer-facing fallback from available supplier data", () => {
    const description = productDescriptionText(null, {
      supplierName: "Холодильник Weissgauff WRK 2000",
      vendor: "Weissgauff",
      categoryName: "Холодильники",
      warranty: "12",
      deliveryDays: 2,
      multiplicity: 2,
    });

    expect(description).toContain("Холодильник Weissgauff WRK 2000");
    expect(description).toContain("Бренд: Weissgauff");
    expect(description).toContain("Категория: Холодильники");
    expect(description).toContain("Гарантия: 12 мес.");
    expect(description).toContain("Заказ кратно 2 шт.");
    expect(description).toContain("Ориентировочный срок поставки: 2 дня.");
  });
});
