import { describe, expect, it } from "vitest";
import { isDegradedRetailName } from "@/lib/retail-products";

describe("isDegradedRetailName", () => {
  it("detects damaged-package and demo-condition goods", () => {
    expect(isDegradedRetailName("Поврежденная упаковка клавиатура Defender")).toBe(true);
    expect(isDegradedRetailName("Уценка: холодильник")).toBe(true);
    expect(isDegradedRetailName("Витринный образец телевизор")).toBe(true);
    expect(isDegradedRetailName("Смартфон Samsung Galaxy")).toBe(false);
  });
});
