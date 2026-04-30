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
  it("returns only useful customer-facing facts", () => {
    expect(
      buildProductFacts({
        sku: 123,
        vendor: "Samsung",
        part: "ABC-1",
        warranty: "0",
        weight: 2.5,
        volume: null,
        deliveryDays: 3,
      }),
    ).toEqual([
      { label: "SKU", value: "123" },
      { label: "Бренд", value: "Samsung" },
      { label: "Партномер", value: "ABC-1" },
      { label: "Вес", value: "2.5 кг" },
      { label: "Срок поставки", value: "3 дня" },
    ]);
  });
});

describe("productDescriptionText", () => {
  it("uses the real description when it exists and a retail fallback otherwise", () => {
    expect(productDescriptionText("  Подробное описание товара. ")).toBe("Подробное описание товара.");
    expect(productDescriptionText(null)).toContain("Подробное описание пока не заполнено");
  });
});
