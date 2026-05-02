import { describe, expect, it } from "vitest";
import { extractProductNameSpecs } from "@/lib/product-name-specs";

describe("extractProductNameSpecs", () => {
  it("extracts obvious climate specs from dehumidifier names", () => {
    expect(
      extractProductNameSpecs("Осушитель воздуха Ballu Vector BD-30L VT белый, 30 л/сутки, 4 л, очистка воздуха, гигростат"),
    ).toEqual([
      { label: "Производительность", value: "30 л/сутки" },
      { label: "Объем бака", value: "4 л" },
    ]);
  });

  it("extracts TV diagonal and resolution hints", () => {
    expect(extractProductNameSpecs('Телевизор Samsung UE55CU7100U 55" 4K UHD Smart TV')).toEqual([
      { label: "Диагональ", value: '55"' },
      { label: "Разрешение", value: "4K UHD" },
    ]);
  });

  it("extracts computer memory and storage hints", () => {
    expect(extractProductNameSpecs("Ноутбук Lenovo IdeaPad 15, 16 ГБ RAM, SSD 512 ГБ, Windows 11")).toEqual([
      { label: "Оперативная память", value: "16 ГБ" },
      { label: "Накопитель", value: "SSD 512 ГБ" },
    ]);
  });

  it("does not invent specs for generic names", () => {
    expect(extractProductNameSpecs("Стиральная машина белая")).toEqual([]);
  });
});
